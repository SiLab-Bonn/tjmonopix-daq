import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors, cm
import math


def plot_scurve_hist(scurves, scan_parameter_range, repeat):
    max_occ = repeat + 200
    x_bins = scan_parameter_range
    y_bins = np.arange(-0.5, max_occ + 0.5, 1)

    param_count = scan_parameter_range.shape[0]

    hist = np.empty((param_count, max_occ), dtype=np.uint32)

    for param in range(param_count):
        
        hist[param] = np.bincount(scurves[:, param], minlength=max_occ)

    cmap = plt.get_cmap('cool')
    fig, ax = plt.subplots()
    fig.patch.set_facecolor("white")

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
        cb = fig.colorbar(im, ticks=np.linspace(start=0.0, stop=z_max, num=min(11, math.ceil(z_max) + 1), endpoint=True), fraction=0.04, pad=0.05)
    else:
        cb = fig.colorbar(im, fraction=0.04, pad=0.05)
    cb.set_label("#")

    plt.show()
