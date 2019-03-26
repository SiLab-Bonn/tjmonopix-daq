import sys,time,os
import numpy as np
import matplotlib.pyplot as plt
from numba import njit
import tables

hit_idx_dtype=np.dtype([("col","<u1"),("row","<u1"),("le","<u1"),("te","<u1"),("cnt","<u4"),
                    ("timestamp","<u8"),("index","<u4")])
                    
@njit
def _interpret_idx(raw,buf,start,col,row,le,te,noise,timestamp,rx_flg,
               ts_timestamp,ts_pre,ts_flg,ts_cnt,
               ts2_timestamp,ts2_pre,ts2_flg,ts2_cnt,
               ts2t_timestamp,ts2t_flg,ts2t_cnt,
               ts3_timestamp,ts3_pre,ts3_flg,ts3_cnt,
               ts4_timestamp,ts4_pre,ts4_flg,ts4_cnt,debug):
    TJ_MASK_LOWER = np.uint64(0x00000000FFFFFFF0)
    TJ_MASK_UPPER = np.uint64(0x00FFFFFF00000000)

    TS_MASK_DAT           =0x0000000000FFFFFF
    TS_MASK1    =np.uint64(0xFFFFFFFFFF000000)
    TS_MASK2    =np.uint64(0xFFFF000000FFFFFF)
    TS_MASK3    =np.uint64(0x0000FFFFFFFFFFFF)

    TS_MASK_TOT = np.uint64(0x0000000000FFFF00)
    TS_DIV_MASK_DAT = np.uint64(0x00000000000000FF)
    err=0
    buf_i=0
    for r_i,r in enumerate(raw):
        ########################
        ### MONOPIX_RX
        ########################
        if (r & 0xF0000000 == 0x30000000):
            pass #TODO get count
        elif (r & 0xF0000000 == 0x00000000):
            col = 2 * (r & 0x3f) + (((r & 0x7FC0) >> 6) // 256)
            row = ((r & 0x7FC0) >> 6) % 256
            te = (r & 0x1F8000) >> 15
            le = (r & 0x7E00000) >> 21
            noise = (r & 0x8000000) >> 27
           #if debug & 0x4 ==0x4:
               #print r_i,hex(r),rx_flg,"ts=",hex(timestamp),col,row,noise

            if rx_flg==0x0:
              rx_flg=0x1
            else:
               err=err+1
               buf[buf_i]["row"]=0xE1
               buf[buf_i]["col"]=0
               buf[buf_i]["le"]=rx_flg
               buf[buf_i]["te"]=0
               buf[buf_i]["timestamp"]= 0
               buf[buf_i]["cnt"]=r
               buf[buf_i]["index"]=r_i+start
               buf_i=buf_i+1
               rx_flg=0
           
        elif (r & 0xF0000000 == 0x10000000):
            timestamp = (timestamp & TJ_MASK_UPPER) | (
                np.uint64(r)<<np.uint64(4) & TJ_MASK_LOWER)
           #if debug & 0x4 ==0x4:
               #print r_i,hex(r),rx_flg,"ts=",hex(timestamp),le,te
               #pass
               
            if rx_flg==0x1:
              rx_flg=0x2
            else:
               err=err+1
               buf[buf_i]["row"]=0xE1
               buf[buf_i]["col"]=1
               buf[buf_i]["le"]=rx_flg
               buf[buf_i]["te"]=0
               buf[buf_i]["timestamp"]= 0
               buf[buf_i]["cnt"]=r
               buf[buf_i]["index"]=r_i+start
               buf_i=buf_i+1
               rx_flg=0

        elif (r & 0xF0000000 == 0x20000000):
            timestamp = (timestamp & TJ_MASK_LOWER) | (
                (np.uint64(r) << np.uint64(32)) & TJ_MASK_UPPER)
           #if debug & 0x4 ==0x4:
               #print r_i,hex(r),rx_flg,"ts=",hex(timestamp)
               
            if rx_flg == 0x2:
               buf[buf_i]["row"]=row
               buf[buf_i]["col"]=col
               buf[buf_i]["le"]=le
               buf[buf_i]["te"]=te
               buf[buf_i]["timestamp"]= timestamp
               buf[buf_i]["cnt"]=noise
               buf[buf_i]["index"]=r_i+start
               buf_i=buf_i+1
               rx_flg=0
            else:
               err=err+1
               buf[buf_i]["row"]=0xE1
               buf[buf_i]["col"]=2
               buf[buf_i]["le"]=rx_flg
               buf[buf_i]["te"]=0
               buf[buf_i]["timestamp"]= 0
               buf[buf_i]["cnt"]=r
               buf[buf_i]["index"]=r_i+start
               buf_i=buf_i+1
               rx_flg=0
              
        ########################
        ### TIMESTMP
        ########################
        elif r & 0xFF000000 == 0x40000000: 
            pass ## TODO get count
        elif r & 0xFF000000 == 0x41000000: ## timestamp
            ts_timestamp = (ts_timestamp & TS_MASK1) | np.uint64(r & TS_MASK_DAT)
            ts_cnt=ts_cnt+1
            #if debug & 0x4 ==0x4:
                #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts_flg==2:
               ts_flg=0
               if debug & 0x1 == 0x1:
                   ts_inter=(ts_timestamp-ts_pre)& 0xFFFFFFFF
                   buf[buf_i]["col"]=0xFE
                   buf[buf_i]["row"]= np.uint8(ts_inter)
                   buf[buf_i]["le"]=np.uint8(ts_inter>>np.uint64(8))
                   buf[buf_i]["te"]=np.uint8(ts_inter>>np.uint64(16))
                   buf[buf_i]["timestamp"]=ts_timestamp
                   buf[buf_i]["cnt"]=ts_cnt
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
            else:
               if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEE
                   buf[buf_i]["row"]=2
                   buf[buf_i]["le"]=ts_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
               err=err+1
               ts_flg=0
        elif r & 0xFF000000 == 0x42000000: ## timestamp
            ts_timestamp=(ts_timestamp & TS_MASK2) + (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            #if debug & 0x4 ==0x4:
                #print r_i,hex(r),"timestamp2",hex(ts_timestamp),

            if ts_flg==0x1:
              ts_flg=0x2
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEE
                   buf[buf_i]["row"]=1
                   buf[buf_i]["le"]=ts_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts_flg=0x0
                err=err+1
        elif r & 0xFF000000 == 0x43000000: ## timestamp
            ts_pre=ts_timestamp
            ts_timestamp=(ts_timestamp & TS_MASK3)+ (np.uint64(r & TS_MASK_DAT) << np.uint64(48))
            #if debug & 0x4 ==0x4:
               #print r_i,hex(r),"timestamp3",hex(ts_timestamp),

            if ts_flg==0x0:
               ts_flg=0x1
            else:
               if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEE
                   buf[buf_i]["row"]=0
                   buf[buf_i]["le"]=ts_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
               ts_flg=0x0  
               err=err+1
               
        ########################
        ### TIMESTMP160 INJ
        ########################
        elif r & 0xFF000000 == 0x50000000:
            pass  # TODO get count
        elif r & 0xFF000000 == 0x51000000:  # timestamp
            ts3_timestamp = (ts3_timestamp & np.uint64(0xFFFFFFFFFF000000)) | np.uint64( r & TS_MASK_DAT )
            ts3_cnt = ts3_cnt+1
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts3_flg == 2:
                ts3_flg = 0
                if debug & 0x1 == 0x1:
                    buf[buf_i]["col"] = 0xFC
                    buf[buf_i]["row"] = 0
                    buf[buf_i]["le"] = 0
                    buf[buf_i]["te"] = 0
                    buf[buf_i]["timestamp"] = ts3_timestamp
                    buf[buf_i]["cnt"] = ts3_cnt
                    buf[buf_i]["index"]=r_i+start
                    #if debug & 0x80 == 0x80:
                    #    buf[buf_i]['idx']=r_i
                    buf_i = buf_i+1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEC
                   buf[buf_i]["row"]=2
                   buf[buf_i]["le"]=ts3_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts3_flg = 0 
                err=err+1
        elif r & 0xFF000000 == 0x52000000:  # timestamp
            ts3_timestamp = (ts3_timestamp & np.uint64(0xFFFF000000FFFFFF)) | \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp)

            if ts3_flg == 0x1:
                ts3_flg = 0x2
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEC
                   buf[buf_i]["row"]=1
                   buf[buf_i]["le"]=ts3_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts3_flg = 0 
                err=err+1
        elif r & 0xFF000000 == 0x53000000:  # timestamp
            ts3_timestamp = (ts3_timestamp & np.uint64(0x0000FFFFFFFFFFFF)) | (np.uint64(r & np.uint64(0x000000000000FFFF)) << np.uint64(48))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"ts2_timestamp",hex(ts_timestamp)

            if ts3_flg == 0x0:
                ts3_flg = 0x1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEC
                   buf[buf_i]["row"]=0
                   buf[buf_i]["le"]=ts3_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts3_flg = 0 
                err=err+1

        ########################
        ### TIMESTMP640 MON
        ########################
        elif r & 0xFF000000 == 0x60000000:
            pass  # TODO get count
        elif r & 0xFF000000 == 0x61000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & np.uint64(0xFFFFFFFFFF000000)) | np.uint64( r & TS_MASK_DAT )
            ts2_cnt = ts2_cnt+1
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts2_flg == 2:
                ts2_flg = 0
                if debug & 0x1 == 0x1:
                    buf[buf_i]["col"] = 0xFD
                    buf[buf_i]["row"] = 0
                    buf[buf_i]["le"] = 0
                    buf[buf_i]["te"] = 0
                    buf[buf_i]["timestamp"] = ts2_timestamp
                    buf[buf_i]["cnt"] = ts2_cnt
                    buf[buf_i]["index"]=r_i+start
                    #if debug & 0x80 == 0x80:
                    #    buf[buf_i]['idx']=r_i
                    buf_i = buf_i+1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xED
                   buf[buf_i]["row"]=2
                   buf[buf_i]["le"]=ts2_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts2_flg = 0   
                err=err+1 
        elif r & 0xFF000000 == 0x62000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & np.uint64(0xFFFF000000FFFFFF)) | \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp)

            if ts2_flg == 0x1:
                ts2_flg = 0x2
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xED
                   buf[buf_i]["row"]=1
                   buf[buf_i]["le"]=ts2_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts2_flg = 0 
                err=err+1   
        elif r & 0xFF000000 == 0x63000000:  # timestamp
            ts2_timestamp = (ts2_timestamp & np.uint64(0x0000FFFFFFFFFFFF)) | \
                (np.uint64(r & TS_DIV_MASK_DAT) << np.uint64(48))
            ts2_tot = (np.uint64(r & TS_MASK_TOT) >> np.uint64(8))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"ts2_timestamp",hex(ts_timestamp)

            if ts2_flg == 0x0:
                ts2_flg = 0x1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xED
                   buf[buf_i]["row"]=0
                   buf[buf_i]["le"]=ts2_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts2_flg = 0  
                err=err+1
        elif r & 0xFF000000 == 0x65000000:  # timestamp
            ts2t_timestamp = (ts2t_timestamp & np.uint64(0xFFFFFFFFFF000000)) | np.uint64( r & TS_MASK_DAT )
            ts2t_cnt = ts2t_cnt+1
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts2t_flg == 2:
                ts2t_flg = 0
                if debug & 0x1 == 0x1:
                    buf[buf_i]["col"] = 0xFD
                    buf[buf_i]["row"] = 1
                    buf[buf_i]["le"] = 0
                    buf[buf_i]["te"] = 0
                    buf[buf_i]["timestamp"] = ts2t_timestamp
                    buf[buf_i]["cnt"] = ts2t_cnt
                    buf[buf_i]["index"]=r_i+start
                    #if debug & 0x80 == 0x80:
                    #    buf[buf_i]['idx']=r_i
                    buf_i = buf_i+1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xED
                   buf[buf_i]["row"]=2+4
                   buf[buf_i]["le"]=ts2t_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts2t_flg = 0   
                err=err+1 
        elif r & 0xFF000000 == 0x66000000:  # timestamp
            ts2t_timestamp = (ts2t_timestamp & np.uint64(0xFFFF000000FFFFFF)) | \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp)

            if ts2t_flg == 0x1:
                ts2t_flg = 0x2
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xED
                   buf[buf_i]["row"]=1+4
                   buf[buf_i]["le"]=ts2t_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts2t_flg = 0 
                err=err+1   
        elif r & 0xFF000000 == 0x67000000:  # timestamp
            ts2t_timestamp = (ts2t_timestamp & np.uint64(0x0000FFFFFFFFFFFF)) | \
                (np.uint64(r & TS_DIV_MASK_DAT) << np.uint64(48))
            if ts2t_flg == 0x0:
                ts2t_flg = 0x1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xED
                   buf[buf_i]["row"]=0+4
                   buf[buf_i]["le"]=ts2t_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts2t_flg = 0  
                err=err+1
   
        ########################
        ### TIMESTMP160 TLU
        ########################
        elif r & 0xFF000000 == 0x70000000:
            pass  # TODO get count
        elif r & 0xFF000000 == 0x71000000:  # timestamp
            ts4_timestamp = (ts4_timestamp & np.uint64(0xFFFFFFFFFF000000)) | np.uint64( r & TS_MASK_DAT )
            ts4_cnt = ts4_cnt+1
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp),ts_cnt

            if ts4_flg == 2:
                ts4_flg = 0
                if debug & 0x1 == 0x1:
                    buf[buf_i]["col"] = 0xFB
                    buf[buf_i]["row"] = 0
                    buf[buf_i]["le"] = 0
                    buf[buf_i]["te"] = 0
                    buf[buf_i]["timestamp"] = ts4_timestamp
                    buf[buf_i]["cnt"] = ts4_cnt
                    buf[buf_i]["index"]=r_i+start
                    #if debug & 0x80 == 0x80:
                    #    buf[buf_i]['idx']=r_i
                    buf_i = buf_i+1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEB
                   buf[buf_i]["row"]=2
                   buf[buf_i]["le"]=ts4_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts4_flg = 0  
                err=err+1
        elif r & 0xFF000000 == 0x72000000:  # timestamp
            ts4_timestamp = (ts4_timestamp & np.uint64(0xFFFF000000FFFFFF)) | \
                (np.uint64(r & TS_MASK_DAT) << np.uint64(24))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"timestamp1",hex(ts_timestamp)

            if ts4_flg == 0x1:
                ts4_flg = 0x2
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEB
                   buf[buf_i]["row"]=1
                   buf[buf_i]["le"]=ts4_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts4_flg = 0 
                err=err+1 
        elif r & 0xFF000000 == 0x73000000:  # timestamp
            ts4_timestamp = (ts4_timestamp & np.uint64(0x0000FFFFFFFFFFFF)) | (np.uint64(r & np.uint64(0x000000000000FFFF)) << np.uint64(48))
            # if debug & 0x4 ==0x4:
            #print r_i,hex(r),"ts2_timestamp",hex(ts_timestamp)

            if ts4_flg == 0x0:
                ts4_flg = 0x1
            else:
                if debug & 0x1 == 0x1:
                   buf[buf_i]["col"]=0xEB
                   buf[buf_i]["row"]=0
                   buf[buf_i]["le"]=ts4_flg
                   buf[buf_i]["te"]=0
                   buf[buf_i]["timestamp"]=0
                   buf[buf_i]["cnt"]=r
                   buf[buf_i]["index"]=r_i+start
                   buf_i=buf_i+1
                ts4_flg = 0 
                err=err+1                         

        ########################
        ### TLU
        ########################
        elif (r & 0x80000000 == 0x80000000):
            tlu = r & 0xFFFF
            tlu_org =(r>>12) & 0x7FFF0  #16-4(160MHz)
            if debug & 0x20 ==0x00:
                tlu_timestamp= ts_pre & np.uint64(0xFFFFFFFFFFF80000) | np.uint64(tlu_org)
                if tlu_org < (np.int32(ts_pre) & 0x7FFF0):
                #if np.uint64(tlu_timestamp - ts_pre) & np.uint64(0x8000) == np.uint64(0x8000):
                    tlu_timestamp = tlu_timestamp + np.uint64(0x80000)
            else:
                tlu_timestamp= ts2_pre & np.uint64(0xFFFFFFFFFFF80000) | np.uint64(tlu_org)
                if tlu_org < (np.int32(ts2_pre) & 0x7FFF0):
                    tlu_timestamp = tlu_timestamp + np.uint64(0x80000)
            #if debug & 0x4 ==0x4:
                #print r_i,hex(r),"ts=",hex(tlu_timestamp),"tlu",tlu,hex(tlu_tmp),tlu_tmp < trig_tmp

            if debug & 0x2 == 0x2:
                buf[buf_i]["col"]=0xFF
                buf[buf_i]["row"]=0xFF
                buf[buf_i]["le"]= 0xFF 
                buf[buf_i]["te"]= 0xFF
                buf[buf_i]["timestamp"]=tlu_timestamp
                buf[buf_i]["cnt"]=tlu
                buf[buf_i]["index"]=r_i+start
                buf_i=buf_i+1
        else:
            buf[buf_i]["col"]=0xE0
            buf[buf_i]["row"]=0
            buf[buf_i]["le"]=0
            buf[buf_i]["te"]=0
            buf[buf_i]["timestamp"]=0
            buf[buf_i]["cnt"]=r
            buf[buf_i]["index"]=r_i+start
            buf_i=buf_i+1
            err=err+1   
    return err,buf[:buf_i],r_i,col,row,le,te,noise,timestamp,rx_flg,\
                      ts_timestamp,ts_pre,ts_flg,ts_cnt,\
                      ts2_timestamp,ts2_pre,ts2_flg,ts2_cnt,ts2t_timestamp,ts2t_flg,ts2t_cnt,\
                      ts3_timestamp,ts3_pre,ts3_flg,ts3_cnt,\
                      ts4_timestamp,ts4_pre,ts4_flg,ts4_cnt

                      
