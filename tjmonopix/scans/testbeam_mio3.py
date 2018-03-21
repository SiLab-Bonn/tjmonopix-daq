import time
import tables as tb
import numpy as np
import yaml
import os
import logging

from tjmonopix.scan_base import ScanBase
from tjmonopix.tjmonopix import TJMonoPix
from tjmonopix.analysis.interpreter import interpret_h5
from tjmonopix.scans.simple_scan import SimpleScan


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='TJ-MONOPIX simple scan \n example: simple_scan --scan_time 10 --data simple_0', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--data',  type=str, default=None,
                        help='Name of data file without extention')
    parser.add_argument('--scan_timeout', type=int, default=10,
                        help="Scan time in seconds. Default=10, disable=0")
    #parser.add_argument('--config_file', type=str, default=None,
    #                    help="Name of config file(yaml)")
    args = parser.parse_args()    

    dut = "/home/silab/tjmonopix/tjmonopix-daq/tjmonopix-daq/tjmonopix/tjmonopix_mio3.yaml"
    scan = SimpleScan(dut=dut,filename=args.data,send_addr="tcp://131.220.162.237:5500")

    ####### CONFIGURE mask ######
    scan.dut['CONF_SR']['EN_PMOS'].setall(True)
    scan.dut['CONF_SR']['MASKD'].setall(True)
    scan.dut['CONF_SR']['MASKH'].setall(True)
    scan.dut['CONF_SR']['MASKV'].setall(True)

    # TO USE THE MASK FUNCTION YOU MUST INPUT THE FLAVOR, COLUMN AND ROW
    # THE FLAVOR NUMERS IS: 0 FOR PMOS_NOSF, 1 FOR PMOS, 2 FOR COMP, 3 FOR HV
    scan.dut.mask(1, 33, 72)
    scan.dut.mask(1, 17, 30)
    scan.dut.mask(1, 19, 31)
    scan.dut.mask(1, 41, 66)
    scan.dut.mask(1, 97, 94)
    scan.dut.mask(1, 34, 151)
    scan.dut.mask(1, 40, 123)
    scan.dut.mask(1, 82, 193)
    scan.dut.mask(1, 71, 31)
    scan.dut.mask(1, 71, 111)
    scan.dut.mask(1, 38, 188)
    scan.dut.mask(1, 97, 214)
    scan.dut.mask(1, 86, 104)
    scan.dut.mask(1, 35, 212)
    scan.dut.mask(1, 35, 88)
    scan.dut.mask(1, 43, 14)
    scan.dut.mask(1, 38, 177)
    scan.dut.mask(1, 17, 57)
    scan.dut.mask(1, 54, 1)
    scan.dut.mask(1, 38, 21)
    scan.dut.mask(1, 71, 9)
    scan.dut.mask(1, 58, 46)
    scan.dut.mask(1, 74, 84)
    scan.dut.mask(1, 53, 167)
    scan.dut.mask(1, 35, 158)
    scan.dut.mask(1, 72, 77)
    scan.dut.mask(1, 14, 54)
    scan.dut.mask(1, 78, 196)
    scan.dut.mask(1, 88, 96)
    scan.dut.mask(1, 78, 209)
    scan.dut.mask(1, 62, 66)
    
    #This sets up the hit_or in a single pixel
    col = 48
    row = 32
    scan.dut['CONF_SR']['EN_HITOR_OUT'][1]=False
    scan.dut.enable_column_hitor(1,col)
    scan.dut['CONF_SR']['MASKH'][row]=False
    scan.dut.write_conf()

    ####### CONFIGURE THE FRONT END ######
    # SET VRESET_P, THIS IS THE BASELINE OF THE FRONT END INPUT, ONE HOT ENCODING
    scan.dut.set_vreset_dacunits(35,1) #1V

    ## 128-bit DAC (7-bit binary equivalent)
    ## SET THE CURRENTS USING THERMOMETER ENCODING, I = #BITS_ACTIVE*140nA*SCALING, SCALING IS DIFFERENT FOR EACH CURRENT
    ## SCALING: IBIAS=10, IDB=16, ITHR=0.125, ICASN=4, IRESET=0.03125
    ## ACTIVE BITS SHOULD BE SET STARTING FROM THE MIDDLE e.g. for 15 active bits, (128-15)/2=56,5 so 56zeros,15ones,57zeros
    ## Thus, Ix[71:57] = True

    # SET ICASN, THIS CURRENT CONTROLS THE OUTPUT BASELINE, BE CAREFUL NOT TO SET IT TO HIGH
    # ALWAYS MONITOR THE POWER AFTER SETTING ICASN. IF VDDD IS SEVERAL mA, REDUCE IT UNTIL IT RETURNS TO 0
    # ICASN MAINLY CONTROLS THE THRESHOLD
    scan.dut.set_icasn_dacunits(0,1) #4.375nA # approx 1.084V at -3V backbias, 600mV at 0V backbias

    # SET IRESET, THIS CURRENT CONTROLS THE RESET RATE OF THE FRONT END INPUT (ALSO THE THRESHOLD)
    scan.dut.set_ireset_dacunits(2,1,1) #270pA, HIGH LEAKAGE MODE, NORMAL SCALING, 0 = LOW LEAKAGE MODE, SCALING*0.01

    # SET ITHR, THIS CURRENT CONTROLS THE RESET RATE OF THE OUTPUT (AND THE THRESHOLD)
    scan.dut.set_ithr_dacunits(5,1) #680pA

    # SET ITHR, THIS CURRENT CONTROLS THE BIASING OF THE DISCRIMINATOR (AND THE THRESHOLD)
    scan.dut.set_idb_dacunits(15,1) #500nA

    # SET IBIAS, THIS CURRENT IS THE DC CURRENT OF THE MAIN BRANCH
    scan.dut.set_ibias_dacunits(50,1) #500nA OF THE FRONT END THAT PROVIDES AMPLIFICATION
    # IT CONTROLS MAINLY THE RISE TIME
    #self.dut.set_ibias_dacunits(50,1) #500nA
    scan.dut.write_conf()
    
    output_filename=scan.start(scan_timeout=args.scan_timeout, with_tdc=True, with_timestamp=True, with_tlu=True)
    scan.analyze()
