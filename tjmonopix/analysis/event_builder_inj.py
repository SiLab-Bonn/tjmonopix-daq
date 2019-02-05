import sys,time,os
import numpy as np
import matplotlib.pyplot as plt
from numba import njit
import tables
import yaml

TS_TLU=251
TS_INJ=252
TS_MON=253
TS_GATE=254
TLU=255
COL_SIZE=36
ROW_SIZE=129

### debug
### 1 = 1: contined to next file read 0: data is the end of file DONOT use this bit
### 2 = 1: reset inj_cnt when the injection period is wrong
### 4 = 1: include noise flg data 0: delete
### 8 = 1: include hits which were not injected, NOT implemented!!
###     0:only the data from injected pixel

@njit
def _build_inj(dat,param,injlist,thlist,phaselist,inj_period,inj_n,mode,buf,sid,pre_inj,inj_id,inj_cnt):
    b_i=0
    d_i=0
    err=0
    while d_i < len(dat):
        if sid!=dat[d_i]["index"]:
            if inj_id!=len(injlist)-1 or inj_cnt!=inj_n-1:
                print ("ERROR: Broken data, wrong ts_inj idx, inj_cnt,inj_n-1,inj_id,len(injlist)-1"),
                print (d_i,inj_cnt,inj_n-1,inj_id,len(injlist)-1)
            inj_id=-1
            inj_cnt=inj_n-1
        sid=dat[d_i]["index"]
        if dat[d_i]["col"]==TS_INJ:
            d_ii=d_i+1
            while d_ii<len(dat):
                if dat[d_ii]["col"]==TS_INJ:
                   break
                d_ii=d_ii+1
            if d_ii == len(dat) and (mode & 0x1)==1: ## not the end of file:
                return err,d_i,buf[:b_i],sid,pre_inj,inj_id,inj_cnt
            cnt=d_ii-d_i

            ts_inj=np.uint64(dat[d_i]["timestamp"])
            #print (d_i,cnt, inj_id, inj_cnt, (ts_inj-pre_inj)>>4)

            if inj_cnt==inj_n-1:
                inj_cnt=0
                inj_id=inj_id+1
                #print len(injlist),d_i,inj_id
            elif (np.uint64(ts_inj-pre_inj)>>np.uint64(4))!=np.uint64(inj_period):
                print ("ERROR: wrong inj_period: ts_inj-pre_inj,inj_period,inj_cnt,inj_id"),
                print (np.uint64(ts_inj-pre_inj)>>np.uint64(4), inj_period, inj_cnt,inj_id)
                err=err+1
                if (mode & 0x2) ==2:
                    inj_cnt=0
                    inj_id=max(inj_id+1,len(injlist)-1)
                else:
                    inj_cnt=inj_cnt+1
            else:
                inj_cnt=inj_cnt+1

            ts_mon=0x7FFFFFFFFFFFFFFF
            ts_mon_t=0x7FFFFFFFFFFFFFFF
            for d_ii in range(d_i+1, d_i+cnt):
                if dat[d_ii]["col"]==TS_MON and dat[d_ii]["row"]==0 \
                     and ts_mon==0x7FFFFFFFFFFFFFFF:
                    ts_mon=np.int64(dat[d_ii]["timestamp"])
                elif dat[d_ii]["col"]==TS_MON and dat[d_ii]["row"]==1 \
                     and ts_mon_t==0x7FFFFFFFFFFFFFFF:
                    ts_mon_t=np.int64(dat[d_ii]["timestamp"])
                elif dat[d_ii]["col"]<COL_SIZE:
                    if mode & 0x4 ==0x4 or dat[d_ii]["cnt"]==0:
                        ts_token=np.int64(dat[d_ii]["timestamp"])
                        #buf[b_i]["event_number"]= sid*len(injlist)*inj_n+inj_id*inj_n+inj_cnt
                        buf[b_i]["scan_param_id"]= sid
                        buf[b_i]["inj_id"]= inj_id
                        buf[b_i]["col"]= dat[d_ii]["col"]
                        buf[b_i]["row"]= dat[d_ii]["row"]
                        buf[b_i]["inj"]= injlist[inj_id]
                        buf[b_i]["th"]= thlist[inj_id]
                        buf[b_i]["phase"]= phaselist[inj_id]
                        buf[b_i]["ts_mon"]= ts_mon
                        buf[b_i]["ts_inj"]= ts_inj
                        buf[b_i]["ts_token"]= ts_token 
                        buf[b_i]["tot"]= (dat[d_ii]["te"]-dat[d_ii]["le"])&0xFF
                        buf[b_i]["tof"]= dat[d_ii]["le"]
                        buf[b_i]["tot_mon"]= ts_mon_t-ts_mon
                        buf[b_i]["flg"]= dat[d_ii]["cnt"]
                        b_i=b_i+1
            pre_inj=ts_inj
            d_i=d_i + cnt
        else:
            d_i=d_i+1
    return err,d_i,buf[:b_i],sid,pre_inj,inj_id,inj_cnt

