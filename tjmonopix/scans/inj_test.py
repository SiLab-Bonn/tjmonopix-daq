import time
import tables as tb
import numpy as np

from tjmonopix.scan_base import ScanBase
from tjmonopix.analysis.interpret_scan import interpret_data


class InjectionTest(ScanBase):
    scan_id = "injection_test"

    def analyze(self, filename=None):
        if not filename:
            filename = self.filename
        
        with tb.open_file(filename, "r+") as data_file:
            raw_data = data_file.root.raw_data[:]
            hit_data = interpret_data(raw_data)
            print(hit_data)

if __name__ == "__main__":
    scan = InjectionTest(working_dir="/home/silab/tjmonopix/scans/")
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
    #scan.dut.enable_injection(1,18,99)

    #scan.dut['CONF_SR']['INJ_ROW'][223] = False # FOR THE ANALOG MONITORING TOP PIXEL
    #scan.dut['CONF_SR']['INJ_IN_MON_L'] = 0 # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS LEFT SIDE
    #scan.dut['CONF_SR']['INJ_IN_MON_R'] = 0 # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS RIGHT SIDE

    # FRONT END TUNING
    scan.dut.set_vl_dacunits(49,1)
    scan.dut.set_vh_dacunits(79,1)
    scan.dut.set_vreset_dacunits(40,1)
    scan.dut.set_icasn_dacunits(0,1)
    scan.dut.set_ireset_dacunits(3,1,1) # Change analog input (at the sensor) reset rate, also reduces pile-up at the input
    scan.dut.set_ithr_dacunits(8,1) # change analog output reset rate, tot resolution
    scan.dut.set_idb_dacunits(15,1) # Hihter IDB, Higher Threshold
    scan.dut.set_ibias_dacunits(50,1)
    #################################

    scan.dut.write_conf()


    with scan.readout():
        scan.dut["data_rx"].set_en(True)
        time.sleep(10)
  
    scan.stop()
    scan.analyze()
