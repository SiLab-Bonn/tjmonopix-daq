import tables as tb
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors, cm
from numba import njit
from scipy.optimize import curve_fit
from tqdm import tqdm

from tjmonopix.analysis import analysis_utils as au


@njit
def tot_hist4d(hits, scan_param_range):
    """
    Returns a histogram of TOT values for every pixel and injection step
    """
    hist_tot = np.zeros(shape=(112, 224, len(scan_param_range), 64), dtype=np.uint16)

    for hit in hits:
        col = hit["col"]
        row = hit["row"]
        param = hit["scan_param_id"]
        tot = hit["tot"]
#         if col >= 0 and col < hist_tot.shape[0] and row >= 0 and row < hist_tot.shape[1] and param < hist_tot.shape[2] and tot < hist_tot.shape[3]:
        if col >= 0 and col < hist_tot.shape[0] and row >= 0 and row < 112 and param < hist_tot.shape[2] and tot < hist_tot.shape[3]:
            hist_tot[col, row, param, tot] += 1

    return hist_tot


@njit
def tot_hist2d(hits, scan_param_range):
    """
    Returns a histogram of TOT values for every injection step
    """
    hist_tot = np.zeros(shape=(len(scan_param_range), 64), dtype=np.uint32)

    for hit in hits:
        param = hit["scan_param_id"]
        tot = hit["tot"]
        row = hit["row"]
        if row < 112 and param < hist_tot.shape[0] and tot < hist_tot.shape[1]:
            hist_tot[param, tot] += 1

    return hist_tot


def calibrate_tot_vs_inj(tot_mean, tot_err):
    slope = np.zeros(shape=112 * 224, dtype=np.float)
    offset = np.zeros(shape=112 * 224, dtype=np.float)

    tot_mean_lin = tot_mean.reshape(112 * 224, 65)
    tot_err_lin = tot_err.reshape(112 * 224, 65)

    pbar = tqdm(total=len(tot_mean_lin))
    i = 0
    while i < len(tot_mean_lin):
        res = au.fit_line(tot_mean_lin[i, 20:50], tot_err_lin[i, 20:50], np.arange(20, 50, 1))
        slope[i] = res[0]
        offset[i] = res[1]
        i += 1
        pbar.update()
    pbar.close()

    return slope.reshape(112, 224), offset.reshape(112, 224)


if __name__ == "__main__":
    with tb.open_file("/media/silab/Maxtor/tjmonopix-data/measurements/threshold_scan/modified_process/pmos/W04R08_-6_-6_idb30_interpreted.h5", "r") as in_file:
        hits = in_file.root.Hits[:]

    inj_steps = np.unique(hits["scan_param_id"])

    # Histogram ToT values for each pixel and injection step
    hist = tot_hist4d(hits, inj_steps)
    print hist.shape

#     # Calculate mean Tot and std for each pixel and injection step
#     bin_positions = np.zeros_like(hist, dtype=np.uint16)
#     bin_positions[:, :, :, :] = np.arange(0, 64, 1)
    tot_mean = au.get_mean_from_histogram(hist, np.arange(0, 64, 1), axis=3)
    flattened = np.reshape(tot_mean, (112 * 224, 65))
    print flattened[:, 20]

    tot_hist = np.empty([65, 64])
    sigma = np.zeros(65)
    for param in range(65):
            hh, _ = np.histogram(flattened[:, param], bins=np.arange(-0.5, 64.5, 1))
            tot_hist[param] = hh
            if param > 22:
                sigma[param] = au.get_std_from_histogram(hh, bin_positions=np.arange(0, 64), axis=0)
#     tot_err = au.get_std_from_histogram(hist, bin_positions, axis=3)

    # # just for debug purposes
    # tot_fit = tot_mean[22, 150, 20:50]
    # tot_err_fit = tot_err[22, 150, 20:50]
    # x = np.arange(20, 50, 1)
    #
    # y = tot_fit[~np.isnan(tot_fit)]
    # y_err = tot_err_fit[~np.isnan(tot_fit)]
    # x_sel = x[~np.isnan(tot_fit)]
    #
    # p0 = [(y[-1] - y[0]) / (x[-1] - x[0]),
    #       np.mean(y - (y[-1] - y[0]) / (x[-1] - x[0]) * x)]
    #
    #
    # def line(x, m, b):
    #     return m * x + b
    #
    #
    # popt = curve_fit(f=line, xdata=x_sel, ydata=y, p0=p0, sigma=y_err,
    #                  absolute_sigma=True)[0]

#     plt.title("Pixel (col/row): {}/{}".format(22, 45))
#     plt.ylabel("ToT")
#     plt.xlabel("Injection DU")
#     plt.errorbar(x=np.arange(1, 65, 1), y=tot_mean[25, 45, 1:], yerr=tot_err[25, 45, 1:], fmt='.')
#     # plt.errorbar(x=x_sel, y=y, yerr=y_err, fmt='.', label="Fit data points")
#
#     slope, offset = calibrate_tot_vs_inj(tot_mean, tot_err)
#     plt.plot(np.arange(0, 65, 3), line(np.arange(0, 65, 3), slope[25, 45], offset[25, 45]), '-', label="Fit result")
#     plt.legend(loc=0)
#
#     # print('From single fit: m={} b={}'.format(popt[0], popt[1]))
#     print('From all fits: m={} b={}'.format(slope[25, 45], offset[25, 45]))
#     print(np.median(slope), np.median(offset))

    print flattened.shape

    fig, ax = plt.subplots()

    x_bins = np.arange(-0.5, max(inj_steps) + 1.5)
    y_bins = np.arange(-0.5, 64.5, 1)

#     tot_hist = tot_hist2d(hits, inj_steps)
    tot_hist = np.ma.masked_where(tot_hist < 5, tot_hist)

    cmap = cm.get_cmap('cool')
    bounds = np.linspace(start=0.0, stop=np.amax(tot_hist), num=255, endpoint=True)
    norm = colors.BoundaryNorm(bounds, cmap.N)

    im = ax.pcolormesh(x_bins, y_bins, tot_hist.T, norm=norm, rasterized=True)
    cb = fig.colorbar(im, fraction=0.04, pad=0.05)

    ax.set_title("W4 PMOS -6 V/-6 V IDB30 full DPW")
    ax.set_xlabel("Injected charge / DU")
    ax.set_ylabel("Mean measured charge / TOT")

    print sigma
    print np.mean(sigma[sigma != 0])

    plt.show()

    fig, ax = plt.subplots()
    ax.plot(inj_steps[sigma != 0], sigma[sigma != 0], '.')
    ax.set_title("W4 PMOS -6 V/-6 V IDB30 full DPW")
    ax.set_xlabel("Injected charge / DU")
    ax.set_ylabel("ToT dispersion ($\sigma$)")
    ax.set_xlim(0, 65)

    plt.show()
