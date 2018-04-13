import time
import tables as tb
import numpy as np
import yaml
import os
import logging

from tjmonopix.scan_base import ScanBase
from tjmonopix.tjmonopix import TJMonoPix
from tjmonopix.analysis.interpreter import interpret_h5

class NoiseOccupancyScan(ScanBase):
    scan_id = "noise_occupancy"

    def scan(self, **kwargs):
        with_tlu = kwargs.pop('with_tlu', False)
        with_timestamp = kwargs.pop('with_timestamp', False)
        with_tdc = kwargs.pop('with_tdc', False)
        scan_time = kwargs.pop('scan_time', 100)
        # start_freeze=50,start_read=52,stop_read=52+2,stop_freeze=52+36,stop=52+36+10,
        #start_freeze = kwargs.pop('start_freeze', 50)
        #start_read = kwargs.pop('start_read', start_freeze+2)
        #stop_read = kwargs.pop('stop_read', start_read+2)
        #stop_freeze = kwargs.pop('stop_freeze', start_freeze+36)
        #stop_rx = kwargs.pop('stop', stop_freeze+10)

        self.dut['CONF_SR']['MASKD'].setall(False)
        self.dut['CONF_SR']['MASKH'].setall(False)
        self.dut['CONF_SR']['MASKV'].setall(False)
        self.dut['CONF_SR']['EN_PMOS'].setall(False)

        self.dut.write_conf()
        self.dut.get_power_status()

        # SELECT WHICH DOUBLE COLUMNS TO ENABLE
        self.dut['CONF_SR']['EN_PMOS_NOSF'].setall(False)
        self.dut['CONF_SR']['EN_PMOS'].setall(False)
        self.dut['CONF_SR']['EN_COMP'].setall(False)
        self.dut['CONF_SR']['EN_HV'].setall(False)
        self.dut['CONF_SR']['EN_OUT'].setall(False) #ENABLES OR DISABLES THE NORMAL OUTPUT PADS, ACTIVE LOW
        self.dut['CONF_SR']['nEN_OUT'].setall(True) #ENABLES OR DISABLES THE COMPLEMENTARY OUTPUT PADS, ACTIVE LOW
        self.dut['CONF_SR']['EN_HITOR_OUT'].setall(True) #ENABLES OR DISABLES THE NORMAL HITOR PADS, HITOR0-3 =  1-4 flavor, ACTIVE LOW
        self.dut['CONF_SR']['nEN_HITOR_OUT'].setall(True) #ENABLES OR DISABLES THE COMPLEMENTARY HITOR PADS, ACTIVE LOW

        #self.dut['CONF_SR']['EN_PMOS'].setall(True)
        self.dut['CONF_SR']['EN_PMOS'][9] = 1
        self.dut['CONF_SR']['EN_PMOS'][10] = 1
        self.dut['CONF_SR']['EN_PMOS'][11] = 1
        self.dut['CONF_SR']['EN_HITOR_OUT'][1] = 0

        # SELECT WHICH PHYSICAL COLUMNS, ROWS, DIAGONALS TO MASK
        # TO MASK ONE PIXEL, MASKV, MASKH and MASKD OF THIS PIXEL SHOULD BE 0 (FALSE)
        # THE MASKD NUMBER OF THE PIXEL WE WANT TO MASK (or UNMASK), IS GIVEN BY: MASKD = PHYSCOL- PHYSROW
        # IF PHYSCOL-PHYSROW<0, then MASKD = 448+PHYSCOL-PHYSROW
        #self.dut['CONF_SR']['MASKD'].setall(False)
        #self.dut['CONF_SR']['MASKH'].setall(False)
        #self.dut['CONF_SR']['MASKV'].setall(False)

        # TO USE THE MASK FUNCTION YOU MUST INPUT THE FLAVOR, COLUMN AND ROW
        # THE FLAVOR NUMERS IS: 0 FOR PMOS_NOSF, 1 FOR PMOS, 2 FOR COMP, 3 FOR HV

        self.dut['CONF_SR']['MASKD'].setall(True)
        self.dut['CONF_SR']['MASKH'].setall(True)
        self.dut['CONF_SR']['MASKV'][224:112] = True
        self.dut['CONF_SR']['EN_PMOS'].setall(True)

        self.dut.mask(1, 33, 72)
        self.dut.mask(1, 17, 30)
        # self.dut.mask(1, 19, 31)
        self.dut.mask(1, 41, 66)
        self.dut.mask(1, 97, 94)
        self.dut.mask(1, 34, 151)
        self.dut.mask(1, 40, 123)
        self.dut.mask(1, 82, 193)
        # self.dut.mask(1, 71, 31)
        self.dut.mask(1, 71, 111)
        self.dut.mask(1, 38, 188)
        self.dut.mask(1, 97, 214)
        self.dut.mask(1, 86, 104)
        self.dut.mask(1, 35, 212)
        self.dut.mask(1, 35, 88)
        self.dut.mask(1, 43, 14)
        self.dut.mask(1, 38, 177)
        self.dut.mask(1, 17, 57)
        self.dut.mask(1, 54, 1)
        self.dut.mask(1, 38, 21)
        self.dut.mask(1, 71, 9)
        self.dut.mask(1, 58, 46)
        self.dut.mask(1, 74, 84)
        self.dut.mask(1, 53, 167)
        self.dut.mask(1, 35, 158)
        self.dut.mask(1, 72, 77)
        self.dut.mask(1, 14, 54)
        self.dut.mask(1, 78, 196)

        # SELECT PHYSICAL COLUMN(S) FOR HITOR OUTPUT
        # nMASKH (SO SETTING MASKH TO FALSE) ENABLES HITOR FOR THE SPECIFIC ROW
        self.dut['CONF_SR']['DIG_MON_SEL'].setall(False)
        self.dut.enable_column_hitor(1,20)

        self.dut.write_conf()

        ####### CONFIGURE THE FRONT END ######

        ## SET THE INJECTION PULSE AMPLITUDE
        ## 128-bit DAC (7-bit binary equivalent)
        ## SET THE VOLTAGES IN ONE HOT ENCODING, ONLY ONE BIT ACTIVE AT A TIME.
        ## V = (127/1.8)*#BIT
        # The default values are VL=44, VH=79, VH-VL=35
        # VDAC LSB=14.17mV, Cinj=230aF, 1.43e-/mV, ~710e-

        self.dut.set_vl_dacunits(44,1)
        self.dut.set_vh_dacunits(79,1)

        # SET VRESET_P, THIS IS THE BASELINE OF THE FRONT END INPUT, ONE HOT ENCODING
        self.dut.set_vreset_dacunits(35,1) #1V

        ## 128-bit DAC (7-bit binary equivalent)
        ## SET THE CURRENTS USING THERMOMETER ENCODING, I = #BITS_ACTIVE*140nA*SCALING, SCALING IS DIFFERENT FOR EACH CURRENT
        ## SCALING: IBIAS=10, IDB=16, ITHR=0.125, ICASN=4, IRESET=0.03125
        ## ACTIVE BITS SHOULD BE SET STARTING FROM THE MIDDLE e.g. for 15 active bits, (128-15)/2=56,5 so 56zeros,15ones,57zeros
        ## Thus, Ix[71:57] = True

        # SET ICASN, THIS CURRENT CONTROLS THE OUTPUT BASELINE, BE CAREFUL NOT TO SET IT TO HIGH
        # ALWAYS MONITOR THE POWER AFTER SETTING ICASN. IF VDDD IS SEVERAL mA, REDUCE IT UNTIL IT RETURNS TO 0
        # ICASN MAINLY CONTROLS THE THRESHOLD
        self.dut.set_icasn_dacunits(0,1) #4.375nA # approx 1.084V at -3V backbias, 600mV at 0V backbias

        # SET IRESET, THIS CURRENT CONTROLS THE RESET RATE OF THE FRONT END INPUT (ALSO THE THRESHOLD)
        self.dut.set_ireset_dacunits(128+2,1) #270pA, HIGH LEAKAGE MODE, NORMAL SCALING, 0 = LOW LEAKAGE MODE, SCALING*0.01

        # SET ITHR, THIS CURRENT CONTROLS THE RESET RATE OF THE OUTPUT (AND THE THRESHOLD)
        self.dut.set_ithr_dacunits(10,1) #680pA

        # SET ITHR, THIS CURRENT CONTROLS THE BIASING OF THE self.dut.get_power_status()DISCRI17.050179545339105,MINATOR (AND THE THRESHOLD)
        self.dut.set_idb_dacunits(15,1) #500nA

        # SET IBIAS, THIS CURRENT IS THE DC CURRENT OF THE MAIN BRANCH OF THE FRONT END THAT PROVIDES AMPLIFICATION
        # IT CONTROLS MAINLY THE RISE TIME
        self.dut.set_ibias_dacunits(50,1) #500nA  # default 50
        self.dut.get_power_status()
        ############ ENABLE THE DAC CURRENT MONITORING ###########
        # self.dut['CONF_SR']['SWCNTL_DACMONI'] = 0

        ########## SET THE BIAS CURRENTS OF THE TWO STAGE SOURCE 157.3336886021775,FOLLOWER THAT BUFFERS THE ANALOG MONITORING VOLTAGES #########
        # CONTROLS THE RESPONSE TIME AND THE LEVEL SHIFT OF THE BUFFER
        # self.dut['CONF_SR']['SET_IBUFN_L'] = 0b1001
        # self.dut['CONF_SR']['SET_IBUFP_L'] = 0b0101

        self.dut.write_conf()

        time.sleep(0.1)

        print self.dut.get_power_status()
        raw_input()

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
                                 (scanned, cnt, (cnt - pre_cnt) / (scanned - pre_scanned) / 1024))
                if scanned + 10 > scan_time and scan_time > 0:
                    break
                elif scanned < 30:
                    time.sleep(1)
                else:
                    time.sleep(10)
            time.sleep(max(0, scan_time - scanned))
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
        interpret_h5(filename, filename[:-3]+"_interpreted.h5",data_format=0x43)

if __name__ == "__main__":
    dut = TJMonoPix()
    dut.init()

    print(dut.get_power_status())

    scan = NoiseOccupancyScan(dut,send_addr="tcp")
    scan.start(scan_time=120)
    scan.analyze()
