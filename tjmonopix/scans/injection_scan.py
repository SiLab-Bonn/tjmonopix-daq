import time
import numpy as np
import tables as tb
import yaml
import numba

from tjmonopix.scan_base import ScanBase
from tjmonopix.analysis import analysis
from tjmonopix.analysis import plotting

from tqdm import tqdm

from matplotlib import pyplot as plt


class InjectionScan(ScanBase):

    def scan(self, **kwargs):
        """ List of kwargs
            pix: list of pixel
            n_mask_pix: number of pixels injected at onece
            injlist: list of inj (inj_high-inj_low)
            phaselist: list of phase
            with_tdc: get timestamp of mon (mon will be enabled)
        """

        # Get parameters from kwargs
        n_mask_pix = min(kwargs.pop("n_mask_pix"), 1)
        injlist = kwargs.pop("inj_list", [65])  # Use default charge if not given
        phaselist = kwargs.pop("phaselist", [self.dut["inj"].get_phase()])  # Use default phase if not given
        with_tdc = kwargs.pop("with_tdc")

        # Stop readout and clean FIFO
        self.dut.stop_all()
        self.dut['fifo'].reset()

        # Write scan_id (type) to file
        self.meta_data_table.attrs.scan_id = "injection_scan"

        # Why is this needed?
        self.dut['data_rx'].set_en(True)
        self.dut['fifo'].get_data()
        self.dut['data_rx'].set_en(False)

        # Setup injection
        repeat = 100
        delay = 5000
        width = 350
        phase = 0

        self.dut['inj'].set_delay(delay)
        self.dut['inj'].set_width(width)
        self.dut['inj'].set_repeat(repeat)
        self.dut['inj'].set_phase(phase)
        self.dut['inj'].set_en(0)

        self.dut.set_vl_dacunits(35)
        self.dut.set_vh_dacunits(35)
        self.dut.write_conf()

        # Compute cartesian product to make list of all possible combinations of inj and phase
        param_list = np.reshape(np.stack(np.meshgrid(injlist, phaselist), axis=2), [-1, 2])





        param_dtype = [("scan_param_id", "<i4"), ("pix", "<i2", (n_mask_pix, 2))]

        # Create a table for scan_params
        description = np.zeros((1,), dtype=param_dtype).dtype
        self.scan_param_table = self.h5_file.create_table(
            self.h5_file.root,
            name='scan_parameters',
            title='scan_parameters',
            description=description,
            filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False)
        )
        self.kwargs.append("inj_list")
        self.kwargs.append(yaml.dump(param_list[:, 0]))
        self.kwargs.append("phaselist")
        self.kwargs.append(yaml.dump(param_list[:, 1]))

        scan_param_id = 0
        inj_delay_org = self.dut["inj"].get_delay()
        inj_width_org = self.dut["inj"].get_width()

        masks = self.dut.prepare_injection_mask(
            start_col=18,
            stop_col=20,
            step_col=1,
            start_row=99,
            stop_row=100,
            step_row=1
        )

        pbar = tqdm(total=len(masks))
        for mask in masks:
            # Enable injection in columns and rows for this mask step
            self.dut['CONF_SR']['COL_PULSE_SEL'] = mask["col"]
            self.dut['CONF_SR']['INJ_ROW'] = mask["row"]
            self.dut.write_conf()

            # if with_tdc:
            #     self.dut.set_mon_en(mask_pix)### TODO

            # if g is not None:
            #    self.dut.set_global(**g) ### implement this function

            ####################
            # # start readout
            self.dut.set_monoread()
            self.dut.set_timestamp("inj")
            if with_tdc:
                self.dut.set_timestamp("mon")

            ####################
            # # save scan_param
            self.scan_param_table.row['scan_param_id'] = scan_param_id
