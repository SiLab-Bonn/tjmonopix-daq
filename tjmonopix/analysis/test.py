import numpy as np
import tables as tb

with tb.open_file("/home/silab/git/tjmonopix-daq/output_data/20180315_133522_threshold_scan_interpreted.h5", "r") as in_file:
    data = in_file.root.Hits[:]

pix = data[np.logical_and(data["col"] == 18, data["row"] == 99)]

timestamps, ts_counts = np.unique(pix["timestamp"], return_counts=True)

tot = (pix["te"] - pix["le"]) & 0x3F

print(np.unique(tot, return_counts=True))