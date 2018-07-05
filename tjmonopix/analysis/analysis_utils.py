import numpy as np
from numba import njit


def init_outs(n_hits):
    hit_dtype = [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"),
                 ("cnt", "<u4"), ("timestamp", "<u8"), ("idx", "<u8")]

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

    return np.zeros(shape=n_hits, dtype=hit_dtype), col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_cnt, ts_flg, ts2_timestamp, ts2_tot, ts2_cnt, ts2_flg, ts3_timestamp, ts3_cnt, ts3_flg


@njit
def interpret_data(rawdata, buf, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt,
                   ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt, debug):
    MASK1_LOWER = np.uint64(0x00000000FFFFFFF0)
    MASK1_UPPER = np.uint64(0x00FFFFFF00000000)
    TS_MASK_DAT = np.uint64(0x0000000000FFFFFF)
    TS_MASK1 = np.uint64(0xFFFFFFFFF0000000)
    TS_MASK2 = np.uint64(0xFFF000000FFFFFF0)
    TS_MASK3 = np.uint64(0x000FFFFFFFFFFFF0)
    TS_MASK_TOT = np.uint64(0x0000000000FFFF00)
    TS_DIV_MASK_DAT = np.uint64(0x00000000000000FF)

    buf_i = 0
    for r_i, word in enumerate(rawdata):
        ########################
        # TJMONOPIX_RX
        ########################
        if (word & 0xF0000000 == 0x30000000):
            # Token data
            # rx_cnt= (rx_cnt & 0xF)  | ((np.uint32(word) << np.int64(4)) & 0xFFFFFFF0)
            pass
        elif (word & 0xF0000000 == 0x00000000):
            # TJMonoPix data
            col = 2 * (word & 0x3f) + (((word & 0x7FC0) >> 6) // 256)
            row = ((word & 0x7FC0) >> 6) % 256
            te = (word & 0x1F8000) >> 15
            le = (word & 0x7E00000) >> 21
            noise = (word & 0x8000000) >> 27

            # Processed TJMonoPix pixel data, expect TJMonoPix timestamp data next
            if rx_flg == 0x0:
                rx_flg = 0x1
            else:
                # Interpreter did not expect TJMonoPix data, return error and data so far
                return 1, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        elif (word & 0xF0000000 == 0x10000000):
            # TJMonoPix timestamp data part 1
            # Shift by four to convert to 640 MHz timestamp
            timestamp = (timestamp & MASK1_UPPER) | (np.uint64(word) << np.uint64(4) & MASK1_LOWER)

            if rx_flg == 0x1:
                rx_flg = 0x2
            else:
                return 2, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        elif (word & 0xF0000000 == 0x20000000):
            # TJMonoPix Timestamp data part 2
            timestamp = (timestamp & MASK1_LOWER) | (
                (np.uint64(word) << np.uint64(32)) & MASK1_UPPER)

            if rx_flg == 0x2:
                buf[buf_i]["row"] = row
                buf[buf_i]["col"] = col
                buf[buf_i]["le"] = le
                buf[buf_i]["te"] = te
                buf[buf_i]["timestamp"] = timestamp
                buf[buf_i]["cnt"] = noise
                buf[buf_i]["idx"] = r_i
                buf_i = buf_i + 1
                rx_flg = 0
            else:
                return 3, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        ########################
        # TIMESTMP (MIMOSA_MKD)
        ########################
        elif word & 0xFF000000 == 0x50000000:
            pass  # TODO get count
        elif word & 0xFF000000 == 0x51000000:  # timestamp
            ts_timestamp = (ts_timestamp & TS_MASK1) | \
                (np.uint64(word & TS_MASK_DAT) << np.uint64(4))
            ts_cnt = ts_cnt + 1
#             if debug & 0x4 == 0x4:
#                 print r_i, hex(word), "timestamp1", hex(ts_timestamp), ts_cnt

            if ts_flg == 2:
                ts_flg = 0
                if debug & 0x1 == 0x1:
                    ts_inter = (ts_timestamp - ts_pre) & 0xFFFFFFFF
                    buf[buf_i]["col"] = 0xFE
                    buf[buf_i]["row"] = np.uint16(ts_inter)
                    buf[buf_i]["le"] = np.uint8(ts_inter >> np.uint64(8))
                    buf[buf_i]["te"] = np.uint8(ts_inter >> np.uint64(16))
                    buf[buf_i]["timestamp"] = ts_timestamp
                    buf[buf_i]["cnt"] = ts_cnt
                    buf[buf_i]["idx"] = r_i
                    buf_i = buf_i + 1
            else:
                return 6, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
        elif word & 0xFF000000 == 0x52000000:  # timestamp
            ts_timestamp = (ts_timestamp & TS_MASK2) | \
                (np.uint64(word & TS_MASK_DAT) << np.uint64(28))
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"timestamp2",hex(ts_timestamp),
            if ts_flg == 0x1:
                ts_flg = 0x2
            else:
                return 5, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
        elif word & 0xFF000000 == 0x53000000:  # timestamp
            ts_pre = ts_timestamp
            ts_timestamp = (ts_timestamp & TS_MASK3) | \
                (np.uint64(word & TS_MASK_DAT) << np.uint64(52))
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"timestamp3",hex(ts_timestamp),
            if ts_flg == 0x0:
                ts_flg = 0x1
            else:
                return 4, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        ########################
        # TIMESTMP_DIV2 (TDC)
        ########################
        elif word & 0xFF000000 == 0x60000000:
            pass  # TODO get count
        elif word & 0xFF000000 == 0x61000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & np.uint64(0xFFFFFFFFFF000000)) | \
                np.uint64(word & TS_MASK_DAT)
            ts2_cnt = ts2_cnt + 1
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts2_flg == 2:
                ts2_flg = 0
                if debug & 0x1 == 0x1:
                    buf[buf_i]["col"] = 0xFD
                    buf[buf_i]["row"] = np.uint16(ts2_cnt & 0xFFFF)
                    buf[buf_i]["le"] = np.uint8(ts2_cnt >> 16)
                    buf[buf_i]["te"] = np.uint8(ts2_cnt >> 8)
                    buf[buf_i]["timestamp"] = ts2_timestamp
                    buf[buf_i]["cnt"] = ts2_tot
                    buf[buf_i]['idx'] = r_i
                    buf_i = buf_i + 1
            else:
                return 10, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
        elif word & 0xFF000000 == 0x62000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & np.uint64(0xFFFF000000FFFFFF)) | \
                (np.uint64(word & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"timestamp1",hex(ts_timestamp)

            if ts2_flg == 0x1:
                ts2_flg = 0x2
            else:
                return 9, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
        elif word & 0xFF000000 == 0x63000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & np.uint64(0x0000FFFFFFFFFFFF)) | \
                (np.uint64(word & TS_DIV_MASK_DAT) << np.uint64(48))
            ts2_tot = (np.uint64(word & TS_MASK_TOT) >> np.uint64(8))
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"ts2_timestamp",hex(ts_timestamp)

            if ts2_flg == 0x0:
                ts2_flg = 0x1
            else:
                return 8, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        ########################
        # TIMESTMP_DIV3 (TLU)
        ########################
        elif word & 0xFF000000 == 0x70000000:
            pass  # TODO get count
        elif word & 0xFF000000 == 0x71000000:  # timestamp
            ts3_timestamp = (ts3_timestamp & np.uint64(0xFFFFFFFFFF000000)) | \
                np.uint64(word & TS_MASK_DAT)
            ts3_cnt = ts3_cnt + 1
            # if debug & 0x4 ==0x4:
            #    print r_i,hex(word),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts3_flg == 2:
                ts3_flg = 0
                if debug & 0x1 == 0x1:
                    buf[buf_i]["col"] = 0xFC
                    buf[buf_i]["row"] = 0xFFFF
                    buf[buf_i]["le"] = 0xFF
                    buf[buf_i]["te"] = 0xFF
                    buf[buf_i]["timestamp"] = ts3_timestamp
                    buf[buf_i]["cnt"] = ts3_cnt
                    buf[buf_i]['idx'] = r_i
                    buf_i = buf_i + 1
            else:
                return 10, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        elif word & 0xFF000000 == 0x72000000:  # timestamp
            ts3_timestamp = (ts3_timestamp & np.uint64(0xFFFF000000FFFFFF)) | \
                (np.uint64(word & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"timestamp1",hex(ts_timestamp)
            if ts3_flg == 0x1:
                ts3_flg = 0x2
            else:
                return 9, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
        elif word & 0xFF000000 == 0x73000000:  # timestamp
            ts3_timestamp = (ts3_timestamp & np.uint64(0x0000FFFFFFFFFFFF)) + \
                (np.uint64(word & TS_MASK_DAT) << np.uint64(48))
            # if debug & 0x4 ==0x4:
            #     print r_i,hex(word),"ts2_timestamp",hex(ts_timestamp)

            if ts3_flg == 0x0:
                ts3_flg = 0x1
            else:
                return 8, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

        ########################
        # TLU
        ########################
        elif (word & 0x80000000 == 0x80000000):
            tlu = word & 0xFFFF
            tlu_timestamp = np.uint64(word >> 12) & np.uint64(0x7FFF0)
            if debug & 0x2 == 0x2:
                buf[buf_i]["col"] = 0xFF
                buf[buf_i]["row"] = 0xFFFF
                buf[buf_i]["le"] = 0xFF
                buf[buf_i]["te"] = 0xFF
                buf[buf_i]["timestamp"] = tlu_timestamp
                buf[buf_i]["cnt"] = tlu
                buf[buf_i]['idx'] = r_i
                buf_i = buf_i + 1

        else:
            # if debug & 0x4 == 0x4:
            #    print r_i,hex(word),"trash"

            return 7, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt

    return 0, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_tot, ts2_flg, ts2_cnt, ts3_timestamp, ts3_flg, ts3_cnt