@njit
def _assign_scan_id(dat,meta):
    m_i=0
    d_i=0
    while m_i<len(meta) and d_i< len(dat):
        if meta[m_i]["index_start"] <= dat[d_i]["index"] \
           and meta[m_i]["index_stop"] > dat[d_i]["index"]:
                dat[d_i]["index"]=meta[m_i]["scan_param_id"]
                d_i=d_i+1
        elif meta[m_i]["index_stop"] <= dat[d_i]["index"]:
            m_i=m_i+1
        else: # meta[m_i]["index_start"] > data[d_i]["index"]
            #print "error", m_i,d_i,meta[m_i]["index_start"],dat[d_i]["index"]
            #break
            return 1,dat,m_i,d_i
    return 0,dat,m_i, d_i
                      
                      
def interpret_idx_h5(fin,fout,debug=12, n=100000000):
    buf=np.empty(n,dtype=hit_idx_dtype)
    col=0xFF
    row=0xFF
    le=0xFF
    te=0xFF
    noise=0
    timestamp=np.uint64(0x0)
    rx_flg=0
    
    ts_timestamp=np.uint64(0x0)
    ts_pre=ts_timestamp
    ts_cnt=0x0
    ts_flg=0
    
    ts2_timestamp=np.uint64(0x0)
    ts2_pre=ts2_timestamp
    ts2_cnt=0x0
    ts2_flg=0
    ts2t_timestamp=np.uint64(0x0)
    ts2t_cnt=0x0
    ts2t_flg=0
    
    ts3_timestamp=np.uint64(0x0)
    ts3_pre=ts3_timestamp
    ts3_cnt=0x0
    ts3_flg=0
    
    ts4_timestamp=np.uint64(0x0)
    ts4_pre=ts4_timestamp
    ts4_cnt=0x0
    ts4_flg=0
    
    with tables.open_file(fout, "w") as f_o:
        description=np.zeros((1,),dtype=hit_idx_dtype).dtype
        hit_table=f_o.create_table(f_o.root,name="Hits",description=description,title='hit_data')
        with tables.open_file(fin) as f:
            meta=f.root.meta_data[:]
            end=len(f.root.raw_data)
            start=0
            t0=time.time()
            hit_total=0
            while start<end:
                tmpend=min(end,start+n)
                raw=f.root.raw_data[start:tmpend]
                (err,hit_dat,r_i,col,row,le,te,noise,timestamp,rx_flg,
                    ts_timestamp,ts_pre,ts_flg,ts_cnt,
                    ts2_timestamp,ts2_pre,ts2_flg,ts2_cnt,ts2t_timestamp,ts2t_flg,ts2t_cnt,
                    ts3_timestamp,ts3_pre,ts3_flg,ts3_cnt,
                    ts4_timestamp,ts4_pre,ts4_flg,ts4_cnt
                    ) = _interpret_idx(
                    raw,buf,start,col,row,le,te,noise,timestamp,rx_flg,
                    ts_timestamp,ts_pre,ts_flg,ts_cnt,
                    ts2_timestamp,ts2_pre,ts2_flg,ts2_cnt,ts2t_timestamp,ts2t_flg,ts2t_cnt,
                    ts3_timestamp,ts3_pre,ts3_flg,ts3_cnt,
                    ts4_timestamp,ts4_pre,ts4_flg,ts4_cnt,debug)
                n_hit=len(hit_dat)
                hit_total=hit_total+n_hit
                err,hit_dat,m_i,d_i = _assign_scan_id(hit_dat,meta)
                meta=meta[m_i:]
                if d_i!=n_hit:
                    print "assing_scan has error data=%d, assigned=%d"%(n_hit,d_i)
                print "%d %d %.3f%% %.3fs %dhits %derrs"%(start,r_i,100.0*(start+r_i+1)/end,time.time(),len(hit_dat),err)
                hit_table.append(hit_dat)
                hit_table.flush()
                start=start+r_i+1

