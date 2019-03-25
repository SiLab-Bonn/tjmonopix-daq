import numpy as np
import tables as tb
import numba
import yaml


def increase_only(array):
    return False if np.count_nonzero(np.diff(array) >= 0) is 0 else True


def check_tlu_sync(tlu_timestamp, tlu_ts_timestamp, tlu_offset):
    """ Check if TLU words and high resolution TLU timestamp are synchronized

    Parameters:
    -----------
    tlu_timestamp: int
        Timestamp from TLU word (16bit)
    tlu_ts_timestamp: int
        Timestamp from 640 MHu TLU timestamp (64bit)
    tlu_offset: int
        Expected delay of TLU word. Used to determine limits for sync condition

    Returns:
    --------
    boolean (True if in sync, False otherwise)
    """
    if (tlu_timestamp - tlu_ts_timestamp) & 0x7FFFF > (tlu_offset - 16) and (tlu_timestamp - tlu_ts_timestamp) & 0x7FFFF < (tlu_offset + 16 * 2):
        # Timestamps are between tlu_offset - 16 and tlu_offset + 2 * 16 clock cycles apart
        return True
    else:
        return False


@numba.njit
def align_tlu_timestamp(tlu_data, tlu_ts_data, output_buffer, tlu_offset):
    """ Attach high resolution timestamp to tlu word

    Parameters:
    -----------
    tlu_data: np.recarray(["cnt", "timestamp"])
        Data with TLU words and low resolution timestamp
    tlu_ts_data: np.recarray(["timestamp"])
        High-resolution TLU timestamp
    Returns:
    --------
    output_buffer: np.recarray(["tlu_number", "tlu_timestamp", "ts_timestamp"])
    """
    tlu_i = 0
    ts_i = 0
    out_i = 0

    while tlu_i < len(tlu_data) and ts_i < len(tlu_ts_data) and out_i < len(output_buffer):
        if (tlu_data[tlu_i]["timestamp"] - tlu_ts_data[ts_i]["timestamp"] - (tlu_offset + 16 * 2)) & 0x7FFFF <= 0x40000:
            raise ValueError("TLU and TLU TS data is not synchronized!")
        elif ((tlu_data[tlu_i]["timestamp"] - tlu_ts_data[ts_i]["timestamp"] - (tlu_offset - 16)) & 0x7FFFF) > 0x40000:
            raise ValueError("TLU and TLU TS data is not synchronized!")
        else:
            # Found matching pair of TLU word and high-res TLU timestamp
            output_buffer[out_i]["tlu_number"] = tlu_data[tlu_i]["cnt"]
            output_buffer[out_i]["tlu_timestamp"] = tlu_data[tlu_i]["timestamp"]
            output_buffer[out_i]["ts_timestamp"] = tlu_ts_data[ts_i]["timestamp"]
            ts_i = ts_i + 1
            tlu_i = tlu_i + 1
            out_i = out_i + 1
    return output_buffer[:out_i]


@numba.njit
def align_hit_data(tlu_data, hit_data, output_buffer, upper_lim=0x400, lower_lim=0x4000):
    """ Align hit data with TLU number by high resolution timestamp

    Parameters:
    -----------
    tlu_data: np.recarray(["tlu_number", "tlu_timestamp", "ts_timestamp"])
        Array of TLU numbers aligned with high resolution timestamp (ts_timestamp)
    hit_data: np.recarray(["col", "row", "le", "te", "cnt", "timestamp", "scan_param_id"])
        Array with DUT hit data
    output_buffer: np.recarray(["col", "row", "le", "te", "flg", "tlu_number", "tlu_timestamp", "ts_timestamp"])

    Returns:
    --------
    output_buffer: np.recarray
        Filled output_buffer
    """
    hit_i, tlu_i, out_i = 0, 0, 0
    while tlu_i < len(tlu_data) and hit_i < len(hit_data) and out_i < len(output_buffer):
        if tlu_data[tlu_i]["ts_timestamp"] > hit_data[hit_i]["timestamp"] + np.abs(upper_lim):
            # TLU timestamp is larger than DUT timestamp + upper limit. Move to next TJ hit
            # Works, because timestamps are continuously increasing
            hit_i += 1
        elif tlu_data[tlu_i]["ts_timestamp"] < hit_data[hit_i]["timestamp"] - np.abs(lower_lim):
            # TLU timestamp is smaller than DUT timestamp - lower limit. Move to next TLU word
            # Works, because timestamps are continuously increasing
            tlu_i += 1
        else:
            # There is a DUT hit close to the given TLU hit (acceptable range defined by upper and lower limit)
            for hit_ii in range(hit_i, len(hit_data)):
                # Iterate over DUT data, starting from first hit that is close to TLU hit
                if tlu_data[tlu_i]["ts_timestamp"] < hit_data[hit_ii]["timestamp"] - np.uint64(np.abs(lower_lim)) and hit_data[hit_ii]["cnt"] == 0:
                    # Reached DUT data that is too far off from TLU data
                    break
                if out_i >= len(output_buffer):
                    return output_buffer[:out_i]
                output_buffer[out_i]["tlu_timestamp"] = tlu_data[tlu_i]["ts_timestamp"]
                output_buffer[out_i]["tlu_number"] = tlu_data[tlu_i]["tlu_number"]
