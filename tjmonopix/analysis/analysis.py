import numpy as np
import tables as tb
import logging
import numba
from tqdm import tqdm

from tjmonopix.analysis import analysis_utils as au
from tjmonopix.analysis import interpreter
from pixel_clusterizer.clusterizer import HitClusterizer

logging.basicConfig(
    format="%(asctime)s - [%(name)-8s] - %(levelname)-7s %(message)s")
loglevel = logging.INFO


class Analysis():
    def __init__(self, raw_data_file=None, cluster_hits=False):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(loglevel)

        self.build_event = False

        self.raw_data_file = raw_data_file
        self.chunk_size = 10000000
        self.cluster_hits = cluster_hits
        if self.cluster_hits:
            self._setup_clusterizer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def _setup_clusterizer(self):
        ''' Define data structure and settings for hit clusterizer package '''

        # Define all field names and data types
        hit_fields = {'event_number': 'event_number',
                      'timestamp': 'frame',
                      'col': 'column',
                      'row': 'row',
                      'le': 'le',
                      'te': 'te',
                      'cnt': 'cnt',
                      'tot': 'charge',
                      'scan_param_id': 'scan_param_id'
                      }

        hit_description = [('event_number', '<i8'),
                           ('timestamp', '<i8'),
                           ('col', '<u1'),
                           ('row', '<u2'),
                           ('le', '<u1'),
                           ('te', '<u1'),
                           ('cnt', '<u4'),
                           ('tot', '<u1'),
                           ('scan_param_id', '<i4')]

        cluster_fields = {'event_number': 'event_number',
                          'column': 'column',
                          'row': 'row',
                          'size': 'n_hits',
                          'id': 'ID',
                          'tot': 'charge',
                          'scan_param_id': 'scan_param_id',
                          'seed_col': 'seed_column',
                          'seed_row': 'seed_row',
                          'mean_col': 'mean_column',
                          'mean_row': 'mean_row'}

        cluster_description = [('event_number', '<i8'),
                               ('id', '<u2'),
                               ('size', '<u2'),
                               ('tot', '<u1'),
                               ('seed_col', '<u1'),
                               ('seed_row', '<u2'),
                               ('mean_col', '<f4'),
                               ('mean_row', '<f4'),
                               ('dist_col', '<u4'),
                               ('dist_row', '<u4'),
                               ('cluster_shape', '<i8'),
                               ('scan_param_id', '<i4')]

#         # Add TDC data entries
#         if self.analyze_tdc:
#             hit_fields.update({'tdc_value': 'tdc_value', 'tdc_timestamp': 'tdc_timestamp', 'tdc_status': 'tdc_status'})
#             hit_description.extend([('tdc_value', 'u2'), ('tdc_timestamp', 'u2'), ('tdc_status', 'u1')])
#             cluster_fields.update({'tdc_value': 'tdc_value', 'tdc_timestamp': 'tdc_timestamp', 'tdc_status': 'tdc_status'})
#             cluster_description.extend([('tdc_value', '<u2'), ('tdc_timestamp', '<u2'), ('tdc_status', '<u1')])

        hit_dtype = np.dtype(hit_description)
        self.cluster_dtype = np.dtype(cluster_description)

        if self.cluster_hits:  # Allow analysis without clusterizer installed
            # Define end of cluster function to calculate cluster shape
            # and cluster distance in column and row direction
            @numba.njit
            def _end_of_cluster_function(hits, clusters, cluster_size,
                                         cluster_hit_indices, cluster_index,
                                         cluster_id, charge_correction,
                                         noisy_pixels, disabled_pixels,
                                         seed_hit_index):
                hit_arr = np.zeros((15, 15), dtype=np.bool_)
                center_col = hits[cluster_hit_indices[0]].column
                center_row = hits[cluster_hit_indices[0]].row
                hit_arr[7, 7] = 1
                min_col = hits[cluster_hit_indices[0]].column
                max_col = hits[cluster_hit_indices[0]].column
                min_row = hits[cluster_hit_indices[0]].row
                max_row = hits[cluster_hit_indices[0]].row
                for i in cluster_hit_indices[1:]:
                    if i < 0:  # Not used indices = -1
                        break
                    diff_col = np.int32(hits[i].column - center_col)
                    diff_row = np.int32(hits[i].row - center_row)
                    if np.abs(diff_col) < 8 and np.abs(diff_row) < 8:
                        hit_arr[7 + hits[i].column - center_col,
                                7 + hits[i].row - center_row] = 1
                    if hits[i].column < min_col:
                        min_col = hits[i].column
                    if hits[i].column > max_col:
                        max_col = hits[i].column
                    if hits[i].row < min_row:
                        min_row = hits[i].row
                    if hits[i].row > max_row:
                        max_row = hits[i].row

                if max_col - min_col < 8 and max_row - min_row < 8:
                    # Make 8x8 array
                    col_base = 7 + min_col - center_col
                    row_base = 7 + min_row - center_row
                    cluster_arr = hit_arr[col_base:col_base + 8,
                                          row_base:row_base + 8]
                    # Finally calculate cluster shape
                    # uint64 desired, but numexpr and others limited to int64
                    if cluster_arr[7, 7] == 1:
                        cluster_shape = np.int64(-1)
                    else:
                        cluster_shape = np.int64(
                            au.calc_cluster_shape(cluster_arr))
                else:
                    # Cluster is exceeding 8x8 array
                    cluster_shape = np.int64(-1)

                clusters[cluster_index].cluster_shape = cluster_shape
                clusters[cluster_index].dist_col = max_col - min_col + 1
                clusters[cluster_index].dist_row = max_row - min_row + 1

            def end_of_cluster_function(hits, clusters, cluster_size,
                                        cluster_hit_indices, cluster_index,
                                        cluster_id, charge_correction,
                                        noisy_pixels, disabled_pixels,
                                        seed_hit_index):
                _end_of_cluster_function(hits, clusters, cluster_size,
                                         cluster_hit_indices, cluster_index,
                                         cluster_id, charge_correction,
                                         noisy_pixels, disabled_pixels,
                                         seed_hit_index)

            # Define end of cluster function for calculating TDC related cluster properties
            def end_of_cluster_function_tdc(hits, clusters, cluster_size,
                                            cluster_hit_indices, cluster_index,
                                            cluster_id, charge_correction,
                                            noisy_pixels, disabled_pixels,
                                            seed_hit_index):
                _end_of_cluster_function(hits, clusters, cluster_size,
                                         cluster_hit_indices, cluster_index,
                                         cluster_id, charge_correction,
                                         noisy_pixels, disabled_pixels,
                                         seed_hit_index)

                # Calculate cluster TDC and cluster TDC status
                cluster_tdc = 0
                cluster_tdc_status = 1  # valid
                for j in range(clusters[cluster_index].n_hits):
                    hit_index = cluster_hit_indices[j]
                    cluster_tdc += hits[hit_index].tdc_value
                    cluster_tdc_status &= (hits[hit_index].tdc_status == 0x00000001)  # check for valid TDC status
                clusters[cluster_index].tdc_value = cluster_tdc
                clusters[cluster_index].tdc_status = cluster_tdc_status

            # Initialize clusterizer with custom hit/cluster fields
            self.clz = HitClusterizer(
                hit_fields=hit_fields,
                hit_dtype=hit_dtype,
                cluster_fields=cluster_fields,
                cluster_dtype=self.cluster_dtype,
                min_hit_charge=0,
                max_hit_charge=64,
                column_cluster_distance=4,
                row_cluster_distance=4,
                frame_cluster_distance=10,
                ignore_same_hits=True)