def list2img(dat,delete_noise=True):
    if delete_noise==True:
        dat=without_noise(dat)
    return np.histogram2d(dat["col"],dat["row"],bins=[np.arange(0,37,1),np.arange(0,130,1)])[0]

def list2cnt(dat,delete_noise=True):
    if delete_noise==True:
        dat=without_noise(dat)
    uni,cnt=np.unique(dat[["col","row"]],return_counts=True)
    ret=np.empty(len(uni),dtype=[("col","<u1"),("row","<u1"),("cnt","<i8")])

    ret["col"]=uni["col"]
    ret["row"]=uni["row"]
    ret["cnt"]=cnt
    return ret
    
def without_noise(dat):
    return dat[np.bitwise_or(dat["cnt"]==0,dat["col"]>=36)]
    

class InterRawIdx():
    def __init__(self,chunk=100000000,debug=0):
        self.reset()
        self.buf=np.empty(chunk,dtype=hit_idx_dtype)
        self.n=chunk
        self.debug=0
    def reset(self):
        self.col=0xFF
        self.row=0xFF
        self.le=0xFF
        self.te=0xFF
        self.noise=0
        self.timestamp=np.int64(0x0)
        self.rx_flg=0
        
        self.ts_timestamp=np.uint64(0x0)
        self.ts_pre=self.ts_timestamp
        self.ts_cnt=0x0
        self.ts_flg=0
        
        self.ts2_timestamp=np.uint64(0x0)
        self.ts2_pre=self.ts2_timestamp
        self.ts2_cnt=0x0
        self.ts2_flg=0
        self.ts2t_timestamp=np.uint64(0x0)
        self.ts2t_cnt=0x0
        self.ts2t_flg=0
        
        self.ts3_timestamp=np.uint64(0x0)
        self.ts3_pre=self.ts3_timestamp
        self.ts3_cnt=0x0
        self.ts3_flg=0
        
        self.ts4_timestamp=np.uint64(0x0)
        self.ts4_pre=self.ts4_timestamp
        self.ts4_cnt=0x0
        self.ts4_flg=0

    def run(self,raw,data_format=3):
        start=0
        end=len(raw)
        ret=np.empty(0,dtype=hit_idx_dtype)
        while start<end: ##TODO make chunk work
            tmpend=min(end,start+self.n)
            ( err,hit_dat,r_i,
              self.col,self.row,self.le,self.te,self.noise,self.timestamp,self.rx_flg,
              self.ts_timestamp,self.ts_pre,self.ts_flg,self.ts_cnt,
              self.ts2_timestamp,self.ts2_pre,self.ts2_flg,self.ts2_cnt,
              self.ts2t_timestamp,self.ts2t_flg,self.ts2t_cnt,
              self.ts3_timestamp,self.ts3_pre,self.ts3_flg,self.ts3_cnt,
              self.ts4_timestamp,self.ts4_pre,self.ts4_flg,self.ts4_cnt
              ) = _interpret_idx(
              raw[start:tmpend],self.buf,start,
              self.col,self.row,self.le,self.te,self.noise,self.timestamp,self.rx_flg,
              self.ts_timestamp,self.ts_pre,self.ts_flg,self.ts_cnt,
              self.ts2_timestamp,self.ts2_pre,self.ts2_flg,self.ts2_cnt,
              self.ts2t_timestamp,self.ts2t_flg,self.ts2t_cnt,
              self.ts3_timestamp,self.ts3_pre,self.ts3_flg,self.ts3_cnt,
              self.ts4_timestamp,self.ts4_pre,self.ts4_flg,self.ts4_cnt,data_format)
            if err!=0:
               self.reset()
            ret=np.append(ret,hit_dat)
            start=start+r_i+1
        return ret
        
    def mk_list(self,raw,delete_noise=True):
        dat=self.run(raw)
        if delete_noise==True:
            dat=without_noise(dat)
        return dat

    def mk_img(self,raw,delete_noise=True):
        dat=self.run(raw)
        return list2img(dat,delete_noise=True)
    
    def mk_cnt(self,raw,delete_noise=True):
        dat=self.run(raw)
        return list2cnt(dat,delete_noise=True)
        
def raw2list(raw,delete_noise=True):
    inter=InterRaw()
    dat=inter.run(raw)
    if delete_noise==True:
        dat=without_noise(dat)
    return dat

def raw2img(raw,delete_noise=True):
    inter=InterRaw()
    return list2img(inter.run(raw),noise=noise)

def raw2cnt(raw,delete_noise=True):
    inter=InterRaw()
    return list2cnt(inter.run(raw),delete_noise=delete_noise)

if __name__ == "__main__":
    import sys
    fin=sys.argv[1]
    fout=fin[:-8]+"_hit.h5"
    interpret_idx_h5(fin,fout,debug=3)
    # debug 
    # 
    # 0x20 correct tlu_timestamp based on timestamp2 0x00 based on timestamp
    print fout
               
