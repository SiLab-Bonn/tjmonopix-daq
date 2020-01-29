import time
import os
import logging
import yaml
import tables as tb
import zmq
from online_monitor.utils import utils

from contextlib import contextmanager
from tjmonopix import TJMonoPix
from fifo_readout import FifoReadout


class ScanBase(object):
    """
    Basic run meta class
    """

    def __init__(self, dut=None, filename=None, send_addr="tcp://127.0.0.1:5500"):
        # If DUT instance is not passed as argument, initialize it
        if isinstance(dut, TJMonoPix):
            self.dut = dut
        elif dut:
            self.dut = TJMonoPix(conf=dut)
            # Initialize self.dut and power up
            self.dut.init()
            self.dut.write_conf()
            self.dut.set_vreset_dacunits(35, 1)  # 1V. Set V_reset_p, this is the baseline of the front end input (one hot encoding)
            self.dut.set_icasn_dacunits(0, 1)  # 4.375nA approx. 1.084V at -3V backbias, 600mV at 0V backbias
            self.dut.set_ireset_dacunits(2, 1, 1)  # 270pA, HIGH LEAKAGE MODE, NORMAL SCALING, 0 = LOW LEAKAGE MODE, SCALING*0.01
            self.dut.set_ithr_dacunits(5, 1)  # 680pA
            self.dut.set_idb_dacunits(15, 1)  # 500nA
            self.dut.set_ibias_dacunits(50, 1)  # 500nA. Current of the front end that provides amplification
            self.dut.write_conf()

        if filename is None:
            self.working_dir = os.path.join(os.getcwd(), "output_data")
            self.run_name = time.strftime("%Y%m%d_%H%M%S_") + self.scan_id
        else:
            self.working_dir = os.path.dirname(os.path.realpath(filename))
            self.run_name = os.path.basename(os.path.realpath(filename))
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.output_filename = os.path.join(self.working_dir, self.run_name)

        # Online Monitor
        # self.socket = send_addr
        self.send_addr = send_addr

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
                self.log.exception('Cannot connect to socket for data sending.')
                self.socket = None
        else:
            self.socket = None

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
        if self.socket is not None:
            try:
                online_monitor.sender.close(self.socket)
            except Exception:
                pass
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
            send_data(self.socket, data=data_tuple)

    def _handle_err(self, exc):
        msg = str(exc[1])
        if msg:
            self.logger.error(msg)
        else:
            self.logger.error("Aborting run...")


def send_data(socket, data, scan_parameters={}, name='ReadoutData'):
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
            scan_parameters=scan_parameters
        )
        try:
            # data_ser = utils.simple_enc(data[0], meta=data_meta_data)
            socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
            socket.send(data[0], flags=zmq.NOBLOCK)
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