#             if g is not None:
#                 for g_key in g.keys():
#                     self.scan_param_table.row[g_key] = g[g_key]
            self.scan_param_table.row.append()
            self.scan_param_table.flush()

            cnt = 0
            with self.readout(scan_param_id=scan_param_id, fill_buffer=False, clear_buffer=True, readout_interval=0.001):
                for inj, phase in param_list:  # Iterate through parameters
                    inj_high = self.dut.get_vl_dacunits() + inj
                    # Set injection and phase
                    if inj_high > 0 and self.dut.get_vh_dacunits() != inj_high:
                        self.dut.set_vh_dacunits(inj_high)
                        self.dut.write_conf()
                        self.dut.SET["INJ_HI"] = inj_high
                    if phase > 0 and self.dut["inj"].get_phase() != phase:
                        self.dut["inj"].set_phase(int(phase) % 16)
                        self.dut["inj"].set_delay(inj_delay_org + int(phase) // 16)
                        self.dut["inj"].set_width(inj_width_org - int(phase) // 16)

                    # Inject
                    self.dut["inj"].start()
                    while not self.dut["inj"].is_done():
                        time.sleep(0.005)

                # Stop readout
                self.dut.stop_all()
                time.sleep(0.2)
                pre_cnt = cnt
                cnt = self.fifo_readout.get_record_count()

            self.logger.info('pix= dat=%d' % (cnt - pre_cnt))
            scan_param_id += 1
            pbar.update(1)
        pbar.close()

    def analyze(self, data_file=None, create_plots=True):
        if data_file is None:
            data_file = self.output_filename + '.h5'

        fhit = data_file[:-6] + 'hit.h5'
        fev = data_file[:-6] + 'ev.h5'

        # Interpret and event_build
        with analysis.Analysis(raw_data_file=data_file) as a:
            a.analyze_data()

        import tjmonopix.analysis.event_builder_inj as event_builder_inj
        event_builder_inj.build_inj_h5(fhit, data_file, fev, n=10000000)
        self.logger.info('timestamp assigned %s' % (fev))

        # Analyze
        import tjmonopix.analysis.analyze_hits as analyze_hits
        ana = analyze_hits.AnalyzeHits(fev, data_file)
        ana.init_hist_ev()
        ana.init_injected()
        ana.init_cnts()
        ana.run()

    def new_analyze(self, data_file=None):
        if data_file is None:
            data_file = self.output_filename + '.h5'

        n_inj = 100
        phaselist = np.arange(0, 32)
        # TODO: Read from file if run externally

        # Interpret and event_build
        with analysis.Analysis(raw_data_file=data_file) as a:
            a.analyze_data()
            hit_file = a.analyzed_data_file

            with tb.open_file(hit_file, "r") as in_file:
                hits = in_file.root.Hits[:]

            out_buffer = np.empty(500000, dtype=[("col", "<u1"), ("row", "<u1"), ("tot", "<u1"), ("toa", "<u1"), ("phase", "<u1"), ("ts_inj", "<i8")])

            result = get_phase(hits, out_buffer, n_inj, phaselist)

            with tb.open_file(hit_file[:-3] + "_smallev.h5", "w") as out_file:
                output_table = out_file.create_table(
                    out_file.root, name='Hits',
                    description=out_buffer.dtype,
                    title='Hits',
                    filters=tb.Filters(complib='blosc',
                                       complevel=5,
                                       fletcher32=False)
                )
                output_table.append(result)
                output_table.flush()
            le_hist = le_hist_2d(result)
            print le_hist.shape
            with plotting.Plotting(analyzed_data_file=a.analyzed_data_file) as p:
                p._plot_histogram2d(le_hist, suffix='le_hist')

    def plot(self):
        fev = self.output_filename[:-4] + 'ev.h5'
        fraw = self.output_filename + '.h5'
        fpdf = self.output_filename + '.pdf'

        import tjmonopix.analysis.plotting_base as plotting_base
        with plotting_base.PlottingBase(fpdf, save_png=True) as plotting:
            # Configuration
            with tb.open_file(fraw) as f:
                # TODO: format kwargs and firmware setting
                dat = yaml.load(f.root.meta_data.attrs.status)
                inj_n = dat["inj"]["REPEAT"]

                dat = yaml.load(f.root.meta_data.attrs.dac_status)
                dat.update(yaml.load(f.root.meta_data.attrs.power_status))
                plotting.table_1value(dat, page_title="Chip configuration")

                dat = yaml.load(f.root.meta_data.attrs.pixel_conf)
                plotting.plot_2d_pixel_4(
                    [dat["PREAMP_EN"], dat["INJECT_EN"], dat["MONITOR_EN"], dat["TRIM_EN"]],
                    page_title="Pixel configuration",
                    title=["Preamp", "Inj", "Mon", "TDAC"],
                    z_min=[0, 0, 0, 0], z_max=[1, 1, 1, 15])
            # Plot data
            with tb.open_file(fev) as f:
                dat = f.root.HistOcc[:]
                plotting.plot_2d_pixel_hist(dat, title=f.root.HistOcc.title, z_axis_title="Hits",
                                            z_max=inj_n)


@numba.njit
def get_phase(hits, output_buffer, n_inj, phaselist):
    inj_cnt = -1
    out_i = 0
    for i in range(len(hits)):
        if hits[i]["col"] == 252:
            inj_cnt += 1
            ts_inj = hits[i]["timestamp"]
        elif hits[i]["col"] < 115 and inj_cnt >= 0:
            output_buffer[out_i]["col"] = hits[i]["col"]
            output_buffer[out_i]["row"] = hits[i]["row"]
            output_buffer[out_i]["tot"] = (hits[i]["te"] - hits[i]["le"]) & 0x3F
            output_buffer[out_i]["toa"] = hits[i]["le"]
            output_buffer[out_i]["phase"] = phaselist[inj_cnt // n_inj]
            output_buffer[out_i]["ts_inj"] = ts_inj
            out_i += 1

    return output_buffer[:out_i]


@numba.njit
def le_hist_2d(hits):
    hist = np.zeros(shape=((np.amax(hits["phase"] - np.amin(hits["phase"]) + 1)), 64))
    for hit in hits:
        hist[hit["phase"], hit["toa"] - ((hit["ts_inj"] - hit["phase"]) >> 4) & 0x3F] += 1

    return hist


if __name__ == "__main__":
    from tjmonopix.tjmonopix import TJMonoPix
    dut = TJMonoPix()

    local_configuration = {"injlist": None,  # np.arange(0.1,0.6,0.05),
                           "ithr": None,  # None, [0.82], np.arange(),
                           "p": None,  # np.arange(0,16,1),
                           "pix": [18, 25],
                           "n_mask_pix": 12,
                           "with_mon": False
                           }

    # fname=time.strftime("%Y%m%d_%H%M%S_simples_can")
    # fname=(os.path.join(monopix_extra_functions.OUPUT_DIR,"simple_scan"),fname)

    scan = InjectionScan(dut, online_monitor_addr="tcp://127.0.0.1:6500")
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
