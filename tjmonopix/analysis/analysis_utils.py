import numpy as np
from numba import njit
from scipy.special import erf
import multiprocessing as mp
from scipy.optimize import curve_fit
from functools import partial

import logging
from tqdm import tqdm

logger = logging.getLogger('Analysis')

np.warnings.filterwarnings('ignore')


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


def scurve(x, A, mu, sigma):
    return 0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


def zcurve(x, A, mu, sigma):
    return -0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


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


@njit
def correlate_scan_ids(hits, meta_data):
    meta_i = 0

    for i, d in enumerate(hits["idx"]):
        while meta_i < len(meta_data):
            # print d
            if d >= meta_data[meta_i]['index_start'] and d < meta_data[meta_i]['index_stop']:
                hits[i]['idx'] = meta_data[meta_i]['scan_param_id']
                break
            elif d >= meta_data[meta_i]['index_stop']:
                meta_i = meta_i + 1
    return hits


@njit
def occ_hist2d(hits):
    hist_occ = np.zeros(shape=(112, 224), dtype=np.uint32)

    for hit in hits:
        col = hit['col']
        row = hit['row']
        if col >= 0 and col < hist_occ.shape[0] and row >= 0 and row < hist_occ.shape[1]:
            hist_occ[col, row] += 1

    return hist_occ


@njit
def scurve_hist3d(hits, scan_param_range):
    hist_scurves = np.zeros(shape=(112, 224, len(scan_param_range)), dtype=np.uint16)

    for hit in hits:
        col = hit["col"]
        row = hit["row"]
        param = hit["idx"]
        if col >= 0 and col < hist_scurves.shape[0] and row >= 0 and row < hist_scurves.shape[1]:
            hist_scurves[col, row, param] += 1

    return hist_scurves


def imap_bar(func, args, n_processes=None):
    ''' Apply function (func) to interable (args) with progressbar
    '''
    p = mp.Pool(n_processes)
    res_list = []
    pbar = tqdm(total=len(args))
    for _, res in enumerate(p.imap(func, args)):
        pbar.update()
        res_list.append(res)
    pbar.close()
    p.close()
    p.join()
    return res_list


def get_threshold(x, y, n_injections, invert_x=False):
    ''' Fit less approximation of threshold from s-curve.

        From: https://doi.org/10.1016/j.nima.2013.10.022

        Parameters
        ----------
        x, y : numpy array like
            Data in x and y
        n_injections: integer
            Number of injections
    '''

    # Sum over last dimension to support 1D and 2D hists
    M = y.sum(axis=len(y.shape) - 1)  # is total number of hits
    d = np.diff(x)[0]  # Delta x
    if not np.all(np.diff(x) == d):
        raise NotImplementedError('Threshold can only be calculated for equidistant x values!')
    if invert_x:
        return x.min() + (d * M).astype(np.float) / n_injections
    return x.max() - (d * M).astype(np.float) / n_injections


def get_noise(x, y, n_injections, invert_x=False):
    ''' Fit less approximation of noise from s-curve.

        From: https://doi.org/10.1016/j.nima.2013.10.022

        Parameters
        ----------
        x, y : numpy array like
            Data in x and y
        n_injections: integer
            Number of injections
    '''

    mu = get_threshold(x, y, n_injections, invert_x)
    d = np.abs(np.diff(x)[0])

    if invert_x:
        mu1 = y[x > mu].sum()
        mu2 = (n_injections - y[x < mu]).sum()
    else:
        mu1 = y[x < mu].sum()
        mu2 = (n_injections - y[x > mu]).sum()

    return d * (mu1 + mu2).astype(np.float) / n_injections * np.sqrt(np.pi / 2.)


def fit_scurve(scurve_data, scan_param_range, n_injections, sigma_0, invert_x):
    '''
        Fit one pixel data with Scurve.
        Has to be global function for the multiprocessing module.

        Returns:
            (mu, sigma, chi2/ndf)
    '''

    scurve_data = np.array(scurve_data, dtype=np.float)

    # Deselect masked values (== nan)
    x = scan_param_range[~np.isnan(scurve_data)]
    y = scurve_data[~np.isnan(scurve_data)]

    # Only fit data that is fittable
    if np.all(y == 0) or np.all(np.isnan(y)) or x.shape[0] < 3:
        return (0., 0., 0.)
    if y.max() < 0.2 * n_injections:
        return (0., 0., 0.)

    # Calculate data errors, Binomial errors
    yerr = np.sqrt(y * (1. - y.astype(np.float) / n_injections))
    # Set minimum error != 0, needed for fit minimizers
    # Set arbitrarly to error of 0.5 injections
    min_err = np.sqrt(0.5 - 0.5 / n_injections)
    yerr[yerr < min_err] = min_err
    # Additional hits not following fit model set high error
    sel_bad = y > n_injections
    yerr[sel_bad] = (y - n_injections)[sel_bad]

    # Calculate threshold start value:
    mu = get_threshold(x=x, y=y,
                       n_injections=n_injections,
                       invert_x=invert_x)

    # Set fit start values
    p0 = [n_injections, mu, sigma_0]

    try:
        if invert_x:
            popt = curve_fit(f=zcurve, xdata=x,
                             ydata=y, p0=p0, sigma=yerr,
                             absolute_sigma=True if np.any(yerr) else False)[0]
            chi2 = np.sum((y - zcurve(x, *popt))**2)
        else:
            popt = curve_fit(f=scurve, xdata=x,
                             ydata=y, p0=p0, sigma=yerr,
                             absolute_sigma=True if np.any(yerr) else False,
                             method='lm')[0]
            chi2 = np.sum((y - scurve(x, *popt))**2)
    except RuntimeError:  # fit failed
        return (0., 0., 0.)

    # Treat data that does not follow an S-Curve, every fit result is possible here but not meaningful
    max_threshold = x.max() + 5. * np.abs(popt[2])
    min_threshold = x.min() - 5. * np.abs(popt[2])
    if popt[2] <= 0 or not min_threshold < popt[1] < max_threshold:
        return (0., 0., 0.)

    return (popt[1], popt[2], chi2 / (y.shape[0] - 3 - 1))