#                 output_buffer[out_i]["token_timestamp"] = hit_data[hit_ii]["timestamp"]
                output_buffer[out_i]["row"] = hit_data[hit_ii]["row"]
                output_buffer[out_i]["col"] = hit_data[hit_ii]["col"]
                output_buffer[out_i]["te"] = hit_data[hit_ii]["te"]
                output_buffer[out_i]["le"] = hit_data[hit_ii]["le"]
                output_buffer[out_i]["flg"] = hit_data[hit_ii]["cnt"]
                out_i += 1
            tlu_i += 1
    return output_buffer[:out_i]


@numba.njit
def create_events(hits, output_buffer):
    """ Build events
    """
    hit_i, out_i = 0, 0
    return output_buffer[:out_i]


# @numba.njit
# def convert(hit_data, ref, hit, row_offset, row_factor, col_offset, col_factor):
#     out_i = 0
#     ref_i = 0
#     mono_i = 0
#     while mono_i < len(hit_data) and ref_i < len(ref):
#         mono_trig = np.uint16(hit_data[mono_i]["tlu_number"] & 0x7FFF)
#         ref_trig = np.uint16(ref[ref_i]["trigger_number"] & 0x7FFF)
#         if (mono_trig - ref_trig) & 0x4000 == 0x4000:  # means: difference is larger than 16384
#             mono_i = mono_i + 1
#         elif mono_trig == ref_trig:
#             hit[out_i]["event_number"] = ref[ref_i]["event_number"]
#             hit[out_i]["column"] = col_offset + col_factor * hit_data[mono_i]["col"]
#             hit[out_i]["row"] = row_offset + row_factor * hit_data[mono_i]["row"]
#             hit[out_i]["charge"] = (hit_data[mono_i]["te"] - hit_data[mono_i]["le"]) & 0x3F
#             hit[out_i]["frame"] = 1
#             out_i += 1
#             mono_i += 1
#         else:
#             ref_i = ref_i + 1
#     return hit[:out_i], mono_i, ref_i


class EventBuilder(object):
    def __init__(self, raw_data_file, max_hits=100):
        self.max_hits = max_hits
        self.get_tlu_configuration(raw_data_file)

    def get_tlu_configuration(self, raw_data_file):
        # Get TLU configuration from file meta data
        with tb.open_file(raw_data_file) as in_file_h5:
            try:
                conf_s = in_file_h5.root.meta_data.get_attr("status")
            except Exception:
                conf_s = in_file_h5.root.meta_data.get_attr("status_before")
        conf = yaml.load(conf_s)
        WAIT_CYCLES = conf['tlu']["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]
        self.tlu_offset = (WAIT_CYCLES + 1) * 16

    def build_events(self, hits, tlu_ts, tlu):
        """ Build events from hit and tlu data.

        Merge the TLU word with a high resolution timestamp from an external module first.
        Afterwards join hit data and TLU word by timestamp.

        Parameters:
        -----------
        hits: np.recarray(["col", "row", "le", "te", "cnt", "timestamp", "scan_param_id"])
            Hit array (DUT data only)
        tlu: np.recarray(["cnt", "timestamp"])
            Hit arrray (TLU data only)
        tlu_ts: np.recarray(["timestamp"])
            Hit array (TLU high-res timestamp data only)

        Returns:
        --------
        events: np.recarray(["event_number", "frame", "column", "row", "charge"])
            Event array
        """
        # Validate input data:
        if not increase_only(hits["timestamp"]):
            raise ValueError("Hit data timestamp is not continuously increasing!")
        if not increase_only(tlu_ts["timestamp"]):
            raise ValueError("TLU 640 MHz timestamp is not continuously increasing!")
        if not increase_only(tlu["cnt"]):
            raise ValueError("TLU trigger number is not continuously increasing!")

        # Check if TLU data is synchronized and do minor corrections if possible
        if check_tlu_sync(tlu[0]["timestamp"], tlu_ts[0]["timestamp"], self.tlu_offset):
            # In sync, go on
            pass
        elif check_tlu_sync(tlu[0]["timestamp"], tlu_ts[1]["timestamp"], self.tlu_offset):
            tlu_ts = tlu_ts[1:]
        elif check_tlu_sync(tlu[1]["timestamp"], tlu_ts[0]["timestamp"], self.tlu_offset):
            tlu = tlu[1:]
        else:
            raise ValueError("TLU word and TLU timestamp are not synchronized!")

        # Merge TLU words and high resolution timestamp
        out_buffer = np.zeros(len(tlu), dtype=[('tlu_number', '<u4'), ('tlu_timestamp', '<i8'), ('ts_timestamp', '<i8')])
        aligned_tlu_data = align_tlu_timestamp(tlu, tlu_ts, out_buffer, self.tlu_offset)

        # Validate result
        if not increase_only(aligned_tlu_data["ts_timestamp"]):
            raise ValueError("TLU high-res timestamp is not continuously increasing!")

        # Delete data words with too many hits at the same time
        _, idx, cnt = np.unique(hits["timestamp"], return_inverse=True, return_counts=True)
        mask = cnt <= self.max_hits
        hits = hits[mask[idx]]

        # Join hit data with TLU number by high-res timestamp
        out_buffer = np.zeros(2 * len(aligned_tlu_data) + 2 * len(hits), dtype=[('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('flg', '<u1'), ('tlu_number', '<u4'), ('tlu_timestamp', '<i8')])
        aligned_hits = align_hit_data(aligned_tlu_data, hits, out_buffer)

        event_type = np.dtype([("event_number", "<i8"), ("frame", "<u1"), ("column", "<u2"), ("row", "<u2"), ("charge", "<u2")])
        event_buffer = np.zeros(2 * len(hits), dtype=event_type)

        events = create_events(aligned_hits, event_buffer)

        return events
