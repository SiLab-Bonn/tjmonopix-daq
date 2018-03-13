import zlib  # workaround
import yaml
import logging
import os
import time
import struct
import numpy as np
import tables as tb

from math import sqrt
import matplotlib.pyplot as plt
from matplotlib import colors
from mpl_toolkits.axes_grid1 import make_axes_locatable
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

    def gauss(self, x, A, mu, sigma):
        return A * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))

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

    def plot_scurve_histogram(self, max_occ, DUtoe, folder):

	scurves = np.load('./'+folder+'/scurvedatabot.npy')
	scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)
	scurves[:,0]=0
	scurves[:,1]=0

	param_count = scurves.shape[1]

	ticks=np.arange(0, param_count*DUtoe, 50)

	hist = np.empty([param_count, max_occ], dtype=np.uint32)
	for param in range(param_count):
    	    hist[param] = np.bincount(scurves[:, param], minlength=max_occ)[:max_occ]
 
	fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16,6), dpi=150)

	p1 = ax1.imshow(hist.T, norm=colors.LogNorm(), aspect='auto', origin='lower', extent=[0, param_count*DUtoe, 0, max_occ])
	ax1.set(xlabel='Injection [e-]', ylabel='#hits',xticks=ticks, title='Entire Bottom Half of Second Flavor (FULL DPW)')
	p1.set_interpolation('nearest')

	cb1 = fig.colorbar(p1, ax=ax1)
	figtitle = fig.suptitle('S-Curve Superposition (Histogram)', fontsize=14, fontweight='bold')
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label]):
                    #[ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
                    #ax1.get_xticklabels() + ax1.get_yticklabels()):
    	    item.set_fontsize(14)
	ax1.title.set_fontweight('bold')

	scurves = np.load('./'+folder+'/scurvedatatop.npy')
	scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)
	scurves[:,0]=0
	scurves[:,1]=0

	param_count = scurves.shape[1]

	hist = np.empty([param_count, max_occ], dtype=np.uint32)
	for param in range(param_count):
    	    hist[param] = np.bincount(scurves[:, param], minlength=max_occ)[:max_occ]
             
	p1 = ax2.imshow(hist.T, norm=colors.LogNorm(), aspect='auto', origin='lower', extent=[0, param_count*DUtoe, 0, max_occ])
	ax2.set(xlabel='Injection [e-]', ylabel='#hits',xticks=ticks, title='Entire Top Half of Second Flavor (REM DPW)')
	p1.set_interpolation('nearest')

	cb1 = fig.colorbar(p1, ax=ax2)

	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
                    #[ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
                    #ax1.get_xticklabels() + ax1.get_yticklabels()):
    	    item.set_fontsize(14)
	ax2.title.set_fontweight('bold')
	fig.savefig('./'+folder+'/Scurve_dispersion.png')

    def fit_scurvedata(self, VHLrange, start_dif, max_occ, DUtoe, threshold, sigma, folder):

	for part in ('bot', 'top'):
	    xhits = np.arange(start_dif,VHLrange+start_dif+1)*DUtoe
	    scurves = np.load('./'+folder+'/scurvedata'+part+'.npy')
	    #scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)      
	    scurves[:,0]=0
	    scurves[:,1]=0

	    thresholds = np.empty(scurves.shape[0], dtype=np.float32)
	    encs = np.empty(scurves.shape[0], dtype=np.float32)

	    for i in range(scurves.shape[0]):
		if ~np.any(scurves[i,:]):
		    thresholds[i]=0
		    encs[i]=0
		else:
		    popt, _ = curve_fit(self.scurve, xhits, scurves[i,:], p0=[max_occ, threshold, sigma], check_finite=False)
		    thresholds[i]=popt[1]
		    encs[i]=popt[2]

	    np.save('./'+folder+'/threshold'+part+'.npy',thresholds)
	    np.save('./'+folder+'/enc'+part+'.npy',encs)
	logger.info(' S-Curve fit data saved successfully')

    def plot_thr_dispersion(self, folder):

	thr = np.load('./'+folder+'/thresholdbot.npy')
	thrdelzero=np.delete(thr, (np.where(thr==0)[0]))

	diff = np.amax(thr) - np.amin(thrdelzero)
	if (np.amax(thr)) > np.median(thr)*5:
	    plot_range = np.arange(np.amin(thrdelzero), np.median(thr)*5, diff/200.)
	else:
	    plot_range = np.arange(np.amin(thrdelzero), np.amax(thr)+diff/200., diff/200.)

	tick_size = plot_range[1] - plot_range[0]

	hist, bins =  np.histogram(thr, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)

	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)
	    
	fig, (ax1, ax2) = plt.subplots(2,1, figsize=(14,14), dpi=150)
	b1 = ax1.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax1.plot(points, gau, "r-", linewidth='3')

	sCinj=popt[1]*0.07
	sFE=sqrt(((popt[2])**2.)-(sCinj**2))

	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$\n$\sigma(Cinj)=%.2fe^-$\n$\sigma(FE)=%.2fe^-$' % (abs(popt[1]), abs(popt[2]), sCinj, sFE)
	ax1.set(xlabel='Threshold [e-]', ylabel='#counts', title='Entire Bottom Half of Second Flavor (FULL DPW)')
	#props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
	t1 = ax1.text(0.02, 0.8, textright, transform=ax1.transAxes, fontsize=14, bbox=dict(facecolor='wheat', alpha=0.4))
	figtitle = fig.suptitle('Threshold Histogram', fontsize=14, fontweight='bold')
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
		     ax1.get_xticklabels() + ax1.get_yticklabels()):
	    item.set_fontsize(14)
	ax1.title.set_fontweight('bold')  
  
	###############################################   
	thr = np.load('./'+folder+'/thresholdtop.npy')
	thrdelzero=np.delete(thr, (np.where(thr==0)[0]))

	diff = np.amax(thr) - np.amin(thrdelzero)
	if (np.amax(thr)) > np.median(thr)*5:
	    plot_range = np.arange(np.amin(thrdelzero), np.median(thr)*5, diff/200.)
	else:
	    plot_range = np.arange(np.amin(thrdelzero), np.amax(thr)+diff/200., diff/200.)

	tick_size = plot_range[1] - plot_range[0]

	hist, bins =  np.histogram(thr, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)

	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)
	    
	b1 = ax2.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax2.plot(points, gau, "r-", linewidth='3')

	sCinj=popt[1]*0.07
	sFE=sqrt(((popt[2])**2.)-(sCinj**2))

	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$\n$\sigma(Cinj)=%.2fe^-$\n$\sigma(FE)=%.2fe^-$' % (abs(popt[1]), abs(popt[2]), sCinj, sFE)
	ax2.set(xlabel='Threshold [e-]', ylabel='#counts', title='Entire Top Half of Second Flavor (REM DPW)')
	t1 = ax2.text(0.02, -0.4, textright, transform=ax1.transAxes, fontsize=14, bbox=dict(facecolor='wheat', alpha=0.4))
	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label] +
		     ax2.get_xticklabels() + ax2.get_yticklabels()):
	    item.set_fontsize(14)
	ax2.title.set_fontweight('bold')
	fig.savefig('./'+folder+'/thr_dispersion.png')

    def plot_enc_dispersion(self, folder):
	enc = np.load('./'+folder+'/encbot.npy')
	encdelzero=np.delete(enc, (np.where(enc==0)[0]))

	diff = np.amax(enc) - np.amin(encdelzero)
	if (np.amax(enc)) > np.median(enc)*5:
	    plot_range = np.arange(np.amin(encdelzero), np.median(enc)*5, diff/700.)
	else:
	    plot_range = np.arange(np.amin(encdelzero), np.amax(enc)+diff/700., diff/700.)
	    

	tick_size = plot_range[1] - plot_range[0]
	hist, bins =  np.histogram(enc, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)

	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)

	fig, (ax1, ax2) = plt.subplots(2,1, figsize=(14,14), dpi=150)
	figtitle = fig.suptitle('ENC Histogram', fontsize=14, fontweight='bold')

	b1 = ax1.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax1.plot(points, gau, "r-", linewidth='2')
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	t1 = ax1.text(0.15, 0.88, textright, transform=ax1.transAxes, fontsize=14, bbox=dict(facecolor='wheat', alpha=0.4))
	ax1.set(xlabel='ENC [e-]', ylabel='#counts', title='Entire Bottom Half of Second Flavor (FULL DPW)')
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
		     ax1.get_xticklabels() + ax1.get_yticklabels()):
	    item.set_fontsize(14)
	ax1.title.set_fontweight('bold')
	#ax1.set_yscale("log", nonposy='clip') 
   
	############################################### 	    
	enc = np.load('./'+folder+'/enctop.npy')
	hist, bins =  np.histogram(enc, bins=plot_range)

	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)
	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)

	b1 = ax2.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax2.plot(points, gau, "r-", linewidth='2')
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	t1 = ax2.text(0.15, -0.32, textright, transform=ax1.transAxes, fontsize=14, bbox=dict(facecolor='wheat', alpha=0.4))
	ax2.set(xlabel='ENC [e-]', ylabel='#counts', title='Entire Top Half of Second Flavor (REM DPW)')
	figtitle = fig.suptitle('ENC Histogram', fontsize=14, fontweight='bold')
	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label] +
		     ax2.get_xticklabels() + ax2.get_yticklabels()):
	    item.set_fontsize(14)
	ax2.title.set_fontweight('bold')
	#ax2.set_yscale("log", nonposy='clip')
	fig.savefig('./'+folder+'/enc_dispersion.png')

    def dplot(self, folder, thresholdorenc):

	datatop = np.load('./'+folder+'/'+thresholdorenc+'top.npy')
	databot = np.load('./'+folder+'/'+thresholdorenc+'bot.npy')

	datatop2d = np.reshape(datatop, (112,-1))
	databot2d = np.reshape(databot, (112,-1))

	dataall2d = np.concatenate((databot2d.T,datatop2d.T))
	dataall2d = np.ma.masked_where(dataall2d == 0, dataall2d)

	cmap = plt.cm.OrRd
	cmap.set_bad(color='black')

	fig, ax1 = plt.subplots(1, 1, figsize=(12,12), dpi=150)
	p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap)
	t1 = ax1.set(xlabel='COLUMN', ylabel='ROW')
	divider = make_axes_locatable(ax1)
	cax1 = divider.append_axes("right", size="5%", pad=0.05)
	cb1 = fig.colorbar(p1, cax=cax1)
	fig.savefig('./'+folder+'/'+thresholdorenc+'_2dplot.png')

	fig, ax1 = plt.subplots(1, 1, figsize=(12,12), dpi=150)
	p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', norm=colors.LogNorm(), extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap)
	t1 = ax1.set(xlabel='COLUMN', ylabel='ROW')
	divider = make_axes_locatable(ax1)
	cax1 = divider.append_axes("right", size="5%", pad=0.05)
	cb1 = fig.colorbar(p1, cax=cax1)
	fig.savefig('./'+folder+'/'+thresholdorenc+'_2dplotlog.png')
