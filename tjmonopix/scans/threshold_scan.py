import time
import numpy as np
import yaml
import os
import logging

from tjmonopix.scan_base import ScanBase
from tjmonopix.tjmonopix import TJMonoPix

from tjmonopix.analysis import analysis
from tjmonopix.analysis import plotting


class ThresholdScan(ScanBase):
    scan_id = "threshold_scan"

    def scan(self, **kwargs):

        if self.dut.SET["fl"] == "EN_PMOS":
            fl_n = 1
        elif self.dut.SET["fl"] == "EN_HV":
            fl_n = 3
        with_tlu = kwargs.pop('with_tlu', False)
        with_timestamp = kwargs.pop('with_timestamp', False)
        with_tdc = kwargs.pop('with_tdc', False)
        inj_low_limit = kwargs.pop('inj_low_limit', 35)
        inj_high_limit = kwargs.pop('inj_high_limit', 100)

        ####################
        # stop readout and clean fifo
        if with_timestamp:
            self.dut.stop_timestamp()
        if with_tlu:
            self.dut.stop_tlu()
        if with_tdc:
            self.dut.stop_tdc()

        print self.dut.get_power_status()

        cnt = 0
        scanned = 0

        # Write scan_id (type) to file
        self.meta_data_table.attrs.scan_id = "threshold_scan"

        # Why is this needed?
        # self.dut['data_rx'].set_en(True)
        # self.dut['fifo'].get_data()
        # self.dut['data_rx'].set_en(False)

        # Setup injection
        repeat = 100
        delay = 5000
        width = 350
        noise_en = 0

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

        self.dut['inj'].set_delay(delay)
        self.dut['inj'].set_width(width)
        self.dut['inj'].set_repeat(repeat)
        self.dut['inj'].set_en(0)

        ####################
        # start readout
        self.dut.set_monoread()
        #if with_tdc:
        #    self.dut.set_tdc()
        #if with_tlu:
        #    tlu_delay = kwargs.pop('tlu_delay', 8)
        #    self.dut.set_tlu(tlu_delay)
        #if with_timestamp:
        #    self.dut.set_timestamp()

#         scan_param_id = scan_range[0] - inj_low_limit
        scan_param_id = 0

        # Start values for scanning whole flavor  

        # Iterate over whole flavor

        injcol_step = 56
        injrow_step = 4
        injcol_start = 0
        injrow_start = 0
        # set cols to inject
        for seedi in range(injcol_start, injcol_step):
            self.dut['CONF_SR']['COL_PULSE_SEL'].setall(False)
            self.dut.write_conf()
            for col in range(seedi, self.dut.COL, injcol_step):
                self.dut['CONF_SR']['COL_PULSE_SEL'][fl_n * 112 + col] = 1
                self.dut.write_conf()

            # Set rows to inject
            for seedj in range(injrow_start, injrow_step):
                self.dut['CONF_SR']['INJ_ROW'].setall(False)
                self.dut.write_conf()
                for row in range(seedj, self.dut.ROW - 2, injrow_step):  # -2 : christian's suggestion
                    self.dut['CONF_SR']['INJ_ROW'][row] = 1
                    self.dut.write_conf()
                # readout trash data
                for _ in range(10):
                    self.dut["fifo"].reset()
                    time.sleep(0.02)

                scan_param_id = 0

                for step in scan_range:
                    # Ramp to vh value
                    if vh > step:
                        vh_step = -1
                    else:
                        vh_step = 1
                    for vh in range(vh, step, vh_step):
                        self.dut.set_vh_dacunits(vh, 1)
                        self.dut.write_conf()

                    with self.readout(scan_param_id=scan_param_id,
                                      fill_buffer=False, clear_buffer=True, reset_sram_fifo=True):

                        # time.sleep(0.07)  ## might not be needed...
                        self.dut["inj"].start()
                        while not self.dut['inj'].is_ready:
                            time.sleep(0.005)
                    scan_param_id = scan_param_id + 1

        # stop readout
        if with_timestamp:
            self.dut.stop_timestamp()
            self.meta_data_table.attrs.timestamp_status = yaml.dump(
                self.dut["timestamp"].get_configuration())
        if with_tlu:
            self.dut.stop_tlu()
            self.meta_data_table.attrs.tlu_status = yaml.dump(
                self.dut["tlu"].get_configuration())
        if with_tdc:
            self.dut.stop_tdc()
        self.dut.stop_monoread()

    @classmethod
    def analyze(self, data_file=None, scan_param_id=True, create_plots=True):
        if data_file is None:
            data_file = self.output_filename + '.h5'

        with analysis.Analysis(raw_data_file=data_file) as a:
            a.analyze_data(data_format=0x3, put_scan_param_id=True)
            mean_thr_rdpw = np.median(a.threshold_map[:, 112:220][np.nonzero(a.threshold_map[:, 112:220])])
            mean_thr_fdpw = np.median(a.threshold_map[:, :112][np.nonzero(a.threshold_map[:, :112])])

            print np.mean(a.threshold_map[:, 112:220][np.nonzero(a.threshold_map[:, 112:220])])
            print np.mean(a.threshold_map[:, :112][np.nonzero(a.threshold_map[:, :112])])

            logging.info("Mean threshold for removed DPW region is %i DAC units" % (int(mean_thr_rdpw)))
            logging.info("Mean threshold for full DPW region is %i DAC units" % (int(mean_thr_fdpw)))

        if create_plots:
            with plotting.Plotting(analyzed_data_file=a.analyzed_data_file) as p:
                p.create_standard_plots()
                p.create_threshold_map()
                p.create_scurves_plot()
                p.create_threshold_distribution_plot()


if __name__ == "__main__":
    scan = ThresholdScan()
    scan.scan()
    scan.analyze()

#     ThresholdScan.analyze("/home/silab/tjmonopix/data/W4_1e15_PMOS/threshold_scan_adapted.h5")
#     ThresholdScan.analyze("/home/silab/tjmonopix/data/Threshold_scans/threshold_test.h5", create_plots=True)