def fit_scurves_multithread(scurves, scan_param_range, n_injections=None, invert_x=False, optimize_fit_range=False):
    ''' Fit Scurves on all available cores in parallel.

        Parameters
        ----------
        scurves: numpy array like
            Histogram with S-Curves. Channel index in the first and data in the second dimension.
        scan_param_range: array like
            Values used durig S-Curve scanning.
        n_injections: integer
            Number of injections
        invert_x: boolean
            True when x-axis inverted
        optimize_fit_range: boolean
            Reduce fit range of each S-curve independently to the S-Curve like range. Take full
            range if false
    '''

    scan_param_range = np.array(scan_param_range)  # Make sure it is numpy array

    # Loop over S-curves to determine the fit range. Noisy data is excluded by searching for the
    # plateau region of an S-curve and only taking the value until the plateau ends. Fit range
    # is specified by a masked array.
    if optimize_fit_range:
        scurve_mask = np.ones_like(scurves, dtype=np.bool)  # Mask to specify fit range
        for i, scurve in enumerate(scurves):
            if not np.any(scurve) or np.all(scurve == n_injections):  # Speedup, nothing to do
                continue

            scurve_diff = np.diff(scurve.astype(np.float))
            max_inj = np.min([n_injections, scurve.max()])

            # Get indeces where S-Curve is settled (max injections and no slope)
            # Convert the result to a 1D numpy array
            idc_settled = np.array(np.argwhere(np.logical_and(scurve_diff == 0, scurve[:-1] == max_inj)))[:, 0]

            try:
                # Get highest index of settled values
                idx_max = idc_settled.max()  # Maximum value
                settle_region = idc_settled - np.arange(idx_max - idc_settled.shape[0], idx_max)
                idx_min = np.argmax(settle_region == 1)  # Minimum of settled region
                idx_max = np.argmax(settle_region[::-1] == 1)  # Maximum of settled region
                idx_start = idc_settled[idx_min]  # Start value for fit for zcurve
                idx_stop = idc_settled[::-1][idx_max] + 1  # Stop value for fit for scurve
            except ValueError:  # No settled region
                idx_start = 0
                idx_stop = scurve.shape[0]

            # At least 2 points are needed
            if idx_start > scurve.shape[0] - 3:
                idx_start = scurve.shape[0] - 3
            if idx_stop < 2:
                idx_stop = 2

            if invert_x:
                scurve_mask[i, idx_start:] = 0
            else:
                scurve_mask[i, :idx_stop] = 0
        scurves_masked = np.ma.masked_array(scurves, scurve_mask)
    else:
        scurves_masked = np.ma.masked_array(scurves)

    # Calculate noise median for fit start value
    logger.info("Calculate S-curve fit start parameters")
    sigmas = []
    for curve in tqdm(scurves_masked):
        # Calculate from pixels with valid data (maximum = n_injections)
        if curve.max() == n_injections:
            if np.all(curve.mask == np.ma.nomask):
                x = scan_param_range
            else:
                x = scan_param_range[~curve.mask]

            sigma = get_noise(x=x,
                              y=curve.compressed(),
                              n_injections=n_injections,
                              invert_x=invert_x)
            sigmas.append(sigma)
    sigma_0 = np.median(sigmas)

    logger.info("Start S-curve fit on %d CPU core(s)", mp.cpu_count())

    partialfit_scurve = partial(fit_scurve,
                                scan_param_range=scan_param_range,
                                n_injections=n_injections,
                                sigma_0=sigma_0,
                                invert_x=invert_x)

    result_list = imap_bar(partialfit_scurve, scurves_masked.tolist())  # Masked array entries to list leads to NaNs
    result_array = np.array(result_list)
    logger.info("S-curve fit finished")

    thr = result_array[:, 0]
    sig = result_array[:, 1]
    chi2ndf = result_array[:, 2]
    thr2D = np.reshape(thr, (112, 224))
    sig2D = np.reshape(sig, (112, 224))
    chi2ndf2D = np.reshape(chi2ndf, (112, 224))
    return thr2D, sig2D, chi2ndf2D



# def param_hist(hits, n_params):
#     hist_params = np.empty(shape=(112, 224, n_params))
#     for hit in hits:
#         col = hit['col']
#         row = hit['row']
#         par = hit['scan_param_id']
#         if col >= 0 and col < hist_params.shape[0] and row >= 0 and row < hist_params.shape[1] and par >= 0 and par < hist_params.shape[2]:
#             hist_params[col, row, par] += 1
#         else:
#             ValueError
