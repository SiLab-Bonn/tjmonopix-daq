import numpy as np
import tables as tb
import logging
from tqdm import tqdm

from tjmonopix.analysis import analysis_utils as au


class Analysis():
    def __init__(self, raw_data_file=None):

        self.logger = logging.getLogger(self.__class__.__name__)
#         self.logger.setLevel(loglevel)

        self.raw_data_file = raw_data_file
        self.chunk_size = 1000000

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def analyze_data(self, data_format=0x0, put_scan_param_id=False):
        self.analyzed_data_file = self.raw_data_file[:-3] + '_interpreted.h5'

        with tb.open_file(self.raw_data_file) as in_file:
            n_words = in_file.root.raw_data.shape[0]
            meta_data = in_file.root.meta_data[:]

            if meta_data.shape[0] == 0:
                self.logger.warning('Data is empty. Skip analysis!')
                return

            # Set initial values for interpretation and prepare output array for hits
            (hits, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_cnt, ts_flg, ts2_timestamp,
             ts2_tot, ts2_cnt, ts2_flg, ts3_timestamp, ts3_cnt, ts3_flg
             ) = au.init_outs(n_hits=self.chunk_size * 4)

            with tb.open_file(self.analyzed_data_file, "w") as out_file:
                hit_table = out_file.create_table(out_file.root, name="Hits",
                                                  description=hits.dtype,
                                                  expectedrows=self.chunk_size,
                                                  title='hit_data',
                                                  filters=tb.Filters(complib='blosc',
                                                                     complevel=5,
                                                                     fletcher32=False))

                # TODO: Copy all attributes properly to output_file, maybe own table
                out_file.root.Hits.attrs.scan_id = in_file.root.meta_data.attrs.scan_id

                start = 0
                pbar = tqdm(total=n_words)

                while start < n_words:
                    tmpend = min(n_words, start + 1000000)
                    raw_data = in_file.root.raw_data[start:tmpend]
                    (err, hit_dat, r_i, col, row, le, te, noise, timestamp, rx_flg,
                     ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
                     ) = au.interpret_data(
                        raw_data, hits, col, row, le, te, noise, timestamp, rx_flg,
                        ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt, data_format)
                    if err == 0:
                        pass
                    elif err == 1 or err == 2 or err == 3:
#                         print "tjmonopix data broken", err, start, r_i, hex(
#                             raw_data[r_i]), "flg=", rx_flg
#                         if data_format & 0x8 == 0x8:
#                             for i in range(max(0, r_i - 100), min(r_i + 100, tmpend - start - 6), 6):
#                                 print hex(
#                                     raw[start + i]), hex(raw[start + i + 1]), hex(raw[start + i + 2]),
#                                 print hex(
#                                     raw[start + i + 3]), hex(raw[start + i + 4]), hex(raw[start + i + 5])

                        # Error in TJMonoPix data occured, reset rx_flg and timestamp and proceed with next word
                        rx_flg = 0
                        timestamp = np.uint64(0x0)
                    elif err == 4 or err == 5 or err == 6:
                        print "timestamp data broken", err, start, r_i, hex(
                            raw_data[r_i]), "flg=", ts_flg, ts_timestamp
                        ts_flg = 0
                        ts_timestamp = np.uint64(0x0)
                        ts_pre = ts_timestamp
                    elif err == 7:
                        print "trash data", err, start, r_i, hex(raw_data[r_i])
                    elif err == 8 or err == 9 or err == 10:
                        print "ts2_timestamp data broken", err, start, r_i, hex(
                            raw_data[r_i]), "flg=", ts2_flg, ts2_timestamp
                        ts2_flg = 0
                    hit_dat['idx'] = hit_dat['idx'] + start

                    if put_scan_param_id is True:
                        hit_dat = au.correlate_scan_ids(hit_dat, meta_data)

                    hit_table.append(hit_dat)
                    hit_table.flush()
                    start = start + r_i + 1

                    pbar.update(r_i)
                pbar.close()

                self._create_additional_hit_data()

    def _create_additional_hit_data(self):
        with tb.open_file(self.analyzed_data_file, 'r+') as out_file:
            hits = out_file.root.Hits[:]
            scan_id = out_file.root.Hits.attrs["scan_id"]  # TODO: Read from proper dictionary (or similar)

            hist_occ = au.occ_hist2d(hits)

            out_file.create_carray(out_file.root,
                                   name='HistOcc',
                                   title='Occupancy Histogram',
                                   obj=hist_occ,
                                   filters=tb.Filters(complib='blosc',
                                                      complevel=5,
                                                      fletcher32=False))
            