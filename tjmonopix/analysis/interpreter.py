import sys
import time
import os
import numpy as np
import matplotlib.pyplot as plt
from numba import njit
import tables

hit_dtype = np.dtype([("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("cnt", "<u4"),
                      ("timestamp", "<u8")])


@njit
def _interpret(raw, buf, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt,
               ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp, debug):
    MASK1_LOWER = np.uint64(0x000000000FFFFFFF)
    MASK1_UPPER = np.uint64(0x000FFFFFF0000000)
    MASK2 = np.uint64(0x0000000000FFF000)
    NOT_MASK2 = np.uint64(0x000FFFFFFF000FFF)
    MASK3 = np.uint64(0x000FFFFFFF000000)
    NOT_MASK3 = np.uint64(0x0000000000FFFFFF)
    TS_MASK_DAT = 0x0000000000FFFFFF
    TS_MASK1 = np.uint64(0xFFFFFFFFFF000000)
    TS_MASK2 = np.uint64(0xFFFF000000FFFFFF)
    TS_MASK3 = np.uint64(0x0000FFFFFFFFFFFF)
    TLU_NOT_MASK = np.uint64(0xFFFFFFFFFFFF8000)
    TDC_NOT_MASK = np.uint64(0xFFFFFFFFFFFF0000)

    buf_i = 0
    for r_i, r in enumerate(raw):
        ########################
        # MONOPIX_RX
        ########################
        if (r & 0xF0000000 == 0x30000000):
            #rx_cnt= (rx_cnt & 0xF)  | ((np.uint32(r) << np.int64(4)) & 0xFFFFFFF0)
            pass
        elif (r & 0xF0000000 == 0x00000000):

            col = 2 * (r & 0x3f) + (((r & 0x7FC0) >> 6) // 256)
            row = ((r & 0x7FC0) >> 6) % 256
            te = (r & 0x1F8000) >> 15
            le = (r & 0x7E00000) >> 21
            noise = (r & 0x8000000) >> 27

            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),rx_flg,"ts=",hex(timestamp),col,row,noise

            if rx_flg == 0x0:
                rx_flg = 0x1
            else:
                return 1, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp

        elif (r & 0xF0000000 == 0x10000000):
            timestamp = (timestamp & MASK1_UPPER) | (
                np.uint64(r) & MASK1_LOWER)
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),rx_flg,"ts=",hex(timestamp),le,te
            # pass
            if rx_flg == 0x1:
                rx_flg = 0x2
            else:
                return 2, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp

        elif (r & 0xF0000000 == 0x20000000):
            timestamp = (timestamp & MASK1_LOWER) | (
                (np.uint64(r) << np.uint64(28)) & MASK1_UPPER)
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),rx_flg,"ts=",hex(timestamp)

            if rx_flg == 0x2:
                buf[buf_i]["row"] = row
                buf[buf_i]["col"] = col
                buf[buf_i]["le"] = le
                buf[buf_i]["te"] = te
                buf[buf_i]["timestamp"] = timestamp
                buf[buf_i]["cnt"] = noise
                buf_i = buf_i+1
                rx_flg = 0
            else:
                return 3, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp

        ########################
        # TIMESTMP
        ########################
        elif r & 0xFF000000 == 0x50000000:
            pass  # TODO get count
        elif r & 0xFF000000 == 0x51000000:  # timestamp
            ts_timestamp = (ts_timestamp & TS_MASK1) | np.uint64(
                r & TS_MASK_DAT)
            ts_cnt = ts_cnt+1
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts_flg == 2:
                ts_flg = 0
                if debug & 0x1 == 0x1:
                    ts_inter = (ts_timestamp-ts_pre) & 0xFFFFFFFF
                    buf[buf_i]["col"] = 0xFE
                    buf[buf_i]["row"] = np.uint16(ts_inter)
                    buf[buf_i]["le"] = np.uint8(ts_inter >> np.uint64(8))
                    buf[buf_i]["te"] = np.uint8(ts_inter >> np.uint64(16))
                    buf[buf_i]["timestamp"] = ts_timestamp
                    buf[buf_i]["cnt"] = ts_cnt
                    buf_i = buf_i+1
            else:
                return 6, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp
        elif r & 0xFF000000 == 0x52000000:  # timestamp
            ts_timestamp = (ts_timestamp & TS_MASK2) + \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp2",hex(ts_timestamp),

            if ts_flg == 0x1:
                ts_flg = 0x2
            else:
                return 5, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp
        elif r & 0xFF000000 == 0x53000000:  # timestamp
            ts_pre = ts_timestamp
            ts_timestamp = (ts_timestamp & TS_MASK3) + \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(48))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp3",hex(ts_timestamp),

            if ts_flg == 0x0:
                ts_flg = 0x1
            else:
                return 4, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp

        ########################
        # TIMESTMP2
        ########################
        elif r & 0xFF000000 == 0x60000000:
            pass  # TODO get count
        elif r & 0xFF000000 == 0x61000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & TS_MASK1) | np.uint64(
                r & TS_MASK_DAT)
            ts2_cnt = ts2_cnt+1
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts2_flg == 2:
                ts2_flg = 0
                if debug & 0x1 == 0x1:
                    ts2_inter = (ts2_timestamp-ts2_pre) & 0xFFFFFFFF
                    buf[buf_i]["col"] = 0xFD
                    buf[buf_i]["row"] = np.uint16(ts2_inter)
                    buf[buf_i]["le"] = np.uint8(ts2_inter >> np.uint64(8))
                    buf[buf_i]["te"] = np.uint8(ts2_inter >> np.uint64(16))
                    buf[buf_i]["timestamp"] = ts2_timestamp
                    buf[buf_i]["cnt"] = ts2_cnt
                    buf_i = buf_i+1
            else:
                return 10, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp
        elif r & 0xFF000000 == 0x62000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & TS_MASK2) + \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp)

            if ts2_flg == 0x1:
                ts2_flg = 0x2
            else:
                return 9, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp
        elif r & 0xFF000000 == 0x63000000:  # timestamp
            ts2_pre = ts2_timestamp
            ts2_timestamp = (ts2_timestamp & TS_MASK3) + \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(48))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"ts2_timestamp",hex(ts_timestamp)

            if ts2_flg == 0x0:
                ts2_flg = 0x1
            else:
                return 8, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp

        ########################
        # TLU
        ########################
        elif (r & 0x80000000 == 0x80000000):
            tlu = r & 0xFFFF
            tlu_org = (r >> 16) & 0x7FFF
            if debug & 0x20 == 0x00:
                tlu_timestamp = ts_pre & TLU_NOT_MASK | np.uint64(tlu_org)
                if tlu_org < (np.int32(ts_pre) & 0x7FFF):
                    # if np.uint64(tlu_timestamp - ts_pre) & np.uint64(0x8000) == np.uint64(0x8000):
                    tlu_timestamp = tlu_timestamp + np.uint64(0x8000)
            else:
                tlu_timestamp = ts2_pre & TLU_NOT_MASK | np.uint64(tlu_org)
                if tlu_org < (np.int32(ts2_pre) & 0x7FFF):
                    tlu_timestamp = tlu_timestamp + np.uint64(0x8000)
            # if debug & 0x4 ==0x4:
                #print r_i,hex(r),"ts=",hex(tlu_timestamp),"tlu",tlu,hex(tlu_tmp),tlu_tmp < trig_tmp

            if debug & 0x2 == 0x2:
                buf[buf_i]["col"] = 0xFF
                buf[buf_i]["row"] = 0xFF
                buf[buf_i]["le"] = 0xFF
                buf[buf_i]["te"] = 0xFF
                buf[buf_i]["timestamp"] = tlu_timestamp
                buf[buf_i]["cnt"] = tlu
                buf_i = buf_i+1
        ########################
        # TDC
        ########################
        elif (r & 0xF0000000 == 0x40000000):
            tdc = r & 0x0FFF
            tdc_org = (r >> 12) & 0xFFFF
            tdc_trig = (r >> 20) & 0xFF
            if debug & 0x20 == 0x00:
                tdc_timestamp = ts_pre & TDC_NOT_MASK | np.uint64(tdc_org)
                if tdc_org < (np.int32(ts_pre) & 0xFFFF):
                    # if np.uint64(tlu_timestamp - ts_pre) & np.uint64(0x8000) == np.uint64(0x8000):
                    tdc_timestamp = tdc_timestamp + np.uint64(0x10000)
            else:
                tdc_timestamp = ts2_pre & TDC_NOT_MASK | np.uint64(tlu_org)
                if tdc_org < (np.int32(ts2_pre) & 0xFFFF):
                    tdc_timestamp = tdc_timestamp + np.uint64(0x10000)
            # if debug & 0x4 ==0x4:
                #print r_i,hex(r),"ts=",hex(tlu_timestamp),"tlu",tlu,hex(tlu_tmp),tlu_tmp < trig_tmp

            if debug & 0x40 == 0x40:
                buf[buf_i]["col"] = 0xFC
                buf[buf_i]["row"] = 0xFF
                buf[buf_i]["le"] = tdc_trig
                buf[buf_i]["te"] = 0xFF
                buf[buf_i]["timestamp"] = tdc_timestamp
                buf[buf_i]["cnt"] = tdc
                buf_i = buf_i+1
        else:
            # if debug & 0x4 == 0x4:
            #    print r_i,hex(r),"trash"

            return 7, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp
    return 0, buf[:buf_i], r_i, col, row, le, te, noise, timestamp, rx_flg, ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp

