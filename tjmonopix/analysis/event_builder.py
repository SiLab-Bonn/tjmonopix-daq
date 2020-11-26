import numba
import numpy as np
import tables as tb
import logging

from tqdm import tqdm

logging.basicConfig(
    format="%(asctime)s - [%(name)-8s] - %(levelname)-7s %(message)s", level=logging.INFO,
)

logger = logger = logging.getLogger(__name__)

class_spec = [
    ("chunk_size", numba.uint32),
    ("tlu_index", numba.int64),
    ("trigger_number", numba.int64),
    ("trigger_timestamp", numba.int64),
]


def build_events(hit_data, chunk_size=1000000):
    event_dtype = [
        ("event_number", "<i8"),
        ("frame", "u1"),
        ("column", "u1"),
        ("row", "u1"),
        ("charge", "u1"),
    ]

    builder = EventBuilder()
    events = np.array([], dtype=event_dtype)

    start = 0
    n_hits = len(hit_data)
    end_of_last_chunk = np.zeros(23, dtype=hit_data.dtype)

    logger.info("Building events")
    pbar = tqdm(total=n_hits)
    while start < n_hits:
        tmp_end = min(n_hits, start + chunk_size)
        hits = hit_data[start:tmp_end]
        ev_buffer = np.zeros(len(hits), dtype=event_dtype)
        event_chunk, end_of_last_chunk = builder.build_events(hits, ev_buffer, end_of_last_chunk)

        events = np.append(events, event_chunk)
        pbar.update(tmp_end - start)
        start = tmp_end
    pbar.close()
    logger.info("%s events build" % len(events))

    return events


@numba.experimental.jitclass(class_spec)
class EventBuilder(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.tlu_index = 0
        self.trigger_number = -1
        self.trigger_timestamp = -1

    def build_events(self, hits, ev_buffer, end_of_last_chunk):
        # Use only DUT and TLU words
        sel = np.logical_or(hits["col"] == 255, hits["col"] < 112)
        data = hits[sel]

        # Add last chunk in beginning of current one
        data = np.append(end_of_last_chunk, data)

        # Go through TLU words
        tlu_indices = np.where(data["col"][:-8] == 255)[0]  # Look only until -8th data word
        out_i = 0
        for tlu_word_i in tlu_indices:
            # if tlu_word_i > (len(dat) - 8):
            #     continue

            # Check for trigger timestamp overflow
            if self.trigger_timestamp >= 0 and data[tlu_word_i]["timestamp"] < (self.trigger_timestamp & 0x7FFF0):
                self.trigger_timestamp = (2 ** 15 << 4) + self.trigger_timestamp
            # Get trigger timestamp
            if self.trigger_timestamp < 0:
                self.trigger_timestamp = data[tlu_word_i]["timestamp"]
            else:
                self.trigger_timestamp = (0x7FFFFFFFFFF80000 & self.trigger_timestamp) | data[tlu_word_i]["timestamp"]

            # For every TLU word look for (time-wise) close hits in vicinity
            for word in data[tlu_word_i - 15 : tlu_word_i + 8]:
                if (  # DO NOT CHANGE CONSTANTS HERE: optimized for 99.99% correct event reconstruction
                    word["col"] < 112
                    and ((self.trigger_timestamp & 0x7FFF0) - (word["timestamp"] & 0x7FFF0)) > -518
                    and ((self.trigger_timestamp & 0x7FFF0) - (word["timestamp"] & 0x7FFF0)) < 773
                ):
                    # Check for trigger number overflow
                    if self.trigger_number >= 0 and data[tlu_word_i]["cnt"] < (
                        self.trigger_number & 0x000000000000FFFF
                    ):
                        self.trigger_number = np.int64(2 ** 16) + self.trigger_number
                    # Get trigger number
                    if self.trigger_number < 0:
                        self.trigger_number = data[tlu_word_i]["cnt"]
                    else:
                        self.trigger_number = (0x7FFFFFFFFFFF0000 & self.trigger_number) | data[tlu_word_i]["cnt"]

                    ev_buffer[out_i]["event_number"] = self.trigger_number
                    ev_buffer[out_i]["column"] = word["col"] + 1
                    ev_buffer[out_i]["row"] = word["row"] + 1
                    ev_buffer[out_i]["charge"] = ((word["te"] - word["le"]) & 0x3F) + 1
                    out_i += 1
        end_of_chunk = data[-23:]  # Carry last 15 + 8 words to next chunk
        return ev_buffer[:out_i], end_of_chunk


if __name__ == "__main__":
    with tb.open_file(
        "/media/silab/seagate_4tb/2020_07_27_DESY_testbeam/Cz_xp_0e15_hv/run31/tjmonopix_interpreted.h5", "r"
    ) as in_file:
        hits = in_file.root.Dut[:]

    events = build_events(hits)
