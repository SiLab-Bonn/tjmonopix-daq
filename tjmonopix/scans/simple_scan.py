import time
import numpy as np
import yaml
import logging

from tjmonopix.scan_base import ScanBase
from tjmonopix.tjmonopix import TJMonoPix

from tjmonopix.analysis import analysis
from tjmonopix.analysis import plotting



class SimpleScan(ScanBase):
    scan_id = "simple"

    def scan(self, **kwargs):
        with_tj = kwargs.pop('with_tj', True)
        with_tlu = kwargs.pop('with_tlu', True)
        with_timestamp = kwargs.pop('with_timestamp', True)
        with_tdc = kwargs.pop('with_tdc', True)
        scan_timeout = kwargs.pop('scan_timeout', 10)

        cnt = 0
        scanned = 0

        # Stop readout and clean FIFO but this does not clean all
        if with_timestamp:
            self.dut.stop_timestamp()
        if with_tlu:
            self.dut.stop_tlu()
        if with_tdc:
            self.dut.stop_tdc()
        # if with_tj:
        #    self.dut.set_monoread()
        #    for _ in range(5): ### reset fifo to clean up.
        #        time.sleep(0.1)
        #        self.dut['fifo'].reset()
        self.dut.stop_monoread()
        self.dut['fifo'].reset()

        ####################
        # start readout
        if with_tj:
            self.dut.set_monoread()
        for _ in range(5): ### reset fifo to clean up.
            time.sleep(0.1)
            self.dut['fifo'].reset()
        if with_tdc:
            self.dut.set_tdc()
        if with_tlu:
            tlu_delay = kwargs.pop('tlu_delay', 8)
            self.dut.set_tlu(tlu_delay)
        if with_timestamp:
            self.dut.set_timestamp()

        # Start FIFO readout
        with self.readout(scan_param_id=0, fill_buffer=False, clear_buffer=True, readout_interval=0.2, timeout=0):
            t0 = time.time()

            self.logger.info(
                "*****{} is running **** don't forget to start tlu ****".format(self.__class__.__name__))
            while True:
                pre_cnt = cnt
                cnt = self.fifo_readout.get_record_count()
                pre_scanned = scanned
                scanned = time.time()-t0
                self.logger.info('time=%.0fs dat=%d rate=%.3fk/s' %
                                 (scanned, cnt, (cnt-pre_cnt)/(scanned-pre_scanned)/1024))
                if scanned+2 > scan_timeout and scan_timeout > 0:
                    break
                elif scanned < 30:
                    time.sleep(1)
                else:
                    time.sleep(1)
            time.sleep(max(0, scan_timeout-scanned))
        ####################
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
        if with_tj:
            self.dut.stop_monoread()

        if create_plots:
            with plotting.Plotting(analyzed_data_file=a.analyzed_data_file) as p:
                p.create_standard_plots()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='TJ-MONOPIX simple scan \n example: simple_scan --scan_time 10 --data simple_0', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--data',  type=str, default=None,
                        help='Name of data file without extention')
    parser.add_argument('--scan_timeout', type=int, default=10,
                        help="Scan time in seconds. Default=10, disable=0")

    args = parser.parse_args()    

    scan = SimpleScan(dut=dut,filename=args.data,send_addr="tcp://131.220.162.237:5500")
    output_filename=scan.start(scan_timeout=args.scan_timeout, with_tdc=True, with_timestamp=True, with_tlu=True, with_tj=True)
    scan.analyze()
