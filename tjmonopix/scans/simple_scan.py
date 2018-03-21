import time
import tables as tb
import numpy as np
import yaml
import os
import logging

from tjmonopix.scan_base import ScanBase
from tjmonopix.tjmonopix import TJMonoPix
from tjmonopix.analysis.interpreter import interpret_h5


class SimpleScan(ScanBase):
    scan_id = "simple"


    def scan(self, **kwargs):
        with_tlu = kwargs.pop('with_tlu', True)
        with_timestamp = kwargs.pop('with_timestamp', True)
        with_tdc = kwargs.pop('with_tdc', True)
        scan_time = kwargs.pop('scan_time', 10)
        # start_freeze=50,start_read=52,stop_read=52+2,stop_freeze=52+36,stop=52+36+10,
        #start_freeze = kwargs.pop('start_freeze', 50)
        #start_read = kwargs.pop('start_read', start_freeze+2)
        #stop_read = kwargs.pop('stop_read', start_read+2)
        #stop_freeze = kwargs.pop('stop_freeze', start_freeze+36)
        #stop_rx = kwargs.pop('stop', stop_freeze+10)

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

        ####################
        # start readout
        self.dut.set_monoread()
        if with_tdc:
            self.dut.set_tdc()
        if with_tlu:
            tlu_delay = kwargs.pop('tlu_delay', 8)
            self.dut.set_tlu(tlu_delay)
        if with_timestamp:
            self.dut.set_timestamp()

        ####################
        # start read fifo
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
                if scanned+10 > scan_time and scan_time > 0:
                    break
                elif scanned < 30:
                    time.sleep(1)
                else:
                    time.sleep(10)
            time.sleep(max(0, scan_time-scanned))
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
        self.dut.stop_monoread()

    def analyze(self, filename=None):
        if filename == None:
            filename = self.output_filename+'.h5'
        interpret_h5(filename, filename[:-3]+"_hit.h5",data_format=0x43)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='TJ-MONOPIX simple scan \n example: simple_scan --scan_time 10 --data simple_0', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--data',  type=str, default=None,
                        help='Name of data file without extention')
    parser.add_argument('--scan_time', type=int, default=10,
                        help="Scan time in seconds. Default=10, disable=0")
    parser.add_argument('--config_file', type=str, default=None,
                        help="Name of config file(yaml)")
    args = parser.parse_args()

    dut = TJMonoPix()
    
    if args.config_file==None:
        dut.init(B=True)
        ### set mask 
        dut['CONF_SR']['EN_PMOS'][9] = 1
        dut['CONF_SR']['EN_PMOS'][10] = 1
        dut['CONF_SR']['EN_PMOS'][11] = 1
        dut['CONF_SR']['EN_HITOR_OUT'][1] = 0
        for d in range(28,34):
           dut['CONF_SR']['MASKD'][d] = True
        for i in range(99,105):    
           dut['CONF_SR']['MASKH'][i] = True
        dut['CONF_SR']['MASKH'][102] = False
        dut.mask(1, 33, 72)
        dut.mask(1, 17, 30)
        dut.mask(1, 41, 66)
        dut.mask(1, 97, 94)
        dut.mask(1, 34, 151)
        dut.mask(1, 40, 123)
        dut.mask(1, 82, 193)
        dut.enable_column_hitor(1,20)
        dut.write_conf()
        ### set globals
        dut.set_vl_dacunits(49,1)
        dut.set_vh_dacunits(79,1)
        dut.set_vreset_dacunits(40,1) #1V
        dut.set_icasn_dacunits(0,1) #4.375nA
        dut.set_ireset_dacunits(131,1) #270pA,
        dut.set_ithr_dacunits(15,1) #680pA
        dut.set_idb_dacunits(20,1) #500nA
        dut.set_ibias_dacunits(100,1) #500nA
        dut.write_conf()
    else:
        dut.load_config(args.config_file)
    
    ### run  
    scan = SimpleScan(dut,fname=args.data,sender_addr="tcp://127.0.0.1:6500")
    scan.start(scan_time=args.scan_time)
    scan.analyze()
