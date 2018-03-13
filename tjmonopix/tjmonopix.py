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

import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import erf

import basil
#from bitarray import bitarray
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
    format="%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s")

logger = logging.getLogger('TJMONOPIX')
logger.setLevel(loglevel)


class TJMonoPix(Dut):

    """ Map hardware IDs for board identification """
    hw_map = {
        0: 'SIMULATION',
        1: 'MIO2',
    }

    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'tjmonopix' +
                                os.sep + 'tjmonopix.yaml')

        logger.debug("Loading configuration file from {:s}".format(conf))

        super(TJMonoPix, self).__init__(conf)

    def get_daq_version(self):
        ret = self['intf'].read(0x0000, 2)
        fw_version = str('%s.%s' % (ret[1], ret[0]))

        ret = self['intf'].read(0x0002, 2)
        board_version = ret[0] + (ret[1] << 8)

        return fw_version, board_version

    def init(self):
        super(TJMonoPix, self).init()

        self.fw_version, self.board_version = self.get_daq_version()
        print(self.board_version)
        # logger.info('Found board %s running firmware version %s' % (self.hw_map[self.board_version], self.fw_version))

        # if self.fw_version != VERSION[:3]:     # Compare only the first two digits
        #     raise Exception("Firmware version %s does not satisfy version requirements %s!)" % ( self.fw_version, VERSION))

        self['CONF_SR'].set_size(3925)

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

        self['VDDP'].set_current_limit(60, unit='mA') #Sense resistor is 0.1Ohm, so 300mA=60mA*5
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

    def power_off(self):
        # Deactivate all
        for pwr in ['VDDP', 'VDDD', 'VDDA', 'VDDA_DAC']:
            self[pwr].set_enable(False)

    def get_power_status(self, log=False):
        status = {}

        for pwr in ['VDDP', 'VDDD', 'VDDA', 'VDDA_DAC']:
            status[pwr+' [V]'] = self[pwr].get_voltage(unit='V')
            status[pwr+' [mA]'] = 5*self[pwr].get_current(unit='mA')

        return status

    def set_inj_amplitude(self):

        self['INJ_LO'].set_voltage(0.2, unit='V')
        self['INJ_HI'].set_voltage(3.6, unit='V')


    def interprete_raw_data(self, raw_data):
        hit_data_sel = ((raw_data & 0xf0000000) == 0)
        hit_data = raw_data[hit_data_sel]
        hit_dtype = np.dtype([("col","<u1"),("row","<u2"),("le","<u1"),("te","<u1"),("noise","<u1")])
        ret = np.empty(hit_data.shape[0], dtype = hit_dtype)

        ret['col'] = (hit_data & 0x3f) 
        ret['row'] = (hit_data & 0x7FC0) >> 6
        ret['te'] = (hit_data & 0x1F8000) >> 15
        ret['le'] = (hit_data & 0x7E00000) >> 21
        ret['noise'] = (hit_data & 0x8000000) >> 27
        
        return ret


    def interprete_data(self, raw_data):
        hit_data_sel = ((raw_data & 0xf0000000) == 0)
        hit_data = raw_data[hit_data_sel]
        hit_dtype = np.dtype([("col","<u1"),("row","<u2"),("le","<u1"),("te","<u1"),("noise","<u1")])
        ret = np.empty(hit_data.shape[0], dtype = hit_dtype)

        ret['col'] = 2 * (hit_data & 0x3f) + (((hit_data & 0x7FC0) >> 6) // 256)
        ret['row'] = ((hit_data & 0x7FC0) >> 6) % 256
        ret['te'] = (hit_data & 0x1F8000) >> 15
        ret['le'] = (hit_data & 0x7E00000) >> 21
        ret['noise'] = (hit_data & 0x8000000) >> 27

	return ret
	
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
		print 'ibias = ' +str(1400.0*((dacunits+1)/128.0)) + 'nA'

    def set_idb_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_IDB'].setall(False)
	self['CONF_SR']['SET_IDB'][high:low] = True
	if (printen == 1):
		print 'idb = ' +str(2240.0*((dacunits+1)/128.0)) + 'nA'

    def set_ithr_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_ITHR'].setall(False)
	self['CONF_SR']['SET_ITHR'][high:low] = True
	if (printen == 1):
		print 'ithr = ' +str(17.5*((dacunits+1)/128.0)) + 'nA'

    def set_icasn_dacunits(self, dacunits, printen):
	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
	low = (128-(dacunits+1))/2
	high = ((dacunits+1)/2)+63
	self['CONF_SR']['SET_ICASN'].setall(False)
	self['CONF_SR']['SET_ICASN'][high:low] = True
	if (printen == 1):
		print 'icasn = ' +str(560.0*((dacunits+1)/128.0)) + 'nA'

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
			print 'ireset = ' +str(4.375*((dacunits+1)/128.0)) + 'nA, high leakage mode'
		else:
			print 'ireset = ' +str(43.75*((dacunits+1)/128.0)) + 'pA, low leakage mode'

    def set_vreset_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VRESET_P'].setall(False)
   	self['CONF_SR']['SET_VRESET_P'][dacunits] = True
	if (printen == 1):
    		print 'vreset = ' +str(((1.8/127.0)*dacunits+0.555)) + 'V'

    def set_vh_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VH'].setall(False)
   	self['CONF_SR']['SET_VH'][dacunits] = True
	if (printen == 1):
    		print 'vh = ' +str(((1.8/127.0)*dacunits+0.385)) + 'V'

    def set_vl_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VL'].setall(False)
   	self['CONF_SR']['SET_VL'][dacunits] = True
	if (printen == 1):
    		print 'vl = ' +str(((1.8/127.0)*dacunits+0.385)) + 'V'

    def set_vcasn_dac_dacunits(self, dacunits, printen):
    	assert 0 <= dacunits <= 127, 'Dac Units must be between 0 and 127'
    	self['CONF_SR']['SET_VCASN'].setall(False)
   	self['CONF_SR']['SET_VCASN'][dacunits] = True
	if (printen == 1):
    		print 'vcasn = ' +str(((1.8/127.0)*dacunits)) + 'V'

###############################################################################################

    def inj_scan(self, flavor, col, startrow, rownumber, VL, VHLrange, start_dif, delay, width, repeat, noise_en, analog_en, sleeptime):

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

if __name__ == '__main__':
    chip = TJMonoPix()
    chip.init()
