import os
import logging
import basil
import yaml
import time
import numpy as np
import tables as tb

from contextlib import contextmanager
from tjmonopix import TJMonoPix
from fifo_readout import FifoReadout


class ScanBase(object):
    """
    Basic run meta class
    """

    def __init__(self, working_dir=None):
        """
        Constructor. Sets output folder, logger and starts device.

        Parameters
        ----------
        working_dir : string, optional
            Path to folder for output data (data and log files). If None,
            create folder "output_data" in current working directory.
        """
        # Set output folder and create if necessary
        self.run_name = self.scan_id + "_" + time.strftime("%Y%m%d_%H%M%S")

        if working_dir:
            self.working_dir = os.path.join(working_dir, self.run_name)
        else:
            self.working_dir = os.path.join(os.getcwd(), "output_data")
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        # Set up logging to log to file and console and format log messages
        self.fh = logging.FileHandler(os.path.join(self.working_dir, "log.log"))
        self.fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s"))
        self.fh.setLevel(logging.DEBUG)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.fh)
        logging.info("Initializing {0}".format(self.__class__.__name__))

        # Initialize chip and power up
        self.dut = TJMonoPix()
        self.dut['CONF']['DEF_CONF_N'] = 0
        self.dut['CONF']['AB_SELECT'] = 1
        self.dut['CONF'].write()
        self.dut.init()

        self.dut['data_rx'].CONF_START_FREEZE = 15  # default 3
        self.dut['data_rx'].CONF_STOP_FREEZE = 100  # default 40
        self.dut['data_rx'].CONF_START_READ = 35  # default 6
        self.dut['data_rx'].CONF_STOP_READ = 37  # default 7
        self.dut['data_rx'].CONF_STOP = 105  # default 45

        self.dut.power_on()

        # TODO MAybe move this stuff somewhere else. For now, leave here since it is needed for everything

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

        self.dut.set_icasn_dacunits(0, 0)
        self.dut.set_vreset_dacunits(35, 0)
        self.dut.set_ireset_dacunits(5, 1, 0)
        self.dut.set_ithr_dacunits(30, 0)
        self.dut.set_idb_dacunits(50, 0)

        self.dut['CONF_SR']['EN_HV'].setall(False)
        self.dut['CONF_SR']['EN_COMP'].setall(False)
        self.dut['CONF_SR']['EN_PMOS'].setall(False)
        self.dut['CONF_SR']['EN_PMOS_NOSF'].setall(False)
        self.dut['CONF_SR']['EN_TEST_PATTERN'].setall(False)

        self.dut['CONF_SR']['MASKD'].setall(False)
        self.dut['CONF_SR']['MASKH'].setall(False)
        self.dut['CONF_SR']['MASKV'].setall(False)

        self.dut.write_conf()

        self.dut['CONF']['DEF_CONF_N'] = 1
        self.dut['CONF'].write()

        # SELECT WHICH DOUBLE COLUMNS TO ENABLE
        self.dut['CONF_SR']['EN_PMOS_NOSF'].setall(False)
        self.dut['CONF_SR']['EN_PMOS'].setall(False)
        self.dut['CONF_SR']['EN_COMP'].setall(False)
        self.dut['CONF_SR']['EN_HV'].setall(False)
        # ENABLES OR DISABLES THE NORMAL OUTPUT PADS, ACTIVE LOW
        self.dut['CONF_SR']['EN_OUT'].setall(False)
        # ENABLES OR DISABLES THE COMPLEMENTARY OUTPUT PADS, ACTIVE LOW
        self.dut['CONF_SR']['nEN_OUT'].setall(True)
        # ENABLES OR DISABLES THE NORMAL HITOR PADS, HITOR0-3 =  1-4 flavor, ACTIVE LOW
        self.dut['CONF_SR']['EN_HITOR_OUT'].setall(True)
        # ENABLES OR DISABLES THE COMPLEMENTARY HITOR PADS, ACTIVE LOW
        self.dut['CONF_SR']['nEN_HITOR_OUT'].setall(True)

        #self.dut['CONF_SR']['EN_PMOS'][9] = 1
        self.dut['CONF_SR']['EN_PMOS'].setall(True)
        #self.dut['CONF_SR']['EN_HITOR_OUT'][1] = 0

        # SELECT WHICH PHYSICAL COLUMNS, ROWS, DIAGONALS TO MASK
        # TO MASK ONE PIXEL, MASKV, MASKH and MASKD OF THIS PIXEL SHOULD BE 0 (FALSE)
        # THE MASKD NUMBER OF THE PIXEL WE WANT TO MASK (or UNMASK), IS GIVEN BY: MASKD = PHYSCOL- PHYSROW
        # IF PHYSCOL-PHYSROW<0, then MASKD = 448+PHYSCOL-PHYSROW
        self.dut['CONF_SR']['MASKD'].setall(True)
        self.dut['CONF_SR']['MASKH'].setall(True)
        self.dut['CONF_SR']['MASKV'].setall(True)

        # TO USE THE MASK FUNCTION YOU MUST INPUT THE FLAVOR, COLUMN AND ROW
        # THE FLAVOR NUMERS IS: 0 FOR PMOS_NOSF, 1 FOR PMOS, 2 FOR COMP, 3 FOR HV
        self.dut.mask(1, 5, 179)
        self.dut.mask(1, 59, 95)
        self.dut.mask(1, 42, 136)
        self.dut.mask(1, 60, 137)
        self.dut.mask(1, 86, 126)

        self.dut.mask(1, 102, 139)
        self.dut.mask(1, 66, 39)
        self.dut.mask(1, 103, 154)
        self.dut.mask(1, 102, 149)
        self.dut.mask(1, 38, 144)
        self.dut.mask(1, 45, 131)
        self.dut.mask(1, 101, 131)
        self.dut.mask(1, 106, 119)
        self.dut.mask(1, 0, 101)
        self.dut.mask(1, 11, 117)
        self.dut.mask(1, 81, 51)
        self.dut.mask(1, 39, 93)
        self.dut.mask(1, 80, 144)
        self.dut.mask(1, 29, 103)
        self.dut.mask(1, 66, 129)
        self.dut.mask(1, 35, 157)
        self.dut.mask(1, 13, 16)
        self.dut.mask(1, 23, 45)
        self.dut.mask(1, 48, 157)
        self.dut.mask(1, 26, 60)
        self.dut.mask(1, 102, 134)
        self.dut.mask(1, 87, 184)
        self.dut.mask(1, 108, 1)
        self.dut.mask(1, 45, 149)
        self.dut.mask(1, 24, 96)
        self.dut.mask(1, 28, 98)
        self.dut.mask(1, 42, 210)
        self.dut.mask(1, 108, 196)

        #self.dut['CONF_SR']['MASKD'][31] = True
        #self.dut['CONF_SR']['MASKH'][99] = False

        # SELECT WHICH PHYSICAL COLUMS TO INJECT
        # INJ_IN_MON_L AND INJ_IN_MON_L SELECT THE LEFT AND RIGHT SPECIAL ANALOG MONITORING PIXELS
        self.dut['CONF_SR']['COL_PULSE_SEL'].setall(False)

        # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS LEFT SIDE
        self.dut['CONF_SR']['INJ_IN_MON_L'] = 1
        # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS RIGHT SIDE
        self.dut['CONF_SR']['INJ_IN_MON_R'] = 0

        # SELECT WHICH PHYSICAL ROWS TO INJECT
        # THE SPEXIAL PIXELS OUTA_MON3 to OUTA_MON0 CORRESPONT TO ROWS 223 to 220 FOR INJECTION
        self.dut['CONF_SR']['INJ_ROW'].setall(False)
        # FOR THE ANALOG MONITORING TOP PIXEL
        self.dut['CONF_SR']['INJ_ROW'][223] = True

        # SELECT PHYSICAL COLUMNS AND ROWS FOR INJECTION WITH FUNCTION
        self.dut.enable_injection(1, 18, 99)

        # SELECT PHYSICAL COLUMN(S) FOR HITOR OUTPUT
        # nMASKH (SO SETTING MASKH TO FALSE) ENABLES HITOR FOR THE SPECIFIC ROW
        self.dut['CONF_SR']['DIG_MON_SEL'].setall(False)
        # self.dut.enable_column_hitor(1,18)

        self.dut.write_conf()

    def start(self):
        self.filename = os.path.join(self.working_dir, "data.h5")  # TODO
        self.h5_file = tb.open_file(self.filename, mode="w", title="")
        self.raw_data_earray = self.h5_file.create_earray(
            self.h5_file.root,
            name="raw_data",
            atom=tb.UIntAtom(),
            shape=(0,),
            title="Raw data",
            filters=tb.Filters(complib="blosc", complevel=5, fletcher32=False))

        self.fifo_readout = FifoReadout(self.dut)

    def stop(self):
        self.h5_file.close()

    @contextmanager
    def readout(self, *args, **kwargs):
        self._start_readout()
        yield
        self._stop_readout()

    def _start_readout(self, **kwargs):
        callback = kwargs.pop('callback', self._handle_data)
        clear_buffer = kwargs.pop('clear_buffer', False)
        fill_buffer = kwargs.pop('fill_buffer', False)
        reset_sram_fifo = kwargs.pop('reset_sram_fifo', False)
        errback = kwargs.pop('errback', self._handle_err)
        no_data_timeout = kwargs.pop('no_data_timeout', None)
        # self.scan_param_id = scan_param_id
        self.fifo_readout.start(reset_sram_fifo=reset_sram_fifo,
                                fill_buffer=fill_buffer,
                                clear_buffer=clear_buffer,
                                callback=callback,
                                errback=errback,
                                no_data_timeout=no_data_timeout)

    def _stop_readout(self):
        self.fifo_readout.stop()

    def _handle_data(self, data_tuple):
        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()

        # TODO: meta data handling

    def _handle_err(self, exc):
        msg = str(exc[1])
        if msg:
            self.logger.error(msg)
        else:
            self.logger.error("Aborting run...")
