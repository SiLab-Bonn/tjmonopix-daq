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
from matplotlib.ticker import LogFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.optimize import curve_fit
from scipy.special import erf
from scipy.misc import factorial

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

    def poisson(self, k, A, lamb):
        return A * (lamb**k/factorial(k)) * np.exp(-lamb)


    def plot_scurve(self, col, row, xhits, hits, max_occ, threshold, s, se, DUtoe, transparent):

        popt, _ = curve_fit(self.scurve, xhits, hits, p0=[max_occ, threshold, s], check_finite=False)

        newxhits = np.arange(xhits[0],xhits[-1],0.01)
        fit = self.scurve(newxhits, *popt)

        fig, (ax1) = plt.subplots(1, sharey=True, figsize=(10,8))

        xhitse = (np.array(xhits))*DUtoe
        popt, _ = curve_fit(self.scurve, xhitse, hits, p0=[max_occ, threshold*DUtoe, se], check_finite=False)
        newxhitse = newxhits*DUtoe
        fite = self.scurve(newxhitse, *popt)

        ax1.plot(xhitse, hits, 'o', label='data', markersize=10)
        ax1.plot(newxhitse, fite, label='fit', linewidth=3)
        ax1.set(xlabel='Injection [e-]', ylabel='Hit count')#,title=('ENC of pixel (' +str(col) +',' +str(row) +')'))
        ax1.legend(loc='best', fontsize=16)
        ax1.text(280, max_occ*0.8, ('Theshold=' +str(round(popt[1],2)) +'e-, ENC=' +str(round(popt[2],2)) +'e-'), bbox=dict(facecolor='wheat', alpha=0.4), fontsize=20)
        #ax1.text(-20, max_occ*0.7, "1DU=14.1mV, 1,43e/mV", bbox=dict(facecolor='white'), fontsize=16)
        [i.set_linewidth(1) for i in ax1.spines.itervalues()]
        for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label]):
                    #ax1.get_xticklabels() + ax1.get_yticklabels()):
            item.set_fontsize(20)
            item.set_fontweight('bold')
        for item in (ax1.get_xticklabels() + ax1.get_yticklabels()):
            item.set_fontsize(16)
            item.set_fontweight('bold')
        fig.savefig('ENC.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent, format='png')


    def plot_scurve2(self, col, row, xhits, hits, max_occ, threshold, s, se, DUtoe, transparent):

        popt, _ = curve_fit(self.scurve, xhits, hits, p0=[max_occ, threshold, s], check_finite=False)

        newxhits = np.arange(xhits[0],xhits[-1],0.01)
        fit = self.scurve(newxhits, *popt)

        fig, (ax1, ax2) = plt.subplots(1, 2, sharey=True, figsize=(15,5))
        ax1.plot(xhits, hits, 'o', label='data')
        ax1.plot(newxhits, fit, label='fit')
        ax1.set(xlabel='DU', ylabel='Hit count',title=('ENC of pixel (' +str(col) +',' +str(row) +')'))
        ax1.legend(loc='best')
        ax1.text(-1, max_occ*0.8, ('Theshold=' +str(round(popt[1],2)) +'DU, ENC=' +str(round(popt[2],2)) +'DU'), bbox=dict(facecolor='white', alpha=0.5))
        ax1.text(-1, max_occ*0.7, "1DU=14.1mV, 1,43e/mV", bbox=dict(facecolor='white', alpha=0.5))

        xhitse = (np.array(xhits))*DUtoe
        popt, _ = curve_fit(self.scurve, xhitse, hits, p0=[max_occ, threshold*DUtoe, se], check_finite=False)
        newxhitse = newxhits*DUtoe
        fite = self.scurve(newxhitse, *popt)

        ax2.plot(xhitse, hits, 'o', label='data')
        ax2.plot(newxhitse, fite, label='fit')
        ax2.set(xlabel='e-', ylabel='Hit count',title=('ENC of pixel (' +str(col) +',' +str(row) +')'))
        ax2.legend(loc='best')
        ax2.text(-20, max_occ*0.8, ('Theshold=' +str(round(popt[1],2)) +'e-, ENC=' +str(round(popt[2],2)) +'e-'), bbox=dict(facecolor='white', alpha=0.5))
        ax2.text(-20, max_occ*0.7, "1DU=14.1mV, 1,43e/mV", bbox=dict(facecolor='white', alpha=0.5))
        fig.savefig('ENC.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)

    def plot_scurve_histogram(self, max_occ, DUtoe, xtickspacing, ytickspacing, figx, figy, dpi, transparent, folder):

	scurves = np.load('./'+folder+'/scurvedatabot.npy')
	scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)
	scurves[:,0]=0
	scurves[:,1]=0

	param_count = scurves.shape[1]

	xticks=np.arange(0, param_count*DUtoe, xtickspacing)
	yticks=np.arange(0, max_occ, ytickspacing)

	hist = np.empty([param_count, max_occ], dtype=np.uint32)
	for param in range(param_count):
    	    hist[param] = np.bincount(scurves[:, param], minlength=max_occ)[:max_occ]
 
	fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(figx, figy), dpi=dpi)

	p1 = ax1.imshow(hist.T, norm=colors.LogNorm(), aspect='auto', origin='lower', extent=[0, param_count*DUtoe, 0, max_occ])
	ax1.set(xlabel='Injection [e-]', ylabel='#hits',xticks=xticks, yticks=yticks, title='Entire Bottom Half of Second Flavor (FULL DPW)')
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
	ax2.set(xlabel='Injection [e-]', ylabel='#hits',xticks=xticks, yticks=yticks, title='Entire Top Half of Second Flavor (REM DPW)')
	p1.set_interpolation('nearest')

	cb1 = fig.colorbar(p1, ax=ax2)

	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
                    #[ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
                    #ax1.get_xticklabels() + ax1.get_yticklabels()):
    	    item.set_fontsize(14)
	ax2.title.set_fontweight('bold')
	fig.savefig('./'+folder+'/Scurve_dispersion.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)
	
	
    def plot_scurve_histogram_all(self, max_occ, DUtoe, xtickspacing, ytickspacing, figx, figy, dpi, transparent, folder):

	scurves = np.load('./'+folder+'/scurvedata.npy')
	scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)
	scurves[:,0]=0
	scurves[:,1]=0

	param_count = scurves.shape[1]

	xticks=np.arange(0, param_count*DUtoe, xtickspacing)
	yticks=np.arange(0, max_occ, ytickspacing)

	hist = np.empty([param_count, max_occ], dtype=np.uint32)
	for param in range(param_count):
    	    hist[param] = np.bincount(scurves[:, param], minlength=max_occ)[:max_occ]
 
	fig, (ax1) = plt.subplots(1, 1, figsize=(figx, figy), dpi=dpi)

	p1 = ax1.imshow(hist.T, norm=colors.LogNorm(), aspect='auto', origin='lower', extent=[0, param_count*DUtoe, 0, max_occ])
	ax1.set(xlabel='Injection [e-]', ylabel='#hits',xticks=xticks, yticks=yticks, title='Full Second Flavor (RED DPW)')
	p1.set_interpolation('nearest')

	cb1 = fig.colorbar(p1, ax=ax1)
	figtitle = fig.suptitle('S-Curve Superposition (Histogram)', fontsize=14, fontweight='bold')
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label]):
                    #[ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
                    #ax1.get_xticklabels() + ax1.get_yticklabels()):
    	    item.set_fontsize(14)
	ax1.title.set_fontweight('bold')
	fig.savefig('./'+folder+'/Scurve_dispersion.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)

    def fit_scurvedata(self, VHLrange, start_dif, max_occ, DUtoe, threshold, sigma, folder):
	errorstot=0
	for part in ('bot', 'top'):
	    xhits = np.arange(start_dif,VHLrange+start_dif+1)*DUtoe
	    scurves = np.load('./'+folder+'/scurvedata'+part+'.npy')
	    #scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)      
	    scurves[:,0]=0
	    scurves[:,1]=0

	    thresholds = np.empty(scurves.shape[0], dtype=np.float32)
	    encs = np.empty(scurves.shape[0], dtype=np.float32)
	    errors=0
	    for i in range(scurves.shape[0]):
			if ~np.any(scurves[i,:]):
				thresholds[i]=0
				encs[i]=0
			else:
				try:
					popt, _ = curve_fit(self.scurve, xhits, scurves[i,:], p0=[max_occ, threshold, sigma], check_finite=False)
					thresholds[i]=popt[1]
					encs[i]=popt[2]
				except:
					errors += 1
					thresholds[i]=0
					encs[i]=0
					logger.info('Fitting Error in part %s, no=%d' %(part, i)) 	
					errorstot += errors
	    if errors != 0:
			logger.info('%d Fitting Errors in part %s' %(errors, part)) 	

	    np.save('./'+folder+'/threshold'+part+'.npy',thresholds)
	    np.save('./'+folder+'/enc'+part+'.npy',encs)
	logger.info('S-Curve fit data saved successfully, total errors=%d' %(errorstot))
	
	
    def fit_scurvedata_all(self, VHLrange, start_dif, max_occ, DUtoe, threshold, sigma, folder):
	errorstot=0
	xhits = np.arange(start_dif,VHLrange+start_dif+1)*DUtoe
	scurves = np.load('./'+folder+'/scurvedata.npy')
	#scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)      
	scurves[:,0]=0
	scurves[:,1]=0

	thresholds = np.empty(scurves.shape[0], dtype=np.float32)
	encs = np.empty(scurves.shape[0], dtype=np.float32)
	errors=0
	for i in range(scurves.shape[0]):
		if ~np.any(scurves[i,:]):
			thresholds[i]=0
			encs[i]=0
		else:
			try:
				popt, _ = curve_fit(self.scurve, xhits, scurves[i,:], p0=[max_occ, threshold, sigma], check_finite=False)
				thresholds[i]=popt[1]
				encs[i]=popt[2]
			except:
				errors += 1
				thresholds[i]=0
				encs[i]=0
				logger.info('Fitting Error, no=%d' %(i)) 	
				errorstot += errors
	if errors != 0:
		logger.info('%d Fitting Errors' %(errors)) 	

	np.save('./'+folder+'/threshold.npy',thresholds)
	np.save('./'+folder+'/enc.npy',encs)
	logger.info('S-Curve fit data saved successfully, total errors=%d' %(errorstot))


    def fit_scurvedata_local(self, VHLrange, start_dif, max_occ, DUtoe, threshold, sigma, folder, part):
	errorstot=0
        xhits = np.arange(start_dif,VHLrange+start_dif+1)*DUtoe
        scurves = np.load('./'+folder+'scurvedata'+part+'.npy')
        #scurves = np.delete(scurves, (np.where(~scurves.any(axis=1))[0]), axis=0)      
        scurves[:,0]=0
        scurves[:,1]=0

        thresholds = np.zeros(scurves.shape[0], dtype=np.float32)
        encs = np.zeros(scurves.shape[0], dtype=np.float32)
        errors=0
        for i in range(scurves.shape[0]):
            if ~np.any(scurves[i,:]):
                thresholds[i]=0
                encs[i]=0
            else:
                try:
                    popt, _ = curve_fit(self.scurve, xhits, scurves[i,:], p0=[max_occ, threshold, sigma], check_finite=False)
                    thresholds[i]=popt[1]
                    encs[i]=popt[2]
                except:
                    errors += 1
                    thresholds[i]=0
                    encs[i]=0
                    logger.info('Fitting Error in part %s, no=%d' %(part, i)) 	
        errorstot += errors
        if errors != 0:
            logger.info('%d Fitting Errors in part %s' %(errors, part)) 	

        np.save('./'+folder+'threshold'+part+'.npy',thresholds)
        np.save('./'+folder+'enc'+part+'.npy',encs)
	logger.info('S-Curve fit data saved successfully, total errors=%d' %(errorstot))

    def plot_thr_dispersion(self, figx, figy, dpi, autoscale, samescale, rangelowbot, rangehighbot, resolutionbot, rangelowtop, rangehightop, resolutiontop, ytickauto, ytickhigh, ytickspacing, xtickauto, xticklow, xtickhigh, xtickspacing, transparent, folder):

	thr = np.load('./'+folder+'/thresholdbot.npy')
	thr=np.delete(thr, (np.where(thr==0)[0]))

	diff = np.amax(thr) - np.amin(thr)
	if autoscale == True:
	    if (np.amax(thr)) > np.median(thr)*5:
	        plot_range = np.arange(np.amin(thr), np.median(thr)*5, diff/200.)
	    else:
	        plot_range = np.arange(np.amin(thr), np.amax(thr)+diff/200., diff/200.)
	else:
	    plot_range=np.arange(rangelowbot, rangehighbot, diff/resolutionbot)

	tick_size = plot_range[1] - plot_range[0]

	hist, bins =  np.histogram(thr, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)

	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)
	    
	fig, (ax1, ax2) = plt.subplots(1,2, figsize=(figx,figy), dpi=dpi)
	b1 = ax1.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax1.plot(points, gau, "r-", linewidth='3')

	sCinj=popt[1]*0.07
	sFE=sqrt(((popt[2])**2.)-(sCinj**2))

	yticks=np.arange(0, ytickhigh, ytickspacing)
	xticks=np.arange(xticklow, xtickhigh, xtickspacing)
	#textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$\n$\sigma(FE)=%.2fe^-$' % (abs(popt[1]), abs(popt[2]), sFE)
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	ax1.set(xlabel='Injection [e-]', ylabel='#counts', title='Entire Bottom Half of Second Flavor (FULL DPW)')
	if ytickauto==False:
	   ax1.yaxis.set_ticks(yticks)
	if xtickauto==False:
	   ax1.xaxis.set_ticks(xticks)

	#props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
	t1 = ax1.text(0.02, 0.9, textright, transform=ax1.transAxes, fontsize=16, bbox=dict(facecolor='wheat', alpha=0.4))
	figtitle = fig.suptitle('Threshold Histogram', fontsize=16, fontweight='bold')
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
		     ax1.get_xticklabels() + ax1.get_yticklabels()):
	    item.set_fontsize(14)
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label]):
    	    item.set_fontsize(16)
	ax1.title.set_fontweight('bold')  
  
	###############################################   
	thr = np.load('./'+folder+'/thresholdtop.npy')
	thr=np.delete(thr, (np.where(thr==0)[0]))

	#diff = np.amax(thr) - np.amin(thr)
	if autoscale == True:
	    if samescale == False:
	        if (np.amax(thr)) > np.median(thr)*5:
	            plot_range = np.arange(np.amin(thr), np.median(thr)*5, diff/200.)
	        else:
	            plot_range = np.arange(np.amin(thr), np.amax(thr)+diff/200., diff/200.)
	else:
	    plot_range=np.arange(rangelowtop, rangehightop, diff/resolutiontop)

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
	
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	#textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$\n$\sigma(FE)=%.2fe^-$' % (abs(popt[1]), abs(popt[2]), sFE)
	ax2.set(xlabel='Injection [e-]', ylabel='#counts', title='Entire Top Half of Second Flavor (REM DPW)')
	if ytickauto==False:
	   ax2.yaxis.set_ticks(yticks)
	if xtickauto==False:
	   ax2.xaxis.set_ticks(xticks)

	t1 = ax2.text(1.22, 0.9, textright, transform=ax1.transAxes, fontsize=16, bbox=dict(facecolor='wheat', alpha=0.4))
	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label] +
		     ax2.get_xticklabels() + ax2.get_yticklabels()):
	    item.set_fontsize(14)
	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
    	    item.set_fontsize(16)
	ax2.title.set_fontweight('bold')

	fig.savefig('./'+folder+'/thr_dispersion.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)


    def plot_thr_dispersion_local(self, figx, figy, dpi, autoscale, rangelow, rangehigh, resolution, ytickauto, ytickhigh, ytickspacing, xtickauto, xticklow, xtickhigh, xtickspacing, folder, part):

	thr = np.load('./'+folder+'threshold'+part+'.npy')
	thr=np.delete(thr, (np.where(thr==0)[0]))

	diff = np.amax(thr) - np.amin(thr)
	if autoscale == True:
	    if (np.amax(thr)) > np.median(thr)*5:
	        plot_range = np.arange(np.amin(thr), np.median(thr)*5, diff/200.)
	    else:
	        plot_range = np.arange(np.amin(thr), np.amax(thr)+diff/200., diff/200.)
	else:
	    plot_range=np.arange(rangelow, rangehigh, diff/resolution)

	tick_size = plot_range[1] - plot_range[0]

	hist, bins =  np.histogram(thr, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)

	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)
	    
	fig, (ax1) = plt.subplots(1, figsize=(figx,figy), dpi=dpi)
	b1 = ax1.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax1.plot(points, gau, "r-", linewidth='3')

	sCinj=popt[1]*0.07
	sFE=sqrt(((popt[2])**2.)-(sCinj**2))

	yticks=np.arange(0, ytickhigh, ytickspacing)
	xticks=np.arange(xticklow, xtickhigh, xtickspacing)
	#textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$\n$\sigma(FE)=%.2fe^-$' % (abs(popt[1]), abs(popt[2]), sFE)
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	ax1.set(xlabel='Injection [e-]', ylabel='#counts', title='Entire Bottom Half of Second Flavor (FULL DPW)')
	if ytickauto==False:
	   ax1.yaxis.set_ticks(yticks)
	if xtickauto==False:
	   ax1.xaxis.set_ticks(xticks)

	#props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
	t1 = ax1.text(0.02, 0.9, textright, transform=ax1.transAxes, fontsize=16, bbox=dict(facecolor='wheat', alpha=0.4))
	figtitle = fig.suptitle('Threshold Histogram', fontsize=16, fontweight='bold')
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
		     ax1.get_xticklabels() + ax1.get_yticklabels()):
	    item.set_fontsize(14)
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label]):
    	    item.set_fontsize(16)
	ax1.title.set_fontweight('bold')
	return abs(popt[1]),abs(popt[2])  


    def plot_enc_dispersion(self, figx, figy, dpi, autoscale, samescale, rangelowbot, rangehighbot, resolutionbot, rangelowtop, rangehightop, resolutiontop, ytickauto, ytickhigh, ytickspacing, xtickauto, xticklow, xtickhigh, xtickspacing, transparent, folder):
	enc = np.load('./'+folder+'/encbot.npy')
	enc=np.delete(enc, (np.where(enc<=2.5)[0]))

	diff = np.amax(enc) - np.amin(enc)
	if autoscale==True:
	    if (np.amax(enc)) > np.median(enc)*5:
	        plot_range = np.arange(np.amin(enc), np.median(enc)*5, diff/700.)
	    else:
	        plot_range = np.arange(np.amin(enc), np.amax(enc)+diff/700., diff/700.)
	else:
	    plot_range=np.arange(rangelowbot, rangehighbot, diff/resolutionbot)

	tick_size = plot_range[1] - plot_range[0]
	hist, bins =  np.histogram(enc, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)
	
	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)
	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)

	fig, (ax1, ax2) = plt.subplots(1,2, figsize=(figx, figy), dpi=dpi)
	figtitle = fig.suptitle('ENC Histogram', fontsize=16, fontweight='bold')

	b1 = ax1.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax1.plot(points, gau, "r-", linewidth='2')

	yticks=np.arange(0, ytickhigh, ytickspacing)
	xticks=np.arange(xticklow, xtickhigh, xtickspacing)
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	t1 = ax1.text(0.02, 0.9, textright, transform=ax1.transAxes, fontsize=16, bbox=dict(facecolor='wheat', alpha=0.4))
	ax1.set(xlabel='Injection [e-]', ylabel='#counts', title='Entire Bottom Half of Second Flavor (FULL DPW)')
	if ytickauto==False:
	   ax1.yaxis.set_ticks(yticks)
	if xtickauto==False:
	   ax1.xaxis.set_ticks(xticks)

	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
		     ax1.get_xticklabels() + ax1.get_yticklabels()):
	    item.set_fontsize(14)
	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label]):
    	    item.set_fontsize(16)
	ax1.title.set_fontweight('bold')
	#ax1.set_yscale("log", nonposy='clip') 
   
	############################################### 	    
	enc = np.load('./'+folder+'/enctop.npy')
	enc=np.delete(enc, (np.where(enc<=2.5)[0]))
	#diff = np.amax(enc) - np.amin(enc)

	if autoscale==True:
	    if samescale==False:
	        if (np.amax(enc)) > np.median(enc)*5:
	            plot_range = np.arange(np.amin(enc), np.median(enc)*5, diff/700.)
	        else:
	            plot_range = np.arange(np.amin(enc), np.amax(enc)+diff/700., diff/700.)
	else:
	    plot_range=np.arange(rangelowtop, rangehightop, diff/resolutiontop)
	
	tick_size = plot_range[1] - plot_range[0]
	hist, bins =  np.histogram(enc, bins=plot_range)

	bin_centres = (bins[:-1] + bins[1:]) / 2
	p0 = (np.amax(hist), np.mean(bins), (max(plot_range)-min(plot_range))/3)
	popt, _ = curve_fit(self.gauss, bin_centres, hist, p0=p0)

	points = np.linspace(min(plot_range), max(plot_range), 500)
	gau = self.gauss(points, *popt)

	b1 = ax2.bar(bins[:-1], hist, width=tick_size, align='edge')
	g1 = ax2.plot(points, gau, "r-", linewidth='2')
	textright = '$\mu=%.2fe^-$\n$\sigma=%.2fe^-$' % (abs(popt[1]), abs(popt[2]))
	t1 = ax2.text(1.22, 0.9, textright, transform=ax1.transAxes, fontsize=16, bbox=dict(facecolor='wheat', alpha=0.4))
	ax2.set(xlabel='Injection [e-]', ylabel='#counts', title='Entire Top Half of Second Flavor (REM DPW)')
	if ytickauto==False:
	   ax2.yaxis.set_ticks(yticks)
	if xtickauto==False:
	   ax2.xaxis.set_ticks(xticks)

	figtitle = fig.suptitle('ENC Histogram', fontsize=16, fontweight='bold')
	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label] +
		     ax2.get_xticklabels() + ax2.get_yticklabels()):
	    item.set_fontsize(14)
	ax2.title.set_fontweight('bold')
	for item in ([ax2.title, ax2.xaxis.label, ax2.yaxis.label]):
    	    item.set_fontsize(16)
	#ax2.set_yscale("log", nonposy='clip')
	fig.savefig('./'+folder+'/enc_dispersion.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)

    def dplot(self, folder, thresholdorenc, figx, figy, dpi, colm, vauto, Log, vmin, vmax, cbtickauto, cbtickmin, cbtickmax, cbtickspacing, mint1, mint2, transparent, flavor):

	datatop = np.load('./'+folder+'/'+thresholdorenc+'top.npy')
	databot = np.load('./'+folder+'/'+thresholdorenc+'bot.npy')

	datatop2d = np.reshape(datatop, (112,-1))
	databot2d = np.reshape(databot, (112,-1))

	dataall2d = np.concatenate((databot2d.T,datatop2d.T))
	dataall2d = np.ma.masked_where(dataall2d == 0, dataall2d)

	cmap = plt.get_cmap(colm)
	cmap.set_bad(color='black')
	formatter = LogFormatter(10, labelOnlyBase=False, minor_thresholds=(mint1, mint2)) 
	xticks=np.arange(0, 113, 14)
	yticks=np.arange(0, 224, 10)

	if vauto==False:
	    cbticks=np.arange(vmin, vmax, cbtickspacing)
	if cbtickauto==False:
	    cbticks=np.arange(cbtickmin, cbtickmax, cbtickspacing)

	fig, ax1 = plt.subplots(1, 1, figsize=(figx,figy), dpi=dpi)

	if thresholdorenc=='threshold':
	    titlefw='Threshold'
	if thresholdorenc=='enc':
	    titlefw='ENC'

	if Log==True:
	    if vauto==True:
	        p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap, norm=colors.LogNorm())
	    else:
	        p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap, vmin=vmin, vmax=vmax, norm=colors.LogNorm())
	    t1 = ax1.set(xlabel='COLUMN', ylabel='ROW', xticks=xticks, yticks=yticks, title=titlefw +' 2-D plot of the ' + flavor + ' flavor, Log color')
	else:
	    if vauto==True:
	        p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap)
	    else:
	        p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap, vmin=vmin, vmax=vmax)
	    t1 = ax1.set(xlabel='COLUMN', ylabel='ROW', xticks=xticks, yticks=yticks, title=titlefw +' 2-D plot of the ' + flavor + ' flavor')


	divider = make_axes_locatable(ax1)
	cax1 = divider.append_axes("right", size="5%", pad=0.05)

	if vauto == False or cbtickauto == False:
	    if Log==True:
	        cb1 = fig.colorbar(p1, cax=cax1, ticks=cbticks, format=formatter)
	    else:
	  	cb1 = fig.colorbar(p1, cax=cax1, ticks=cbticks)
	else:
	    if Log==True:
	        cb1 = fig.colorbar(p1, cax=cax1, format=formatter)
	    else:
	  	cb1 = fig.colorbar(p1, cax=cax1)

	for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
		     ax1.get_xticklabels() + ax1.get_yticklabels()):
	    item.set_fontsize(12)
	ax1.title.set_fontweight('bold')

	fig.savefig('./'+folder+'/'+thresholdorenc+'_2dplot.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)

#	fig, ax1 = plt.subplots(1, 1, figsize=(12,12), dpi=100)
#	if vauto==True:
#	    p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap, norm=colors.LogNorm())
#	else:
#	    p1 = ax1.imshow(dataall2d, aspect='equal', origin='lower', extent=[0, dataall2d.shape[1]-1, 0, dataall2d.shape[0]-1], cmap=cmap, vmin=vmin, vmax=vmax, norm=colors.LogNorm())
#	t1 = ax1.set(xlabel='COLUMN', ylabel='ROW', xticks=xticks, yticks=yticks)
#	divider = make_axes_locatable(ax1)
#	cax1 = divider.append_axes("right", size="5%", pad=0.05)
#	cb1 = fig.colorbar(p1, cax=cax1)
#	fig.savefig('./'+folder+'/'+thresholdorenc+'_2dplotlog.png')

    def dplot_all(self, folder, thresholdorenc, figx, figy, dpi, colm, vauto, Log, vmin, vmax, cbtickauto, cbtickmin, cbtickmax, cbtickspacing, mint1, mint2, transparent, flavor):
		data = np.load('./'+folder+'/'+thresholdorenc+'.npy')
		data2d = np.reshape(data, (112,-1))
		data2dT = data2d.T
		data2dT = np.ma.masked_where(data2dT == 0, data2dT)

		cmap = plt.get_cmap(colm)
		cmap.set_bad(color='black')
		formatter = LogFormatter(10, labelOnlyBase=False, minor_thresholds=(mint1, mint2)) 
		xticks=np.arange(0, 113, 14)
		yticks=np.arange(0, 224, 10)

		if vauto==False:
			cbticks=np.arange(vmin, vmax, cbtickspacing)
		if cbtickauto==False:
			cbticks=np.arange(cbtickmin, cbtickmax, cbtickspacing)

		fig, ax1 = plt.subplots(1, 1, figsize=(figx,figy), dpi=dpi)

		if thresholdorenc=='threshold':
			titlefw='Threshold'
		if thresholdorenc=='enc':
			titlefw='ENC'

		if Log==True:
			if vauto==True:
				p1 = ax1.imshow(data2dT, aspect='equal', origin='lower', extent=[0, data2dT.shape[1]-1, 0, data2dT.shape[0]-1], cmap=cmap, norm=colors.LogNorm())
			else:
				p1 = ax1.imshow(data2dT, aspect='equal', origin='lower', extent=[0, data2dT.shape[1]-1, 0, data2dT.shape[0]-1], cmap=cmap, vmin=vmin, vmax=vmax, norm=colors.LogNorm())
			t1 = ax1.set(xlabel='COLUMN', ylabel='ROW', xticks=xticks, yticks=yticks, title=titlefw +' 2-D plot of the ' + flavor + ' flavor, Log color')
		else:
			if vauto==True:
				p1 = ax1.imshow(data2dT, aspect='equal', origin='lower', extent=[0, data2dT.shape[1]-1, 0, data2dT.shape[0]-1], cmap=cmap)
			else:
				p1 = ax1.imshow(data2dT, aspect='equal', origin='lower', extent=[0, data2dT.shape[1]-1, 0, data2dT.shape[0]-1], cmap=cmap, vmin=vmin, vmax=vmax)
			t1 = ax1.set(xlabel='COLUMN', ylabel='ROW', xticks=xticks, yticks=yticks, title=titlefw +' 2-D plot of the ' + flavor + ' flavor')


		divider = make_axes_locatable(ax1)
		cax1 = divider.append_axes("right", size="5%", pad=0.05)

		if vauto == False or cbtickauto == False:
			if Log==True:
				cb1 = fig.colorbar(p1, cax=cax1, ticks=cbticks, format=formatter)
			else:
				cb1 = fig.colorbar(p1, cax=cax1, ticks=cbticks)
		else:
			if Log==True:
				cb1 = fig.colorbar(p1, cax=cax1, format=formatter)
			else:
				cb1 = fig.colorbar(p1, cax=cax1)

		for item in ([ax1.title, ax1.xaxis.label, ax1.yaxis.label] +
				 ax1.get_xticklabels() + ax1.get_yticklabels()):
			item.set_fontsize(12)
		ax1.title.set_fontweight('bold')

		fig.savefig('./'+folder+'/'+thresholdorenc+'_2dplot.png', bbox_inches='tight', dpi='figure', frameon=False, transparent=transparent)
