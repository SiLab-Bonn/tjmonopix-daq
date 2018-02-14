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

logger = logging.getLogger('RD53A')
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
#         print self.board_version
#         logger.info('Found board %s running firmware version %s' % (self.hw_map[self.board_version], self.fw_version))

#         if self.fw_version != VERSION[:3]:     # Compare only the first two digits
#             raise Exception("Firmware version %s does not satisfy version requirements %s!)" % ( self.fw_version, VERSION))

        self['CONF_SR'].set_size(3924)

    def write_conf(self):

        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)

    def power_on(self, **kwargs):
        # Set power
        # TODO: Is a current limit necessary?
        self['VDDP'].set_voltage(1.8, unit='V')
        self['VDDP'].set_enable(True)
        self['VDDD'].set_voltage(1.8, unit='V')
        self['VDDD'].set_enable(True)
        self['VDDA'].set_voltage(1.8, unit='V')
        self['VDDA'].set_enable(True)
        self['VDDA_DAC'].set_voltage(1.8, unit='V')
        self['VDDA_DAC'].set_enable(True)

    def power_off(self):
        # Deactivate all
        for pwr in ['VDDP', 'VDDD', 'VDDA', 'VDDA_DAC']:
            self[pwr].set_enable(False)

    def get_power_status(self, log=False):
        status = {}

        for pwr in ['VDDP', 'VDDD', 'VDDA', 'VDDA_DAC']:
            status[pwr+' [V]'] = self[pwr].get_voltage(unit='V')
            status[pwr+' [mA]'] = self[pwr].get_current(unit='mA')

        return status

    def interpret_raw_data(self, raw_data):
        hit_data_sel = ((raw_data & 0xf0000000) == 0)
        hit_data = raw_data[hit_data_sel]

        hit_dtype = np.dtype(
            [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("noise", "<u1")])
        ret = np.empty(hit_data.shape[0], dtype=hit_dtype)

        ret['col'] = hit_data & 0x3f
        ret['row'] = (hit_data & 0x7FC0) >> 6
        ret['te'] = (hit_data & 0x1F8000) >> 15
        ret['le'] = (hit_data & 0x7E00000) >> 21
        ret['noise'] = (hit_data & 0x8000000) >> 27

        return ret


if __name__ == '__main__':
    chip = TJMonoPix()
    chip.init()
