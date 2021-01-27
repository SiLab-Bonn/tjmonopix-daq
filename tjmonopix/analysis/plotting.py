import numpy as np
import tables as tb
import math
import matplotlib
import logging

from scipy.optimize import curve_fit
from matplotlib import colors, cm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable

logging.basicConfig(format="%(asctime)s - [%(name)-8s] - %(levelname)-7s %(message)s")
loglevel = logging.INFO

TITLE_COLOR = '#07529a'
OVERTEXT_COLOR = '#07529a'


class Plotting(object):

    def __init__(self, analyzed_data_file,  due=21, pdf_file=None, save_png=False, save_single_pdf=False):
        self.logger = logging.getLogger('Plotting')
        self.logger.setLevel(loglevel)

        self.save_png = save_png
        self.save_single_pdf = save_single_pdf
        self.clustered = False

        self.calibration = {'e_conversion_slope': due, 'e_conversion_offset': 0, 'e_conversion_slope_error': 0, 'e_conversion_offset_error': 0}
        self.qualitative = False

        if pdf_file is None:
            self.filename = '.'.join(analyzed_data_file.split('.')[:-1]) + '.pdf'
        else:
            self.filename = pdf_file
        self.out_file = PdfPages(self.filename)

        with tb.open_file(analyzed_data_file, 'r') as in_file:
            self.HistOcc = in_file.root.HistOcc[:]
            self.run_config = dict()
            self.run_config['scan_id'] = in_file.root.Dut.attrs.scan_id  # TODO: Read all attributes from proper dictionary

            if self.run_config['scan_id'] in ['threshold_scan', 'global_threshold_tuning', 'local_threshold_tuning']:
                self.HistSCurve = in_file.root.HistSCurve[:]
                self.ThresholdMap = in_file.root.ThresholdMap[:, :]
                self.Chi2Map = in_file.root.Chi2Map[:, :]
                self.NoiseMap = in_file.root.NoiseMap[:]
                # self.n_failed_scurves = self.n_enabled_pixels - len(self.ThresholdMap[self.ThresholdMap != 0])

            try:
                self.Cluster = in_file.root.Cluster[:]
                self.HistClusterSize = in_file.root.HistClusterSize[:]
                self.HistClusterShape = in_file.root.HistClusterShape[:]
                self.HistClusterTot = in_file.root.HistClusterTot[:]
                self.clustered = True
            except tb.NoSuchNodeError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.out_file is not None and isinstance(self.out_file, PdfPages):
            self.logger.info('Closing output PDF file: %s',
                             str(self.out_file._file.fh.name))
            self.out_file.close()

    def create_standard_plots(self):
        self.create_occupancy_map()

        if self.clustered:
            self.create_cluster_tot_plot()
            self.create_cluster_shape_plot()
            self.create_cluster_size_plot()

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
                                 electron_axis=True,
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

            self._plot_scurves(scurves=self.HistSCurve[:, 112:224, :],
                               scan_parameters=np.arange(0, self.HistSCurve[:, 112:224, :].shape[2], 1),
                               electron_axis=electron_axis,
                               scan_parameter_name=scan_parameter_name,
                               title="S-Curves removed deep p-well")

            self._plot_scurves(scurves=self.HistSCurve[:, :112, :],
                               scan_parameters=np.arange(0, self.HistSCurve[:, :112, :].shape[2], 1),
                               electron_axis=electron_axis,
                               scan_parameter_name=scan_parameter_name,
                               title='S-Curves full deep p-well')
        except Exception:
            self.logger.error('Could not create scurve plot!')

    def create_threshold_plot(self, logscale=False, scan_parameter_name='Scan parameter'):
        try:
            title = 'Threshold distribution'
            if self.run_config['scan_id'] in ['threshold_scan', 'in_time_threshold_scan', 'crosstalk_scan']:
                # plot_range = [v - self.run_config['VCAL_MED'] for v in range(self.run_config['VCAL_HIGH_start'],
                #                                                              self.run_config['VCAL_HIGH_stop'] + 1,
                #                                                              self.run_config['VCAL_HIGH_step'])]
                plot_range = np.arange(0.5, 80.5, 1)  # TODO: Get from scan
                scan_parameter_name = '$\Delta$ DU'
                electron_axis = True
            # elif self.run_config['scan_id'] == 'fast_threshold_scan':
            #     plot_range = np.array(self.scan_params[:]['vcal_high'] - self.scan_params[:]['vcal_med'], dtype=np.float)
            #     scan_parameter_name = '$\Delta$ DU'
            #     electron_axis = True
            # elif self.run_config['scan_id'] == 'global_threshold_tuning':
            #     plot_range = range(self.run_config['VTH_stop'],
            #                        self.run_config['VTH_start'],
            #                        self.run_config['VTH_step'])
            #     scan_parameter_name = self.run_config['VTH_name']
            #     electron_axis = False
            # elif self.run_config['scan_id'] == 'injection_delay_scan':
            #     scan_parameter_name = 'Finedelay [LSB]'
            #     electron_axis = False
            #     plot_range = range(0, 16)
            #     title = 'Fine delay distribution for enabled pixels'

            mask = np.full((112, 224), False)
            sel = np.logical_and(self.Chi2Map > 0., self.ThresholdMap > 0)  # Mask not converged fits (chi2 = 0)
            mask[~sel] = True

            data = np.ma.masked_array(self.ThresholdMap, mask)
            data_rdpw = data[:, 112:220]
            data_fdpw = data[:, :112]

            self._plot_distribution(data_fdpw.T,
                                    plot_range=plot_range,
                                    electron_axis=electron_axis,
                                    x_axis_title=scan_parameter_name,
                                    title="Threshold distribution (full deep p-well)",
                                    log_y=logscale,
                                    print_failed_fits=False,
                                    suffix='threshold_distribution')

            self._plot_distribution(data_rdpw.T,
                                    plot_range=plot_range,
                                    electron_axis=electron_axis,
                                    x_axis_title=scan_parameter_name,
                                    title="Threshold distribution (removed deep p-well)",
                                    log_y=logscale,
                                    print_failed_fits=False,
                                    suffix='threshold_distribution')
        except Exception as e:
            self.logger.error('Could not create threshold plot! ({0})'.format(e))



    def create_cluster_size_plot(self):
        try:
            self._plot_cl_size(self.HistClusterSize)
        except Exception:
            self.logger.error('Could not create cluster size plot!')

    def create_cluster_tot_plot(self):
        try:
            self._plot_cl_tot(self.HistClusterTot)
        except Exception:
            self.logger.error('Could not create cluster TOT plot!')

    def create_cluster_shape_plot(self):
        try:
            self._plot_cl_shape(self.HistClusterShape)
        except Exception:
            self.logger.error('Could not create cluster shape plot!')

    def _plot_cl_size(self, hist):
        ''' Create 1D cluster size plot w/wo log y-scale '''
        self._plot_1d_hist(hist=hist, title='Cluster size',
                           log_y=False, plot_range=range(0, 10),
                           x_label='Cluster size',
                           y_label='# of clusters', suffix='cluster_size')
        self._plot_1d_hist(hist=hist, title='Cluster size (log)',
                           log_y=True, plot_range=range(0, 100),
                           x_label='Cluster size',
                           y_label='# of clusters', suffix='cluster_size_log')

    def _plot_cl_tot(self, hist):
        ''' Create 1D cluster size plot w/wo log y-scale '''
        self._plot_1d_hist(hist=hist, title='Cluster ToT',
                           log_y=False, plot_range=range(0, 64),
                           x_label='Cluster ToT [25 ns]',
                           y_label='# of clusters', suffix='cluster_tot')

    def _plot_cl_shape(self, hist):
        ''' Create a histogram with selected cluster shapes '''
        x = np.arange(12)
        fig = Figure()
        _ = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        selected_clusters = hist[[1, 3, 5, 6, 9, 13, 14, 7, 11, 19, 261, 15]]
        ax.bar(x, selected_clusters, align='center')
        ax.xaxis.set_ticks(x)
        fig.subplots_adjust(bottom=0.2)
        ax.set_xticklabels([u"\u2004\u2596",
                            # 2 hit cluster, horizontal
                            u"\u2597\u2009\u2596",
                            # 2 hit cluster, vertical
                            u"\u2004\u2596\n\u2004\u2598",
                            u"\u259e",  # 2 hit cluster
                            u"\u259a",  # 2 hit cluster
                            u"\u2599",  # 3 hit cluster, L
                            u"\u259f",  # 3 hit cluster
                            u"\u259b",  # 3 hit cluster
                            u"\u259c",  # 3 hit cluster
                            # 3 hit cluster, horizontal
                            u"\u2004\u2596\u2596\u2596",
                            # 3 hit cluster, vertical
                            u"\u2004\u2596\n\u2004\u2596\n\u2004\u2596",
                            # 4 hit cluster
                            u"\u2597\u2009\u2596\n\u259d\u2009\u2598"])
        ax.set_title('Cluster shapes', color=TITLE_COLOR)
        ax.set_xlabel('Cluster shape')
        ax.set_ylabel('# of clusters')
        ax.grid(True)
        ax.set_yscale('log')
        ax.set_ylim(ymin=1e-1)

        self._save_plots(fig, suffix='cluster_shape')

    def _plot_1d_hist(self, hist, yerr=None, plot_range=None, x_label=None, y_label=None, title=None, x_ticks=None, color='C0', log_y=False, suffix=None):
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        hist = np.array(hist)
        if plot_range is None:
            plot_range = range(0, len(hist))
        plot_range = np.array(plot_range)
        plot_range = plot_range[plot_range < len(hist)]
        if yerr is not None:
            ax.bar(x=plot_range, height=hist[plot_range],
                   color=color, align='center', yerr=yerr)
        else:
            ax.bar(x=plot_range,
                   height=hist[plot_range], color=color, align='center')
        ax.set_xlim((min(plot_range) - 0.5, max(plot_range) + 0.5))

        ax.set_title(title, color=TITLE_COLOR)
        if x_label is not None:
            ax.set_xlabel(x_label)
        if y_label is not None:
            ax.set_ylabel(y_label)
        if x_ticks is not None:
            ax.set_xticks(plot_range)
            ax.set_xticklabels(x_ticks)
            ax.tick_params(which='both', labelsize=8)
        if np.allclose(hist, 0.0):
            ax.set_ylim((0, 1))
        else:
            if log_y:
                ax.set_yscale('log')
                ax.set_ylim((1e-1, np.amax(hist) * 2))
        ax.grid(True)

        self._save_plots(fig, suffix=suffix)

    def _plot_distribution(self, data, plot_range=None, x_axis_title=None, electron_axis=False, use_electron_offset=False, y_axis_title='# of hits', log_y=False, align='edge', title=None, print_failed_fits=False, suffix=None):
        if plot_range is None:
            diff = np.amax(data) - np.amin(data)
            if (np.amax(data)) > np.median(data) * 5:
                plot_range = np.arange(np.amin(data), np.median(data) * 2, np.median(data) / 100.)
            else:
                plot_range = np.arange(np.amin(data), np.amax(data) + diff / 100., diff / 100.)
        tick_size = np.diff(plot_range)[0]

        hist, bins = np.histogram(np.ravel(data), bins=plot_range)

        bin_centres = (bins[:-1] + bins[1:]) / 2
        p0 = (np.amax(hist), np.nanmean(bins),
              (max(plot_range) - min(plot_range)) / 3)

        try:
            coeff, _ = curve_fit(self._gauss, bin_centres, hist, p0=p0)
        except Exception as e:
            coeff = None
            self.logger.warning('Gauss fit failed!')
            self.logger.error(e)

        if coeff is not None:
            points = np.linspace(min(plot_range), max(plot_range), 500)
            gau = self._gauss(points, *coeff)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        # self._add_text(fig)

        ax.bar(bins[:-1], hist, width=tick_size, align=align)
        if coeff is not None:
            ax.plot(points, gau, "r-", label='Normal distribution')

        if log_y:
            if title is not None:
                title += ' (logscale)'
            ax.set_yscale('log')

        ax.set_xlim(min(plot_range), max(plot_range))
        ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)

        if not self.qualitative:
            mean = np.nanmean(data)
            rms = np.nanstd(data)
            if np.nanmean(data) < 10:
                if electron_axis:
                    textright = '$\mu={0:1.1f}\;\Delta$DU\n$\;\;\,=({1[0]:1.0f}) \; e^-$\n\n$\sigma={2:1.1f}\;\Delta$DU\n$\;\;\,=({3[0]:1.0f}) \; e^-$'.format(
                        mean, self._convert_to_e(mean, use_offset=use_electron_offset), rms, self._convert_to_e(rms, use_offset=False))
                else:
                    textright = '$\mu={0:1.1f}\;\Delta$DU\n$\sigma={1:1.1f}\;\Delta$DU'.format(mean, rms)
            else:
                if electron_axis:
                    textright = '$\mu={0:1.0f}\;\Delta$DU\n$\;\;\,=({1[0]:1.0f}) \; e^-$\n\n$\sigma={2:0.1f}\;\Delta$DU\n$\;\;\,=({3[0]:1.0f}) \; e^-$'.format(
                        mean, self._convert_to_e(mean, use_offset=use_electron_offset), rms, self._convert_to_e(rms, use_offset=False))
                else:
                    textright = '$\mu={0:1.0f}\;\Delta$DU\n$\sigma={1:1.0f}\;\Delta$DU'.format(mean, rms)

            # Fit results
            if coeff is not None:
                textright += '\n\nFit results:\n'
                if coeff[1] < 10:
                    if electron_axis:
                        textright += '$\mu={0:1.1f}\;\Delta$DU\n$\;\;\,=({1[0]:1.0f}) \; e^-$\n\n$\sigma={2:1.1f}\;\Delta$DU\n$\;\;\,=({3[0]:1.0f}) \; e^-$'.format(
                            abs(coeff[1]), self._convert_to_e(abs(coeff[1]), use_offset=use_electron_offset), abs(coeff[2]), self._convert_to_e(abs(coeff[2]), use_offset=False))
                    else:
                        textright += '$\mu={0:1.1f}\;\Delta$DU\n$\sigma={1:1.1f}\;\Delta$VCAL'.format(abs(coeff[1]), abs(coeff[2]))
                else:
                    if electron_axis:
                        textright += '$\mu={0:1.0f}\;\Delta$DU\n$\;\;\,=({1[0]:1.0f}) \; e^-$\n\n$\sigma={2:0.1f}\;\Delta$DU\n$\;\;\,=({3[0]:1.0f}) \; e^-$'.format(
                            abs(coeff[1]), self._convert_to_e(abs(coeff[1]), use_offset=use_electron_offset), abs(coeff[2]), self._convert_to_e(abs(coeff[2]), use_offset=False))
                    else:
                        textright += '$\mu={0:1.0f}\;\Delta$DU\n$\sigma={1:1.0f}\;\Delta$DU'.format(abs(coeff[1]), abs(coeff[2]))
                if print_failed_fits:
                    textright += '\n\nFailed fits: {0}'.format(self.n_failed_scurves)

            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.78, 0.95, textright, transform=ax.transAxes, fontsize=8, verticalalignment='top', bbox=props)

        if electron_axis:
            self._add_electron_axis(fig, ax, use_electron_offset=use_electron_offset)

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())

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

    def _convert_to_e(self, dac, use_offset=False):
        if use_offset:
            e = dac * self.calibration['e_conversion_slope'] + self.calibration['e_conversion_offset']
            de = math.sqrt((dac * self.calibration['e_conversion_slope_error'])**2 + self.calibration['e_conversion_offset_error']**2)
        else:
            e = dac * self.calibration['e_conversion_slope']
            de = dac * self.calibration['e_conversion_slope_error']
        return e, de

    def _add_electron_axis(self, fig, ax, use_electron_offset=True):
        fig.subplots_adjust(top=0.75)
        ax.title.set_position([.5, 1.15])

        fig.canvas.draw()
        ax2 = ax.twiny()

        xticks = []
        for t in ax.get_xticks(minor=False):
            xticks.append(int(self._convert_to_e(float(t), use_offset=use_electron_offset)[0]))

        ax2.set_xticklabels(xticks)

        l1 = ax.get_xlim()
        l2 = ax2.get_xlim()

        def f(x):
            return l2[0] + (x - l1[0]) / (l1[1] - l1[0]) * (l2[1] - l2[0])

        ticks = f(ax.get_xticks())
        ax2.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
        ax2.set_xlabel('Electrons', labelpad=7)

        return ax2

    def _gauss(self, x, *p):
        amplitude, mu, sigma = p
        return amplitude * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))

    def _double_gauss(self, x, a1, a2, m1, m2, sd1, sd2):
        return self._gauss(x, a1, m1, sd1) + self._gauss(x, a2, m2, sd2)

    def _lin(self, x, *p):
        m, b = p
        return m * x + b
