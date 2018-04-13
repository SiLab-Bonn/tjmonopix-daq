import numpy as np
import matplotlib.pyplot as plt
import tables as tb

def load_data(filename):
    with tb.open_file(filename, "r") as in_file:
        data = in_file.root.Hits[:]

    return data

def fit_spectrum(tot_data):
    from scipy.optimize import curve_fit

    def gauss(x, a, mu, sigma):
        return a * np.exp(- (x - mu) * (x - mu) / (2 * sigma * sigma))


    hist, edges = np.histogram(tot_data, bins=np.arange(-0.5, 63.5, 1))
    mids = edges[:-1] + 0.5

    popt, pcov = curve_fit(gauss, mids[-30:], hist[-30:], p0=(np.amax(hist), mids[hist == np.amax(hist)], 1))

    plt.bar(edges[:-1], hist, align="edge", width=1)
    plt.plot(np.arange(0, 64, 0.01), gauss(np.arange(0, 64, 0.01), np.amax(hist), mids[hist == np.amax(hist)], 1), 'C1-', label="Guess")
    plt.plot(np.arange(0, 64, 0.01), gauss(np.arange(0, 64, 0.01), *popt), 'C2-', label="Fit")
    plt.plot((mids[-30], mids[-30]), (0, 2000), 'C3-', label="Lower fit limit")
    plt.legend(loc=0)
    plt.show()


if __name__ == "__main__":
    data = load_data("/home/silab/git/tjmonopix-daq/fe_calibration_interpreted.h5")

    pix_data = data[data["col"] == 15]
    pix_data = data[data["row"] == 101]

    tot = (pix_data["te"] - pix_data["le"]) & 0x3F

    # plt.hist(tot, bins=np.arange(-0.5, 63.5, 1))
    # plt.show()

    fit_spectrum(tot)