def interpret_h5(fin, fout, data_format=0x43, n=100000000):
    buf = np.empty(n, dtype=hit_dtype)
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
    ts2_pre = ts_timestamp
    ts2_cnt = 0x0
    ts2_flg = 0

    tlu = 0
    tlu_timestamp = np.uint64(0x0)
    tdc = 0
    tdc_timestamp = np.uint64(0x0)

    with tables.open_file(fout, "w") as f_o:
        description = np.zeros((1,), dtype=hit_dtype).dtype
        hit_table = f_o.create_table(
            f_o.root, name="Hits", description=description, title='hit_data')
        with tables.open_file(fin) as f:
            end = len(f.root.raw_data)
            start = 0
            t0 = time.time()
            hit_total = 0
            while start < end:
                tmpend = min(end, start+n)
                raw = f.root.raw_data[start:tmpend]
                (err, hit_dat, r_i, col, row, le, te, noise, timestamp, rx_flg,
                 ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp
                ) = _interpret(
                    raw, buf, col, row, le, te, noise, timestamp, rx_flg,
                    ts_timestamp, ts_pre, ts_flg, ts_cnt, ts2_timestamp, ts2_pre, ts2_flg, ts2_cnt, tlu, tlu_timestamp, tdc, tdc_timestamp, data_format)
                hit_total = hit_total+len(hit_dat)
                if err == 0:
                    print "%d %d %.3f%% %.3fs %dhits" % (
                        start, r_i, 100.0*(start+r_i+1)/end, time.time()-t0, hit_total)
                elif err == 1 or err == 2 or err == 3:
                    print "tjmonopix data broken", err, start, r_i, hex(
                        raw[r_i]), "flg=", rx_flg
                    if debug & 0x8 == 0x8:
                        for i in range(max(0, r_i-100), min(r_i+100, tmpend-start-6), 6):
                            print hex(
                                raw[start+i]), hex(raw[start+i+1]), hex(raw[start+i+2]),
                            print hex(
                                raw[start+i+3]), hex(raw[start+i+4]), hex(raw[start+i+5])
                    rx_flg = 0
                    timestamp = np.uint64(0x0)
                elif err == 4 or err == 5 or err == 6:
                    print "timestamp data broken", err, start, r_i, hex(
                        raw[r_i]), "flg=", ts_flg, ts_timestamp
                    ts_flg = 0
                    ts_timestamp = np.uint64(0x0)
                    ts_pre = ts_timestamp
                elif err == 7:
                    print "trash data", err, start, r_i, hex(raw[r_i])
                elif err == 8 or err == 9 or err == 10:
                    print "ts2_timestamp data broken", err, start, r_i, hex(
                        raw[r_i]), "flg=", ts2_flg, ts2_timestamp
                hit_table.append(hit_dat)
                hit_table.flush()
                start = start+r_i+1
                # if debug &0x4 ==0x4:
                #   break


