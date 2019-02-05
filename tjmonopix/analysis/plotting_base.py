import numpy as np
import math
import logging
import shutil
import os,sys
import matplotlib
import random
import datetime
import tables

import matplotlib.pyplot as plt
from collections import OrderedDict
from scipy.optimize import curve_fit
from scipy.stats import norm
from matplotlib.figure import Figure
from matplotlib.artist import setp
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import colors, cm
from matplotlib import gridspec
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as ticker

COL_SIZE = 36 ##TODO change hard coded values
ROW_SIZE = 129
TITLE_COLOR = '#07529a'
OVERTEXT_COLOR = '#07529a'

import monopix_daq.analysis.utils

class PlottingBase(object):
    def __init__(self, fout, save_png=False ,save_single_pdf=False):
        self.logger = logging.getLogger()
        #self.logger.setLevel(loglevel)
        
        self.plot_cnt = 0
        self.save_png = save_png
        self.save_single_pdf = save_single_pdf
        self.filename = fout
        self.out_file = PdfPages(self.filename)
        
    def _save_plots(self, fig, suffix=None, tight=True):
        increase_count = False
        bbox_inches = 'tight' if tight else ''
        fig.tight_layout()
        if suffix is None:
            suffix = str(self.plot_cnt)
        self.out_file.savefig(fig, bbox_inches=bbox_inches)
        if self.save_png:
            fig.savefig(self.filename[:-4] + '_' +
                        suffix + '.png') #, bbox_inches=bbox_inches)
            increase_count = True
        if self.save_single_pdf:
            fig.savefig(self.filename[:-4] + '_' +
                        suffix + '.pdf') #, bbox_inches=bbox_inches)
            increase_count = True
        if increase_count:
            self.plot_cnt += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.out_file is not None and isinstance(self.out_file, PdfPages):
            self.logger.info('Closing output PDF file: %s', str(self.out_file._file.fh.name))
            self.out_file.close()
            shutil.copyfile(self.filename, os.path.join(os.path.split(self.filename)[0], 'last_scan.pdf'))

    def _add_title(self,text,fig):
        #fig.subplots_adjust(top=0.85)
        #y_coord = 0.92
        #fig.text(0.1, y_coord, text, fontsize=12, color=OVERTEXT_COLOR, transform=fig.transFigure)
        fig.suptitle(text, fontsize=12,color=OVERTEXT_COLOR)

    def table_1value(self,dat,n_row=20,n_col=3,
                     page_title="Chip configurations"):
        keys=np.sort(np.array(dat.keys()))
        ##fill table
        cellText=[["" for i in range(n_col*2)] for j in range(n_row)]
        for i,k in enumerate(keys):
            cellText[i%20][i/20*2]=k
            cellText[i%20][i/20*2+1]=dat[k]
        colLabels=[]
        colWidths=[]
        for i in range(n_col):
            colLabels.append("Param")
            colWidths.append(0.15) ## width for param name
            colLabels.append("Value")
            colWidths.append(0.15) ## width for value
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        fig.patch.set_visible(False)
        ax.set_adjustable('box')
        ax.axis('off')
        ax.axis('tight')

        tab=ax.table(cellText=cellText,
                 colLabels=colLabels,
                 colWidths = colWidths,
                 loc='upper center')
        tab.set_fontsize(10)
        for key, cell in tab.get_celld().items():
           cell.set_linewidth(0.1)
        if page_title is not None and len(page_title)>0:
            self._add_title(page_title,fig)
        tab.scale(1,0.5)
        self.out_file.savefig(fig)
        #self._save_plots(fig, suffix=None, tight=True)
        
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_adjustable('box')

    def plot_2d_pixel_4(self, dat, page_title="Pixel configurations",
                        title=["Preamp","Inj","Mon","TDAC"], 
                        x_axis_title="Column", y_axis_title="Row", z_axis_title="",
                        z_min=[0,0,0,0], z_max=[1,1,1,15]):
        fig = Figure()
        FigureCanvas(fig)
        for i in range(4):
            ax = fig.add_subplot(221+i)
            
            cmap = cm.get_cmap('plasma')
            cmap.set_bad('w')
            cmap.set_over('r')  # Make noisy pixels red