buf_type=[#("event_number","<i8"),
          ("scan_param_id","<i4"),("inj_id","<i4"),  ### this is redundant. can be deleted later..
          ("col","<u1"),("row","<u1"),("tot","<u1"),("tof","<u1"),("flg","<u1"),
          ("ts_inj","<u8"),("ts_mon","<u8"),("ts_token","<u8"),("tot_mon","<u8"),
          ("inj","<f4"),("th","<f4"),("phase","<u1")]

def build_inj_h5(fhit,fraw,fout,n=500000,debug=0x2):
    buf=np.empty(n,dtype=buf_type)
    with tables.open_file(fraw) as f:
        meta=f.root.meta_data[:]
        param=f.root.scan_parameters[:]
        inj_low=yaml.load(f.root.meta_data.attrs.power_status)["INJ_LOset"]
        firmware=yaml.load(f.root.meta_data.attrs.firmware)
        for i in range(0,len(f.root.kwargs),2):
            if f.root.kwargs[i]=="injlist":
                injlist=yaml.load(f.root.kwargs[i+1])
            elif f.root.kwargs[i]=="thlist":
                thlist=yaml.load(f.root.kwargs[i+1])
            elif f.root.kwargs[i]=="phaselist":
                phaselist=yaml.load(f.root.kwargs[i+1])
    inj_period=firmware['inj']["WIDTH"]+firmware['inj']["DELAY"]
    inj_n=firmware['inj']["REPEAT"]
    sid=-1
    inj_id=len(injlist)-1
    inj_cnt=inj_n-1
    pre_inj=0
    with tables.open_file(fout,"w") as f_o:
        description=np.zeros((1,),dtype=buf_type).dtype
        hit_table=f_o.create_table(f_o.root,name="Hits",description=description,title='hit_data')
        with tables.open_file(fhit) as f:
            end=len(f.root.Hits)
            start=0
            t0=time.time()
            while start<end:   ## this does not work, need to read with one chunck
                tmpend=min(end,start+n)
                dat=f.root.Hits[start:tmpend]
                print "data (inj_n %d,inj_loop %d): INJ=%d MONO=%d MON=%d"%(
                        inj_n,len(injlist),
                        len(np.where(dat["col"]==TS_INJ)[0]),
                        len(np.where(dat["col"]<COL_SIZE)[0]),
                        len(np.where(dat["col"]==TS_MON)[0]))
                if end==tmpend:
                    mode=0 | debug
                else:
                    mode=1 | debug
                (err,d_i,hit_dat,sid,pre_inj,inj_id,inj_cnt
                    ) =_build_inj(
                    dat,param,
                    injlist,thlist,phaselist, ## not well written.
                    inj_period,inj_n,mode,buf,
                    sid,pre_inj,inj_id,inj_cnt)
                hit_table.append(hit_dat)
                hit_table.flush()
                print "%d %d %.3f%% %.3fs %dhits %derrs"%(start,d_i,100.0*(start+d_i)/end,time.time()-t0,len(hit_dat),err)
                start=start+d_i
    return
            
if __name__ == "__main__":
    import sys
    fraw=sys.argv[1]
    fhit=fraw[:-7]+"hit.h5"
    fout=fraw[:-7]+"ts.h5"
    assign_ts(fhit,fraw,fts,n=10000000)
    print fout
               