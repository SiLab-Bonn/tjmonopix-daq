import time
import numpy as np
import matplotlib.pyplot as plt

# import tables after numpy and matplotlib to prevent libpng error
import tables as tb
import yaml
import os
import logging

from tjmonopix.scan_base import ScanBase
from tjmonopix.tjmonopix import TJMonoPix
from tjmonopix.analysis.interpreter import interpret_h5
from tjmonopix.analysis.interpret_scan import interpret_rx_data_scan

from tjmonopix.analysis.tools import fit_scurve, scurve, fit_scurves_multithread
from tjmonopix.analysis.plotting import plot_scurve_hist
from tqdm import tqdm

from numpy.lib.recfunctions import append_fields

from numba import njit


class ThresholdScan(ScanBase):
    scan_id = "threshold_scan"

    def scan(self, **kwargs):
    
        
        with_tlu = kwargs.pop('with_tlu', False)
        with_timestamp = kwargs.pop('with_timestamp', False)
        with_tdc = kwargs.pop('with_tdc', False)
        inj_low_limit = kwargs.pop('inj_low_limit', 35)
        inj_high_limit = kwargs.pop('inj_high_limit', 100)

        print self.dut.get_power_status()
        raw_input("Check power consumption, especially VDDD (should be 0.5mA). Press any key to continue and start scan")

        cnt = 0
        scanned = 0

        ####################
        # stop readout and clean fifo
        if with_timestamp:
            self.dut.stop_timestamp()
        if with_tlu:
            self.dut.stop_tlu()
        if with_tdc:
            self.dut.stop_tdc()
        self.dut.stop_monoread()
        self.dut['fifo'].reset()

        # Why is this needed?
        self.dut['data_rx'].set_en(True)
        self.dut['fifo'].get_data()
        self.dut['data_rx'].set_en(False)

        # Setup injection
        repeat = 100
        sleeptime = repeat * 0.0001
        delay = 5000
        width = 350
        noise_en = 0

        # SET THE INJECTION PULSE AMPLITUDE
        # 128-bit DAC (7-bit binary equivalent)
        # SET THE VOLTAGES IN ONE HOT ENCODING, ONLY ONE BIT ACTIVE AT A TIME.
        # V = (127/1.8)*#BIT
        # The default values are VL=44, VH=79, VH-VL=35
        # VDAC LSB=14.17mV, Cinj=230aF, 1.43e-/mV, ~710e-
        self.dut.set_vl_dacunits(35, 1)
        self.dut.set_vh_dacunits(35, 1)
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

        scan_param_id = scan_range[0] - inj_low_limit

        # Start values for scanning whole flavor  
        area_coords = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (3, 2), (3, 3), (8, 0), (8, 1), (8, 2), (8, 3), (9, 0), (9, 1), (9, 2), (9, 3), (10, 0), (10, 1), (10, 2), (10, 3), (11, 0), (11, 1), (11, 2), (11, 3), (16, 0), (16, 1), (16, 2), (16, 3), (17, 0), (17, 1), (17, 2), (17, 3), (18, 0), (18, 1), (18, 2), (18, 3), (19, 0), (19, 1), (19, 2), (19, 3), (24, 0), (24, 1), (24, 2), (24, 3), (25, 0), (25, 1), (25, 2), (25, 3), (26, 0), (26, 1), (26, 2), (26, 3), (27, 0), (27, 1), (27, 2), (27, 3), (32, 0), (32, 1), (32, 2), (32, 3), (33, 0), (33, 1), (33, 2), (33, 3), (34, 0), (34, 1), (34, 2), (34, 3), (35, 0), (35, 1), (35, 2), (35, 3), (40, 0), (40, 1), (40, 2), (40, 3), (41, 0), (41, 1), (41, 2), (41, 3), (42, 0), (42, 1), (42, 2), (42, 3), (43, 0), (43, 1), (43, 2), (43, 3), (48, 0), (48, 1), (48, 2), (48, 3), (49, 0), (49, 1), (49, 2), (49, 3), (50, 0), (50, 1), (50, 2), (50, 3), (51, 0), (51, 1), (51, 2), (51, 3), (56, 0), (56, 1), (56, 2), (56, 3), (57, 0), (57, 1), (57, 2), (57, 3), (58, 0), (58, 1), (58, 2), (58, 3), (59, 0), (59, 1), (59, 2), (59, 3), (64, 0), (64, 1), (64, 2), (64, 3), (65, 0), (65, 1), (65, 2), (65, 3), (66, 0), (66, 1), (66, 2), (66, 3), (67, 0), (67, 1), (67, 2), (67, 3), (72, 0), (72, 1), (72, 2), (72, 3), (73, 0), (73, 1), (73, 2), (73, 3), (74, 0), (74, 1), (74, 2), (74, 3), (75, 0), (75, 1), (75, 2), (75, 3), (80, 0), (80, 1), (80, 2), (80, 3), (81, 0), (81, 1), (81, 2), (81, 3), (82, 0), (82, 1), (82, 2), (82, 3), (83, 0), (83, 1), (83, 2), (83, 3), (88, 0), (88, 1), (88, 2), (88, 3), (89, 0), (89, 1), (89, 2), (89, 3), (90, 0), (90, 1), (90, 2), (90, 3), (91, 0), (91, 1), (91, 2), (91, 3), (96, 0), (96, 1), (96, 2), (96, 3), (97, 0), (97, 1), (97, 2), (97, 3), (98, 0), (98, 1), (98, 2), (98, 3), (99, 0), (99, 1), (99, 2), (99, 3), (104, 0), (104, 1), (104, 2), (104, 3), (105, 0), (105, 1), (105, 2), (105, 3), (106, 0), (106, 1), (106, 2), (106, 3), (107, 0), (107, 1), (107, 2), (107, 3)]

        # Iterate over whole flavor
        start = timer()

        for area in area_coords:
            for _ in range(20):
                self.dut["fifo"].get_data()

            # TODO Set injected columns and rows here
            self.dut['CONF_SR']['COL_PULSE_SEL'].setall(False)
            self.dut['CONF_SR']['INJ_ROW'].setall(False)

            self.dut.write_conf()

            # Set columns and rows to inject
            self.dut['CONF_SR']['COL_PULSE_SEL'][112 + area[0]] = 1
            self.dut['CONF_SR']['COL_PULSE_SEL'][112 + area[0] + 4] = 1
            for row in (np.arange(0, 221, 4) + area[1]):
               self.dut['CONF_SR']['INJ_ROW'][row] = 1

            self.dut.write_conf()

            for _ in range(10):
                self.dut["fifo"].get_data()
            
            # Loop over all injection steps
            for step in scan_range:
                # Set injection voltage for current step
                self.dut.set_vh_dacunits(step, 1)
                self.dut.write_conf()

                self.dut['fifo'].reset()
                with self.readout(scan_param_id=scan_param_id, fill_buffer=False, clear_buffer=True, readout_interval=0.2, timeout=0.5):
                    while not self.dut['inj'].is_ready:
                        time.sleep(0.002)
                    for _ in range(10):
                        self.dut['inj'].is_ready
                    self.dut["inj"].start()

                    time.sleep(sleeptime)
                
                scan_param_id = step - inj_low_limit
            stop = timer()
            print("Time: {}".format(stop - start))

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
        

