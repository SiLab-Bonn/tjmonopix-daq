#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import unittest
import os
from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
import sys
import yaml
import time

from tjmonopix.tjmonopix import TJMonoPix

class TestSim(unittest.TestCase):

    def setUp(self):
    
        extra_defines = []
        # if os.environ['SIM']=='icarus':
        os.environ['SIM'] = 'questa'
        # os.environ['WAVES'] = '1'
        # os.environ['GUI'] = '1'
        extra_defines = ['TEST_DC=8']
            
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../
        cocotb_compile_and_run(
            sim_files = [root_dir + '/tests/hdl/tb.sv'],
            extra_defines = extra_defines,
            sim_bus = 'basil.utils.sim.SiLibUsbBusDriver',
            include_dirs = (root_dir, root_dir + "/firmware/src", root_dir + "/tests/hdl"),
            extra = 'VSIM_ARGS += -wlf /tmp/tjmonopix.wlf'
        )
       
        with open(root_dir + '/tjmonopix/tjmonopix.yaml', 'r') as f:
            cnfg = yaml.load(f)

        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        cnfg['hw_drivers'][0]['init']['no_calibration'] = True

        self.dut = TJMonoPix(conf=cnfg)

    def test(self):
        self.dut.init()
        
        self.dut['CONF']['RESET_BCID'] = 1
        self.dut['CONF']['RESET'] = 1
        self.dut['CONF'].write()
        
        self.dut['CONF']['EN_BX_CLK'] = 1
        self.dut['CONF']['EN_OUT_CLK'] = 1
        self.dut['CONF'].write()
        
        self.dut['CONF']['RESET_BCID'] = 0
        self.dut['CONF']['RESET'] = 0
        self.dut['CONF'].write()
	
	self.dut.default_conf()        
       
        self.dut['CONF_SR']['COL_PULSE_SEL'][6] = 1
        self.dut['CONF_SR']['COL_PULSE_SEL'][5] = 1
        self.dut['CONF_SR']['INJ_ROW'][100] = 1
        self.dut['CONF_SR']['INJ_ROW'][200] = 1

        self.dut.write_conf()

        self.dut['CONF']['DEF_CONF_N'] = 1
        self.dut['CONF'].write()
        
        self.dut['data_rx'].set_en(True)
        
        self.dut['inj'].set_delay(200)
        self.dut['inj'].set_width(4)
        self.dut['inj'].set_repeat(1)
        self.dut['inj'].set_en(0)
        self.dut["inj"].start()
       
        while not self.dut['inj'].is_ready:
            time.sleep(0.001)

        for _ in range(10):
            self.dut['inj'].is_ready

        self.dut["inj"].start()
       
        while not self.dut['inj'].is_ready:
            time.sleep(0.001)

        for _ in range(10):
            self.dut['inj'].is_ready

        x = self.dut['fifo'].get_data()
        ix = self.dut.interparete_raw_data(x)
        
        print(ix)

        self.assertEqual(ix['col'].tolist(), [5,5,6,6,5,5,6,6])
        self.assertEqual(ix['row'].tolist(), [100,200,100,200,100,200,100,200])
        
        
    def tearDown(self):
        self.dut.close()
        time.sleep(5)
        cocotb_compile_clean()

if __name__ == '__main__':
    unittest.main()
