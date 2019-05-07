import numpy as np
import tables as tb
import math
import matplotlib
import logging

from matplotlib import colors, cm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable

logging.basicConfig(
    format="%(asctime)s - [%(name)-8s] - %(levelname)-7s %(message)s")
loglevel = logging.INFO

TITLE_COLOR = '#07529a'
OVERTEXT_COLOR = '#07529a'


class Plotting(object):

    def __init__(self, analyzed_data_file, pdf_file=None, save_png=False, save_single_pdf=False):
        self.logger = logging.getLogger('Plotting')
        self.logger.setLevel(loglevel)

        self.save_png = save_png
        self.save_single_pdf = save_single_pdf

        with tb.open_file(analyzed_data_file, 'r') as in_file:
            self.hits = in_file.root.Hits[:]
            self.HistOcc = in_file.root.HistOcc[:]
            self.run_config = dict()
            self.run_config['scan_id'] = in_file.root.Hits.attrs.scan_id  # TODO: Read all attributes from proper dictionary

            if self.run_config['scan_id'] in ['threshold_scan', 'global_threshold_tuning', 'local_threshold_tuning']:
                self.HistSCurve = in_file.root.HistSCurve[:]
                self.ThresholdMap = in_file.root.ThresholdMap[:, :]
                self.Chi2Map = in_file.root.Chi2Map[:, :]
                self.NoiseMap = in_file.root.NoiseMap[:]

        if pdf_file is None:
            self.filename = '.'.join(analyzed_data_file.split('.')[:-1]) + '.pdf'
        else:
            self.filename = pdf_file
        self.out_file = PdfPages(self.filename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.out_file is not None and isinstance(self.out_file, PdfPages):
            self.logger.info('Closing output PDF file: %s',
                             str(self.out_file._file.fh.name))
            self.out_file.close()

    def create_standard_plots(self):
        self.create_occupancy_map()

    def create_occupancy_map(self):
        try:
            if self.run_config['scan_id'] in ['threshold_scan', 'threshold_tuning']:
                title = 'Integrated occupancy'
            else:
                title = 'Occupancy'

            self._plot_occupancy(hist=self.HistOcc[:].T, suffix='occupancy', title=title, z_max=np.ceil(1.1 * np.amax(self.HistOcc[:])))  # TODO: get mask and enable here
        except Exception:
            self.logger.error('Could not create occupancy map!')

    def create_threshold_map(self):
        try:
            mask = np.full((112, 224), False)
            sel = self.Chi2Map[:] > 0.  # Mask not converged fits (chi2 = 0)
            mask[~sel] = True

            self._plot_occupancy(hist=np.ma.masked_array(self.ThresholdMap, mask).T,
                                 electron_axis=False,
                                 z_label='Threshold',
                                 title='Threshold',
                                 show_sum=False,
                                 suffix='threshold_map')
        except Exception:
            self.logger.error('Could not create threshold map!')

    def create_scurves_plot(self, scan_parameter_name='Scan parameter'):
        try:
            if self.run_config['scan_id'] == 'threshold_scan':
                scan_parameter_name = '$\Delta$ DU'
                electron_axis = False

            self._plot_scurves(scurves=self.HistSCurve[:, 112:220, :],
                               scan_parameters=np.arange(0, self.HistSCurve[:, 112:220, :].shape[2], 1),
                               electron_axis=electron_axis,
                               scan_parameter_name=scan_parameter_name,
                               title="S-Curves removed deep p-well")

            self._plot_scurves(scurves=self.HistSCurve[:, :112, :],
                               scan_parameters=np.arange(0, self.HistSCurve[:, 112:220, :].shape[2], 1),
                               electron_axis=electron_axis,
                               scan_parameter_name=scan_parameter_name,
                               title='S-Curves full deep p-well')
        except Exception:
            self.logger.error('Could not create scurve plot!')

    def create_threshold_distribution_plot(self):
        mask = np.full((112, 224), False)
        sel = np.logical_and(self.Chi2Map[:] > 0., self.ThresholdMap > 0)  # Mask not converged fits (chi2 = 0)
        mask[~sel] = True

        data = np.ma.masked_array(self.ThresholdMap, mask)
        data_rdpw = data[:, 112:220].reshape(-1)
        data_fdpw = data[:, :112].reshape(-1)

        hist_rdpw, edges_rdpw = np.histogram(
            data_rdpw,
            bins=np.arange(np.floor(np.mean(data_rdpw) - 3 * np.std(data_rdpw)) - .5, np.ceil(np.mean(data_rdpw) + 3 * np.std(data_rdpw)) + .5, 1),
            range=(np.mean(data_rdpw) - 3 * np.std(data_rdpw), np.mean(data_rdpw) + 3 * np.std(data_rdpw))
        )
        self._plot_histogram1d(hist=hist_rdpw,
                               edges=edges_rdpw,
                               title="Threshold distribution removed deep p-well",
                               suffix='threshold_distribution')

        hist_fdpw, edges_fdpw = np.histogram(
            data_fdpw,
            bins=np.arange(np.floor(np.mean(data_fdpw) - 3 * np.std(data_fdpw)) - .5, np.ceil(np.mean(data_fdpw) + 3 * np.std(data_fdpw)) + .5, 1),
            range=(np.mean(data_fdpw) - 3 * np.std(data_fdpw), np.mean(data_fdpw) + 3 * np.std(data_fdpw))
        )
        self._plot_histogram1d(hist=hist_fdpw,
                               edges=edges_fdpw,
                               title="Threshold distribution full deep p-well",
                               suffix='threshold_distribution')

    def _plot_histogram1d(self, hist, edges, title='Distribution', suffix=None):
        # TODO: histogram data

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_title(title + ' for %d pixel(s)' % (np.sum(hist)), color=TITLE_COLOR)

        ax.bar(edges[:-1], hist, align="edge", width=((edges[-1] - edges[0]) / (len(edges) - 1)))

        self._save_plots(fig, suffix=suffix)

    def _plot_histogram2d(self, hist, z_min=None, z_max=None, suffix=None, xlabel='', ylabel='', title='', z_label='# of hits'):
        x_bins = np.arange(-0.5, hist.shape[0] - 0.5)
        y_bins = np.arange(-0.5, hist.shape[1] - 0.5)

        if z_max == 'median':
            z_max = 2 * np.ma.median(hist)
        elif z_max == 'maximum' or z_max is None:
            z_max = np.ma.max(hist)
        if z_max < 1 or hist.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist)
        if z_min == z_max or hist.all() is np.ma.masked:
            z_min = 0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        fig.patch.set_facecolor('white')
        cmap = cm.get_cmap('cool')
        if np.allclose(hist, 0.0) or hist.max() <= 1:
            z_max = 1.0
        else:
            z_max = hist.max()
        # for small z use linear scale, otherwise log scale
        if z_max <= 10.0:
            bounds = np.linspace(start=0.0, stop=z_max, num=255, endpoint=True)
            norm = colors.BoundaryNorm(bounds, cmap.N)
        else:
            bounds = np.linspace(start=1.0, stop=z_max, num=255, endpoint=True)
            norm = colors.LogNorm()

        im = ax.pcolormesh(x_bins, y_bins, hist.T, norm=norm, rasterized=True)
        ax.set_title(title, color=TITLE_COLOR)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        if z_max <= 10.0:
            cb = fig.colorbar(im, ticks=np.linspace(start=0.0, stop=z_max, num=min(
                11, math.ceil(z_max) + 1), endpoint=True), fraction=0.04, pad=0.05)
        else:
            cb = fig.colorbar(im, fraction=0.04, pad=0.05)
        cb.set_label(z_label)

        self._save_plots(fig, suffix=suffix)

    def _plot_occupancy(self, hist, electron_axis=False, title='Occupancy', z_label='# of hits', z_min=None, z_max=None, show_sum=True, suffix=None):
        if z_max == 'median':
            z_max = 2 * np.ma.median(hist)
        elif z_max == 'maximum' or z_max is None:
            z_max = np.ma.max(hist)
        if z_max < 1 or hist.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist)
        if z_min == z_max or hist.all() is np.ma.masked:
            z_min = 0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        ax.set_adjustable('box')
        bounds = np.linspace(start=z_min, stop=z_max, num=255, endpoint=True)
        cmap = cm.get_cmap('plasma')
        cmap.set_bad('w', 1.0)
        norm = colors.BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(hist, interpolation='none', aspect=0.9, cmap=cmap,
                       norm=norm)  # TODO: use pcolor or pcolormesh
        ax.set_ylim((0, 224))
        ax.set_xlim((0, 112))
        ax.set_title(title + r' ($\Sigma$ = {0})'.format(
            (0 if hist.all() is np.ma.masked else np.ma.sum(hist))), color=TITLE_COLOR)
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')

        divider = make_axes_locatable(ax)
        if electron_axis:
            pad = 1.0
        else:
            pad = 1.0
        cax = divider.append_axes("right", size="5%", pad=pad)
        cb = fig.colorbar(im, cax=cax, ticks=np.linspace(
            start=z_min, stop=z_max, num=10, endpoint=True), orientation='vertical')
        cax.set_xticklabels([int(round(float(x.get_text())))
                             for x in cax.xaxis.get_majorticklabels()])
        cb.set_label(z_label)

        if electron_axis:
            fig.canvas.draw()
            ax2 = cb.ax.twiny()

            pos = ax2.get_position()
            pos.y1 = 0.14
            ax2.set_position(pos)

            for spine in ax2.spines.values():
                spine.set_visible(False)

            xticks = [int(round(self._convert_to_e(float(x.get_text()))))
                      for x in cax.xaxis.get_majorticklabels()]
            ax2.set_xticklabels(xticks)

            lim = cax.get_xlim()
            lim_2 = ax2.get_xlim()

            def f(x):
                return lim_2[0] + (x - lim[0]) / \
                    (lim[1] - lim[0]) * (lim_2[1] - lim_2[0])

            ticks = f(cax.get_xticks())
            ax2.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))

            ax2.set_xlabel('%s [Electrons]' % (z_label), labelpad=7)
            cb.set_label(r'%s [$\Delta$ VCAL]' % z_label)

        self._save_plots(fig, suffix=suffix)

    def _plot_scurves(self, scurves, scan_parameters, electron_axis=False, max_occ=130, scan_parameter_name=None, title='S-curves', ylabel='Occupancy'):
        # TODO: get n_pixels and start and stop columns from run_config
        # start_column = self.run_config['start_column']
        # stop_column = self.run_config['stop_column']
        # start_row = self.run_config['start_row']
        # stop_row = self.run_config['stop_row']
        x_bins = np.arange(-0.5, max(scan_parameters) + 1.5)
        y_bins = np.arange(-0.5, max_occ + 0.5)

        param_count = scurves.shape[2]
        hist = np.empty([param_count, max_occ], dtype=np.uint32)

        # Reformat scurves array as one long list of scurves
        # For very noisy or not properly masked devices, ignore all s-curves where any data
        # is larger than given threshold (max_occ)
        scurves = scurves.reshape((scurves.shape[0] * scurves.shape[1], scurves.shape[2]))

        scurves_masked = scurves[~np.any(scurves >= max_occ, axis=1)]
        n_pixel = scurves_masked.shape[0]

        for param in range(param_count):
            hist[param] = np.bincount(scurves_masked[:, param], minlength=max_occ)[:max_occ]

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        fig.patch.set_facecolor('white')
        cmap = cm.get_cmap('cool')
        if np.allclose(hist, 0.0) or hist.max() <= 1:
            z_max = 1.0
        else:
            z_max = hist.max()
        # for small z use linear scale, otherwise log scale
        if z_max <= 10.0:
            bounds = np.linspace(start=0.0, stop=z_max, num=255, endpoint=True)
            norm = colors.BoundaryNorm(bounds, cmap.N)
        else:
            bounds = np.linspace(start=1.0, stop=z_max, num=255, endpoint=True)
            norm = colors.LogNorm()

        im = ax.pcolormesh(x_bins, y_bins, hist.T, norm=norm, rasterized=True)

        if z_max <= 10.0:
            cb = fig.colorbar(im, ticks=np.linspace(start=0.0, stop=z_max, num=min(
                11, math.ceil(z_max) + 1), endpoint=True), fraction=0.04, pad=0.05)
        else:
            cb = fig.colorbar(im, fraction=0.04, pad=0.05)
        cb.set_label("# of pixels")
        ax.set_title(title + ' for %d pixel(s)' % (n_pixel), color=TITLE_COLOR)
        if scan_parameter_name is None:
            ax.set_xlabel('Scan parameter')
        else:
            ax.set_xlabel(scan_parameter_name)
        ax.set_ylabel(ylabel)

        if electron_axis:
            self._add_electron_axis(fig, ax)

#         if self.qualitative:
#             ax.xaxis.set_major_formatter(plt.NullFormatter())
#             ax.xaxis.set_minor_formatter(plt.NullFormatter())
#             ax.yaxis.set_major_formatter(plt.NullFormatter())
#             ax.yaxis.set_minor_formatter(plt.NullFormatter())
#             cb.formatter = plt.NullFormatter()
#             cb.update_ticks()

        self._save_plots(fig, suffix='scurves')

    def _save_plots(self, fig, suffix=None, tight=False):
        increase_count = False
        bbox_inches = 'tight' if tight else ''
        if suffix is None:
            suffix = str(self.plot_cnt)

        if not self.out_file:
            fig.show()
        else:
            self.out_file.savefig(fig, bbox_inches=bbox_inches)
        if self.save_png:
            fig.savefig(self.filename[:-4] + '_' + suffix + '.png', bbox_inches=bbox_inches)
            increase_count = True
        if self.save_single_pdf:
            fig.savefig(self.filename[:-4] + '_' + suffix + '.pdf', bbox_inches=bbox_inches)
            increase_count = True
        if increase_count:
            self.plot_cnt += 1