if __name__ == "__main__":

    def prepare_data(filename):
        """
        Prepare data for threshold calculation.

        Interpret raw data file and correlate scan_param_id to hits.
        Outputs interpreted data file and file optimized for threshold calculation

        Parameters
        ----------
        filename : file name of input file
        """
        # The data format flag is needed to save the index in the timestamp field
        interpret_h5(fin=filename, fout=filename[:-3] + "_hit.h5", data_format=0xF0)
        with tb.open_file(filename[:-3] + "_hit.h5", "r") as in_file:
            hits = in_file.root.Hits[:]

        with tb.open_file(filename, "r") as in_file:
            meta_data = in_file.root.meta_data[:]

        @njit
        def correlate_scan_ids(hits, meta_data):
            scan_param_ids = np.empty(len(hits), dtype=np.uint16)
            scan_i = 0
            data_i = 0

            while scan_i < len(meta_data) and data_i < len(hits):
                if hits[data_i]["timestamp"] < meta_data[scan_i]["index_stop"]:
                    scan_param_ids[data_i] = meta_data[scan_i]["scan_param_id"]
                    data_i += 1
                else:
                    scan_i += 1

            return scan_param_ids

        logging.info("Start correlating scan_parameters")
        scan_param_ids = correlate_scan_ids(hits, meta_data)
        logging.info("Done correlating scan_parameters")

        # # Add scan_param_ids to hit_array
        hits = append_fields(hits, 'scan_param_id', scan_param_ids)
        # And write all to a file
        with tb.open_file(filename[:-3] + "_threshold.h5", "w") as out_file:
            description = np.zeros((1,), dtype=hits.dtype).dtype
            hit_table = out_file.create_table(
            out_file.root, name="Hits", description=description, title='hit_data')

            hit_table.append(hits)
            hit_table.flush()

    def analyze(filename):
        """
        Calculate threshold from hit table
        """
        n_cols = 112
        n_rows = 224

        # prepare_data(filename)

        with tb.open_file(filename[:-3] + "_threshold.h5", "r") as in_file:
            hit_data = in_file.root.Hits[:]

        # Plot occupancy map
        hist, xedges, yedges = np.histogram2d(hit_data["col"], hit_data["row"], bins=[n_cols, n_rows])

        fig, ax = plt.subplots()
        im = ax.imshow(hist.T, origin="lower", aspect=0.9)
        plt.colorbar(im)
        plt.show()

        hit_data = hit_data[np.logical_and(hit_data["col"] < n_cols, hit_data["row"] < n_rows)]
        params = np.unique(hit_data["scan_param_id"])
        param_count = len(params)
        scan_parameter_range = np.arange(params[0], params[-1] + 1, 1)


        @njit
        def hist_3d(hits, result_hist):
            for hit in hits:
                col = hit['col']
                row = hit['row']
                par  = hit['scan_param_id']
                if col >= 0 and col < result_hist.shape[0] and row >= 0 and row < result_hist.shape[1] and par >= 0 and par < result_hist.shape[2]:
                    result_hist[col, row, par] += 1
                else:
                    ValueError

        result_hist = np.zeros(shape=(n_cols, n_rows, param_count), dtype=np.uint16)
        hist_3d(hit_data, result_hist)
        scurves = result_hist.reshape((result_hist.shape[0] * result_hist.shape[1], result_hist.shape[2]))

        thr, sig, chi = fit_scurves_multithread(scurves=scurves, scan_param_range=scan_parameter_range, n_injections=100)

        # Plot scurve histogram of all curves
        plot_scurve_hist(scurves, scan_parameter_range, 100)

        logging.info("Threshold: {}".format(np.mean(thr[thr > 0])))


    analyze(filename="/media/data/tj-monopix_threshold_debug/debug/scurve_debug.h5")
