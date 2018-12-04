import numpy as np
import numba

from tqdm import tqdm

hits_dtype = np.dtype([
    ('plane', '<u1'),
    ('event_number', '<i8'),
    ('trigger_number', '<i8'),
    ('trigger_time_stamp', '<i8'),
    ('row_time_stamp', '<i8'),
    ('frame_id', '<i8'),
    ('column', '<u2'),
    ('row', '<u2'),
    ('event_status', '<u4')])


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
    return np.int64(word) << np.int64(4) & np.int64(0xFFFFFFF0)


@numba.njit
def get_tjmono_ts_upper(word):
    """Timestamp (recorded with 40MHz) is converted to 640 MHz domain
    """
    return np.int64(word) << np.int64(32) & np.int64(0xFFFFFF00000000)


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
    return np.int64(word & np.int64(0x0000000000FFFF00)) >> np.int64(8)


@numba.njit
def get_timestamp_div_56bit_ts(word):
    return np.int64(word & np.int64(0x00000000000000FF)) << np.int64(48)


@numba.njit
def get_timestamp_div(word):
    return np.int64(word & np.int64(0x0000000000FFFFFF))


@numba.njit
def is_tlu(word):
    return word & 0x80000000 == 0x80000000


@numba.njit
def get_tlu_word(word):
    return word & 0xFFFF


@numba.njit
def get_tlu_timestamp(word):
    return np.uint64(word >> 12) & np.uint64(0x7FFF0)


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
    return word & 0xFF000000 == 0x50000000


@numba.njit
def is_ext_timestamp1(word):
    return word & 0xFF000000 == 0x51000000


@numba.njit
def is_ext_timestamp2(word):
    return word & 0xFF000000 == 0x52000000


@numba.njit
def is_ext_timestamp3(word):
    return word & 0xFF000000 == 0x53000000


class RawDataInterpreter(object):
    def __init(self):
        self.reset()

    def interpret_data(self, raw_data, chunk_size=1000000):
        hit_dtype = [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("cnt", "<u4"), ("timestamp", "<i8")]

        pbar = tqdm(total=len(raw_data))
        start = 0
        while start < len(raw_data):
            tmpend = start + chunk_size

            hit_buffer = np.zeros(shape=chunk_size, dtype=hit_dtype)

            hit_data = raw_data_interpreter(np.array(raw_data[start:tmpend]), hit_buffer)
            start = tmpend
            pbar.update(chunk_size)
        pbar.close()

        return hit_data


