import numpy as np
import matplotlib.pyplot as plt
import tables as tb

from numba import njit
import logging

def get_timewalk_hist(hit_file, show_plots=False):

    # One hit consists of 136 bit of data. Choose chunk size according to available RAM
    chunk_size = 100000000

    tdc_data = np.array([], dtype=[('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('cnt', '<u4'), ('timestamp', '<u8')])
    tlu_data = np.array([], dtype=[('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('cnt', '<u4'), ('timestamp', '<u8')])
    tj_data = np.array([], dtype=[('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('cnt', '<u4'), ('timestamp', '<u8')])

    # TODO: Get all pixels where HIT OR is enabled
    mon_pixels = np.array([[1, 50, 102]])

    with tb.open_file(hit_file, 'r') as in_file:
        start = 0
        end = start + chunk_size
        while True:
            hit_data = in_file.root.Hits[start:end]
            if len(hit_data) == 0:
                break
            else:
                print len(tdc_data)
                print len(hit_data[hit_data['col'] == 253])

                tlu_data = np.concatenate([tlu_data, hit_data[hit_data['col'] == 252]])
                tdc_data = np.concatenate([tdc_data, hit_data[hit_data['col'] == 253]])
                tj_data = np.concatenate([tj_data, hit_data[np.logical_and(hit_data['col'] < 112, hit_data['cnt'] == 0)]])

                start = end
                end = start + chunk_size

    print("TJ: {} hits | TDC: {} hits | TLU: {} hits".format(len(tj_data), len(tdc_data), len(tlu_data)))
    # plt.hist(tdc_data['cnt'])

    tlu_tdc_data = np.empty(len(tj_data) + len(tdc_data),
                            dtype=[("tdc", 'u8'), ("tdc_timestamp", 'u8'),
                            ("tlu", 'u8'), ("tlu_timestamp", 'u8')])

    # search matching TLU hit based on timestamp
    upper_lim, lower_lim = 0, -175  # limits in timestamp units (=clock cycles)

    @njit
    def correlate_tdc_tlu(tdc_data, tlu_data, data_out, upper_lim, lower_lim):
        tdc_i, dat_i, tlu_i = 0, 0, 0
        while tdc_i < len(tdc_data) and dat_i < len(data_out) and tlu_i < len(tlu_data):
            if tdc_data[tdc_i]["timestamp"] > tlu_data[tlu_i]["timestamp"] + np.uint64(np.abs(upper_lim)):
                # TLU timestamp is larger than TDC timestamp + upper limit. Check next TLU timestamp
                tlu_i += 1

            # If we get here, TLU timestamp is not delayed more than upper_limit
            elif tdc_data[tdc_i]["timestamp"] < tlu_data[tlu_i]["timestamp"] - np.uint64(np.abs(lower_lim)):
                # TLU timestamp is smaller than TDC timestamp - lower limit. There is no TLU hit within
                # given range around TDC hit. Move to next TDC hit
                tdc_i += 1
            else:
                # TLU timestamp is close to TDC timestamp
                data_out[dat_i]["tdc"] = tdc_data[tdc_i]["cnt"]
                data_out[dat_i]["tdc_timestamp"] = tdc_data[tdc_i]["timestamp"]
                data_out[dat_i]["tlu_timestamp"] = tlu_data[tlu_i]["timestamp"]
                data_out[dat_i]["tlu"] = tlu_data[tlu_i]["cnt"]
                dat_i = dat_i + 1
                tlu_i = tlu_i + 1
        # print tdc_i < len(tdc_data), dat_i < len(data_out), tlu_i < len(tlu_data)
        # print tdc_i,dat_i,tlu_i
        return data_out[:dat_i]

    tlu_tdc_data = correlate_tdc_tlu(tdc_data, tlu_data, tlu_tdc_data, upper_lim, lower_lim)
    print "# of correated data (TLU-TDC)", len(tlu_tdc_data)
    # print np.int64(tlu_tdc_data["tdc_timestamp"])-np.int64(tlu_tdc_data["tlu_timestamp"])

    # print dat_i, tdc_i, tlu_i

    if show_plots:
        plt.title("Delay between TDC and TLU timestamp")
        plt.hist(np.int64(tlu_tdc_data["tdc_timestamp"]) - np.int64(tlu_tdc_data["tlu_timestamp"]), bins=np.arange(lower_lim, upper_lim, 1))
        plt.xlabel("TDC timestamp - TLU timestamp [clk]")
        plt.show()

    # Find corresponding TJ hits
    upper = 0x200  # 512
    lower = -0x200  # 256

    data_out = np.empty(len(tj_data) + len(tlu_tdc_data),
                        dtype=[("token_timestamp", 'u8'), ("le", 'u2'), ("te", 'u2'), ("row", 'u2'), ("col", 'u2'),
                               ("tdc_timestamp", 'u8'), ("tdc", 'u8'),
                               ("tlu_timestamp", 'u8'), ("tlu", 'u8')])

    @njit
    def correlate_tlu_tj(tlu_tdc_data, tj_data, data_out, upper, lower):
        tj_i, tlu_tdc_i, i = 0, 0, 0

        while tlu_tdc_i < len(tlu_tdc_data) and tj_i < len(tj_data) and i < len(data_out):
            if tlu_tdc_data[tlu_tdc_i]["tdc_timestamp"] > tj_data[tj_i]["timestamp"] + np.uint64(np.abs(upper)):
                # TLU timestamp is larger than TJ hit timestamp + upper limit. Move to next TJ hit
                tj_i += 1

            # If we get here, TJ hit comes at maximum 512 clk cycles after TLU hit
            elif tlu_tdc_data[tlu_tdc_i]["tdc_timestamp"] + np.uint64(np.abs(lower)) < tj_data[tj_i]["timestamp"]:
                # TLU timestamp
                tlu_tdc_i += 1

            else:
                # There is a TJ hit is close to the given TLU hit (acceptable range defined by upper and lower limit)
                data_out[i]["tdc_timestamp"] = tlu_tdc_data[tlu_tdc_i]["tdc_timestamp"]
                data_out[i]["tdc"] = tlu_tdc_data[tlu_tdc_i]["tdc"]
                data_out[i]["tlu_timestamp"] = tlu_tdc_data[tlu_tdc_i]["tlu_timestamp"]
                data_out[i]["tlu"] = tlu_tdc_data[tlu_tdc_i]["tlu"]
                data_out[i]["token_timestamp"] = tj_data[tj_i]["timestamp"]
                data_out[i]["row"] = tj_data[tj_i]["row"]
                data_out[i]["col"] = tj_data[tj_i]["col"]
                data_out[i]["te"] = tj_data[tj_i]["te"]
                data_out[i]["le"] = tj_data[tj_i]["le"]
                i += 1
                tj_i += 1
        return data_out[:i]

    data_out = correlate_tlu_tj(tlu_tdc_data, tj_data, data_out, upper, lower)
    print len(data_out)

    if show_plots:
        plt.title("Delay between TDC and token timestamp")
        plt.hist(np.int64(data_out["tdc_timestamp"]) - np.int64(data_out["token_timestamp"]),
                 bins=np.arange(lower, upper, 1))
        plt.xlabel("TDC timestamp - Token timestamp [clk]")
        plt.show()

    _, ts_indices, cnt = np.unique(
        data_out["token_timestamp"], return_index=True, return_counts=True)
    tot = (data_out['te'] - data_out['le']) & 0x3F

    print len(ts_indices)

    # dat_max stores only hits that are seed pixels
    dat_max = np.empty(len(ts_indices),
                       dtype=[("token_timestamp", 'u8'), ("le", 'u2'), ("te", 'u2'), ("row", 'u2'), ("col", 'u2'),
                              ("tdc_timestamp", 'u8'), ("tdc", 'u8'),
                              ("tlu_timestamp", 'u8'), ("tlu", 'u8')])

    for i, ts_index in enumerate(ts_indices):
        # max_i is the index of the hit that corresponds to a seed pixel (maximum charge)
        max_i = np.argmax(tot[i: i + cnt[i]])
        dat_max[i] = data_out[i + max_i]

    # for i, pix in enumerate(mon_pixels):
    #     dat=dat_max[np.bitwise_and(dat_max['col']==p[1],dat_max['row']==p[2])]
    #     print i,p,len(dat)
    #     if i==16:
    #         hist=np.histogram(np.int64(dat["tdc_timestamp"])-np.int64(dat["tlu_timestamp"]),
    #                           bins=np.arange(-200,0,1));
    print "dat_max: ", len(dat_max), dat_max["col"][:100]

    dat = dat_max[np.logical_and(dat_max["col"] == mon_pixels[0][1], dat_max["row"] == mon_pixels[0][2])]

    # logging.info("# of correlated entries from selected pixel(s): {}".format(len(dat)))

    # sel = np.logical_and(dat_max["col"] == 10, dat_max["row"] == 80)
    # plt.plot(dat_max["tdc"][sel], (dat_max["te"][sel] - dat_max["le"][sel]) & 0x3F, '.', label="before seed pixel")
    # plt.plot(dat["tdc"], (dat["te"] - dat["le"]) & 0x3F, '.', label="after seed pixel")
    # plt.xlabel("TDC")
    # plt.ylabel("ToT")

    # plt.legend()
    # plt.show() 

    return dat


if __name__ == "__main__":
    hit_files = ["/media/data/tjmonopix_tb_elsa_26-03-2018/run36/tjmonopix_36_180327-025812_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run41/tjmonopix_41_180327-053722_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run42/tjmonopix_42_180327-063853_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run43/tjmonopix_43_180327-074107_hit.h5"]

    # High bias, low rate
    hit_files_1 = ["/media/data/tjmonopix_tb_elsa_26-03-2018/run84/tjmonopix_84_180328-170452_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run85/tjmonopix_85_180328-181237_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run86/tjmonopix_86_180328-193052_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run88/tjmonopix_88_180328-210053_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/run89/tjmonopix_89_180328-222253_hit.h5"]

    # Low bias, high rate
    hit_files_2 = ["/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_54_180327-184451_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_55_180327-194630_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_56_180327-210236_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_58_180327-225546_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_59_180328-000721_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_60_180328-011841_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_61_180328-022254_hit.h5",
                "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_63_180328-030613_hit.h5"]

    # High bias, high rate
    hit_files_3 = ["/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_94_180329-010926_hit.h5",
                 "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_95_180329-025838_hit.h5",
                 "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_96_180329-040832_hit.h5",
                 "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_97_180329-052037_hit.h5",
                 "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_98_180329-063041_hit.h5",
                 "/media/data/tjmonopix_tb_elsa_26-03-2018/tjmonopix_99_180329-074059_hit.h5"]

    hit_files = ["/media/data/tjmonopix_180417-144806_hit.h5"]

    # Sr90 data
    # hit_files = ["/home/silab/git/tjmonopix-daq/tjmonopix/scans/output_data/20180322_001649_simple_hit.h5"]

    hist, edges = np.histogram(np.array([]), bins=np.arange(-200,0,1))
    labels = ["TH=low HV: -3V/-3V", "TH=high HV: -3V/-3V", "TH=low HV: -5V/-20V"]

    for hit_file in hit_files:
        data = get_timewalk_hist(hit_file)
        tmp_hist, _ = np.histogram(np.int64(data["tdc_timestamp"]) - np.int64(data["tlu_timestamp"]), bins=np.arange(-200,0,1))
        hist += tmp_hist

    # Calculate center of bins and convert to ns
    mids = (edges[:-1] + 0.5 * (edges[11] - edges[10])) / .64

    start = mids[hist > 0][0]
    # n_two_bin = hist[mids > 0]

    print("# Hits: {}".format(np.sum(hist)))

    plt.step(mids, hist)
    plt.plot([start, start], [0, 30], 'C1--')
    plt.plot([start + 25, start + 25], [0, 30], 'C1--')

    plt.xlabel("HITOR - TLU [ns]")
    plt.show()

    plt.hist2d((data["te"] - data["le"]) & 0x3F,
               (np.int64(data["tdc_timestamp"]) - np.int64(data["tlu_timestamp"])) / .64 + 260,
               bins=[np.arange(-0.5, 63.5, 1), np.arange(-10, 70, 1)])
    plt.xlabel('ToT')
    plt.ylabel('HIT_OR - TLU [clk]')
    cb = plt.colorbar()
    cb.set_label('#')
    plt.show()
    # mids = edges[:-1] + 0.5
    # duration = mids[hist > 0][-1] - mids[hist > 0][0]
    # print mids[hist > 0][-1], mids[hist > 0][0]
    # print duration / 0.64

    # Number of hits that are out of time (more than 25ns late)
    # mids_start = mids[hist > 0][0]
    # print np.sum(hist[mids > mids_start + 25 * 0.64])
