import time
import numpy as np
from numba import njit
import tables
import yaml

TS_TLU = 251
TS_INJ = 252
TS_MON = 253
TS_GATE = 254
TLU = 255
COL_SIZE = 36
ROW_SIZE = 129

# debug
# 1 = 1: contined to next file read 0: data is the end of file DONOT use this bit
# 2 = 1: reset inj_cnt when the injection period is wrong
# 4 = 1: include noise flg data 0: delete
# 8 = 1: include hits which were not injected, NOT implemented!!
#     0: only the data from injected pixel


@njit
def _build_inj(dat, injlist, thlist, phaselist, inj_period, inj_n, mode, buf, scan_param_id, pre_inj, inj_id, inj_cnt):
    buf_i = 0
    dat_i = 0
    err = 0
    while dat_i < len(dat):
        if scan_param_id != dat[dat_i]["index"]:
            if inj_id != len(injlist) - 1 or inj_cnt != inj_n - 1:
                print ("ERROR: Broken data, wrong ts_inj idx, inj_cnt,inj_n-1,inj_id,len(injlist)-1"),
                print (dat_i, inj_cnt, inj_n - 1, inj_id, len(injlist) - 1)
            inj_id = -1
            inj_cnt = inj_n - 1
        scan_param_id = dat[dat_i]["index"]
        if dat[dat_i]["col"] == TS_INJ:
            d_ii = dat_i + 1
            while d_ii < len(dat):
                if dat[d_ii]["col"] == TS_INJ:
                    break
                d_ii = d_ii + 1
            if d_ii == len(dat) and (mode & 0x1) == 1:  # not the end of file:
                return err, dat_i, buf[:buf_i], scan_param_id, pre_inj, inj_id, inj_cnt
            cnt = d_ii - dat_i  # Number of TJ hits counted after one INJ timestamp

            ts_inj = np.int64(dat[dat_i]["timestamp"])
            # print (dat_i,cnt, inj_id, inj_cnt, (ts_inj-pre_inj)>>4)
            if inj_cnt == inj_n - 1:
                # Start counting injection hits and give new injection id
                inj_cnt = 0
                inj_id = inj_id + 1
            elif (np.int64(ts_inj - pre_inj) >> 4) != inj_period:
                # Otherwise, there was a previous injection. Check if timestamp makes sense
                print ("ERROR: wrong inj_period: ts_inj-pre_inj,inj_period,inj_cnt,inj_id"),
                print (np.int64(ts_inj - pre_inj) >> 4, inj_period, inj_cnt, inj_id)
                err = err + 1
                if (mode & 0x2) == 2:
                    inj_cnt = 0
                    inj_id = min(inj_id + 1, len(injlist) - 1)
                else:
                    inj_cnt = inj_cnt + 1
            else:
                # Everything is fine, add injection to counter
                inj_cnt = inj_cnt + 1

            ts_mon = 0x7FFFFFFFFFFFFFFF
            ts_mon_t = 0x7FFFFFFFFFFFFFFF
            for d_ii in range(dat_i + 1, dat_i + cnt):
                # Iterate through all hits for this injection
                if dat[d_ii]["col"] == TS_MON and dat[d_ii]["row"] == 0 and ts_mon == 0x7FFFFFFFFFFFFFFF:
                    ts_mon = np.int64(dat[d_ii]["timestamp"])
                elif dat[d_ii]["col"] == TS_MON and dat[d_ii]["row"] == 1 and ts_mon_t == 0x7FFFFFFFFFFFFFFF:
                    ts_mon_t = np.int64(dat[d_ii]["timestamp"])
                elif dat[d_ii]["col"] < COL_SIZE:
                    if mode & 0x4 == 0x4 or dat[d_ii]["cnt"] == 0:
                        ts_token = np.int64(dat[d_ii]["timestamp"])
                        # buf[buf_i]["event_number"]= scan_param_id*len(injlist)*inj_n+inj_id*inj_n+inj_cnt
                        buf[buf_i]["scan_param_id"] = scan_param_id
                        buf[buf_i]["inj_id"] = inj_id
                        buf[buf_i]["col"] = dat[d_ii]["col"]
                        buf[buf_i]["row"] = dat[d_ii]["row"]
                        buf[buf_i]["inj"] = injlist[inj_id]
                        buf[buf_i]["th"] = thlist[inj_id]
                        buf[buf_i]["phase"] = phaselist[inj_id]
                        buf[buf_i]["ts_mon"] = ts_mon
                        buf[buf_i]["ts_inj"] = ts_inj
                        buf[buf_i]["ts_token"] = ts_token
                        buf[buf_i]["tot"] = (dat[d_ii]["te"] - dat[d_ii]["le"]) & 0x3F
                        buf[buf_i]["toa"] = dat[d_ii]["le"]
                        buf[buf_i]["tot_mon"] = ts_mon_t - ts_mon
                        buf[buf_i]["flg"] = dat[d_ii]["cnt"]
                        buf_i = buf_i + 1
            pre_inj = ts_inj
            dat_i = dat_i + cnt
        else:
            dat_i = dat_i + 1
    return err, dat_i, buf[:buf_i], scan_param_id, pre_inj, inj_id, inj_cnt


