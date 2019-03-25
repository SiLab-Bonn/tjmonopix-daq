import numpy as np
import matplotlib.pyplot as plt

import tables as tb
import tjmonopix.analysis.interpreter as interpreter



raw_file = "/media/data/tj-monopix_threshold_debug/debug/scurve_debug.h5"

from numpy.lib.recfunctions import append_fields

interpreter.interpret_h5(fin=raw_file, fout=raw_file[:-3] + "_hit.h5", data_format=0x8)
with tb.open_file(raw_file[:-3] + "_hit.h5", "r") as in_file:
    hits = in_file.root.Hits[:]

with tb.open_file(raw_file, "r") as in_file:
    meta_data = in_file.root.meta_data[:]

stops = meta_data['index_stop']
starts = meta_data["index_start"]
scan_param_ids = np.empty(len(hits), dtype=np.uint16())

for i in range(len(stops)):
    sel = np.logical_and(hits["timestamp"] >= starts[i], hits["timestamp"] < stops[i])
    print i, stops[i], meta_data["scan_param_id"][i]
    scan_param_ids[sel] = meta_data["scan_param_id"][i]

# Add scan_param_ids to hit_array
hits = append_fields(hits, 'scan_param_id', scan_param_ids)
# And write all to a file
with tb.open_file(raw_file[:-3] + "thresh.h5", "w") as out_file:
    description = np.zeros((1,), dtype=hits.dtype).dtype
    hit_table = out_file.create_table(
    out_file.root, name="Hits", description=description, title='hit_data')

    hit_table.append(hits)
    hit_table.flush()

hist, xedges, yedges = np.histogram2d(hits["col"], hits["row"], bins=[112, 223])
fig, ax = plt.subplots()
im = ax.imshow(hist.T, origin="lower", aspect=0.9)
plt.colorbar(im)

plt.show()