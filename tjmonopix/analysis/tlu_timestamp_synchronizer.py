import sys,time,os
import numpy as np
import matplotlib.pyplot as plt
from numba import njit
import tables
import yaml


data_out_type=[("tlu_id","i2"),("tlu_timestamp","u8"),("ts_timestamp","u8")]
hits_type=[('col', 'u1'), ('row', '<u2'), ('le', 'u1'), ('te', 'u1'), ('cnt', '<u4'), ('timestamp', '<u8')]

@njit
def _sync_tlu_timestamp(tlu,ts,data_out,offset):
    tlu_i=0
    ts_i=0
    i=0
    while tlu_i < len(tlu) and ts_i < len(ts) and i < len(data_out):
        #print tlu_i, hex(tlu[tlu_i]["timestamp"]), ts_i, hex(ts[ts_i]["timestamp"]), 
        #print hex((tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"]) & np.uint64(0x7FFFF)),
        if (tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"] - np.uint64(offset+16*2)) & np.uint64(0x7FFFF)  <= 0x40000:
            #ts_i =ts_i+1
            #print "next ts"
            print "tlu and tlu_ts is not synchronized, synchronize data manually",tlu_i,ts_i
            return 1, i, tlu_i, ts_i, data_out
        elif ((tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"]- np.uint64(offset-16)) & np.uint64(0x7FFFF) ) > 0x40000:
            #tlu_i=tlu_i+1
            #print "next tlu"
            print "tlu and tlu_ts is not synchronized, synchronize data manually",tlu_i,ts_i
            return 2, i, tlu_i, ts_i, data_out
        else:
            data_out[i]["tlu_id"]=tlu[tlu_i]["cnt"] 
            data_out[i]["tlu_timestamp"]=tlu[tlu_i]["timestamp"]
            data_out[i]["ts_timestamp"]=ts[ts_i]["timestamp"]
            ts_i=ts_i+1
            tlu_i=tlu_i+1
            i=i+1
    return 0, i, tlu_i, ts_i, data_out

class TLUTimestampSynchronizer():
    def __init__(self,WAIT_CYCLES=20):
        self.reset(WAIT_CYCLES)
    def reset(self,WAIT_CYCLES, n=1000000):
        self.tlu=np.empty(0,dtype=[('cnt', '<u4'), ('timestamp', '<u8')])
        self.ts=np.empty(0,dtype=[('timestamp', '<u8')])
        self.data_out=np.empty(n,dtype=data_out_type)
        self.offset=(WAIT_CYCLES+1) * 16
    def check_fist_data(self,tlu_e,ts_e):
        if (tlu_e["timestamp"]-ts_e["timestamp"]) & np.uint64(0x7FFFF) > np.uint64(self.offset-16) \
           and (tlu_e["timestamp"]-ts_e["timestamp"]) & np.uint64(0x7FFFF)< np.uint64(self.offset+16*2) :
                print "tlu and tlu_ts is synchronized"
                return 0
        else:
            print "tlu and tlu_ts is not synchronized, synchronize data manually"
            return -1
    def run(self,hits):
        self.tlu=np.append(self.tlu,hits[hits["col"]==255][["timestamp","cnt"]])
        self.ts=np.append(self.ts,hits[hits["col"]==252][["timestamp"]])
        if len(self.tlu) >0 and len(self.ts) > 0:
            self.check_fist_data(self.tlu[0],self.ts[0])
        else:
            return np.empty(0,dtype=data_out_type)
        err, i, tlu_i, ts_i, self.data_out = _sync_tlu_timestamp(self.tlu,self.ts,self.data_out,self.offset)
        if err !=0:
            print "tlu and tlu_ts is not synchronized, data broken err=%d, at tlu_index=%d ts_index=%d"%(err,tlu_i,ts_i)
            return np.empty(0,dtype=data_out_type)
        self.tlu=self.tlu[tlu_i:]
        self.ts=self.ts[ts_i:]
        return self.data_out[:i]
        
if __name__ == "__main__":
    import sys

    fraw=sys.argv[1]
    
    fhit=fraw[:-3]+"_hit.h5"
    
    with tables.open_file(fhit) as f_i:
        hits=f_i.root.Hits[:]
    with tables.open_file(fraw) as f_i:
        conf_s=f_i.root.meta_data.get_attr("status")
        
    conf=yaml.load(conf_s)
    WAIT_CYCLES=conf['tlu']["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]
    
    tlu_synchronizer=TLUTimestampSynchronizer(WAIT_CYCLES=WAIT_CYCLES)
    tlu_synchronizer.run(hits)
    
    #offset=(WAIT_CYCLES+1)*16
    #plt.hist((sync["tlu_timestamp"]-sync["ts_timestamp"]) & 0x7FFFF, bins=np.arange(offset-3*16,offset+3*16,1));
    #plt.xlabel("TLU - TS [640MHz clk]")
    #plt.ylabel("#")
    #plt.savefig('tlu_timestamp_synchronizer.png')