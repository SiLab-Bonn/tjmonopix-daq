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
import online_monitor.sender


class ScanBase(object):
    """
    Basic run meta class
    """

    def __init__(self, working_dir=None, send_addr="tcp://127.0.0.1:5500"):
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

        #### monitor
        self.socket=send_addr

        if isinstance(dut, TJMonoPix):
            # DUT is given at initialization
            self.dut = dut
        else:
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
    
            self.dut.write_conf()

    def start(self, **kwargs):
        self.h5_file = tb.open_file(self.filename, mode="w", title="")
        self.raw_data_earray = self.h5_file.create_earray(
            self.h5_file.root,
            name="raw_data",
            atom=tb.UIntAtom(),
            shape=(0,),
            title="Raw data",
            filters=tb.Filters(complib="blosc", complevel=5, fletcher32=False))

        self.meta_data_table = self.h5_file.create_table(
            self.h5_file.root,
            name='meta_data',
            description=MetaTable,
            title='meta_data',
            filters=tb.Filters(complib='zlib', complevel=5, fletcher32=False))

        ### open socket for monitor
        if (self.socket==""): 
            self.socket=None
        else:
            try:
                self.socket=online_monitor.sender.init(self.socket)
                self.logger.info('ScanBase.start:data_send.data_send_init connected=%s'%self.socket)
            except:
                self.logger.warn('ScanBase.start:data_send.data_send_init failed addr=%s'%self.socket)
                self.socket=None

        self.fifo_readout = FifoReadout(self.dut)
        self.scan(**kwargs)

    def stop(self):
        self.h5_file.close()
        ### close socket
        if self.socket!=None:
           try:
               online_monitor.sender.close(self.socket)
           except:
               pass


    @contextmanager
    def readout(self, *args, **kwargs):
        """

        """
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

        total_words = self.raw_data_earray.nrows
        len_raw_data = data_tuple[0].shape[0]

        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()

        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.dut['CONF_SR']['MASKD'].setall(True)
        self.dut['CONF_SR']['MASKH'].setall(True)
        self.dut['CONF_SR']['MASKV'].setall(True)
        # TODO: more meta data handling

        self.meta_data_table.row.append()
        self.meta_data_table.flush()
        if self.socket!=None:
            #try:
                online_monitor.sender.send_data(self.socket,data_tuple)
                #print data_tuple
                #raw_input()
            #except:
            #    self.logger.warn('ScanBase.hadle_data:sender.send_data failed')
            #    try:
            #        online_monitor.sender.close(self.socket)
            #    except:
            #        pass
            #    self.socket=None

    def _handle_err(self, exc):
        msg = str(exc[1])
        if msg:
            self.logger.error(msg)
        else:
            self.logger.error("Aborting run...")


class MetaTable(tb.IsDescription):
    index_start = tb.UInt32Col(pos=0)
    index_stop = tb.UInt32Col(pos=1)
    data_length = tb.UInt32Col(pos=2)