#            if z_max[i]+2-z_min[i] < 20:
#                bounds = np.linspace(start=z_min[i], stop=z_max[i] + 1,
#                                 num=z_max[i]+2-z_min[i],
#                                 endpoint=True)
#                norm = colors.BoundaryNorm(bounds, cmap.N)
#            else:
#                norm = colors.BoundaryNorm()

            im=ax.imshow(np.transpose(dat[i]),origin='lower',aspect="auto",
                     vmax=z_max[i]+1,vmin=z_min[i], interpolation='none',
                     cmap=cmap #, norm=norm
                     )
            ax.set_title(title[i])
            ax.set_ylim((-0.5, ROW_SIZE-0.5))
            ax.set_xlim((-0.5, COL_SIZE-0.5))

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.1)
            cb = fig.colorbar(im, cax=cax)
            cb.set_label(z_axis_title)
        if page_title is not None and len(page_title)>0:
            fig.suptitle(page_title, fontsize=12,color=OVERTEXT_COLOR, y=1.05)
        self._save_plots(fig)
        
    def plot_1d_pixel_hists(self,hist2d_array, mask=None, bins=30,
                           top_axis_factor=None,
                           top_axis_title="Threshold [e]",
                           x_axis_title="Test pulse injection [V]",
                           y_axis_title="# of pixel",
                           dat_title=["TH=0.81V"],
                           page_title=None,
                           title="Threshold dispersion"):
        if mask is None:
            mask=np.ones([COL_SIZE, ROW_SIZE],dtype=int)
        elif isinstance(mask,list):
            mask=np.array(mask)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_adjustable('box')

        for hist2d in hist2d_array:
            hist2d=hist2d[mask==1]
            hist=ax.hist(hist2d.reshape([-1]),
            bins=bins, histtype="step")
            
        ax.set_xbound(hist[1][0],hist[1][-1])

        ax.set_xlabel(x_axis_title)
        ax.set_ylabel(y_axis_title)
        
        if top_axis_factor is None:
            ax.set_title(title,color=TITLE_COLOR)
        else:
            ax2=ax.twiny()
            ax2.set_xbound(hist[1][0]*top_axis_factor,hist[1][-1]*top_axis_factor)
            ax2.set_xlabel(top_axis_title)
            pad=40
            ax.set_title(title,pad=40,color=TITLE_COLOR)


        if page_title is not None and len(page_title)>0:
            self._add_title(page_title,fig)
        self._save_plots(fig)
        
    def plot_2d_pixel_hist(self, hist2d, page_title=None,
                           title="Hit Occupancy",
                           z_axis_title=None, 
                           z_min=0, z_max=None):
        if z_max == 'median':
            z_max = 2 * np.ma.median(hist2d)
        elif z_max == 'maximum':
            z_max = np.ma.max(hist2d)
        elif z_max is None:
            z_max = np.percentile(hist2d, q=90)
            if np.any(hist2d > z_max):
                z_max = 1.1 * z_max
        if z_max < 1 or hist2d.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist2d)
        if z_min == z_max or hist2d.all() is np.ma.masked:
            z_min = 0
            
        x_axis_title="Column"
        y_axis_title="Row"

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_adjustable('box')
        #extent = [0.5, 400.5, 192.5, 0.5]
        bounds = np.linspace(start=z_min, stop=z_max + 1, num=255, endpoint=True)
        cmap = cm.get_cmap('viridis')
        cmap.set_bad('k')
        cmap.set_over('r')  # Make noisy pixels red
        cmap.set_under('w')
        #norm = colors.BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(np.transpose(hist2d), interpolation='none', aspect='auto', 
                       vmax=z_max+1,vmin=z_min,
                       cmap=cmap, # norm=norm,
                       origin='lower')  # TODO: use pcolor or pcolormesh
        ax.set_ylim((-0.5, ROW_SIZE-0.5))
        ax.set_xlim((-0.5, COL_SIZE-0.5))
        ax.set_title(title + r' ($\Sigma$ = {0})'.format((0 if hist2d.all() is np.ma.masked else np.ma.sum(hist2d))), color=TITLE_COLOR)
        ax.set_xlabel(x_axis_title)
        ax.set_ylabel(y_axis_title)

        divider = make_axes_locatable(ax)

        cax = divider.append_axes("right", size="5%", pad=0.2)
        cb = fig.colorbar(im, cax=cax)
        cb.set_label(z_axis_title)
        if page_title is not None and len(page_title)>0:
            self._add_title(page_title,fig)
        self._save_plots(fig)
        
    def plot_2d_hist(self, hist2d, bins=None,
                     page_title=None,
                     title="Hit Occupancy",
                     x_axis_title="Test pulse injection [V]",
                     y_axis_title="Counts", 
                     z_axis_title=None, z_min=1, z_max=None, z_scale="lin"):
        if z_max == 'median':
            z_max = 2 * np.ma.median(hist2d)
        elif z_max == 'maximum':
            z_max = np.ma.max(hist2d)*1.1
        elif z_max is None:
            z_max = np.percentile(hist2d, q=90)
            if np.any(hist2d > z_max):
                z_max = 1.1 * z_max
        if z_max < 1 or hist2d.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist2d)
        if z_min == z_max or hist2d.all() is np.ma.masked:
            z_min = 0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_adjustable('box')

        bounds = np.linspace(start=z_min, stop=z_max + 1, num=255, endpoint=True)
        cmap = cm.get_cmap('viridis')
        
        cmap.set_over('r')
        cmap.set_under('w')
        
        if z_scale=="log":
            norm = colors.LogNorm()
            cmap.set_bad('w')
        else:
            norm = None
            cmap.set_bad('k')

        im = ax.imshow(np.transpose(hist2d), interpolation='none', aspect='auto', 
                       vmax=z_max+1,vmin=z_min,
                       cmap=cmap,norm=norm,
                       extent=[bins[0][0],bins[0][-1],bins[1][0],bins[1][-1]],
                       origin='lower')

        ax.set_title(title + r' ($\Sigma$ = {0})'.format((0 if hist2d.all() is np.ma.masked else np.ma.sum(hist2d))), color=TITLE_COLOR)
        ax.set_xlabel(x_axis_title)
        ax.set_ylabel(y_axis_title)

        divider = make_axes_locatable(ax)

        cax = divider.append_axes("right", size="5%", pad=0.2)
        cb = fig.colorbar(im, cax=cax)
        cb.set_label(z_axis_title)
        if page_title is not None and len(page_title)>0:
            self._add_title(page_title,fig)
        self._save_plots(fig)
        
    def plot_2d_hist_4(self, dat, page_title="Pixel configurations",
                        bins=None,
                        title=["Preamp","Inj","Mon","TDAC"], 
                        x_axis_title="Column",
                        y_axis_title="Row",
                        z_axis_title="",
                        z_min=[0,0,0,0], z_max=[1,1,1,15]):
        fig = Figure()
        FigureCanvas(fig)
        for i in range(4):
            ax = fig.add_subplot(221+i)
            if z_max[i]=='maximum':
                z_max[i]=np.max(dat[i])
            
            cmap = cm.get_cmap('viridis')
            cmap.set_bad('w')
            cmap.set_over('r')  # Make noisy pixels red
            im=ax.imshow(np.transpose(dat[i]),origin='lower',aspect="auto",
                     vmax=z_max[i]+1,vmin=z_min[i], interpolation='none',
                     extent=[bins[0][0],bins[0][-1],bins[1][0],bins[1][-1]],
                     cmap=cmap #, norm=norm
                     )
            ax.set_title(title[i])
            #ax.set_ylim((-0.5, ROW_SIZE-0.5))
            #ax.set_xlim((-0.5, COL_SIZE-0.5))

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.1)
            cb = fig.colorbar(im, cax=cax)
            cb.set_label(z_axis_title)
        if page_title is not None and len(page_title)>0:
            fig.suptitle(page_title, fontsize=12,color=OVERTEXT_COLOR, y=1.05)
        self._save_plots(fig)
        
    def plot_scurve(self,dat,
                   top_axis_factor=None,
                   top_axis_title="Threshold [e]",
                   x_axis_title="Test pulse injection [V]",
                   y_axis_title="# of pixel",
                   y_max=200,
                   y_min=None,
                   x_min=None,
                   x_max=None,
                   reverse=True,
                   dat_title=["TH=0.81V"],
                   page_title=None,
                   title="Pixel xx-xx"):
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_adjustable('box')
        print len(dat)
        for i, d in enumerate(dat):
            color = next(ax._get_lines.prop_cycler)['color']
            ax.plot(d["x"], d["y"],linestyle="", marker="o",color=color,label=dat_title[i])
            x,y=monopix_daq.analysis.utils.scurve_from_fit(d["x"], d["A"],d["mu"],d["sigma"],reverse=reverse,n=500)
            ax.plot(x,y,linestyle="-", marker="",color=color)
        if x_min is None:
            x_min=np.min(d["x"])
        if x_max is None:
            x_max=np.max(d["x"])
        if y_min is None:
            y_min=np.min(d["y"])
        if y_max is None:
            y_max=np.max(d["y"])
        ax.set_xbound(x_min,x_max)
        ax.set_ybound(y_min,y_max)
        
        ax.set_xlabel(x_axis_title)
        ax.set_ylabel(y_axis_title)
        
        if top_axis_factor is None:
            ax.set_title(title,color=TITLE_COLOR)
        else:
            ax2=ax.twiny()
            ax2.set_xbound(x_min*top_axis_factor,x_max*top_axis_factor)
            ax2.set_xlabel(top_axis_title)
            pad=40
            ax.set_title(title,pad=40,color=TITLE_COLOR)
        ax.legend()

        if page_title is not None and len(page_title)>0:
            self._add_title(page_title,fig)
        self._save_plots(fig)
