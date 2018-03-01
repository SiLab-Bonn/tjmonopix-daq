import numpy as np

def interpret_data(raw_data):
    hit_data_sel = ((raw_data & 0xf0000000) == 0)
    hit_data = raw_data[hit_data_sel]
    hit_dtype = np.dtype([("col","<u1"),("row","<u2"),("le","<u1"),("te","<u1"),("noise","<u1")])
    ret = np.empty(hit_data.shape[0], dtype = hit_dtype)

    ret['col'] = 2 * (hit_data & 0x3f) + (((hit_data & 0x7FC0) >> 6) // 256)
    ret['row'] = ((hit_data & 0x7FC0) >> 6) % 256
    ret['te'] = (hit_data & 0x1F8000) >> 15
    ret['le'] = (hit_data & 0x7E00000) >> 21
    ret['noise'] = (hit_data & 0x8000000) >> 27

    return ret