@numba.njit
def raw_data_interpreter(raw_data, hit_data):
    """ This function is interpreting the data recorded with TJ MonoPix.
    It consists at minimum of just TJ data, but can contain several timestamps (HitOr, TLU, external) and further data (TLU word, TDC charge)
    For additional info about data structure check corresponding modules in basil software package.

    Parameters:
    ----------
    raw_data : np.array
        The array with the raw data words
    hit_data : np.recarray with dtype: ("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("cnt", "<u4"), ("timestamp", "<i8")
        An array prepared to be filled with interpreted data
    hit_index : int
        Usually start with index 0. Optionally (in case of failure) pass hit_index to continue with interpretation
    tj_data_flag : int
        TJ data is spread across four consecutive data words. This flag stores information about which words have
        been processed.
    hitor_timestamp_flag : int
        HitOr timestamp data is spread across three consecutive data words (starting with ID3). This flag stores
        information about which words have been processed.
    ext_timestamp_flag : int
        Analog to hitor_timestamp, but corresponds to data from external timestamp
    tlu_timestamp_flag : int
        Analog to hitor_timestamp, but corresponds to data from 640 MHz tlu timestamp
    """

    # Initialize start values
    hit_index = 0
    tj_data_flag = 0
    hitor_timestamp_flag = 0
    ext_timestamp_flag = 0
    tlu_timestamp_flag = 0
    hitor_timestamp = 0
    ext_timestamp = 0
    tlu_timestamp = 0
    error_cnt = 0

    for raw_data_word in raw_data:
        #############################
        # Part 1: interpret TJ data #
        #############################

        if is_tjmono_data0(raw_data_word):
            if tj_data_flag != 0:
                col, row, te, le, noise, tj_data_flag, tj_timestamp = 0, 0, 0, 0, 0, 0, 0
                error_cnt += 1
                continue

            col = get_col(raw_data_word)
            row = get_row(raw_data_word)
            te = (raw_data_word & 0x1F8000) >> 15
            le = (raw_data_word & 0x7E00000) >> 21
            noise = (raw_data_word & 0x8000000) >> 27

            tj_data_flag = 1
        elif is_tjmono_data1(raw_data_word):
            if tj_data_flag != 1:
                col, row, te, le, noise, tj_data_flag, tj_timestamp = 0, 0, 0, 0, 0, 0, 0
                error_cnt += 1
                continue

            tj_timestamp = get_tjmono_ts_lower(raw_data_word)
            tj_data_flag = 2
        elif is_tjmono_data2(raw_data_word):
            if tj_data_flag != 2:
                col, row, te, le, noise, tj_data_flag, tj_timestamp = 0, 0, 0, 0, 0, 0, 0
                error_cnt += 1
                continue

            # Merge upper and lower part of TJMonoPix timestamp
            tj_timestamp = tj_timestamp | get_tjmono_ts_upper(raw_data_word)

            # TODO: token[3:0] is in this data word
            tj_data_flag = 3
        elif is_tjmono_data3(raw_data_word):
            if tj_data_flag != 3:
                col, row, te, le, noise, tj_data_flag, tj_timestamp = 0, 0, 0, 0, 0, 0, 0
                error_cnt += 1
                continue

            # TODO: Get token[31:4] data

            # Data words are complete, write TJ data to output buffer
            hit_data[hit_index]["row"] = row
            hit_data[hit_index]["col"] = col
            hit_data[hit_index]["le"] = le
            hit_data[hit_index]["te"] = te
            hit_data[hit_index]["cnt"] = noise
            hit_data[hit_index]["timestamp"] = tj_timestamp

            # Prepare for next hit. Increase hit index and reset tj_data flag
            hit_index += 1
            tj_data_flag = 0

        #####################################
        # Part 2: interpret HitOr timestamp #
        #####################################

        elif is_hitor_timestamp0(raw_data_word):
            pass  # TODO: Used for debug mode only

        # Third word comes first in data
        elif is_hitor_timestamp3(raw_data_word):
            if hitor_timestamp_flag != 0:
                hitor_timestamp, hitor_charge, hitor_timestamp_flag = 0, 0, 0
                error_cnt += 1
                continue

            hitor_timestamp = (hitor_timestamp & np.int64(0x0000FFFFFFFFFFFF)) | get_timestamp_div_56bit_ts(raw_data_word)
            hitor_charge = get_tdc(raw_data_word)

            hitor_timestamp_flag = 1

        elif is_hitor_timestamp2(raw_data_word):
            if hitor_timestamp_flag != 1:
                hitor_timestamp, hitor_charge, hitor_timestamp_flag = 0, 0, 0
                error_cnt += 1
                continue

            hitor_timestamp = (hitor_timestamp & np.int64(0xFFFF000000FFFFFF)) | (get_timestamp_div(raw_data_word) << np.int64(24))

            hitor_timestamp_flag = 2

        elif is_hitor_timestamp1(raw_data_word):
            if hitor_timestamp_flag != 2:
                hitor_timestamp, hitor_charge, hitor_timestamp_flag = 0, 0, 0
                error_cnt += 1
                continue

            hitor_timestamp = (hitor_timestamp & np.int64(0xFFFFFFFFFF000000)) | get_timestamp_div(raw_data_word)

            hit_data[hit_index]["col"] = 0xFD
            hit_data[hit_index]["row"] = 0
            hit_data[hit_index]["le"] = 0
            hit_data[hit_index]["te"] = 0
            hit_data[hit_index]["timestamp"] = hitor_timestamp
            hit_data[hit_index]["cnt"] = hitor_charge

            # Prepare for next data block. Increase hit index and reset hitor_timestamp flag
            hit_index += 1
            hitor_timestamp_flag = 0

        ########################################
        # Part 3: interpret external timestamp #
        ########################################

        elif is_ext_timestamp0(raw_data_word):
            pass  # TODO: Used for debug mode only

        # Third word comes first in data
        elif is_ext_timestamp3(raw_data_word):
            if ext_timestamp_flag != 0:
                ext_timestamp, ext_timestamp_flag = 0, 0
                error_cnt += 1
                continue

            ext_timestamp = (ext_timestamp & np.int64(0x0000FFFFFFFFFFFF)) | (get_timestamp_div(raw_data_word) << np.int64(48))

            ext_timestamp_flag = 1

        elif is_ext_timestamp2(raw_data_word):
            if ext_timestamp_flag != 1:
                ext_timestamp, ext_timestamp_flag = 0, 0
                error_cnt += 1
                continue

            ext_timestamp = (ext_timestamp & np.int64(0xFFFF000000FFFFFF)) | (get_timestamp_div(raw_data_word) << np.int64(24))

            ext_timestamp_flag = 2

        elif is_ext_timestamp1(raw_data_word):
            if ext_timestamp_flag != 2:
                ext_timestamp, ext_timestamp_flag = 0, 0
                error_cnt += 1
                continue

            ext_timestamp = (ext_timestamp & np.int64(0xFFFFFFFFFF000000)) | get_timestamp_div(raw_data_word)

            hit_data[hit_index]["col"] = 0xFE
            hit_data[hit_index]["row"] = 0
            hit_data[hit_index]["le"] = 0
            hit_data[hit_index]["te"] = 0
            hit_data[hit_index]["timestamp"] = ext_timestamp
            hit_data[hit_index]["cnt"] = 0

            # Prepare for next data block. Increase hit index and reset ext_timestamp flag
            hit_index += 1
            ext_timestamp_flag = 0

        #########################################
        # Part 4: interpret TLU 64bit timestamp #
        #########################################

        elif is_tlu_timestamp0(raw_data_word):
            pass  # TODO: Used for debug mode only

        # Third word comes first in data
        elif is_tlu_timestamp3(raw_data_word):
            if tlu_timestamp_flag != 0:
                tlu_timestamp, tlu_timestamp_flag = 0, 0
                error_cnt += 1
                continue

            tlu_timestamp = (tlu_timestamp & np.int64(0x0000FFFFFFFFFFFF)) | (get_timestamp_div(raw_data_word) << np.int64(48))

            tlu_timestamp_flag = 1

        elif is_tlu_timestamp2(raw_data_word):
            if tlu_timestamp_flag != 1:
                tlu_timestamp, tlu_timestamp_flag = 0, 0
                error_cnt += 1
                continue

            tlu_timestamp = (tlu_timestamp & np.int64(0xFFFF000000FFFFFF)) | (get_timestamp_div(raw_data_word) << np.int64(24))

            tlu_timestamp_flag = 2

        elif is_tlu_timestamp1(raw_data_word):
            if tlu_timestamp_flag != 2:
                tlu_timestamp, tlu_timestamp_flag = 0, 0
                error_cnt += 1
                continue

            tlu_timestamp = (tlu_timestamp & np.int64(0xFFFFFFFFFF000000)) | get_timestamp_div(raw_data_word)

            hit_data[hit_index]["col"] = 0xFC
            hit_data[hit_index]["row"] = 0
            hit_data[hit_index]["le"] = 0
            hit_data[hit_index]["te"] = 0
            hit_data[hit_index]["timestamp"] = tlu_timestamp
            hit_data[hit_index]["cnt"] = 0

            # Prepare for next data block. Increase hit index and reset tlu_timestamp flag
            hit_index += 1
            tlu_timestamp_flag = 0

        ##############################
        # Part 5: interpret TLU word #
        ##############################

        elif is_tlu(raw_data_word):
            tlu_word = get_tlu_word(raw_data_word)
            tlu_timestamp_low_res = get_tlu_timestamp(raw_data_word)  # TLU data contains a 16bit timestamp

            hit_data[hit_index]["col"] = 0xFF
            hit_data[hit_index]["row"] = 0
            hit_data[hit_index]["le"] = 0
            hit_data[hit_index]["te"] = 0
            hit_data[hit_index]["timestamp"] = tlu_timestamp_low_res
            hit_data[hit_index]["cnt"] = tlu_word

            # Prepare for next data block. Increase hit index
            hit_index += 1

    return hit_data[:hit_index], error_cnt
