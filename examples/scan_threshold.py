import yaml

from basil.dut import Dut
from tjmonopix.tjmonopix import TJMonoPix
from tjmonopix.scans.threshold_scan import ThresholdScan

def reconfigure_frontend(dut):
    # RECONFIGURE THE FRONT END #
    dut.set_vreset_dacunits(dut_config["vreset_dacunits"], 1)  # 1V
    dut.set_vcasn_dac_dacunits(dut_config["vcasn_dacunits"], 1)
    dut.set_icasn_dacunits(dut_config["icasn_dacunits"], 1)
    dut.set_ireset_dacunits(dut_config["ireset_dacunits"]["value"], dut_config["ireset_dacunits"]["mode"], 1)
    dut.set_ithr_dacunits(dut_config["ithr_dacunits"], 1)
    dut.set_idb_dacunits(dut_config["idb_dacunits"], 1)
    dut.set_ibias_dacunits(dut_config["ibias_dacunits"], 1)
    dut["CONF_SR"]["SET_ICASN"].setall(False)  # Fix for cooled devices

    dut.write_conf()

    time.sleep(1)
    dut.set_monoread()
    dut.cleanup_fifo(10)


if __name__ == "__main__":
    config_file = 'W04R22_pmos.yaml'
    output_file = './threshold_scan'

    # Load configuration file
    with open(config_file, "r") as config:
        configuration = yaml.safe_load(config)
        dut_config = configuration["dut"]
        scan_config = configuration["scan"]

    # Initialize DUT
    dut = TJMonoPix(conf=dut_config["file"])
    dut.init(fl=dut_config["flavor"])

    # Configure the front end
    dut.set_vreset_dacunits(dut_config["vreset_dacunits"], 1)  # 1V
    dut.set_vcasn_dac_dacunits(dut_config["vcasn_dacunits"], 1)
    dut.set_icasn_dacunits(dut_config["icasn_dacunits"], 1)
    dut.set_ireset_dacunits(dut_config["ireset_dacunits"]["value"], dut_config["ireset_dacunits"]["mode"], 1)
    dut.set_ithr_dacunits(dut_config["ithr_dacunits"], 1)
    dut.set_idb_dacunits(dut_config["idb_dacunits"], 1)
    dut.set_ibias_dacunits(dut_config["ibias_dacunits"], 1)

    dut.write_conf()

    # Enable pixels
    dut['CONF_SR']['MASKD'].setall(True)  # active low
    dut['CONF_SR']['MASKH'].setall(True)
    dut['CONF_SR']['MASKV'].setall(True)
    dut['CONF_SR'][dut_config["flavor"]].setall(True) # active high

    dut.set_monoread()
    dut.cleanup_fifo(10)

    # Automatically mask noisy pixels
    # dut.auto_mask(th=2, step=5, exp=0.5)
    # dut.cleanup_fifo(10)

    # Mask pixels
    for mask_pix in configuration["mask"]:
        dut.mask(*mask_pix)

    # Threshold scan
    thr_scan = ThresholdScan(dut=dut, filename=output_file, send_addr=scan_config["online_monitor"])
    dut.save_config(thr_scan.output_filename + '.yaml')
    thr_scan.start(with_tdc=False, with_timestamp=False, with_tlu=False, with_tj=True)
    thr_scan.analyze()
    thr_scan.plot()
