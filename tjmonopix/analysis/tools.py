import numpy as np
from scipy.special import erf
from scipy.optimize import curve_fit
import logging
from tqdm import tqdm

import multiprocessing as mp
from functools import partial

logger = logging.getLogger(__name__)

def scurve(x, A, mu, sigma):
    return 0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


def zcurve(x, A, mu, sigma):
    return -0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A



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
    if invert_x:
        x = x[::-1].copy()
    M = y.sum(axis=len(y.shape) - 1)
    d = np.diff(x)[0]
    if invert_x:
        return x.min() + d * M / n_injections
    return x.max() - d * M / n_injections


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

    if invert_x:
        x = x[::-1].copy()
    qmax = x.max()
    M = y.sum()
    d = np.diff(x)[0]
    mu = qmax - d * M / n_injections
    mu1 = y[x < mu].sum()
    mu2 = (n_injections - y[x > mu]).sum()
    return d * (mu1 + mu2) / n_injections * np.sqrt(np.pi / 2.)



def fit_scurve(scurve_data, scan_param_range, n_injections, sigma_0, invert_x):
    '''
        Fit one pixel data with Scurve.
        Has to be global function for the multiprocessing module.

        Returns:
            (mu, sigma, chi2/ndf)
    '''
    scurve_data = np.array(scurve_data)
    # Only fit data that is fittable
    if np.all(scurve_data == 0):
        return (0., 0., 0.)
    if scurve_data.max() < 0.2 * n_injections:
        return (0., 0., 0.)

    # Calculate data errors, Binomial errors
    yerr = np.sqrt(scurve_data *
                   (1. - scurve_data.astype(np.float) / n_injections))
    # Set minimum error != 0, needed for fit minimizers
    # Set arbitrarly to error of 0.5 injections
    min_err = np.sqrt(0.5 - 0.5 / n_injections)
    yerr[yerr < min_err] = min_err
    # Additional hits not following fit model set high error
    sel_bad = scurve_data > n_injections
    yerr[sel_bad] = (scurve_data - n_injections)[sel_bad]

    # Calculate threshold start value:
    mu = get_threshold(x=scan_param_range,
                       y=scurve_data,
                       n_injections=n_injections,
                       invert_x=invert_x)

    # Set fit start values
    p0 = [n_injections, mu, sigma_0]
    try:
        if invert_x:
            popt = curve_fit(f=zcurve, xdata=scan_param_range,
                             ydata=scurve_data, p0=p0, sigma=yerr,
                             absolute_sigma=True if np.any(yerr) else False)[0]
            chi2 = np.sum((scurve_data - zcurve(scan_param_range, *popt))**2)
        else:
            popt = curve_fit(f=scurve, xdata=scan_param_range,
                             ydata=scurve_data, p0=p0, sigma=yerr,
                             absolute_sigma=True if np.any(yerr) else False,
                             method='lm')[0]
            chi2 = np.sum((scurve_data - scurve(scan_param_range, *popt))**2)
    except RuntimeError:  # fit failed
        return (0., 0., 0.)

    # Treat data that does not follow an S-Curve, every fit result is possible
    # here but not meaningful
    if not invert_x:
        max_threshold = scan_param_range[-1] + 0.5 * (scan_param_range[-1] -
                                                      scan_param_range[0])
    else:
        max_threshold = scan_param_range[0] + 0.5 * (scan_param_range[0] -
                                                     scan_param_range[-1])
    if popt[1] < 0 or popt[2] <= 0 or popt[1] > max_threshold:
        return (0., 0., 0.)

    return (popt[1], popt[2], chi2 / (scurve_data.shape[0] - 3 - 1))
 

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



def fit_scurves_multithread(scurves, scan_param_range,
                            n_injections=None, invert_x=False):
    logger.info("Start S-curve fit on %d CPU core(s)", mp.cpu_count())

    scurves = np.array(scurves)
    scan_param_range = np.array(scan_param_range)

    # Calculate noise median for fit start value
    sigmas = []
    for curve in scurves:
            # TODO: n_injections is not defined, can this happen?
        if not n_injections:
            n_injections = curve.max()
        # Calculate from pixels with valid data (maximum = n_injections)
        if curve.max() <= n_injections + 5:
            sigma = get_noise(x=scan_param_range[::-1] if invert_x else scan_param_range,
                              y=curve,
                              n_injections=n_injections)
            sigmas.append(sigma)
    sigma_0 = np.median(sigmas)

    partialfit_scurve = partial(fit_scurve,
                                scan_param_range=scan_param_range,
                                n_injections=n_injections,
                                sigma_0=sigma_0,
                                invert_x=invert_x)

    result_list = imap_bar(partialfit_scurve,
                           scurves.tolist())
    result_array = np.array(result_list)
    result_array = np.asarray(result_list)
    logger.info("S-curve fit finished")

    thr = result_array[:, 0]
    sig = result_array[:, 1]
    chi2ndf = result_array[:, 2]
    thr2D = np.reshape(thr, (112, 224))
    sig2D = np.reshape(sig, (112, 224))
    chi2ndf2D = np.reshape(chi2ndf, (112, 224))
    return thr2D, sig2D, chi2ndf2D


if __name__ ==  "__main__":
    pass