def list2img(dat, delete_noise=True):
    if delete_noise:
        dat = without_noise(dat)
    return np.histogram2d(dat["col"], dat["row"], bins=[np.arange(0, 37, 1), np.arange(0, 130, 1)])[0]


def list2cnt(dat, delete_noise=True):
    if delete_noise:
        dat = without_noise(dat)
    uni, cnt = np.unique(dat[["col", "row"]], return_counts=True)
    ret = np.empty(len(uni), dtype=[
                   ("col", "<u1"), ("row", "<u2"), ("cnt", "<i8")])
    print ret.dtype.names
    ret["col"] = uni["col"]
    ret["row"] = uni["row"]
    ret["cnt"] = cnt
    return ret


def without_noise(dat):
    return dat[np.bitwise_or(dat["cnt"] == 0, dat["col"] >= 36)]


class InterRaw():
    def __init__(self, chunk=100000000, debug=0):
        self.reset()
        self.buf = np.empty(chunk, dtype=hit_dtype)
        self.n = chunk
        self.debug = 0

    def reset(self):
        self.col = 0xFF
        self.row = 0xFFFF
        self.le = 0xFF
        self.te = 0xFF
        self.noise = 0
        self.timestamp = np.int64(0x0)
        self.rx_flg = 0

        self.ts_timestamp = np.uint64(0x0)
        self.ts_pre = self.ts_timestamp
        self.ts_cnt = 0x0
        self.ts_flg = 0
        self.ts2_timestamp = np.uint64(0x0)
        self.ts2_pre = self.ts2_timestamp
        self.ts2_cnt = 0x0
        self.ts2_flg = 0

        self.tlu = 0
        self.tlu_timestamp = np.uint64(0x0)

        self.tdc = 0
        self.tdc_timestamp = np.uint64(0x0)

    def run(self, raw, data_format=0x43):
        start = 0
        end = len(raw)
        ret = np.empty(0, dtype=hit_dtype)
        while start < end:  # TODO make chunk work
            tmpend = min(end, start+self.n)
            (err, hit_dat, r_i,
             self.col, self.row, self.le, self.te, self.noise, self.timestamp, self.rx_flg,
             self.ts_timestamp, self.ts_pre, self.ts_flg, self.ts_cnt,
             self.ts2_timestamp, self.ts2_pre, self.ts2_flg, self.ts2_cnt,
             self.tlu, self.tlu_timestamp, self.tdc, self.tdc_timestamp
             ) = _interpret(
                raw[start:tmpend], self.buf,
                self.col, self.row, self.le, self.te, self.noise, self.timestamp, self.rx_flg,
                self.ts_timestamp, self.ts_pre, self.ts_flg, self.ts_cnt,
                self.ts2_timestamp, self.ts2_pre, self.ts2_flg, self.ts2_cnt,
                self.tlu, self.tlu_timestamp, self.tdc, self.tdc_timestamp,
                data_format)
            if err != 0:
                self.reset()
            ret = np.append(ret, hit_dat)
            start = start+r_i+1
        return ret

    def mk_list(self, raw, delete_noise=True):
        dat = self.run(raw)
        if delete_noise == True:
            dat = without_noise(dat)
        return dat

    def mk_img(self, raw, delete_noise=True):
        dat = self.run(raw)
        return list2img(dat, delete_noise=True)

    def mk_cnt(self, raw, delete_noise=True):
        dat = self.run(raw)
        return list2cnt(dat, delete_noise=True)


def raw2list(raw, delete_noise=True):
    inter = InterRaw()
    dat = inter.run(raw)
    if delete_noise == True:
        dat = without_noise(dat)
    return dat


def raw2img(raw, delete_noise=True):
    inter = InterRaw()
    return list2img(inter.run(raw), noise=noise)


def raw2cnt(raw, delete_noise=True):
    inter = InterRaw()
    return list2cnt(inter.run(raw), delete_noise=delete_noise)


if __name__ == "__main__":
    import sys
    fin = sys.argv[1]
    fout = fin[:-3]+"_hit.h5"
    interpret_h5(fin, fout, debug=3)
    # debug
    #
    # 0x20 correct tlu_timestamp based on timestamp2 0x00 based on timestamp
    print fout
