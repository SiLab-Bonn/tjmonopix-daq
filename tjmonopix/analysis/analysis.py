import numpy as np
import tables as tb
import logging
from tqdm import tqdm

from tjmonopix.analysis import analysis_utils as au


class Analysis():
    def __init__(self, raw_data_file=None):
        self.raw_data_file = raw_data_file

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def analyze_data(self, data_format=0x0):
        hit_dtype = [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"),
                     ("cnt", "<u4"), ("timestamp", "<u8")]
        if (data_format & 0x80) == 0x80:
            hit_dtype.append(("idx", "<u8"))
        buf = np.empty(10000000, dtype=hit_dtype)
        col = 0xFF
        row = 0xFF
        le = 0xFF
        te = 0xFF
        noise = 0
        timestamp = np.uint64(0x0)
        rx_flg = 0

        ts_timestamp = np.uint64(0x0)
        ts_pre = ts_timestamp
        ts_cnt = 0x0
        ts_flg = 0

        ts2_timestamp = np.uint64(0x0)
        ts2_tot = 0
        ts2_cnt = 0x0
        ts2_flg = 0

        ts3_timestamp = np.uint64(0x0)
        ts3_cnt = 0x0
        ts3_flg = 0

        with tb.open_file(self.raw_data_file[:-3] + '_interpreted.h5', "w") as out_file:
            description = np.zeros((1,), dtype=hit_dtype).dtype
            hit_table = out_file.create_table(
                out_file.root, name="Hits", description=description, title='hit_data')
            with tb.open_file(self.raw_data_file) as f:
                n_words = len(f.root.raw_data)
                start = 0
                hit_total = 0
                pbar = tqdm(total=n_words)
                while start < n_words:
                    tmpend = min(n_words, start + 1000000)
                    raw = f.root.raw_data[start:tmpend]
                    (err, hit_dat, r_i, col, row, le, te, noise, timestamp, rx_flg,
                     ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
                     ) = au.interpret_data(
                        raw, buf, col, row, le, te, noise, timestamp, rx_flg,
                        ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt, data_format)
                    hit_total = hit_total + len(hit_dat)
                    if err == 0:
                        pass
#                         print "%d %d %.3f%% %dhits" % (
#                             start, r_i, 100.0 * (start + r_i + 1) / n_words, hit_total)
#                     elif err == 1 or err == 2 or err == 3:
#                         print "tjmonopix data broken", err, start, r_i, hex(
#                             raw[r_i]), "flg=", rx_flg
#                         if data_format & 0x8 == 0x8:
#                             for i in range(max(0, r_i - 100), min(r_i + 100, tmpend - start - 6), 6):
#                                 print hex(
#                                     raw[start + i]), hex(raw[start + i + 1]), hex(raw[start + i + 2]),
#                                 print hex(
#                                     raw[start + i + 3]), hex(raw[start + i + 4]), hex(raw[start + i + 5])
                        rx_flg = 0
                        timestamp = np.uint64(0x0)
                    elif err == 4 or err == 5 or err == 6:
#                         print "timestamp data broken", err, start, r_i, hex(
#                             raw[r_i]), "flg=", ts_flg, ts_timestamp
                        ts_flg = 0
                        ts_timestamp = np.uint64(0x0)
                        ts_pre = ts_timestamp
                    elif err == 7:
                        print "trash data", err, start, r_i, hex(raw[r_i])
                    elif err == 8 or err == 9 or err == 10:
                        print "ts2_timestamp data broken", err, start, r_i, hex(
                            raw[r_i]), "flg=", ts2_flg, ts2_timestamp
                        ts2_flg = 0
                    if data_format & 0x80 == 0x80:
                        hit_dat['idx'] = hit_dat['idx'] + start

                    hit_table.append(hit_dat)
                    hit_table.flush()
                    start = start + r_i + 1
                    # if debug & 0x4 == 0x4:
                    #   break
                    pbar.update(start + r_i)
                pbar.close()
