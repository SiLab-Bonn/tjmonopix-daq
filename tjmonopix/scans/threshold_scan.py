# coding: utf-8

import time
import logging
import numpy as np
from tqdm import tqdm

from tjmonopix.scan_base import ScanBase
from tjmonopix.analysis import analysis
from tjmonopix.analysis import plotting

class ThresholdScan(ScanBase):
    scan_id = 'threshold_scan'

    def scan(self, **kwargs):

        self.max_cols = self.dut.COL
        self.max_rows = self.dut.ROW

        inj_low_limit = kwargs.pop('inj_low_limit', 35)
        inj_high_limit = kwargs.pop('inj_high_limit', 100)
        mask_not_injected = kwargs.pop('mask_not_injected', False)

        # Stop readout and clean FIFO
        self.dut.stop_all()
        self.dut.reset_fifo()

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

        # SET THE INJECTION PULSE AMPLITUDE
        # 128-bit DAC (7-bit binary equivalent)
        # SET THE VOLTAGES IN ONE HOT ENCODING, ONLY ONE BIT ACTIVE AT A TIME.
        # V = (127/1.8)*#BIT
        # The default values are VL=44, VH=79, VH-VL=35
        # VDAC LSB=14.17mV, Cinj=230aF, 1.43e-/mV, ~710e-
        self.dut.set_vl_dacunits(inj_low_limit, 1)
        self.dut.set_vh_dacunits(inj_low_limit, 1)
        vh = inj_low_limit
        self.dut.write_conf()

        scan_range = np.arange(inj_low_limit, inj_high_limit, 1)

        # start readout
        self.dut.set_monoread()

        scan_param_id = 0

        injcol_start = 1
        injrow_start = 1
        injcol_stop = 112
        injrow_stop = 224
        injcol_step = 2
        injrow_step = 2

        masks = self.dut.prepare_injection_mask(
            start_col=injcol_start,
            stop_col=injcol_stop,
            step_col=injcol_step,
            start_row=injrow_start,
            stop_row=injrow_stop,
            step_row=injrow_step
        )

        # Main scan loop
        pbar = tqdm(total=len(masks) * len(scan_range))
        for step in scan_range:
            # Ramp to vh value
            if vh > step:
                vh_step = -5
            else:
                vh_step = 1
            for vh in range(vh, step, vh_step):
                self.dut.set_vh_dacunits(vh, 1)
                self.dut.write_conf()

            with self.readout(scan_param_id=scan_param_id, fill_buffer=False, clear_buffer=True, reset_sram_fifo=True):
                for mask in masks:
                    self.dut['CONF_SR']['COL_PULSE_SEL'] = mask["col"]
                    self.dut['CONF_SR']['INJ_ROW'] = mask["row"]
                    if mask_not_injected:
                        col_enable = mask["col"][self.dut.fl_n * 112: (self.dut.fl_n + 1) * 112]
                        self.dut['CONF_SR'][self.dut.SET['fl']] = col_enable[::2] | col_enable[1::2]
                        self.dut['CONF_SR']['MASKH'].setall(False)
                        self.dut['CONF_SR']['MASKH'] = mask["row"]
                    self.dut.write_conf()
                    self.dut.reset_ibias()
                    time.sleep(0.05)  # This needs to be long enough (0.05 works, maybe less) TODO: optimize wait time

                    # Read out trash data
                    for _ in range(5):
                        self.dut.reset_fifo()
                        time.sleep(0.005)

                    # Start injection and read data
                    self.dut["inj"].start()
                    while not self.dut['inj'].is_ready:
                        time.sleep(0.01)
                    pbar.update(1)
            scan_param_id = scan_param_id + 1
        pbar.close()

        # Stop readout
        self.dut.stop_all()

    def analyze(self, data_file=None):
        if data_file is None:
            data_file = self.output_filename + '.h5'

        with analysis.Analysis(raw_data_file=data_file) as a:
            a.analyze_data()
            self.analyzed_data_file = a.analyzed_data_file
            mean_thr_rdpw = np.median(a.threshold_map[:, 112:220][np.nonzero(a.threshold_map[:, 112:220])])
            mean_thr_fdpw = np.median(a.threshold_map[:, :112][np.nonzero(a.threshold_map[:, :112])])

            logging.info("Mean threshold for removed DPW region is %i DAC units" % (int(mean_thr_rdpw)))
            logging.info("Mean threshold for full DPW region is %i DAC units" % (int(mean_thr_fdpw)))

    def plot(self, analyzed_data_file=None):
        """Plot threshold scan results

        Parameters:
        -----------
        analyzed_data_file: str, optional
            Path to analyzed data file including file extension
        """
        if analyzed_data_file is None:
            if hasattr(self, "analyzed_data_file"):
                analyzed_data_file = self.analyzed_data_file
            else:
                analyzed_data_file = self.output_filename + '_interpreted.h5'

        with plotting.Plotting(analyzed_data_file=analyzed_data_file) as p:
            p.create_standard_plots()
            p.create_threshold_map()
            p.create_scurves_plot()
            p.create_threshold_plot()


if __name__ == "__main__":
    scan = ThresholdScan()
    scan.scan()
    scan.analyze()
