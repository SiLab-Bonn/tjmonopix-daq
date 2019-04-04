import sys
import logging
import datetime

from time import sleep, time, mktime
from threading import Thread, Event, Lock
from collections import deque
from Queue import Queue, Empty

data_iterable = ("data", "timestamp_start", "timestamp_stop", "error")


class RxSyncError(Exception):
    pass


class EightbTenbError(Exception):
    pass


class FifoError(Exception):
    pass


class NoDataTimeout(Exception):
    pass


class StopTimeout(Exception):
    pass


class FifoReadout(object):
    def __init__(self, dut):
        self.dut = dut
        self.callback = None
        self.errback = None
        self.readout_thread = None
        self.worker_thread = None
        self.watchdog_thread = None
        self.fill_buffer = False
        self.readout_interval = 0.003
        self._moving_average_time_period = 10.0
        self._words_per_read = deque(maxlen=int(self._moving_average_time_period / self.readout_interval))
        self._data_deque = deque()
        self._data_buffer = deque()
        self._words_per_read = deque(maxlen=int(self._moving_average_time_period / self.readout_interval))
        self._result = Queue(maxsize=1)
        self._calculate = Event()
        self.stop_readout = Event()
        self.force_stop = Event()
        self.timestamp = None
        self.update_timestamp()
        self._is_running = False
        self.reset_rx()
        self.reset_sram_fifo()
        self._record_count_lock = Lock()
        self.set_record_count(0, reset=True)

    @property
    def is_running(self):
        return self._is_running

    @property
    def is_alive(self):
        if self.worker_thread:
            return self.worker_thread.is_alive()
        else:
            False

    @property
    def data(self):
        if self.fill_buffer:
            return self._data_buffer
        else:
            logging.warning('Data requested but software data buffer not active')

    def data_words_per_second(self):
        if self._result.full():
            self._result.get()
        self._calculate.set()
        try:
            result = self._result.get(timeout=2 * self.readout_interval)
        except Empty:
            self._calculate.clear()
            return None
        return result / float(self._moving_average_time_period)

    def start(self, callback=None, errback=None, reset_rx=False, reset_sram_fifo=False, clear_buffer=False, fill_buffer=False, no_data_timeout=None):
        if self._is_running:
            raise RuntimeError("Readout already running: use stop() before start()")

        logging.info("Starting FIFO readout")
        self._is_running = True
        self.callback = callback
        self.errback = errback
        self.fill_buffer = fill_buffer
        self._record_count = 0
        if reset_rx:
            self.reset_rx()
        if reset_sram_fifo:
            self.reset_sram_fifo()
        else:
            fifo_size = self.dut['fifo']['FIFO_SIZE']
            if fifo_size != 0:
                logging.warning("SRAM FIFO not empty when starting FIFO readout: size = {}".format(fifo_size))
        self._words_per_read.clear()
        if clear_buffer:
            self._data_deque.clear()
            self._data_buffer.clear()
        self.stop_readout.clear()
        self.force_stop.clear()
        if self.errback:
            self.watchdog_thread = Thread(target=self.watchdog, name='WatchdogThread')
            self.watchdog_thread.daemon = True
            self.watchdog_thread.start()
        if self.callback:
            self.worker_thread = Thread(target=self.worker, name='WorkerThread')
            self.worker_thread.daemon = True
            self.worker_thread.start()
        self.readout_thread = Thread(target=self.readout, name="ReadoutThread", kwargs={'no_data_timeout': no_data_timeout})
        self.readout_thread.daemon = True
        self.readout_thread.start()

    def stop(self, timeout=10.):
        if not self._is_running:
            raise RuntimeError("Readout is not running: use start() before stop()")
        self._is_running = False
        self.stop_readout.set()
        try:
            self.readout_thread.join(timeout=timeout)
            if self.readout_thread.is_alive():  # If still alive, join() call timed out
                self.force_stop.set()
                if timeout:
                    raise StopTimeout("FIFO stopped due to timeout after {} second(s)".format(timeout))
                else:
                    logging.warning("FIFO stopped due to timeout")
        except StopTimeout as exc:
            if self.errback:
                self.errback(sys.exc_info())
            else:
                logging.error(exc)

        # If threads are still running, join for good (either because of exception or normal termination)
        if self.readout_thread.is_alive():
            self.readout_thread.join()
        if self.errback:
            self.watchdog_thread.join()
        if self.callback:
            self.worker_thread.join()
        self.callback = None
        self.errback = None
        logging.info("Stopped FIFO readout")

    def print_readout_status(self):
        tdc_discard_count = self.get_tdc_fifo_discard_count()
        data_rx_lost_count = self.get_data_rx_fifo_discard_count()
        tlu_lost_count = self.get_data_tlu_fifo_discard_count()
        timestamp_lost_count = self.get_data_timestamp_fifo_discard_count()

        logging.info('Recived words: %d', self._record_count)
        logging.info('Data queue size: %d', len(self._data_deque))
        logging.info('SRAM FIFO size: %d', self.dut['fifo']['FIFO_SIZE'])
        logging.info('Channel:                     %s', " | ".join(['TDC', 'DATA_RX', 'TLU', 'TIMESTAMP']))
        logging.info('Discard counter:             %s', " | ".join([str(tdc_discard_count).rjust(3), str(data_rx_lost_count).rjust(7),
                                                                    str(tlu_lost_count).rjust(3), str(timestamp_lost_count).rjust(9)]))

        if tdc_discard_count or data_rx_lost_count:
            logging.warning('Errors detected')

    # Helper functions to be called from 'main' methods
    def readout(self, no_data_timeout=None):
        """
        Readout thread continuously reading SRAM
        """
        logging.debug("Starting {}".format(self.readout_thread.name))
        curr_time = self.get_float_time()
        time_wait = 0.

        while not self.force_stop.wait(time_wait if time_wait >= 0. else 0.):
            try:
                time_read = time()
                if no_data_timeout and curr_time + no_data_timeout < self.get_float_time():
                    raise NoDataTimeout("Received no data for {:.2f} second(s)".format(no_data_timeout))
                data = self.read_data()
                self._record_count += len(data)

            except Exception as exc:
                no_data_timeout = None
                if self.errback:
                    self.errback(sys.exc_info())
                else:
                    raise exc
                if self.stop_readout.is_set():
                    break

            else:  # update timestamp and handle data
                data_words = data.shape[0]
                if data_words > 0:
                    last_time, curr_time = self.update_timestamp()
                    status = 0

                    if self.callback:
                        self._data_deque.append((data, last_time, curr_time, status))
                    if self.fill_buffer:
                        self._data_buffer.append((data, last_time, curr_time, status))
                    self._words_per_read.append(data_words)
                elif self.stop_readout.is_set():
                    break
                else:
                    self._words_per_read.append(0)

            finally:
                time_wait = self.readout_interval - (time() - time_read)
            if self._calculate.is_set():
                self._calculate.clear()
                self._result.put(sum(self._words_per_read))

        if self.callback:
            self._data_deque.append(None)  # Set last item to None to stop worker_thread
        logging.debug("Stopped {}".format(self.readout_thread.name))

    def worker(self):
        """
        Worker thread continuously calling callback function when data is available"
        """
        logging.debug("Stating {}".format(self.worker_thread.name))
        while True:
            try:
                data = self._data_deque.popleft()
            except IndexError:
                self.stop_readout.wait(self.readout_interval)  # sleep to reduce CPU usage
            else:
                if data is None:  # if None then exit
                    break
                else:
                    try:
                        self.callback(data)
                    except Exception:
                        self.errback(sys.exc_info())

        logging.debug("Stopped {}".format(self.watchdog_thread.name))

    def watchdog(self):
        logging.debug('Starting %s', self.watchdog_thread.name)
        while True:
            try:
                #if not any(self.get_rx_sync_status()):
                #    raise RxSyncError('No RX sync')
                #if any(self.get_rx_8b10b_error_count()):
                #    raise EightbTenbError('RX 8b10b error(s) detected')

                if self.get_data_rx_fifo_discard_count():
                    raise FifoError('DATA RX FIFO discard error(s) detected')

                if self.get_tdc_fifo_discard_count():
                    raise FifoError('TDC FIFO discard error(s) detected')
            except Exception:
                self.errback(sys.exc_info())
            if self.stop_readout.wait(self.readout_interval * 10):
                break
        logging.debug('Stopped %s', self.watchdog_thread.name)

    def read_data(self):
        """Read SRAM and return data array

        Can be used without threading.

        Returns
        -------
        data : list
            A list of SRAM data words
        """
        return self.dut["fifo"].get_data()

    def update_timestamp(self):
        curr_time = self.get_float_time()
        last_time = self.timestamp
        self.timestamp = curr_time
        return last_time, curr_time

    def read_status(self):
        raise NotImplementedError()

    def get_record_count(self):
        self._record_count_lock.acquire()
        cnt = self._record_count
        self._record_count_lock.release()
        return cnt

    def set_record_count(self, cnt, reset=False):
        self._record_count_lock.acquire()
        if reset:
            self._record_count = cnt
        else:
            self._record_count = self._record_count + cnt
        self._record_count_lock.release()

    def reset_sram_fifo(self):
        fifo_size = self.dut['fifo']['FIFO_SIZE']
        logging.info('Resetting SRAM FIFO: size = %i', fifo_size)
        self.update_timestamp()
        self.dut['fifo']['RESET']
        sleep(0.2)  # sleep here for a while
        fifo_size = self.dut['fifo']['FIFO_SIZE']
        if fifo_size != 0:
            logging.warning('SRAM FIFO not empty after reset: size = %i', fifo_size)

    def reset_rx(self, channels=None):
        pass
        #logging.info('Resetting RX')
        #if channels:
        #    filter(lambda channel: self.dut[channel].RX_RESET, channels)
        #else:
        #    filter(lambda channel: channel.RX_RESET, self.dut.get_modules('fei4_rx'))
        #sleep(0.1)  # sleep here for a while

    def get_tdc_fifo_discard_count(self, channels=None):
        pass
        # return self.dut['tdc'].LOST_DATA_COUNTER

    def get_data_rx_fifo_discard_count(self, channels=None):
        return self.dut['data_rx'].LOST_COUNT

    def get_data_timestamp_fifo_discard_count(self, channels=None):
        try:
            ret = self.dut['timestamp'].LOST_COUNT
        except:
            ret = 0
        return ret

    def get_data_tlu_fifo_discard_count(self, channels=None):
        try:
            ret = self.dut['tlu'].LOST_DATA_COUNTER
        except:
            ret = 0
        return ret

    def get_float_time(self):
        """
        returns time as double precision floats - Time64 in pytables - mapping to and from python datetime's

        """
        t1 = time()
        t2 = datetime.datetime.fromtimestamp(t1)
        return mktime(t2.timetuple()) + 1e-6 * t2.microsecond
