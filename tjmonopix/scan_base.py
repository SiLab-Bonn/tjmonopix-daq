import time
import os
import logging
import yaml
import tables as tb
import zmq
from online_monitor.utils import utils

from contextlib import contextmanager
from tjmonopix.tjmonopix import TJMonoPix
from fifo_readout import FifoReadout


PROJECT_FOLDER = os.path.dirname(__file__)
TESTBENCH_DEFAULT_FILE = os.path.join(PROJECT_FOLDER, 'testbench.yaml')


class ScanBase(object):
    """
    Basic run meta class
    """

    def __init__(self, bench_config=None, dut=None, filename=None):
        bench = self._load_testbench_cfg(bench_config)

        if filename is None:
            self.working_dir = os.path.join(os.getcwd(), "output_data")
            self.run_name = time.strftime("%Y%m%d_%H%M%S_") + self.scan_id
        else:
            self.working_dir = os.path.dirname(os.path.realpath(filename))
            self.run_name = os.path.basename(os.path.realpath(filename))
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.output_filename = os.path.join(self.working_dir, self.run_name)

        self.logger = logging.getLogger()
        flg = 0
        for l in self.logger.handlers:
            if isinstance(l, logging.FileHandler):
                flg = 1
                fh = l
        if flg == 0:
            fh = logging.FileHandler(self.output_filename + '.log')
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s"))
            fh.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        logging.info("Initializing {:s}".format(self.__class__.__name__))

        # If DUT instance is not passed as argument, initialize it
        if isinstance(dut, TJMonoPix):
            self.dut = dut
        elif "dut" in bench.keys():
            chip_cfg = self._load_chip_cfg(bench["dut"])
            self.dut = TJMonoPix()

            # Initialize DUT and power up
            self.dut.init(chip_cfg["flavor"])
            self._configure_chip(chip_cfg)
            self._configure_masks(chip_cfg)

        # Online Monitor
        self.send_addr = bench["dut"]["send_data"]

    def start(self, **kwargs):

        # create and open data file
        self.h5_file = tb.open_file(self.output_filename + '.h5', mode="w", title="")
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
        self.meta_data_table.attrs.kwargs = yaml.dump(kwargs)
        self.meta_data_table.attrs.scan_id = self.scan_id
        status = self.dut.get_power_status()
        self.logger.info('Power status: {:s}'.format(str(status)))
        self.logger.info('Temperature: {:4.1f} C'.format(self.dut.get_temperature()))
        self.meta_data_table.attrs.power_before = yaml.dump(status)
        self.meta_data_table.attrs.status_before = yaml.dump(self.dut.get_configuration())
        self.meta_data_table.attrs.SET_before = yaml.dump(self.dut.SET)
        self.kwargs = self.h5_file.create_vlarray(
            self.h5_file.root,
            name='kwargs',
            atom=tb.VLStringAtom(),
            title='kwargs',
            filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False))
        self.kwargs.append("kwargs")
        self.kwargs.append(yaml.dump(kwargs))

        # Setup socket for Online Monitor
        socket_addr = self.send_addr
        if socket_addr:
            try:
                self.context = zmq.Context()
                self.socket = self.context.socket(zmq.PUB)  # publisher socket
                self.socket.bind(socket_addr)
                self.logger.debug('Sending data to server %s', socket_addr)
            except zmq.error.ZMQError:
                self.logger.exception('Cannot connect to socket for data sending.')
                self.socket = None
        else:
            self.socket = None

        mask = self.dut.get_mask()
        self.h5_file.create_carray(
            self.h5_file.root,
            name='mask',
            title='Masked pixels',
            obj=mask[self.dut.fl_n * 112:(self.dut.fl_n + 1) * 112],
            filters=tb.Filters(complib='blosc', complevel=5, fletcher32=False)
        )

        # Execute scan
        self.fifo_readout = FifoReadout(self.dut)
        self.scan(**kwargs)
        self.fifo_readout.print_readout_status()

        # Log and save power status and configuration
        status = self.dut.get_power_status()
        self.logger.info('Power status: {:s}'.format(str(status)))
        self.logger.info('Temperature: {:4.1f} C'.format(self.dut.get_temperature()))

        self.meta_data_table.attrs.power = yaml.dump(status)
        self.meta_data_table.attrs.status = yaml.dump(self.dut.get_configuration())
        self.meta_data_table.attrs.SET = yaml.dump(self.dut.SET)

        # Close data file
        self.h5_file.close()

        # Close socket from Online Monitor
        if self.socket:
            self.logger.debug('Closing socket connection')
            self.socket.close()
            self.socket = None
        return self.output_filename + '.h5'

    def stop(self):
        try:
            self.h5_file.close()
        except Exception:
            self.logger.warn("Could not close h5 file manually")

    @contextmanager
    def readout(self, *args, **kwargs):
        timeout = kwargs.pop('timeout', 10.0)
        self.fifo_readout.readout_interval = kwargs.pop('readout_interval', 0.003)

        self._start_readout(*args, **kwargs)
        yield
        self._stop_readout(timeout)

    def _start_readout(self, *args, **kwargs):
        callback = kwargs.pop('callback', self._handle_data)
        clear_buffer = kwargs.pop('clear_buffer', False)
        fill_buffer = kwargs.pop('fill_buffer', False)
        reset_sram_fifo = kwargs.pop('reset_sram_fifo', False)
        errback = kwargs.pop('errback', self._handle_err)
        no_data_timeout = kwargs.pop('no_data_timeout', None)
        self.scan_param_id = kwargs.pop('scan_param_id', 0)
        self.fifo_readout.start(reset_sram_fifo=reset_sram_fifo,
                                fill_buffer=fill_buffer,
                                clear_buffer=clear_buffer,
                                callback=callback,
                                errback=errback,
                                no_data_timeout=no_data_timeout)

    def _stop_readout(self, timeout):
        self.fifo_readout.stop(timeout=timeout)

    def _handle_data(self, data_tuple):

        total_words = self.raw_data_earray.nrows
        len_raw_data = data_tuple[0].shape[0]

        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()

        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['error'] = data_tuple[3]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row['scan_param_id'] = self.scan_param_id
        self.meta_data_table.row.append()
        self.meta_data_table.flush()

        if self.socket:
            send_data(self.socket, data=data_tuple, scan_par_id=self.scan_param_id)

    def _handle_err(self, exc):
        msg = str(exc[1])
        if msg:
            self.logger.error('%s Aborting run...', msg)
        else:
            self.logger.error("Aborting run...")

    def _load_testbench_cfg(self, bench_config):
        ''' Load the bench config into the scan

            Parameters:
            ----------
            bench_config : str or dict
                    Testbench configuration (configuration as dict or its filename as string)
        '''
        if bench_config is None:
            bench_config = TESTBENCH_DEFAULT_FILE
        with open(bench_config) as f:
            bench = yaml.full_load(f)

        return bench

    def _load_chip_cfg(self, bench_dut_cfg):
        ''' Load the chip config into the scan

            Paramters:
            ---------
            bench_dut_cfg : dict
                    Testbench configuration dict
        '''
        with open(bench_dut_cfg['chip_configuration']) as f:
            chip = yaml.full_load(f)

        return chip

    def _configure_chip(self, chip_cfg):
        if not self.dut:
            raise RuntimeError("Initialize chip before configuration")
        
        # Configure DACs
        self.dut.set_dac_settings(chip_cfg["dac"])
        if chip_cfg["overwrite_ICASN"]:
            self.dut["CONF_SR"]["SET_ICASN"].setall(False)

        # Enable all pixels
        self.dut["CONF_SR"]["MASKD"].setall(True)
        self.dut["CONF_SR"]["MASKH"].setall(True)
        self.dut["CONF_SR"]["MASKV"].setall(True)
        self.dut.write_conf()

    def _configure_masks(self, chip_cfg):
        try:
            if isinstance(chip_cfg["mask_pixels"], list):
                for pixel_to_mask in chip_cfg["mask_pixels"]:
                    self.dut.mask(*pixel_to_mask)
            else:
                raise ValueError("Illegal type for mask_pixels, list required")
        except KeyError:
            self.logger.warning("No mask information given, chip might be noisy")

        try:
            if isinstance(chip_cfg["mask_file"], str):
                if chip_cfg["mask_file"] == "auto":
                    self.dut.auto_mask_v2()
                else:
                    pass

            else:
                raise ValueError("Illegal type for mask_file, str required")
        except KeyError:
            self.logger.warning("No mask information given, chip might be noisy")


def send_data(socket, data, scan_par_id, name='ReadoutData'):
    '''Sends the data of every read out (raw data and meta data)

        via ZeroMQ to a specified socket.
        Uses a serialization provided by the online_monitor package
    '''

    data_meta_data = dict(
        name=name,
        dtype=str(data[0].dtype),
        shape=data[0].shape,
        timestamp_start=data[1],  # float
        timestamp_stop=data[2],  # float
        readout_error=data[3],  # int
        scan_par_id=scan_par_id
    )
    try:
        data_ser = utils.simple_enc(data[0], meta=data_meta_data)
        # socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
        # socket.send(data[0], flags=zmq.NOBLOCK)
        socket.send(data_ser, flags=zmq.NOBLOCK)
    except zmq.Again:
        pass


class MetaTable(tb.IsDescription):
    index_start = tb.UInt32Col(pos=0)
    index_stop = tb.UInt32Col(pos=1)
    data_length = tb.UInt32Col(pos=2)
    timestamp_start = tb.Float64Col(pos=3)
    timestamp_stop = tb.Float64Col(pos=4)
    scan_param_id = tb.UInt16Col(pos=5)
    error = tb.UInt32Col(pos=6)
