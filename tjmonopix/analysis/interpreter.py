import numpy as np
import numba
from tqdm import tqdm

class_spec = [
    ('chunk_size', numba.uint32),
    ('tj_data_flag', numba.uint8),
    ('hitor_timestamp_flag', numba.uint8),
    ('ext_timestamp_flag', numba.uint8),
    ('inj_timestamp_flag', numba.uint8),
    ('tlu_timestamp_flag', numba.uint8),
    ('tj_timestamp', numba.int64),
    ('hitor_timestamp', numba.int64),
    ('hitor_charge', numba.int16),
    ('ext_timestamp', numba.int64),
    ('inj_timestamp', numba.int64),
    ('tlu_timestamp', numba.int64),
    ('error_cnt', numba.int32),
    ('col', numba.uint8),
    ('row', numba.uint16),
    ('le', numba.uint8),
    ('te', numba.uint8),
    ('noise', numba.uint8),
    ('meta_idx', numba.uint32),
    ('raw_idx', numba.uint32)
]


@numba.njit
def is_tjmono_data0(word):
    return word & 0xF0000000 == 0x00000000


@numba.njit
def is_tjmono_data1(word):
    return word & 0xF0000000 == 0x10000000


@numba.njit
def is_tjmono_data2(word):
    return word & 0xF0000000 == 0x20000000


@numba.njit
def is_tjmono_data3(word):
    return word & 0xF0000000 == 0x30000000


