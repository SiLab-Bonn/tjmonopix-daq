import numpy as np
import numba
from scipy.special import erf
import multiprocessing as mp
from scipy.optimize import curve_fit
from functools import partial

import logging
from tqdm import tqdm

logger = logging.getLogger('Analysis')


def scurve(x, A, mu, sigma):
    return 0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


def zcurve(x, A, mu, sigma):
    return -0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


def line(x, m, b):
    return m * x + b


@numba.njit
def correlate_scan_ids(hits, meta_data):
    meta_i = 0

    for idx, param_id in enumerate(hits["scan_param_id"]):
        while meta_i < len(meta_data):
            if param_id >= meta_data[meta_i]['index_start'] and param_id < meta_data[meta_i]['index_stop']:
                hits[idx]['scan_param_id'] = meta_data[meta_i]['scan_param_id']
                break
            elif param_id >= meta_data[meta_i]['index_stop']:
                meta_i += 1
    return hits


@numba.njit(locals={'cluster_shape': numba.int64})
def calc_cluster_shape(cluster_array):
    '''Boolean 8x8 array to number.
    '''
    cluster_shape = 0
    indices_x, indices_y = np.nonzero(cluster_array)
    for index in np.arange(indices_x.size):
        cluster_shape += 2**xy2d_morton(indices_x[index], indices_y[index])
    return cluster_shape


@numba.njit(numba.int64(numba.uint32, numba.uint32))
def xy2d_morton(x, y):
    ''' Tuple to number.

    See: https://stackoverflow.com/questions/30539347/
         2d-morton-code-encode-decode-64bits
    '''
    x = (x | (x << 16)) & 0x0000FFFF0000FFFF
    x = (x | (x << 8)) & 0x00FF00FF00FF00FF
    x = (x | (x << 4)) & 0x0F0F0F0F0F0F0F0F
    x = (x | (x << 2)) & 0x3333333333333333
    x = (x | (x << 1)) & 0x5555555555555555

    y = (y | (y << 16)) & 0x0000FFFF0000FFFF
    y = (y | (y << 8)) & 0x00FF00FF00FF00FF
    y = (y | (y << 4)) & 0x0F0F0F0F0F0F0F0F
    y = (y | (y << 2)) & 0x3333333333333333
    y = (y | (y << 1)) & 0x5555555555555555

    return x | (y << 1)


@numba.njit
def occ_hist2d(hits):
    hist_occ = np.zeros(shape=(112, 224), dtype=np.uint32)

    for hit in hits:
        col = hit['col']
        row = hit['row']
        if col >= 0 and col < hist_occ.shape[0] and row >= 0 and row < hist_occ.shape[1]:
            hist_occ[col, row] += 1

    return hist_occ


@numba.njit
def scurve_hist3d(hits, scan_param_range):
    hist_scurves = np.zeros(shape=(112, 224, len(scan_param_range)), dtype=np.uint16)

    for hit in hits:
        col = hit["col"]
        row = hit["row"]
        param = hit["scan_param_id"]
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


def fit_line(y_data, y_err, x_data):
        """
            Fit line to x and y data.
            Returns:
                (slope, offset, chi2)
        """
        y_data = np.array(y_data, dtype=np.float)

        # Select valid data
        x = x_data[~np.isnan(y_data)]
        y = y_data[~np.isnan(y_data)]
        y_err = y_err[~np.isnan(y_data)]

        # Return if not enough data points
        if len(y) < 3:
            return (0., 0., 0.)

        # Calculate start values with difference quotient and mean y-intercept
        p0 = [(y[-1] - y[0]) / (x[-1] - x[0]),
              np.mean(y - (y[-1] - y[0]) / (x[-1] - x[0]) * x)]

        try:
            popt = curve_fit(f=line, xdata=x, ydata=y, p0=p0, sigma=y_err,
                             absolute_sigma=True if np.any(y_err) else False)[0]
            chi2 = np.sum((y - line(x, *popt))**2)
        except RuntimeError:
            return (0., 0., 0.)

        return (popt[0], popt[1], chi2 / y.shape[0] - 2 - 1)


def get_mean_from_histogram(counts, bin_positions, axis=0):
    ''' Compute average of an array that represents a histogram along the specified axis.

        The bin positions are the values and counts the occurences of these values.

        Uses vectorized numpy function without looping and is therefore fast.

        Parameters
        ----------
        counts: Array containing occurences of values to be averaged
        axis: None or int
        bin_positions: array_like associated with the values in counts.
                        Shape of count array or 1D array with shape of axis.
    '''
    weights = bin_positions
    return np.average(counts, axis=axis, weights=weights) * weights.sum(axis=min(axis, len(weights.shape) - 1)) / np.nansum(counts, axis=axis)


def get_std_from_histogram(counts, bin_positions, axis=0):
    ''' Compute RMS of an array that represents a histogram along the specified axis.

        The bin positions are the values and counts the occurences of these values.

        Uses vectorized numpy function without looping and is therefore fast.

        Parameters
        ----------
        counts: Array containing occurences of values to be averaged
        axis: None or int
        bin_positions: array_like associated with the values in counts.
                        Same shape like count array is needed!
    '''

    if np.any(bin_positions.sum(axis=axis) == 0):
        raise ValueError('The bin position are all 0 for at least one axis. Maybe you forgot to transpose the bin position array?')

    mean = get_mean_from_histogram(counts, bin_positions, axis=axis)
    weights = (bin_positions - np.expand_dims(mean, axis=axis)) ** 2
    rms_2 = get_mean_from_histogram(counts, bin_positions=weights, axis=axis)
    return np.sqrt(rms_2)




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
