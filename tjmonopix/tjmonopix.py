#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import zlib  # workaround
import yaml
import logging
import os
import time
import struct
import numpy as np
import tables as tb

import basil
from bitarray import bitarray
from basil.dut import Dut
from basil.utils.BitLogic import BitLogic


import pkg_resources
VERSION = pkg_resources.get_distribution("tjmonopix-daq").version

loglevel = logging.INFO

''' Set up main logger '''
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.getLogger('basil.HL.RegisterHardwareLayer').setLevel(logging.WARNING)

logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s] (%(threadName)-10s) %(message)s")
logger = logging.getLogger('TJMONOPIX')
logger.setLevel(loglevel)


class TJMonoPix(Dut):

    """ Map hardware IDs for board identification """
    hw_map = {
        0: 'SIMULATION',
        1: 'MIO2',
    }

    def __init__(self, conf=None, **kwargs):
        if not conf:
            proj_dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            conf = os.path.join(proj_dir, 'tjmonopix' +
                                os.sep + 'tjmonopix.yaml')

        logger.debug("Loading configuration file from {:s}".format(conf))

        super(TJMonoPix, self).__init__(conf)
        self.conf_flg = 1
        self.SET = {'VDDA': None, 'VDDP': None, 'VDDA_DAC': None, 'VDDD': None,
                    'VPCSWSF': None, 'VPC': None, 'BiasSF': None, 'INJ_LO': None, 'INJ_HI': None}

    def get_daq_version(self):
        ret = self['intf'].read(0x0000, 2)
        fw_version = str('%s.%s' % (ret[1], ret[0]))

        ret = self['intf'].read(0x0002, 2)
        board_version = ret[0] + (ret[1] << 8)

        return fw_version, board_version

    def init(self, B=True):
        super(TJMonoPix, self).init()

        self.fw_version, self.board_version = self.get_daq_version()
        logger.info('Found board %s running firmware version %s' % (self.board_version, self.fw_version))

        # do this before powering up
        self['CONF_SR'].set_size(3925)
        self['CONF']['DEF_CONF_N'] = 0
        self['CONF']['AB_SELECT'] = B
        self['CONF'].write()

        self['data_rx'].CONF_START_FREEZE = 57  # default 57
        self['data_rx'].CONF_STOP_FREEZE = 95  # default 95
        self['data_rx'].CONF_START_READ = 60  # default 60
        self['data_rx'].CONF_STOP_READ = 62  # default 62
        self['data_rx'].CONF_STOP = 100  # default 100

        self.power_on()

        self['CONF']['RESET_BCID'] = 1
        self['CONF']['RESET'] = 1
        self['CONF'].write()

        self['CONF']['EN_BX_CLK'] = 1
        self['CONF']['EN_OUT_CLK'] = 1
        self['CONF'].write()

        self['CONF']['RESET_BCID'] = 0
        self['CONF']['RESET'] = 0
        self['CONF'].write()

        self.default_conf()

        self.set_icasn_dacunits(0, 0)
        self.set_vreset_dacunits(35, 0)
        self.set_ireset_dacunits(2, 1, 0)
        #self.set_ireset_dacunits(128 + 5, 0)
        self.set_ithr_dacunits(30, 0)
        self.set_idb_dacunits(50, 0)

        self['CONF_SR']['EN_HV'].setall(False)
        self['CONF_SR']['EN_COMP'].setall(False)
        self['CONF_SR']['EN_PMOS'].setall(False)
        self['CONF_SR']['EN_PMOS_NOSF'].setall(False)
        self['CONF_SR']['EN_TEST_PATTERN'].setall(False)

        self['CONF_SR']['MASKD'].setall(False)
        self['CONF_SR']['MASKH'].setall(False)
        self['CONF_SR']['MASKV'].setall(False)

        self.write_conf()

        self['CONF']['DEF_CONF_N'] = 1
        self['CONF'].write()

        logging.info(str(self.get_power_status()))

    def default_conf(self):

	self['CONF_SR']['nEN_HITOR_OUT'].setall(True)
	self['CONF_SR']['EN_HITOR_OUT'].setall(True)
	self['CONF_SR']['nEN_OUT'].setall(True)
	self['CONF_SR']['EN_OUT'].setall(False)
	self['CONF_SR']['EN_HV'].setall(True)
	self['CONF_SR']['EN_COMP'].setall(True)
	self['CONF_SR']['EN_PMOS'].setall(True)
	self['CONF_SR']['EN_PMOS_NOSF'].setall(True)
	self['CONF_SR']['EN_TEST_PATTERN'].setall(False)

	self['CONF_SR']['SWCNTL_VRESET_P'] = 0
	self['CONF_SR']['SWCNTL_VRESET_D'] = 0
	self['CONF_SR']['SWCNTL_VL'] = 0
	self['CONF_SR']['SWCNTL_VH'] = 0
	self['CONF_SR']['SWCNTL_VCLIP'] = 0
	self['CONF_SR']['SWCNTL_VCASN'] = 0
	self['CONF_SR']['SWCNTL_ITHR'] = 0
	self['CONF_SR']['SWCNTL_IRESET'] = 0
	self['CONF_SR']['SWCNTL_IREF'] = 0
	self['CONF_SR']['SWCNTL_IDB'] = 0
	self['CONF_SR']['SWCNTL_ICASN'] = 0
	self['CONF_SR']['SWCNTL_IBIAS'] = 0
	self['CONF_SR']['SWCNTL_DACMONV'] = 0
	self['CONF_SR']['SWCNTL_DACMONI'] = 0

	self['CONF_SR']['SET_IBUFN_L'] = 0b1001
	self['CONF_SR']['SET_IBUFP_L'] = 0b0101
	self['CONF_SR']['SET_IBUFP_R'] = 0b0101
	self['CONF_SR']['SET_IBUFN_R'] = 0b1001

	self['CONF_SR']['SET_IRESET_BIT'] = 1

	self['CONF_SR']['SET_VCLIP'].setall(False)
	self['CONF_SR']['SET_VRESET_D'].setall(False)
	self['CONF_SR']['SET_VRESET_D'][45] = 1
	self['CONF_SR']['SET_VCASN'].setall(False)
	self['CONF_SR']['SET_VCASN'][40] = 1
	self['CONF_SR']['SET_VL'].setall(False)
	self['CONF_SR']['SET_VL'][44] = 1
	self['CONF_SR']['SET_VH'].setall(False)
	self['CONF_SR']['SET_VH'][79] = 1
	self['CONF_SR']['SET_VRESET_P'].setall(False)
	self['CONF_SR']['SET_VRESET_P'][16] = 1

	#Be carefull!!! because the type is BitLogic, the slicing is verilog type not python, this means the limits are inclusive. Also MSB must be first in the slice
	self['CONF_SR']['SET_ICASN'].setall(False)
	self['CONF_SR']['SET_ICASN'][82:45] = True
	self['CONF_SR']['SET_IRESET'].setall(False)
	self['CONF_SR']['SET_IRESET'][71:57] = True
	self['CONF_SR']['SET_ITHR'].setall(False)
	self['CONF_SR']['SET_ITHR'][67:60] = True
	self['CONF_SR']['SET_IDB'].setall(False)
	self['CONF_SR']['SET_IDB'][78:50] = True
	self['CONF_SR']['SET_IBIAS'].setall(False)
	self['CONF_SR']['SET_IBIAS'][86:41] = True

	self['CONF_SR']['DIG_MON_SEL'].setall(False)

	self['CONF_SR']['MASKD'].setall(True)
	self['CONF_SR']['MASKH'].setall(True)
	self['CONF_SR']['MASKV'].setall(True)

	self['CONF_SR']['INJ_ROW'].setall(False)
	self['CONF_SR']['INJ_IN_MON_R'] = 0
	self['CONF_SR']['INJ_IN_MON_L'] = 0
	self['CONF_SR']['COL_PULSE_SEL'].setall(False)

    def write_conf(self):
        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)

    def power_on(self, **kwargs):
        # Set power

        # Sense resistor is 0.1Ohm, so 300mA=60mA*5
        self['VDDP'].set_current_limit(60, unit='mA')
        self['VDDP'].set_voltage(1.8, unit='V')

        self['VPCSWSF'].set_voltage(0.5, unit='V')
        self['VPC'].set_voltage(1.3, unit='V')
        self['BiasSF'].set_current(100, unit='uA')

        self['VDDA'].set_voltage(1.8, unit='V')
        self['VDDA'].set_enable(True)
        time.sleep(0.01)

        self['VDDP'].set_enable(True)

        self['VDDA_DAC'].set_voltage(1.8, unit='V')
        self['VDDA_DAC'].set_enable(True)

        self['VDDD'].set_voltage(1.8, unit='V')
        self['VDDD'].set_enable(True)

    def write_conf(self):
        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)
        self.conf_flg = 0

    def load_config(self, filename):

        with open(filename) as f:
            conf = yaml.load(f)
        self.default_conf()
        self.write_conf()
        time.sleep(0.1)  # mabe not needed?

        # maybe update power here also?

        self.set_all_mask(mask=conf['CONF_SR'])
        self.write_conf()
        time.sleep(0.1)  # mabe not needed?

        # update gloable setting
        # TODO !!
        self.write_conf()

    def save_config(self, filename=None):
        conf = get_configuration
        conf['SET'] = self.SET
        conf['conf_flg'] = self.conf_flg
        if filename == None:
            filename = None
            # time.strf TODO!
        with open(filename, 'w') as f:
            f.write(yaml.yamldump(conf))

    def power_on(self, VDDA=1.8, VDDP=1.8, VDDA_DAC=1.8, VDDD=1.8, VPCSWSF=0.5, VPC=1.3, BiasSF=100, INJ_LO=0.2, INJ_HI=3.6):
        # Set power

        # Sense resistor is 0.1Ohm, so 300mA=60mA*5
        self['VDDP'].set_current_limit(60, unit='mA')

        self['VPCSWSF'].set_voltage(VPCSWSF, unit='V')
        self.SET["VPCSWSF"] = VPCSWSF
        self['VPC'].set_voltage(VPC, unit='V')
        self.SET["VPC"] = VPC
        self['BiasSF'].set_current(BiasSF, unit='uA')
        self.SET["BiasSF"] = BiasSF

        self['VDDA'].set_voltage(VDDA, unit='V')
        self['VDDA'].set_enable(True)
        self.SET["VDDA"] = VDDA
        time.sleep(0.01)

        self['VDDP'].set_voltage(VDDP, unit='V')
        self['VDDP'].set_enable(True)
        self.SET["VDDP"] = VDDP

        self['VDDA_DAC'].set_voltage(VDDA_DAC, unit='V')
        self['VDDA_DAC'].set_enable(True)
        self.SET["VDDA_DAC"] = VDDA_DAC

        self['VDDD'].set_voltage(VDDD, unit='V')
        self['VDDD'].set_enable(True)
        self.SET["VDDD"] = VDDD

        self['INJ_LO'].set_voltage(INJ_LO, unit='V')
        self.SET["INJ_LO"] = INJ_LO
        self['INJ_HI'].set_voltage(INJ_HI, unit='V')
        self.SET["INJ_HI"] = INJ_HI

    def power_off(self):
        self['INJ_LO'].set_voltage(0.2, unit='V')
        self.SET["INJ_LO"] = 0.2
        self['INJ_HI'].set_voltage(0.2, unit='V')
        self.SET["INJ_LO"] = 0.2
        # Deactivate all
        for pwr in ['VDDP', 'VDDD', 'VDDA', 'VDDA_DAC']:
            self[pwr].set_enable(False)

    def get_power_status(self, log=False):
        status = {}

        for pwr in ['VDDP', 'VDDD', 'VDDA', 'VDDA_DAC', 'VPCSWSF', 'VPC', 'BiasSF']:
            status[pwr+' [V]'] = self[pwr].get_voltage(unit='V')
            status[pwr+' [mA]'] = 5 * self[pwr].get_current(unit='mA') if pwr in [
                "VDDP", "VDDD", "VDDA", "VDDA_DAC"] else self[pwr].get_current(unit='mA')
        return status

    def set_inj_amplitude(self):
        self['INJ_LO'].set_voltage(0.2, unit='V')
        self['INJ_HI'].set_voltage(3.6, unit='V')

    def interprete_raw_data(self, raw_data):
        hit_data_sel = ((raw_data & 0xf0000000) == 0)
        hit_data = raw_data[hit_data_sel]
        hit_dtype = np.dtype(
            [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("noise", "<u1")])
        ret = np.empty(hit_data.shape[0], dtype=hit_dtype)

        ret['col'] = (hit_data & 0x3f)
        ret['row'] = (hit_data & 0x7FC0) >> 6
        ret['te'] = (hit_data & 0x1F8000) >> 15
        ret['le'] = (hit_data & 0x7E00000) >> 21
        ret['noise'] = (hit_data & 0x8000000) >> 27

        return ret

    def interprete_data(self, raw_data):
        hit_data_sel = ((raw_data & 0xf0000000) == 0)
        hit_data = raw_data[hit_data_sel]
        hit_dtype = np.dtype(
            [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("noise", "<u1")])
        ret = np.empty(hit_data.shape[0], dtype=hit_dtype)

        ret['col'] = 2 * (hit_data & 0x3f) + \
            (((hit_data & 0x7FC0) >> 6) // 256)
        ret['row'] = ((hit_data & 0x7FC0) >> 6) % 256
        ret['te'] = (hit_data & 0x1F8000) >> 15
        ret['le'] = (hit_data & 0x7E00000) >> 21
        ret['noise'] = (hit_data & 0x8000000) >> 27

        return ret

    def set_all_mask(self, mask=None):
        self.conf_flg = 1
        if mask == None:
            self['CONF_SR']['MASKD'].setall(False)
            self['CONF_SR']['MASKH'].setall(False)
            self['CONF_SR']['MASKV'].setall(False)
            # hit_or
            self['CONF_SR']['DIG_MON_SEL'].setall(False)
            # ENABLES OR DISABLES THE NORMAL HITOR PADS, HITOR0-3 =  1-4 flavor, ACTIVE LOW
            self['CONF_SR']['EN_HITOR_OUT'].setall(True)
            self['CONF_SR']['nEN_HITOR_OUT'].setall(True)
            # readout
            self['CONF_SR']['EN_PMOS_NOSF'].setall(False)
            self['CONF_SR']['EN_PMOS'].setall(False)
            self['CONF_SR']['EN_COMP'].setall(False)
            self['CONF_SR']['EN_HV'].setall(False)
            # ENABLES OR DISABLES THE NORMAL OUTPUT PADS, ACTIVE LOW
            self['CONF_SR']['EN_OUT'].setall(True)
            # ENABLES OR DISABLES THE COMPLEMENTARY OUTPUT PADS, ACTIVE LOW
            self['CONF_SR']['nEN_OUT'].setall(True)
            # injection
            self['CONF_SR']['INJ_ROW'].setall(False)
            self['CONF_SR']['INJ_IN_MON_R'] = 0
            self['CONF_SR']['INJ_IN_MON_L'] = 0
            self['CONF_SR']['COL_PULSE_SEL'].setall(False)
        else:
            for m in ['MASKD', 'MASKH', 'MASKV', 'DIG_MON_SEL', 'DIG_MON_SEL', 'EN_HITOR_OUT', 'nEN_HITOR_OUT',
                      'EN_PMOS_NOSF', 'EN_PMOS', 'EN_COMP', 'EN_HV', 'EN_OUT', 'nEN_OUT',
                      'INJ_ROW', 'INJ_IN_MON_R', 'INJ_IN_MON_L', 'COL_PULSE_SEL']:
                self['CONF_SR'][m] = conf[m]

    def mask(self, flavor, col, row):
	assert 0 <= flavor <= 3, 'Flavor must be between 0 and 3'
	assert 0 <= col <= 111, 'Column must be between 0 and 111'
	assert 0 <= row <= 223, 'Row must be between 0 and 223'
	mcol=(flavor)*112+col
	md = mcol-row if (mcol-row) >= 0 else 448+mcol-row
	self['CONF_SR']['MASKD'][md] = False
	self['CONF_SR']['MASKV'][mcol] = False
	self['CONF_SR']['MASKH'][row] = False

    def enable_injection(self, flavor, col, row):
	assert 0 <= flavor <= 3, 'Flavor must be between 0 and 3'
	assert 0 <= col <= 111, 'Column must be between 0 and 111'
	assert 0 <= row <= 223, 'Row must be between 0 and 223'
	self['CONF_SR']['COL_PULSE_SEL'][(flavor*112)+col] = 1
	self['CONF_SR']['INJ_ROW'][row] = 1

    def enable_column_hitor(self, flavor, col):
	assert 0 <= flavor <= 3, 'Flavor must be between 0 and 3'
	self['CONF_SR']['DIG_MON_SEL'][(flavor*112)+col] = 1

############################## SET BIAS CURRENTS AND VOLTAGES ##############################

    def set_ibias_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_IBIAS'].setall(False)
	self['CONF_SR']['SET_IBIAS'][high:low] = True
	if (printen == 1):
		logger.info( 'ibias = ' +str(1400.0*((dacunits+1)/128.0)) + 'nA')

    def set_idb_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_IDB'].setall(False)
	self['CONF_SR']['SET_IDB'][high:low] = True
	if (printen == 1):
		logger.info( 'idb = ' +str(2240.0*((dacunits+1)/128.0)) + 'nA')

    def set_ithr_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_ITHR'].setall(False)
	self['CONF_SR']['SET_ITHR'][high:low] = True
	if (printen == 1):
		logger.info('ithr = ' +str(17.5*((dacunits+1)/128.0)) + 'nA')

    def set_icasn_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_ICASN'].setall(False)
	self['CONF_SR']['SET_ICASN'][high:low] = True
	if (printen == 1):
		logger.info( 'icasn = ' +str(560.0*((dacunits+1)/128.0)) + 'nA')

    def set_ireset_dacunits(self, dacunits, mode, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	assert 0 <= mode <= 1, 'Mode must be 0 (low leakage) or 1 (high leakage)'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_IRESET_BIT'] = mode
	self['CONF_SR']['SET_IRESET'].setall(False)
	self['CONF_SR']['SET_IRESET'][high:low] = True
	if (printen == 1):
		if (mode == 1):
			logger.info( 'ireset = ' +str(4.375*((dacunits+1)/128.0)) + 'nA, high leakage mode')
		else:
			logger.info( 'ireset = ' +str(43.75*((dacunits+1)/128.0)) + 'pA, low leakage mode')

    def set_vreset_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VRESET_P'].setall(False)
   	self['CONF_SR']['SET_VRESET_P'][dacunits] = True
	if (printen == 1):
    		logger.info( 'vreset = ' +str(((1.8/127.0)*dacunits+0.555)) + 'V')

    def set_vh_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VH'].setall(False)
   	self['CONF_SR']['SET_VH'][dacunits] = True
	if (printen == 1):
    		logger.info( 'vh = ' +str(((1.8/127.0)*dacunits+0.385)) + 'V')

    def set_vl_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VL'].setall(False)
   	self['CONF_SR']['SET_VL'][dacunits] = True
	if (printen == 1):
    		logger.info( 'vl = ' +str(((1.8/127.0)*dacunits+0.385)) + 'V')

    def set_vcasn_dac_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VCASN'].setall(False)
   	self['CONF_SR']['SET_VCASN'][dacunits] = True
	if (printen == 1):
    		logger.info( 'vcasn = ' +str(((1.8/127.0)*dacunits)) + 'V')

############################## SET data readout ##############################
    def set_tlu(self,tlu_delay=8):
        self["tlu"]["RESET"]=1
        self["tlu"]["TRIGGER_MODE"]=3
        self["tlu"]["EN_TLU_VETO"]=0
        self["tlu"]["MAX_TRIGGERS"]=0
        self["tlu"]["TRIGGER_COUNTER"]=0
        self["tlu"]["TRIGGER_LOW_TIMEOUT"]=0
        self["tlu"]["TRIGGER_VETO_SELECT"]=0
        self["tlu"]["TRIGGER_THRESHOLD"]=0
        self["tlu"]["DATA_FORMAT"]=2
        self["tlu"]["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]=20
        self["tlu"]["TRIGGER_DATA_DELAY"]=tlu_delay
        self["tlu"]["TRIGGER_SELECT"]=0
        self["timestamp_tlu"]["RESET"]=1
        self["timestamp_tlu"]["EXT_TIMESTAMP"]=1
        self["timestamp_tlu"]["ENABLE_TOT"]=0
        logging.info("set_tlu: tlu_delay=%d"%tlu_delay)

        self["timestamp_tlu"]["ENABLE_EXTERN"]=1
        self["tlu"]["TRIGGER_ENABLE"]=1

    def stop_tlu(self):
        self["tlu"]["TRIGGER_ENABLE"]=0
        self["timestamp_tlu"]["ENABLE_EXTERN"]=0
        lost_cnt=self["tdc"]["LOST_COUNT"]
        if lost_cnt!=0:
            logging.warn("stop_tdc: error cnt=%d"%lost_cnt)

    def set_timestamp(self,src="rx1"):
        self["timestamp"].reset()
        self["timestamp"]["EXT_TIMESTAMP"]=True
        self["timestamp"]["ENABLE"]=1
        logging.info("set_timestamp:src=%s"%src)
        
    def stop_timestamp(self):
        self["timestamp"]["ENABLE"]=0
        lost_cnt=self["timestamp"]["LOST_COUNT"]
        if lost_cnt!=0:
            logging.warn("stop_timestamp: lost_cnt=%d"%lost_cnt)
        return lost_cnt

    #def set_monoread(self, start_freeze=64, start_read=66, stop_read=68, stop_freeze=100, stop=105, en=True):
    def set_monoread(self, start_freeze=57, start_read=60, stop_read=62, stop_freeze=95, stop=100, en=True):
        self['data_rx'].CONF_START_FREEZE = start_freeze  # default 57
        self['data_rx'].CONF_STOP_FREEZE = stop_freeze  # default 95
        self['data_rx'].CONF_START_READ = start_read  # default 60
        self['data_rx'].CONF_STOP_READ = stop_read  # default 62
        self['data_rx'].CONF_STOP = stop  # default 100

        self['fifo'].reset()
        time.sleep(0.1)
        self['fifo'].reset()
        self['data_rx'].set_en(en)

    def stop_monoread(self):
        self['data_rx'].set_en(False)
        lost_cnt = self["data_rx"]["LOST_COUNT"]
        if lost_cnt != 0:
            logging.warn("stop_monoread: error cnt=%d" % lost_cnt)

    def set_tdc(self):
        self["tdc"]["RESET"]=1
        self["tdc"]["EXT_TIMESTAMP"]=1
        self["tdc"]["ENABLE_TOT"]=1
        self["tdc"]["ENABLE"]=1
        logging.info("set_tdc:")

    def stop_tdc(self):
        self["tdc"]["ENABLE"]=0
        lost_cnt=self["tdc"]["LOST_COUNT"]
        if lost_cnt!=0:
            logging.warn("stop_tdc: error cnt=%d"%lost_cnt)

########################## scans  #####################################################################
    def inj_scan(self, flavor, col, row, VL, VHLrange, start_dif, delay, width, repeat, noise_en, analog_en, sleeptime):

        hits = np.zeros((VHLrange+1), dtype=int)

        self['inj'].set_delay(delay)
        self['inj'].set_width(width)
        self['inj'].set_repeat(repeat)
        self['inj'].set_en(0)

        self['CONF_SR']['INJ_ROW'].setall(False)
        if analog_en == 1:
            self['CONF_SR']['INJ_ROW'][223] = True
        self['CONF_SR']['COL_PULSE_SEL'].setall(False)
        self.enable_injection(flavor, col, row)
        self.set_vl_dacunits(VL, 0)
        self.set_vh_dacunits(VL+start_dif, 0)
        self.write_conf()

        for _ in range(5):
            x2 = self['fifo'].get_data()

        for i in range(VHLrange+1):
            self.set_vh_dacunits(VL+i+start_dif, 0)
            self.write_conf()

            while not self['inj'].is_ready:
                time.sleep(0.001)
            for _ in range(10):
                self['inj'].is_ready
            self["inj"].start()

            time.sleep(sleeptime)
            x = self['fifo'].get_data()
            ix = self.interprete_data(x)

            cnt = 0
            for hit in ix:
                if hit['col'] == col and hit['row'] == row:
                    if noise_en == 1:
                        if hit['noise'] == 0:
                            cnt += 1
                    else:
                        cnt += 1

            hits[i] = cnt

        return hits


    def inj_scan_row(self, flavor, col, startrow, rownumber, VL, VHLrange, start_dif, delay, width, repeat, noise_en, analog_en, sleeptime):

        hits = np.zeros((rownumber, VHLrange+1), dtype=int)

        self['inj'].set_delay(delay)
        self['inj'].set_width(width)
        self['inj'].set_repeat(repeat)
        self['inj'].set_en(0)

        self['CONF_SR']['INJ_ROW'].setall(False)
        if analog_en == 1:
            self['CONF_SR']['INJ_ROW'][223]=True
        self['CONF_SR']['COL_PULSE_SEL'].setall(False)
        for i in range (startrow, startrow+rownumber):
            self.enable_injection(flavor,col,i)  
        self.set_vl_dacunits(VL,0)
        self.set_vh_dacunits(VL+start_dif,0)
        self.write_conf()

        for _ in range(5):
            x2 = self['fifo'].get_data()
            time.sleep(0.01)

        for i in range(VHLrange+1):
            if i!=0:
                self.set_vh_dacunits(VL+i+start_dif,0)
                self.write_conf()

            while not self['inj'].is_ready:
                time.sleep(0.001)
            for _ in range(10):
                self['inj'].is_ready
            self["inj"].start()

            time.sleep(sleeptime)
            x = self['fifo'].get_data()
            ix = self.interprete_data(x)
            ixd=np.delete(ix, np.where((ix['col']!=col)|(ix['row']<startrow)|(ix['row']>=startrow+rownumber))[0])
            if noise_en == 1:
                ixd=np.delete(ixd, np.where((ix['noise'] == 1))[0])

            uniquerow, countrow = np.unique(ixd['row'], return_counts=True)

            if (uniquerow.size != 0):
                hits[uniquerow-startrow,i]=countrow

        return hits

    def inj_scan(self, flavor, col_high, col_low, row_high, row_low, rowstep, VL, VHLrange, start_dif, delay, width, repeat, noise_en, analog_en, sleeptime, partname):

	col_no=col_high-col_low+1
	row_no=row_high-row_low+1
	pix_no = (col_no)*(row_no)
	scurve = np.zeros((pix_no,VHLrange+1), dtype=int)
	#xhits = range(start_dif,VHLrange+start_dif+1)

	i = 0
	for col in range(col_low,col_high+1):
    	    for row in range(row_low,row_high+1-rowstep,rowstep):
                #print 'row=%d' %row
                hits = self.inj_scan_row(flavor, col, row, rowstep, VL, VHLrange, start_dif, delay, width, repeat, noise_en, analog_en, sleeptime)
                print 'i=%d' %i
                #print hits
                scurve[i:i+20] = hits
                i += 20
                #print 'i+=%d' %i
                time.sleep(0.01)
        
            #print 'row=%d' %(row+rowstep)
            print 'i=%d' %i        
            hits = chip.inj_scan_row(flavor, col, row+rowstep, (row_high%(row+rowstep))+1, VL, VHLrange, start_dif, delay, width, repeat, noise_en, analog_en, sleeptime)
            #print hits
            scurve[i:i+((row_high%(row+rowstep))+1)] = hits
            i += (row_high%(row+rowstep))+1
            #print (row_high%(row+rowstep))+1
            print 'i=%d' %i
            time.sleep(0.01)

        #print scurve
        np.save('scurvedata'+partname+'.npy',scurve)
	logger.info(' S-Curve data saved successfully')

if __name__ == '__main__':
    chip = TJMonoPix()
    chip.init()
