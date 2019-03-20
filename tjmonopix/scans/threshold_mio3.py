import time
import numpy as np
import yaml
import logging

from tjmonopix.tjmonopix import TJMonoPix
from tjmonopix.scans.threshold_scan import ThresholdScan

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='TJ-MONOPIX simple scan \n example: simple_scan --scan_time 10 --data simple_0', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--config', type=str, default=None, help='Name of scan configuration file')
    parser.add_argument('-d', '--data', type=str, default=None, help='Name of data file without extension')

    args = parser.parse_args()

    # Load configuration file
    with open(args.config, "r") as config_file:
        configuration = yaml.safe_load(config_file)
        dut_config = configuration["dut"]
        scan_config = configuration["scan"]

    # TESTBEAM: dut = "/home/silab/tjmonopix/tjmonopix-daq/tjmonopix-testbeam-april/tjmonopix/tjmonopix_mio3.yaml"
    dut = '/home/silab/git/tjmonopix-redo/tjmonopix/tjmonopix_mio3.yaml'
    dut = TJMonoPix(conf=dut)
    dut.init(fl="EN_" + dut_config["flavor"])

    mask = 'auto'
    # maskedpix_file = "/media/silab/Maxtor/tjmonopix-data/measurements/source_scan/modified_process/pmos/W04R08_-6_-6_idb30_conf.yaml"
    if mask == '':
            logging.warn("A masked pixel file was not specified. The device will probably show noisy pixels.")
    elif mask == 'auto':
        pass  # execute later
    elif mask == 'hitor':
        dut.hitor_inarea(hitorpix=[50, 102], flav=3, col_rad=5, row_rad=5, first=True)
        dut.hitor_inarea(hitorpix=[50, 132], flav=3, col_rad=5, row_rad=5, first=False)
        dut.write_conf()
    else:
        with open(mask, 'r') as f:
            conf = yaml.load(f)
            logging.info("Loading pixel masks from: " + str(mask))
            dut.set_all_mask(conf['CONF_SR'])
            disabledpix = dut.get_disabled_pixel()

            logging.info("Number of disabled pixels (Noisy+Ghost): " + str(np.shape(np.argwhere(disabledpix[(dut.fl_n * 112):(dut.fl_n + 1) * 112, :] == 0))[0]))

    # CONFIGURE THE FRONT END #
    # SET VRESET_P, THIS IS THE BASELINE OF THE FRONT END INPUT, ONE HOT ENCODING
    dut.set_vreset_dacunits(dut_config["vreset_dacunits"], 1)  # 1V

    # 128-bit DAC (7-bit binary equivalent)
    # SET THE CURRENTS USING THERMOMETER ENCODING, I = #BITS_ACTIVE*140nA*SCALING, SCALING IS DIFFERENT FOR EACH CURRENT
    # SCALING: IBIAS=10, IDB=16, ITHR=0.125, ICASN=4, IRESET=0.03125
    # ACTIVE BITS SHOULD BE SET STARTING FROM THE MIDDLE e.g. for 15 active bits, (128-15)/2=56,5 so 56zeros,15ones,57zeros
    # Thus, Ix[71:57] = True

    # SET ICASN, THIS CURRENT CONTROLS THE OUTPUT BASELINE, BE CAREFUL NOT TO SET IT TO HIGH
    # ALWAYS MONITOR THE POWER AFTER SETTING ICASN. IF VDDD IS SEVERAL mA, REDUCE IT UNTIL IT RETURNS TO 0
    # ICASN MAINLY CONTROLS THE THRESHOLD
    # dut.set_icasn_dacunits(0,1) #4.375nA # approx 1.084V at -3V backbias, 600mV at 0V backbias
    dut.set_icasn_dacunits(dut_config["icasn_dacunits"], 1)  # 4.375nA # approx 1.084V at -3V backbias, 600mV at 0V backbias

    # SET IRESET, THIS CURRENT CONTROLS THE RESET RATE OF THE FRONT END INPUT (ALSO THE THRESHOLD)
    dut.set_ireset_dacunits(dut_config["ireset_dacunits"]["value"], dut_config["ireset_dacunits"]["mode"], 1)  # 270pA, HIGH LEAKAGE MODE, NORMAL SCALING, 0 = LOW LEAKAGE MODE, SCALING*0.01

    # SET ITHR, THIS CURRENT CONTROLS THE RESET RATE OF THE OUTPUT (AND THE THRESHOLD)
    # scan.dut.set_ithr_dacunits(30,1) #680pA
    dut.set_ithr_dacunits(dut_config["ithr_dacunits"], 1)  # 680pA 27.03.14:30-

    # SET ITHR, THIS CURRENT CONTROLS THE BIASING OF THE DISCRIMINATOR (AND THE THRESHOLD)
    # scan.dut.set_idb_dacunits(15,1) #500nA
    # scan.dut.set_idb_dacunits(20,1) #500nA
    dut.set_idb_dacunits(dut_config["idb_dacunits"], 1)  # 500nA

    # SET IBIAS, THIS CURRENT IS THE DC CURRENT OF THE MAIN BRANCH
    dut.set_ibias_dacunits(dut_config["ibias_dacunits"], 1)  # 500nA OF THE FRONT END THAT PROVIDES AMPLIFICATION
    # IT CONTROLS MAINLY THE RISE TIME
    # self.dut.set_ibias_dacunits(50,1) #500nA
    dut.write_conf()

    time.sleep(1)
    dut.set_monoread()
    dut.cleanup_fifo(10)

    if mask == 'auto':
        dut.auto_mask(th=2, step=5, exp=0.5)
        dut.cleanup_fifo(15)

    for mask_pix in configuration["mask"]:
        dut.mask(*mask_pix)

    scan = ThresholdScan(dut=dut, filename=args.data, send_addr=scan_config["online_monitor"])
    dut.save_config(scan.output_filename + '.yaml')
    scan.start(with_tdc=False, with_timestamp=False, with_tlu=False, with_tj=True)
    scan.analyze(scan.output_filename + '.h5')