buf_type = [  # ("event_number","<i8"),
    ("scan_param_id", "<i4"), ("inj_id", "<i4"),  # ## this is redundant. can be deleted later..
    ("col", "<u1"), ("row", "<u1"), ("tot", "<u1"), ("toa", "<u1"), ("flg", "<u1"),
    ("ts_inj", "<u8"), ("ts_mon", "<u8"), ("ts_token", "<u8"), ("tot_mon", "<u8"),
    ("inj", "<f4"), ("th", "<f4"), ("phase", "<u1")
]


def build_inj_h5(fhit, fraw, fout, n=500000, debug=0x2):
    buf = np.empty(n, dtype=buf_type)
    with tables.open_file(fraw) as f:
        status = yaml.load(f.root.meta_data.attrs.status)
        for i in range(0, len(f.root.kwargs), 2):
            if f.root.kwargs[i] == "injlist":
                injlist = yaml.load(f.root.kwargs[i + 1])
            elif f.root.kwargs[i] == "thlist":
                thlist = yaml.load(f.root.kwargs[i + 1])
            elif f.root.kwargs[i] == "phaselist":
                phaselist = yaml.load(f.root.kwargs[i + 1])
    inj_period = status['inj']["WIDTH"] + status['inj']["DELAY"]
    inj_n = status['inj']["REPEAT"]
    sid = -1
    inj_id = len(injlist) - 1
    inj_cnt = inj_n - 1
    pre_inj = 0
    print phaselist
    with tables.open_file(fout, "w") as f_o:
        description = np.zeros((1,), dtype=buf_type).dtype
        hit_table = f_o.create_table(f_o.root, name="Hits", description=description, title='hit_data')
        with tables.open_file(fhit) as f:
            end = len(f.root.Hits)
            start = 0
            t0 = time.time()
            while start < end:  # # this does not work, need to read with one chunck
                tmpend = min(end, start + n)
                dat = f.root.Hits[start:tmpend]
                print "data (inj_n %d,inj_loop %d): INJ=%d MONO=%d MON=%d" % (
                    inj_n, len(injlist),
                    len(np.where(dat["col"] == TS_INJ)[0]),
                    len(np.where(dat["col"] < COL_SIZE)[0]),
                    len(np.where(dat["col"] == TS_MON)[0])
                )
                if end == tmpend:
                    mode = 0 | debug
                else:
                    mode = 1 | debug
                (err, d_i, hit_dat, sid, pre_inj, inj_id, inj_cnt) = _build_inj(
                    dat,
                    injlist, thlist, phaselist,  # # not well written.
                    inj_period, inj_n, mode, buf,
                    sid, pre_inj, inj_id, inj_cnt
                )
                hit_table.append(hit_dat)
                hit_table.flush()
                print "%d %d %.3f%% %.3fs %dhits %derrs" % (start, d_i, 100.0 * (start + d_i) / end, time.time() - t0, len(hit_dat), err)
                start = start + d_i
    return


if __name__ == "__main__":
    import sys
    fraw = sys.argv[1]
    fhit = fraw[:-7] + "hit.h5"
    fout = fraw[:-7] + "ts.h5"
    assign_ts(fhit, fraw, fts, n=10000000)
    print fout

