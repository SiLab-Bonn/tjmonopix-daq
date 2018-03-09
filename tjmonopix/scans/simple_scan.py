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

    def __init__(self, dut=None, fname=None, send_addr="tcp://127.0.0.1:5500"):
        self.dut = dut

        if fname == None:
            self.working_dir = os.path.join(os.getcwd(), "output_data")
            self.run_name = time.strftime("%Y%m%d_%H%M%S_") + self.scan_id
        else:
            self.working_dir = os.path.dirname(os.path.realpath(fname))
            self.run_name = os.path.basename(os.path.realpath(fname))
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.filename = os.path.join(self.working_dir, self.run_name + '.h5')

        #### monitor
        self.socket=send_addr

        # Set up logging to log to file and console and format log messages
        self.fh = logging.FileHandler(
            os.path.join(self.working_dir, "log.log"))
        self.fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-5.5s] %(message)s"))
        self.fh.setLevel(logging.DEBUG)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.fh)
        logging.info("Initializing {0}".format(self.__class__.__name__))

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
            filename = self.filename
        interpret_h5(filename, filename[:-3]+"_hit.h5",data_format=0x43)


if __name__ == "__main__":
    dut = TJMonoPix()
    dut['CONF']['DEF_CONF_N'] = 0
    dut['CONF']['AB_SELECT'] = 1
    dut['CONF'].write()
    dut.init()

    scan = SimpleScan(dut=dut)
    scan.start()

    print scan.dut.get_power_status()
    raw_input("Check...")

    scan.dut['CONF_SR']['EN_PMOS_NOSF'].setall(False)
    scan.dut['CONF_SR']['EN_PMOS'].setall(False)
    scan.dut['CONF_SR']['EN_COMP'].setall(False)
    scan.dut['CONF_SR']['EN_HV'].setall(False)
    scan.dut['CONF_SR']['EN_OUT'].setall(False)
    scan.dut['CONF_SR']['nEN_OUT'].setall(True)
    scan.dut['CONF_SR']['EN_HITOR_OUT'].setall(True)
    scan.dut['CONF_SR']['nEN_HITOR_OUT'].setall(True)

    scan.dut['CONF_SR']['EN_PMOS'][9] = 1
    scan.dut['CONF_SR']['MASKD'][31] = 1
    # scan.dut.enable_injection(1,18,99)

    # scan.dut['CONF_SR']['INJ_ROW'][223] = False # FOR THE ANALOG MONITORING TOP PIXEL
    # scan.dut['CONF_SR']['INJ_IN_MON_L'] = 0 # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS LEFT SIDE
    # scan.dut['CONF_SR']['INJ_IN_MON_R'] = 0 # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS RIGHT SIDE

    # FRONT END TUNING
    scan.dut.set_vl_dacunits(49, 1)
    scan.dut.set_vh_dacunits(79, 1)
    scan.dut.set_vreset_dacunits(40, 1)
    scan.dut.set_icasn_dacunits(0, 1)
    # Change analog input (at the sensor) reset rate, also reduces pile-up at the input
    scan.dut.set_ireset_dacunits(3, 1, 1)
    # change analog output reset rate, tot resolution
    scan.dut.set_ithr_dacunits(8, 1)
    scan.dut.set_idb_dacunits(15, 1)  # Hihter IDB, Higher Threshold
    scan.dut.set_ibias_dacunits(50, 1)
    #################################

    scan.dut.write_conf()

    with scan.readout():
        scan.dut["data_rx"].set_en(True)
        time.sleep(10)

    scan.stop()
    scan.analyze()
