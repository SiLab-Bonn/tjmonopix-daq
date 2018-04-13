import numpy as np
from numba import njit 
import tables
import yaml

@njit
def _build_with_tlu(sync,tj,data_out,upper,lower,data_format):
    tj_i=0
    i=0
    sync_i=0
    while tj_i< len(tj) and i< len(data_out) and sync_i < len(sync): 
        if sync[sync_i]["ts_timestamp"] > tj[tj_i]["timestamp"] + upper:
            tj_i =tj_i +1
            #print "next tj"
        elif sync[sync_i]["ts_timestamp"]+ lower < tj[tj_i]["timestamp"] :
            #print syn_i, hex(sync[sync_i]["ts_timestamp"]), tj_i, hex(tj[tj_i]["timestamp"]), 
            #print hex(sync[syn_i]["ts_timestamp"] - tj[tj_i]["timestamp"]),
            sync_i = sync_i +1
            #print "nex tlu"
        else:
            #print syn_i, hex(sync[sync_i]["ts_timestamp"]), tj_i, hex(tj[tj_i]["timestamp"]), 
            #print hex(sync[syn_i]["ts_timestamp"] - tj[tj_i]["timestamp"]),
            data_out[i]["trigger_number"]= sync[sync_i]["trigger_number"]
            data_out[i]["column"] = tj[tj_i]["col"]
            data_out[i]["row"] = tj[tj_i]["row"]
            if data_format & 0x2 == 0x2:
                data_out[i]["tlu_timestamp"]= sync[sync_i]["tlu_timestamp"]
                data_out[i]["trigger_timestamp"]= sync[sync_i]["ts_timestamp"]
                data_out[i]["token_timestamp"]= tj[tj_i]["timestamp"]
                data_out[i]["le"]= tj[tj_i]["le"]
                data_out[i]["te"]= tj[tj_i]["te"]
            i= i+1
            tj_i = tj_i+1
    return 0, i, sync_i, tj_i, data_out

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
            #print "tlu and tlu_ts is not synchronized, synchronize data manually",tlu_i,ts_i
            return 1, i, tlu_i, ts_i, data_out
        elif ((tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"]- np.uint64(offset-16)) & np.uint64(0x7FFFF) ) > 0x40000:
            #tlu_i=tlu_i+1
            #print "next tlu"
            #print "tlu and tlu_ts is not synchronized, synchronize data manually",tlu_i,ts_i
            return 2, i, tlu_i, ts_i, data_out
        else:
            data_out[i]["trigger_number"]=tlu[tlu_i]["cnt"] 
            data_out[i]["tlu_timestamp"]=tlu[tlu_i]["timestamp"]
            data_out[i]["ts_timestamp"]=ts[ts_i]["timestamp"]
            ts_i=ts_i+1
            tlu_i=tlu_i+1
            i=i+1
    return 0, i, tlu_i, ts_i, data_out

def build_h5(fraw,fhit,fout,upper=0x80,lower=-0x100,data_format=0x2,n=1000000):
    buf_type=[("trigger_number","i2"),("tlu_timestamp","u8"),("ts_timestamp","u8")]
    if data_format & 0x2 == 0x2:
        data_out_type=[("le","u1"),("te","u1"),("column","u1"),("row","u2"),
                   ("trigger_number","i2"),("trigger_timestamp","u8"),
                   ("tlu_timestamp","u8"), ("token_timestamp","u8")]
    else:
        data_out_type=[("column","u1"),("row","u2"), ("trigger_number","i2")]
    with tables.open_file(fhit) as f_i:
        hits=f_i.root.Hits[:]

    ## set parameters
    with tables.open_file(fraw) as f_i:
        conf_s=f_i.root.meta_data.get_attr("status")
    conf=yaml.load(conf_s)
    WAIT_CYCLES=conf['tlu']["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]
    offset=(WAIT_CYCLES+1) * 16
    upper=np.uint64(np.abs(upper))
    lower=np.uint64(np.abs(lower))
    
    tlu=hits[hits["col"]==255][["timestamp","cnt"]]
    ts=hits[hits["col"]==252][["timestamp"]]
    tj=hits[np.bitwise_and(hits["col"]<112, hits["cnt"]==0)][["timestamp","col","row"]]
    print "# of data: tlu=%d ts=%d tj=%d"%(len(tlu),len(ts),len(tj))
    if len(tlu)==0 or len(ts)==0 or len(tj)==0:
       print "no data"
       return np.empty(0,dtype=data_out_type)
    
    if check_tlu_data(tlu[0],ts[0]) == 0:
             pass
    elif check_tlu_data(tlu[0],ts[1]) == 0:
             ts_i=ts[1:]
    elif check_tlu_data(tlu[1],ts[0]) == 0:
             tlu=tlu[1:]
    else:
        print "synchronize tlu and tlu_ts manually" 
        return np.empty(0,dtype=data_out_type)
             
    buf=np.empty(len(tlu),dtype=buf_type)
    data_out=np.empty(len(tj),dtype=data_out_type)
 
    err, buf_i, tlu_i, ts_i, buf = _sync_tlu_timestamp(tlu,ts,buf,offset)
    print "assign 64bits-timestamp to tlu err=%d assigned=%d tlu=%d ts=%d"(err, buf_i, tlu_i, ts_i)
    
    err, i, buf_i, tj_i, data_out = _build_with_tlu(buf[:buf_i],tj,data_out,upper,lower,data_format)
    print "assign tlu number to tj err=%d assigned=%d tlu_with_ts=%d tj=%d"(err, i, buf_i, tj_i)
    
    with tables.open_file(fout, "w") as f_o:
        description = np.zeros((1,), dtype=data_out_type).dtype
        hit_table = f_o.create_table(
            f_o.root, name="Hits", description=description, title='hit_data')
        hit_table.append(data_out[:i])
        hit_table.flush()
    return data_out[:i]

def check_tlu_data(tlu_e,ts_e):
    if (tlu_e["timestamp"]-ts_e["timestamp"]) & np.uint64(0x7FFFF) > np.uint64(0x15-16) \
       and (tlu_e["timestamp"]-ts_e["timestamp"]) & np.uint64(0x7FFFF)< np.uint64(0x150+16*2) :
            #print "tlu and tlu_ts is synchronized"
            return 0
    else:
        #print "tlu and tlu_ts is not synchronized"
        return -1
    
class BuildEvents():
    def __init__(self,upper=0x80,lower=-0x100,WAIT_CYCLES=20,data_format=0x2):
        self.data_format=2
        self.reset(upper,lower,WAIT_CYCLES)
        
    def reset(self,upper=0x80,lower=-0x100,WAIT_CYCLES=20,n=1000000):
        if self.data_format & 0x2 == 0x2:
            data_out_type=[("column","u1"),("row","u2"), ("trigger_number","i2"),("tlu_timestamp","u8"),("trigger_timestamp","u8"), 
                   ("token_timestamp","u8")]
        else:
            data_out_type=[("column","u1"),("row","u2"), ("trigger_number","i2")]
        buf_type=[("trigger_number","i2"),("tlu_timestamp","u8"),("ts_timestamp","u8")]

        self.tlu=np.empty(0,dtype=[('cnt', '<u4'), ('timestamp', '<u8')])
        self.ts=np.empty(0,dtype=[('timestamp', '<u8')])
        self.tj=np.empty(0,dtype=[('timestamp', '<u8'),("col","u1"),("row","u2")])
        self.buf=np.empty(0,dtype=buf_type)
        self.data_out=np.empty(n,dtype=data_out_type)
        self.tmpbuf=np.empty(n,dtype=buf_type)
        
        self.upper=np.uint64(np.abs(upper))
        self.lower=np.uint64(np.abs(lower))
        self.offset=(WAIT_CYCLES+1) * 16
        
    def run(self, hits):
        self.tlu=np.append(self.tlu,hits[hits["col"]==255][["timestamp","cnt"]])
        self.ts=np.append(self.ts,hits[hits["col"]==252][["timestamp"]])
        self.tj=np.append(self.tj,hits[np.bitwise_and(hits["col"]<112, hits["cnt"]==0)][["timestamp","col","row"]])
        if len(self.tlu) ==0 or len(self.ts) == 0:
            return np.empty(0,dtype=self.data_out.dtype)
        
        if len(self.tlu) > 1 and len(self.ts) > 1:
            #mask=np.uint64(0x7ffff)
            #print "---------------",self.tlu[0]["timestamp"]&mask,self.ts[0]["timestamp"]&mask,self.tlu[1]["timestamp"]&mask,self.ts[1]["timestamp"]&mask
            if check_tlu_data(self.tlu[0],self.ts[0]) == 0:
                #print "okokokokokok"
	              pass
            elif check_tlu_data(self.tlu[0],self.ts[1]) == 0:
                self.ts=self.ts[1:]
            elif check_tlu_data(self.tlu[1],self.ts[0]) == 0:
                self.tlu=self.tlu[1:]
        else:
	       print "synchronize tlu and tlu_ts manually" 
	       return np.empty(0,dtype=self.data_out.dtype)
        err, buf_i, tlu_i, ts_i, self.tmpbuf = _sync_tlu_timestamp(self.tlu,self.ts,self.tmpbuf,self.offset)
        if err != 0:
            print "data might be broken",err,tlu_i,ts_i
            return np.empty(0,dtype=self.data_out.dtype)
        self.tlu=self.tlu[tlu_i:]
        self.ts=self.ts[ts_i:]
        self.buf=np.append(self.buf,self.tmpbuf[:buf_i])
        err, i, buf_ii, tj_i, self.data_out = _build_with_tlu(self.buf,self.tj,self.data_out,self.upper,self.lower,self.data_format)
        if err != 0 or self.data_format & 0x1 ==0x01:
            print "error", err, i, buf_ii, tj_i
        self.tj=self.tj[tj_i:]
        self.buf=self.buf[buf_ii:]
        return self.data_out[:i]
        
if  __name__ == "__main__":
    import sys    
    import matplotlib.pyplot as plt
    
    fraw=sys.argv[1]
    
    fhit=fraw[:-3]+"_hit.h5"
    
    with tables.open_file(fhit) as f_i:
        hits=f_i.root.Hits[:]
    with tables.open_file(fraw) as f_i:
        conf_s=f_i.root.meta_data.get_attr("status")    
    
#    with tables.open_file('20180322_001649_simple_hit.h5', "r") as f_i:
#        hits=f_i.root.Hits[:]
#    with tables.open_file('20180322_001649_simple.h5', "r") as f_i:
#        conf_s=f_i.root.meta_data.get_attr("status")
        
    conf=yaml.load(conf_s)
    
    WAIT_CYCLES=conf['tlu']["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]
    lower = -0x100
    upper = 0x80
    
    builder= BuildEvents(upper,lower,WAIT_CYCLES)
    data_out=builder.run(hits) 
    bins=np.arange(lower,upper,10)
    
    plt.hist((np.int64(data_out["ts_timestamp"])-np.int64(data_out["token_timestamp"])),bins=bins,histtype="step");
    plt.savefig(fraw[:-3]+"_event_builder.png")
