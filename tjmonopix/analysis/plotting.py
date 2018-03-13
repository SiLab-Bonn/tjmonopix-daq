import zlib  # workaround
import yaml
import logging
import os
import time
import struct
import numpy as np
import tables as tb

import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import erf

import basil
#from bitarray import bitarray
from basil.dut import Dut
from basil.utils.BitLogic import BitLogic

loglevel = logging.INFO

''' Set up main logger '''
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.getLogger('basil.HL.RegisterHardwareLayer').setLevel(logging.WARNING)

logging.basicConfig(
    format="%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s")

logger = logging.getLogger('TJMONOPIX-PLOTTING')
logger.setLevel(loglevel)

class plotting():
	
    def scurve(self, x, A, mu, sigma):
        return 0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A    

    def plot_scurve(self, col, row, xhits, hits, max_occ, threshold, s, se, DUtoe):

        popt, _ = curve_fit(self.scurve, xhits, hits, p0=[max_occ, threshold, s], check_finite=False)

        newxhits = np.arange(xhits[0],xhits[-1],0.01)
        fit = self.scurve(newxhits, *popt)

        fig, (ax1, ax2) = plt.subplots(1, 2, sharey=True, figsize=(15,5))
        ax1.plot(xhits, hits, 'o', label='data')
        ax1.plot(newxhits, fit, label='fit')
        ax1.set(xlabel='DU', ylabel='Hit count',title=('ENC of pixel (' +str(col) +',' +str(row) +')'))
        ax1.legend(loc='best')
        ax1.text(0, max_occ*0.8, ('Theshold=' +str(round(popt[1],2)) +'DU, ENC=' +str(round(popt[2],2)) +'DU'), bbox=dict(facecolor='white', alpha=0.5))
        ax1.text(0, max_occ*0.7, "1DU=14.1mV, 1,43e/mV", bbox=dict(facecolor='white', alpha=0.5))

        xhitse = (np.array(xhits))*DUtoe
        popt, _ = curve_fit(self.scurve, xhitse, hits, p0=[max_occ, threshold*DUtoe, se], check_finite=False)
        newxhitse = newxhits*DUtoe
        fite = self.scurve(newxhitse, *popt)

        ax2.plot(xhitse, hits, 'o', label='data')
        ax2.plot(newxhitse, fite, label='fit')
        ax2.set(xlabel='e-', ylabel='Hit count',title=('ENC of pixel (' +str(col) +',' +str(row) +')'))
        ax2.legend(loc='best')
        ax2.text(0, max_occ*0.8, ('Theshold=' +str(round(popt[1],2)) +'e-, ENC=' +str(round(popt[2],2)) +'e-'), bbox=dict(facecolor='white', alpha=0.5))
        ax2.text(0, max_occ*0.7, "1DU=14.1mV, 1,43e/mV", bbox=dict(facecolor='white', alpha=0.5))
        fig.savefig('ENC.png')
