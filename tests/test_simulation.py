#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import unittest
import os
import yaml
import time
from bitarray import bitarray

from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
from tjmonopix.tjmonopix import TJMonoPix


class TestSimulation(unittest.TestCase):

    def setUp(self):

        extra_defines = ['TEST_DC=1']  # Simulate only one double column

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cocotb_compile_and_run(
            sim_files=[root_dir + '/tests/hdl/tb.sv'],
            extra_defines=extra_defines,
            sim_bus='basil.utils.sim.SiLibUsbBusDriver',
            include_dirs=(root_dir, root_dir + "/firmware/src", root_dir + "/tests/hdl"),
            extra='VSIM_ARGS += -wlf /tmp/tjmonopix.wlf \n EXTRA_ARGS += -g2012'
        )

        with open(root_dir + '/tjmonopix/tjmonopix.yaml', 'r') as f:
            cnfg = yaml.safe_load(f)

        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        cnfg['hw_drivers'][0]['init']['no_calibration'] = True

        self.dut = TJMonoPix(conf=cnfg)
        self.dut.init(fl="EN_PMOS_NOSF")

    def test_configuration(self):

        self.dut.set_vreset_dacunits(35)
        self.dut.set_icasn_dacunits(0)
        self.dut.set_ireset_dacunits(2, 1)
        self.dut.set_ithr_dacunits(5)
        self.dut.set_idb_dacunits(15)
        self.dut.set_ibias_dacunits(50)
        self.dut.write_conf()

        self.assertEqual(self.dut['CONF_SR']['SET_VRESET_P'], bitarray('00000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'))
        self.assertEqual(self.dut['CONF_SR']['SET_ICASN'], bitarray('00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000'))
        self.assertEqual(self.dut['CONF_SR']['SET_IRESET'], bitarray('00000000000000000000000000000000000000000000000000000000000000111000000000000000000000000000000000000000000000000000000000000000'))
        self.assertEqual(self.dut['CONF_SR']['SET_IRESET_BIT'], bitarray('1'))
        self.assertEqual(self.dut['CONF_SR']['SET_ITHR'], bitarray('00000000000000000000000000000000000000000000000000000000000001111110000000000000000000000000000000000000000000000000000000000000'))
        self.assertEqual(self.dut['CONF_SR']['SET_IDB'], bitarray('00000000000000000000000000000000000000000000000000000000111111111111111100000000000000000000000000000000000000000000000000000000'))
        self.assertEqual(self.dut['CONF_SR']['SET_IBIAS'], bitarray('00000000000000000000000000000000000000111111111111111111111111111111111111111111111111111000000000000000000000000000000000000000'))

    def test_injection(self):
        self.dut.default_conf()

        # Setup injection
        self.dut['INJ_LO'].set_voltage(0.2, unit='V')
        self.dut['INJ_HI'].set_voltage(3.6, unit='V')
        self.dut['inj'].set_delay(200)
        self.dut['inj'].set_width(4)
        self.dut['inj'].set_repeat(1)
        self.dut['inj'].set_en(0)

        self.dut['CONF_SR']['COL_PULSE_SEL'][0] = 1
        self.dut['CONF_SR']['COL_PULSE_SEL'][1] = 1
        self.dut['CONF_SR']['INJ_ROW'][100] = 1
        self.dut['CONF_SR']['INJ_ROW'][200] = 1
        self.dut.write_conf()

        # Setup flavor
        self.dut['CONF_SR']['EN_COMP'].setall(False)
        self.dut['CONF_SR']['EN_PMOS'].setall(False)
        self.dut['CONF_SR']['EN_PMOS_NOSF'].setall(True)
        self.dut['CONF_SR']['EN_TEST_PATTERN'].setall(False)

        self.dut['CONF_SR']["MASKH"].setall(True)
        self.dut['CONF_SR']["MASKD"].setall(True)
        self.dut['CONF_SR']["MASKV"].setall(True)

        self.dut.write_conf()

        self.dut['data_rx'].set_en(True)

        # Start first injection
        self.dut["inj"].start()

        while not self.dut['inj'].is_ready:
            time.sleep(0.001)

        # Needed for simulation
        for _ in range(10):
            self.dut['inj'].is_ready

        # Start second injection
        self.dut["inj"].start()

        while not self.dut['inj'].is_ready:
            time.sleep(0.001)

        # Needed for simulation
        for _ in range(10):
            self.dut['inj'].is_ready

        hit_data = self.dut.interpret_data(self.dut['fifo'].get_data())
        self.assertListEqual(hit_data["col"].tolist(), [0, 1, 0, 1, 0, 1, 0, 1])
        self.assertListEqual(hit_data["row"].tolist(), [100, 100, 200, 200, 100, 100, 200, 200])
        self.assertListEqual((hit_data["te"] - hit_data["le"]).tolist(), [4, 4, 4, 4, 4, 4, 4, 4])

    def tearDown(self):
        self.dut.close()
        time.sleep(5)
        cocotb_compile_clean()


if __name__ == '__main__':
    unittest.main()