#             # Set end_of_cluster function for shape and distance calculation
#             if self.analyze_tdc:
#                 # If analyze TDC data, set also end of cluster function for calculating TDC properties
#                 self.clz.set_end_of_cluster_function(end_of_cluster_function_tdc)
#             else:
            self.clz.set_end_of_cluster_function(end_of_cluster_function)

    def analyze_data(self):
        self.analyzed_data_file = self.raw_data_file[:-3] + '_interpreted.h5'
        hit_dtype = [('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('cnt', '<u4'), ('timestamp', '<i8'), ('scan_param_id', '<i4')]
        if self.cluster_hits:
            hit_dtype.append(('tot', 'u1'))
            hit_dtype.append(('event_number', '<i8'))
        with tb.open_file(self.raw_data_file) as in_file:
            n_words = in_file.root.raw_data.shape[0]
            meta_data = in_file.root.meta_data[:]

            if meta_data.shape[0] == 0:
                self.logger.warning('Data is empty. Skip analysis!')
                return

            self.n_params = np.amax(meta_data["scan_param_id"])

            with tb.open_file(self.analyzed_data_file, "w") as out_file:
                hit_table = None

                if self.cluster_hits:
                    cluster_table = out_file.create_table(
                        out_file.root, name='Cluster',
                        description=self.cluster_dtype,
                        title='Cluster',
                        filters=tb.Filters(complib='blosc',
                                           complevel=5,
                                           fletcher32=False))
                    hist_cs_size = np.zeros(shape=(100, ), dtype=np.uint32)
                    hist_cs_tot = np.zeros(shape=(100, ), dtype=np.uint32)
                    hist_cs_shape = np.zeros(shape=(300, ), dtype=np.int32)

                start = 0

                data_interpreter = interpreter.RawDataInterpreter(chunk_size=self.chunk_size)
                pbar = tqdm(total=n_words)
                while start < n_words:
                    tmp_end = min(n_words, start + self.chunk_size)
                    raw_data = in_file.root.raw_data[start:tmp_end]
                    hit_buffer = np.zeros(shape=self.chunk_size, dtype=hit_dtype)

                    hit_dat = data_interpreter.interpret(raw_data, meta_data, hit_buffer)

                    if self.cluster_hits:
                        hit_dat["tot"] = ((hit_dat["te"] - hit_dat["le"]) & 0x3F) + 1  # Add one to get also hits where LE = TE
                        hit_dat["event_number"] = hit_dat["timestamp"]

                    if hit_table is None:
                        hit_table = out_file.create_table(
                            where=out_file.root,
                            name="Hits",
                            description=hit_dat.dtype,
                            expectedrows=self.chunk_size,
                            title='hit_data',
                            filters=tb.Filters(
                                complib='blosc',
                                complevel=5,
                                fletcher32=False))

                    hit_table.append(hit_dat)
                    hit_table.flush()

                    if self.cluster_hits:
                        _, cluster = self.clz.cluster_hits(hit_dat)
#                         if self.analyze_tdc:
#                             # Select only clusters where all hits have a valid TDC status
#                             cluster_table.append(cluster[cluster['tdc_status'] == 1])
#                         else:
                        cluster_table.append(cluster)
                        # Create actual cluster hists
                        cs_size = np.bincount(cluster['size'],
                                              minlength=100)[:100]
                        cs_tot = np.bincount(cluster['tot'],
                                             minlength=100)[:100]
                        sel = np.logical_and(cluster['cluster_shape'] > 0,
                                             cluster['cluster_shape'] < 300)
                        cs_shape = np.bincount(cluster['cluster_shape'][sel],
                                               minlength=300)[:300]
                        # Add to total hists
                        hist_cs_size += cs_size.astype(np.uint32)
                        hist_cs_tot += cs_tot.astype(np.uint32)
                        hist_cs_shape += cs_shape.astype(np.uint32)

                    pbar.update(tmp_end - start)
                    start = tmp_end
                pbar.close()
                # TODO: Copy all attributes properly to output_file, maybe own table
                out_file.root.Hits.attrs.scan_id = in_file.root.meta_data.attrs.scan_id
                self._create_additional_hit_data()
                self.logger.info("{:d} errors occured during analysis".format(data_interpreter.get_error_count()))

#                 self._create_additional_hit_data()
                if self.cluster_hits:
                    self._create_additional_cluster_data(hist_cs_size, hist_cs_tot, hist_cs_shape)

    def _create_additional_hit_data(self):
        with tb.open_file(self.analyzed_data_file, 'r+') as out_file:
            hits = out_file.root.Hits[:]
            scan_id = out_file.root.Hits.attrs["scan_id"]

            hist_occ = au.occ_hist2d(hits)

            out_file.create_carray(out_file.root,
                                   name='HistOcc',
                                   title='Occupancy Histogram',
                                   obj=hist_occ,
                                   filters=tb.Filters(complib='blosc',
                                                      complevel=5,
                                                      fletcher32=False))

            # TODO: ToT Histogram?

            if scan_id in ["threshold_scan"]:
                n_injections = 100  # TODO: get from run configuration
                scan_param_range = np.arange(0, self.n_params + 1, 1)  # TODO: get from run configuration

                hist_scurve = au.scurve_hist3d(hits, scan_param_range)

                out_file.create_carray(out_file.root,
                                       name="HistSCurve",
                                       title="Scurve Data",
                                       obj=hist_scurve,
                                       filters=tb.Filters(complib='blosc',
                                                          complevel=5,
                                                          fletcher32=False))

                ave_tots = au.tot_ave3d(hits, scan_param_range)
                ave_tots = np.array(ave_tots, dtype=np.float32) / np.array(hist_scurve, dtype=np.float32)
                out_file.create_carray(out_file.root,
                                       name="ToTAve",
                                       title="ToT average",
                                       obj=ave_tots,
                                       filters=tb.Filters(complib='blosc',
                                                          complevel=5,
                                                          fletcher32=False))

                self.threshold_map, self.noise_map, self.chi2_map = au.fit_scurves_multithread(
                    hist_scurve.reshape(112 * 224, self.n_params + 1), scan_param_range, n_injections=n_injections, invert_x=False
                )

                out_file.create_carray(out_file.root, name='ThresholdMap', title='Threshold Map', obj=self.threshold_map,
                                       filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False))
                out_file.create_carray(out_file.root, name='NoiseMap', title='Noise Map', obj=self.noise_map,
                                       filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False))
                out_file.create_carray(out_file.root, name='Chi2Map', title='Chi2 / ndf Map', obj=self.chi2_map,
                                       filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False))

    def _create_additional_cluster_data(self, hist_cs_size, hist_cs_tot, hist_cs_shape):
        '''
            Store cluster histograms in analyzed data file
        '''
        with tb.open_file(self.analyzed_data_file, 'r+') as out_file:
            out_file.create_carray(out_file.root,
                                   name='HistClusterSize',
                                   title='Cluster Size Histogram',
                                   obj=hist_cs_size,
                                   filters=tb.Filters(complib='blosc',
                                                      complevel=5,
                                                      fletcher32=False))
            out_file.create_carray(out_file.root,
                                   name='HistClusterTot',
                                   title='Cluster ToT Histogram',
                                   obj=hist_cs_tot,
                                   filters=tb.Filters(complib='blosc',
                                                      complevel=5,
                                                      fletcher32=False))
            out_file.create_carray(out_file.root,
                                   name='HistClusterShape',
                                   title='Cluster Shape Histogram',
                                   obj=hist_cs_shape,
                                   filters=tb.Filters(complib='blosc',
                                                      complevel=5,
                                                      fletcher32=False))
