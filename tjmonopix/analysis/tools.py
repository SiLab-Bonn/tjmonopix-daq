import numpy as np
from scipy.special import erf
from scipy.optimize import curve_fit
import logging

def scurve(x, A, mu, sigma):
    return 0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


def fit_scurve(scurve_indexes, scurve_data, repeat_command):  # data of some pixels to fit, has to be global for the multiprocessing module
    index = np.argmax(np.diff(scurve_data))
    max_occ = np.median(scurve_data[index:])
    threshold = scurve_indexes[index]
    if abs(max_occ) <= 1e-08:  # or index == 0: occupancy is zero or close to zero
        popt = [0, 0, 0]
    else:
        try:
            popt, _ = curve_fit(scurve, scurve_indexes, scurve_data, p0=[repeat_command, threshold, 1.], check_finite=False) #0.01 vorher
            logging.debug('Fit-params-scurve: %s %s %s ', str(popt[0]),str(popt[1]),str(popt[2]))
        except RuntimeError:  # fit failed
            popt = [0, 0, 0]
            logging.info('Fit did not work scurve: %s %s %s', str(popt[0]),
                         str(popt[1]), str(popt[2]))

    if popt[1] < 0:  # threshold < 0 rarely happens if fit does not work
        popt = [0, 0, 0]
    return popt