@numba.njit
def get_col(word):
    return 2 * (word & 0x3f) + (((word & 0x7FC0) >> 6) // 256)


@numba.njit
def get_row(word):
    return ((word & 0x7FC0) >> 6) % 256


@numba.njit
def get_tot(word):
    return (((word & 0x1F8000) >> 15) - ((word & 0x7E00000) >> 21)) & 0x3F


@numba.njit
def get_tjmono_ts_lower(word):
    """Timestamp (recorded with 40MHz) is converted to 640 MHz domain
    """
    return (word << 4) & 0xFFFFFFF0


@numba.njit
def get_tjmono_ts_upper(word):
    """Timestamp (recorded with 40MHz) is converted to 640 MHz domain
    """
    return (word << 32) & 0xFFFFFF00000000


@numba.njit
def is_hitor_timestamp0(word):
    return word & 0xFF000000 == 0x60000000


@numba.njit
def is_hitor_timestamp1(word):
    return word & 0xFF000000 == 0x61000000


@numba.njit
def is_hitor_timestamp2(word):
    return word & 0xFF000000 == 0x62000000


@numba.njit
def is_hitor_timestamp3(word):
    return word & 0xFF000000 == 0x63000000


@numba.njit
def get_tdc(word):
    return (word & 0x0000000000FFFF00) >> 8


@numba.njit
def get_timestamp_div_56bit_ts(word):
    return (word & 0x00000000000000FF) << 48


@numba.njit
def get_timestamp_div(word):
    return word & 0x0000000000FFFFFF


@numba.njit
def is_tlu(word):
    return word & 0x80000000 == 0x80000000


@numba.njit
def get_tlu_number(word):
    return word & 0xFFFF


@numba.njit
def get_tlu_timestamp(word):
    return (word >> 12) & 0x7FFF0


@numba.njit
def is_tlu_timestamp0(word):
    return word & 0xFF000000 == 0x70000000


@numba.njit
def is_tlu_timestamp1(word):
    return word & 0xFF000000 == 0x71000000


@numba.njit
def is_tlu_timestamp2(word):
    return word & 0xFF000000 == 0x72000000


@numba.njit
def is_tlu_timestamp3(word):
    return word & 0xFF000000 == 0x73000000


@numba.njit
def is_ext_timestamp0(word):
    return word & 0xFF000000 == 0x40000000


@numba.njit
def is_ext_timestamp1(word):
    return word & 0xFF000000 == 0x41000000


@numba.njit
def is_ext_timestamp2(word):
    return word & 0xFF000000 == 0x42000000


@numba.njit
def is_ext_timestamp3(word):
    return word & 0xFF000000 == 0x43000000


@numba.njit
def is_inj_timestamp0(word):
    return word & 0xFF000000 == 0x50000000


@numba.njit
def is_inj_timestamp1(word):
    return word & 0xFF000000 == 0x51000000


@numba.njit
def is_inj_timestamp2(word):
    return word & 0xFF000000 == 0x52000000


@numba.njit
def is_inj_timestamp3(word):
    return word & 0xFF000000 == 0x53000000


class Interpreter(object):
    def __init(self):
        self.reset()

    def interpret_data(self, raw_data, meta_data, chunk_size=1000000):
        hit_dtype = [('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('cnt', '<u4'), ('timestamp', '<i8'), ('scan_param_id', '<u4')]

        pbar = tqdm(total=len(raw_data))
        start = 0
        data_interpreter = RawDataInterpreter()
        while start < len(raw_data):
            tmpend = start + chunk_size

            hit_buffer = np.zeros(shape=chunk_size, dtype=hit_dtype)

            hit_data = data_interpreter.interpret(raw_data[start:tmpend], meta_data, hit_buffer)

            start = tmpend
            pbar.update(chunk_size)
        pbar.close()

        return hit_data, data_interpreter.get_error_count()


@numba.experimental.jitclass(class_spec)
class RawDataInterpreter(object):
    def __init__(self):
        self.reset()
        self.error_cnt = 0
        self.raw_idx = 0
        self.meta_idx = 0

    def reset(self):
        """ Reset all values that are computed from multiple data words
        """
        self.tj_data_flag = 0
        self.tj_timestamp = 0
        self.hitor_timestamp_flag = 0
        self.ext_timestamp_flag = 0
        self.inj_timestamp_flag = 0
        self.tlu_timestamp_flag = 0
        self.hitor_timestamp = 0
        self.hitor_charge = 0
        self.ext_timestamp = 0
        self.inj_timestamp = 0
        self.tlu_timestamp = 0

    def get_error_count(self):
        return self.error_cnt

    def interpret(self, raw_data, meta_data, hit_data):
        """ This function is interpreting the data recorded with TJ MonoPix.
        It consists at minimum of TJ data, but can contain several timestamps (HitOr, TLU, external) and further data
        (TLU word, TDC charge)

        tj_data_flag:
            TJ data is spread across four consecutive data words. This flag stores information about which words have
            been processed.
        hitor_timestamp_flag:
            HitOr timestamp data is spread across three consecutive data words (starting with ID3). This flag stores
            information about which words have been processed.
        ext_timestamp_flag:
            Analog to hitor_timestamp, but corresponds to data from external timestamp
        tlu_timestamp_flag:
            Analog to hitor_timestamp, but corresponds to data from 640 MHz tlu timestamp

        For additional info about data structure check corresponding modules in basil software package.

        Parameters:
        -----------
        raw_data : np.array
            The array with the raw data words
        meta_data : np.array
            The array with meta information (scan_param_id, data length, ...)
        hit_data : np.recarray(dtype=[("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("cnt", "<u4"),
                                      ("timestamp", "<i8"), ("scan_param_id", "<u4")])
            An array prepared to be filled with interpreted data
        """

        hit_index = 0

        for raw_data_word in raw_data:
            #############################
            # Part 1: interpret TJ data #
            #############################

            if is_tjmono_data0(raw_data_word):
                if self.tj_data_flag != 0:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.col = get_col(raw_data_word)
                self.row = get_row(raw_data_word)
                self.te = (raw_data_word & 0x1F8000) >> 15
                self.le = (raw_data_word & 0x7E00000) >> 21
                self.noise = (raw_data_word & 0x8000000) >> 27

                self.tj_data_flag = 1
            elif is_tjmono_data1(raw_data_word):
                if self.tj_data_flag != 1:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.tj_timestamp = get_tjmono_ts_lower(raw_data_word)
                self.tj_data_flag = 2
            elif is_tjmono_data2(raw_data_word):
                if self.tj_data_flag != 2:
                    self.reset()
                    self.error_cnt += 1
                    continue

                # Merge upper and lower part of TJMonoPix timestamp
                self.tj_timestamp = self.tj_timestamp | get_tjmono_ts_upper(raw_data_word)

                # TODO: token[3:0] is in this data word
                self.tj_data_flag = 3
            elif is_tjmono_data3(raw_data_word):
                if self.tj_data_flag != 3:
                    self.reset()
                    self.error_cnt += 1
                    continue

                # TODO: Get token[31:4] data

                # Data words are complete, write TJ data to output buffer
                hit_data[hit_index]["row"] = self.row
                hit_data[hit_index]["col"] = self.col
                hit_data[hit_index]["le"] = self.le
                hit_data[hit_index]["te"] = self.te
                hit_data[hit_index]["cnt"] = self.noise
                hit_data[hit_index]["timestamp"] = self.tj_timestamp
                hit_data[hit_index]["scan_param_id"] = self.raw_idx
                # Prepare for next hit. Increase hit index and reset tj_data flag
                hit_index += 1
                self.tj_data_flag = 0

            #####################################
            # Part 2: interpret HitOr timestamp #
            #####################################

            elif is_hitor_timestamp0(raw_data_word):
                pass  # TODO: Used for debug mode only

            # Third word comes first in data
            elif is_hitor_timestamp3(raw_data_word):
                if self.hitor_timestamp_flag != 0:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.hitor_timestamp = (self.hitor_timestamp & 0x0000FFFFFFFFFFFF) | get_timestamp_div_56bit_ts(raw_data_word)
                self.hitor_charge = get_tdc(raw_data_word)

                self.hitor_timestamp_flag = 1

            elif is_hitor_timestamp2(raw_data_word):
                if self.hitor_timestamp_flag != 1:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.hitor_timestamp = (self.hitor_timestamp & 0xFFFF000000FFFFFF) | (get_timestamp_div(raw_data_word) << 24)

                self.hitor_timestamp_flag = 2

            elif is_hitor_timestamp1(raw_data_word):
                if self.hitor_timestamp_flag != 2:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.hitor_timestamp = (self.hitor_timestamp & 0xFFFFFFFFFF000000) | get_timestamp_div(raw_data_word)

                hit_data[hit_index]["col"] = 0xFD
                hit_data[hit_index]["row"] = 0
                hit_data[hit_index]["le"] = 0
                hit_data[hit_index]["te"] = 0
                hit_data[hit_index]["cnt"] = self.hitor_charge
                hit_data[hit_index]["timestamp"] = np.int64(self.hitor_timestamp & 0x7FFFFFFFFFFFFFFF)  # Make sure it is unsigned
                hit_data[hit_index]["scan_param_id"] = self.raw_idx

                # Prepare for next data block. Increase hit index and reset hitor_timestamp flag
                hit_index += 1
                self.hitor_timestamp_flag = 0

            ########################################
            # Part 3: interpret external timestamp #
            ########################################

            elif is_ext_timestamp0(raw_data_word):
                pass  # TODO: Used for debug mode only

            # Third word comes first in data
            elif is_ext_timestamp3(raw_data_word):
                if self.ext_timestamp_flag != 0:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.ext_timestamp = (self.ext_timestamp & 0x0000FFFFFFFFFFFF) | (get_timestamp_div(raw_data_word) << 48)

                self.ext_timestamp_flag = 1

            elif is_ext_timestamp2(raw_data_word):
                if self.ext_timestamp_flag != 1:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.ext_timestamp = (self.ext_timestamp & 0xFFFF000000FFFFFF) | (get_timestamp_div(raw_data_word) << 24)

                self.ext_timestamp_flag = 2

            elif is_ext_timestamp1(raw_data_word):
                if self.ext_timestamp_flag != 2:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.ext_timestamp = (self.ext_timestamp & 0xFFFFFFFFFF000000) | get_timestamp_div(raw_data_word)

                hit_data[hit_index]["col"] = 0xFE
                hit_data[hit_index]["row"] = 0
                hit_data[hit_index]["le"] = 0
                hit_data[hit_index]["te"] = 0
                hit_data[hit_index]["cnt"] = 0
                hit_data[hit_index]["timestamp"] = self.ext_timestamp
                hit_data[hit_index]["scan_param_id"] = self.raw_idx

                # Prepare for next data block. Increase hit index and reset ext_timestamp flag
                hit_index += 1
                self.ext_timestamp_flag = 0

            #########################################
            # Part 4: interpret injection timestamp #
            #########################################

            elif is_inj_timestamp0(raw_data_word):
                pass  # TODO: Used for debug mode only

            # Third word comes first in data
            elif is_inj_timestamp3(raw_data_word):
                if self.inj_timestamp_flag != 0:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.inj_timestamp = (self.inj_timestamp & 0x0000FFFFFFFFFFFF) | (get_timestamp_div(raw_data_word) << 48)

                self.inj_timestamp_flag = 1

            elif is_inj_timestamp2(raw_data_word):
                if self.inj_timestamp_flag != 1:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.inj_timestamp = (self.inj_timestamp & 0xFFFF000000FFFFFF) | (get_timestamp_div(raw_data_word) << 24)

                self.inj_timestamp_flag = 2

            elif is_inj_timestamp1(raw_data_word):
                if self.inj_timestamp_flag != 2:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.inj_timestamp = (self.inj_timestamp & 0xFFFFFFFFFF000000) | get_timestamp_div(raw_data_word)

                hit_data[hit_index]["col"] = 0xFC
                hit_data[hit_index]["row"] = 0
                hit_data[hit_index]["le"] = 0
                hit_data[hit_index]["te"] = 0
                hit_data[hit_index]["cnt"] = 0
                hit_data[hit_index]["timestamp"] = self.inj_timestamp
                hit_data[hit_index]["scan_param_id"] = self.raw_idx

                # Prepare for next data block. Increase hit index and reset ext_timestamp flag
                hit_index += 1
                self.inj_timestamp_flag = 0

            #########################################
            # Part 5: interpret TLU 64bit timestamp #
            #########################################

            elif is_tlu_timestamp0(raw_data_word):
                pass  # TODO: Used for debug mode only

            # Third word comes first in data
            elif is_tlu_timestamp3(raw_data_word):
                if self.tlu_timestamp_flag != 0:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.tlu_timestamp = (self.tlu_timestamp & 0x0000FFFFFFFFFFFF) | (get_timestamp_div(raw_data_word) << 48)

                self.tlu_timestamp_flag = 1

            elif is_tlu_timestamp2(raw_data_word):
                if self.tlu_timestamp_flag != 1:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.tlu_timestamp = (self.tlu_timestamp & 0xFFFF000000FFFFFF) | (get_timestamp_div(raw_data_word) << 24)

                self.tlu_timestamp_flag = 2

            elif is_tlu_timestamp1(raw_data_word):
                if self.tlu_timestamp_flag != 2:
                    self.reset()
                    self.error_cnt += 1
                    continue

                self.tlu_timestamp = (self.tlu_timestamp & 0xFFFFFFFFFF000000) | get_timestamp_div(raw_data_word)

                hit_data[hit_index]["col"] = 0xFB
                hit_data[hit_index]["row"] = 0
                hit_data[hit_index]["le"] = 0
                hit_data[hit_index]["te"] = 0
                hit_data[hit_index]["cnt"] = 0
                hit_data[hit_index]["timestamp"] = self.tlu_timestamp
                hit_data[hit_index]["scan_param_id"] = self.raw_idx

                # Prepare for next data block. Increase hit index and reset tlu_timestamp flag
                hit_index += 1
                self.tlu_timestamp_flag = 0

            ##############################
            # Part 6: interpret TLU word #
            ##############################

            elif is_tlu(raw_data_word):
                tlu_word = get_tlu_number(raw_data_word)
                tlu_timestamp_low_res = get_tlu_timestamp(raw_data_word)  # TLU data contains a 15bit timestamp

                hit_data[hit_index]["col"] = 0xFF
                hit_data[hit_index]["row"] = 0
                hit_data[hit_index]["le"] = 0
                hit_data[hit_index]["te"] = 0
                hit_data[hit_index]["cnt"] = tlu_word
                hit_data[hit_index]["timestamp"] = tlu_timestamp_low_res
                hit_data[hit_index]["scan_param_id"] = self.raw_idx

                # Prepare for next data block. Increase hit index
                hit_index += 1

            # Increase raw_index and move to next data word
            self.raw_idx += 1

        # Trim hit_data buffer to interpreted data hits
        hit_data = hit_data[:hit_index]

        # Find correct scan_param_id in meta data and attach to hit
        for scan_idx, param_id in enumerate(hit_data["scan_param_id"]):
            while self.meta_idx < len(meta_data):
                if param_id >= meta_data[self.meta_idx]['index_start'] and param_id < meta_data[self.meta_idx]['index_stop']:
                    hit_data[scan_idx]['scan_param_id'] = meta_data[self.meta_idx]['scan_param_id']
                    break
                elif param_id >= meta_data[self.meta_idx]['index_stop']:
                    self.meta_idx += 1
        return hit_data
