import numpy as np
from tjmonopix.analysis.interpreter import Interpreter 


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


def interpret_rx_data_scan(raw_data, meta_data):
        data_type = {'names':['col','row','le','te','scan_param_id'], 'formats':['uint8','uint16','uint8','uint8','uint16']}
        ret = np.recarray((0), dtype=data_type)
        inter=Interpreter()        
        if len(meta_data):
            param, index = np.unique(meta_data['scan_param_id'], return_index=True)
            index = index[1:]
            index = np.append(index, meta_data.shape[0])
            index = index - 1
            stops = meta_data['index_stop'][index]
            split = np.split(raw_data, stops)
            for i in range(len(split[:-1])):
                tmp=inter.mk_list(split[i])
                tmp=tmp[tmp["col"]<113]
                int_pix_data = np.recarray(len(tmp), dtype=data_type)
                int_pix_data['col']=tmp['col'] 
                int_pix_data['row']=tmp['row']
                int_pix_data['le']=tmp['le']
                int_pix_data['te']=tmp['te']
                int_pix_data['scan_param_id'][:] = param[i]
                if len(ret):
                    ret = np.hstack((ret, int_pix_data))
                else:
                    ret = int_pix_data
        return ret
