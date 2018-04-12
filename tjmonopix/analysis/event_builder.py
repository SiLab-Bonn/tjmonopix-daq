import sys,os,time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tables
import numpy as np
import yaml
from numba import njit

COL=112
ROW=224


fixed_tlu_type=[("tlu_number","i2"),("tlu_timestamp","u8"),("ts_timestamp","u8")]

token_dtype=[('event_number','<i8'),('token_timestamp','<u8'),('min_tot','<u1'),('min_te','<u1'),
          ('tlu_timestamp','<u8'),('tlu_number','<u4'),('diff','<i8'),('ts_timestamp','<u8')]

corr_dtype=[('event_number','<i8'),('token_timestamp','<u8'),('min_tot','<u1'),('flg','<u1'),('diff','<i8'),
          ('event_timestamp','<u8'),('trigger_number','<u4')]
          
hit_dtype=[('event_number','<i8'),('token_timestamp','<u8'),('flg','<u1'),('diff','<i8'),
          ('col','<u1'),('row','<u1'),('le','<u1'),('te','<u1'),('charge','<u1'),('frame','<i8'),
          ('event_timestamp','<u8'),('trigger_number','<u4')]

    
def get_te_offset(dat,debug=None):
     hist=np.histogram((dat["timestamp"] >> np.uint64(4)) - np.uint64(dat["te"])  & np.uint64(0x3FF),
                       bins=np.arange(0,0x3F+1,1),)
     print hist[0]
     print hist[1]
     offset=np.int64(hist[1][np.argmax(hist[0])])
     if debug!=None:
         plt.clf()
         plt.step(hist[1][:-1],hist[0])
         plt.xlabel("TOKEN-TE")
         plt.title("offset %d"%offset)
         plt.yscale("log")
         plt.savefig(debug, dpi=300)
     return offset

def check_tlu_data(tlu_e,ts_e,tlu_offset):
    if (tlu_e["timestamp"]-ts_e["timestamp"]) & np.uint64(0x7FFFF) > np.uint64(tlu_offset-16) \
       and (tlu_e["timestamp"]-ts_e["timestamp"]) & np.uint64(0x7FFFF) < np.uint64(tlu_offset+16*2) :
            #print "tlu and tlu_ts is synchronized"
            return 0
    else:
        #print "tlu and tlu_ts is not synchronized"
        return -1

@njit    
def _sync_tlu_timestamp(tlu,ts,data_out,tlu_offset):
    tlu_i=0
    ts_i=0
    i=0
    while tlu_i < len(tlu) and ts_i < len(ts) and i < len(data_out):
        #print tlu_i, hex(tlu[tlu_i]["timestamp"]), ts_i, hex(ts[ts_i]["timestamp"]), 
        #print hex((tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"]) & np.uint64(0x7FFFF)),
        if (tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"] - np.uint64(tlu_offset+16*2)) & np.uint64(0x7FFFF)  <= 0x40000:
            #ts_i =ts_i+1
            #print "next ts"
            #print "tlu and tlu_ts is not synchronized, synchronize data manually",tlu_i,ts_i
            return 1, i, tlu_i, ts_i, data_out
        elif ((tlu[tlu_i]["timestamp"] - ts[ts_i]["timestamp"]- np.uint64(tlu_offset-16)) & np.uint64(0x7FFFF) ) > 0x40000:
            #tlu_i=tlu_i+1
            #print "next tlu"
            #print "tlu and tlu_ts is not synchronized, synchronize data manually",tlu_i,ts_i
            return 2, i, tlu_i, ts_i, data_out
        else:
            data_out[i]["tlu_number"]=tlu[tlu_i]["cnt"] 
            data_out[i]["tlu_timestamp"]=tlu[tlu_i]["timestamp"]
            data_out[i]["ts_timestamp"]=ts[ts_i]["timestamp"]
            ts_i=ts_i+1
            tlu_i=tlu_i+1
            i=i+1
    return 0, i, tlu_i, ts_i, data_out

@njit
def _corr(token,fixed_tlu,offset):
    tlu_idx=0
    for t_i,t in enumerate(token):
        diff=np.int64(0x7FFFFFFFFFFFFFFF)
        mintot_e=np.int64(t['min_tot'])
        token_e=np.int64(t['token_timestamp'])
        for l_i,l_e in enumerate(fixed_tlu[tlu_idx:]):
            tlu_e=np.int64(l_e['ts_timestamp']>>np.uint64(4))    
            if np.abs(diff)>=np.abs(token_e-mintot_e-tlu_e+offset):
                diff = token_e-mintot_e-tlu_e
                token[t_i]['diff']=diff
                token[t_i]['tlu_timestamp']=l_e['ts_timestamp'] >>np.uint64(4)
                token[t_i]['tlu_number']=l_e['tlu_number']
                token[t_i]['event_number']=np.int64(tlu_idx)+np.int64(l_i)
            #if t_i%1000000 < 100:
            #    print "diff=%d"%(token_e-tlu_e-mintot_e), "new_diff=%d"%diff
            else: #if token_e < tlu_e:
                tlu_idx=max(0,tlu_idx+l_i-1)
                break
    return token

@njit
def _build(corr,dat,buf):
    c_i=0
    buf_i=0
    m_i=0
    while m_i<len(dat) and c_i<len(corr):
        if (dat[m_i]["timestamp"]>>np.uint64(4)) <corr[c_i]["token_timestamp"]:
            m_i=m_i+1
        elif (dat[m_i]["timestamp"]>>np.uint64(4))==corr[c_i]["token_timestamp"]:
            buf[buf_i]['event_number']=corr[c_i]["event_number"]
            buf[buf_i]['trigger_number']=corr[c_i]["trigger_number"]
            buf[buf_i]['event_timestamp']=corr[c_i]["event_timestamp"]
            buf[buf_i]['diff']=corr[c_i]["diff"]
            buf[buf_i]['token_timestamp']=dat[m_i]["timestamp"]>>np.uint64(4)
            buf[buf_i]['col']=dat[m_i]["col"]
            buf[buf_i]['row']=dat[m_i]["row"]
            buf[buf_i]['le']=dat[m_i]["le"]
            buf[buf_i]['te']=dat[m_i]["te"]
            buf[buf_i]['flg']=np.uint8(dat[m_i]["cnt"])
            buf_i=buf_i+1
            m_i=m_i+1
        else:
            c_i=c_i+1
    return buf[:buf_i],m_i,c_i

def build_h5(fraw,fhit,fout,debug=0x0):
     
    with tables.open_file(fraw) as f_i:
        conf_s=f_i.root.meta_data.get_attr("status")         
    conf=yaml.load(conf_s)
    WAIT_CYCLES=conf['tlu']["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]
    tlu_offset=(WAIT_CYCLES+1) * 16
    
    ########################
    ####### read data
    print "event_builder.build_h5(), Input File:",fhit
    with tables.open_file(fhit) as f:
        dat=f.root.Hits[:]
    print "event_builder.build_h5() - Size of data: Total=%d"%len(dat),"TLU=%d"%len(dat[dat["col"]==0xFF]),"TS=%d"%len(dat[dat["col"]==0xFC]),
    print "HIT_OR=%d"%len(dat[dat["col"]==0xFD]),"TJ-Monopix=%d"%len(dat[dat["col"]<COL])
    
    with tables.open_file(fout, "w") as f_o:

        ########################
        ####### check TJ-Monopix timestamp                
        tmp_arg=np.argwhere(dat["col"]<COL)[:,0]
        tmp=dat[tmp_arg]["timestamp"]
        arg=np.argwhere(tmp[1:] < tmp[:-1])[:,0]
        if len(arg)==0:
            print 'event_builder.build_h5() - Check MONO timestamp: increase only True'
        elif len(arg) == 1:
            print 'Cutting data before (unique) TLU module reset at index: ', tmp_arg[arg[0]+1]
            #print tmp_arg[arg[0]+1]
            #for i in range(45,55):
            #    print i,(tmp[1:] < tmp[:-1])[i],tmp[1:][i], tmp[:-1][i]
            #for ii,i in enumerate(np.arange(tmp_arg[arg[0]+1]-5,tmp_arg[arg[0]+1]+5)):
            #    print ii+tmp_arg[arg[0]+1]-5, dat[i]
            dat=dat[tmp_arg[arg[0]+1]:]
        else:
            print "ERROR! Data must be ordered by timestamp. Fix the data!!!"
            for i, a in enumerate(arg):
                #print "before:%d(0x%x)"%(dat[tmp_arg]["timestamp"][a[0]-1],dat[tmp_arg]["timestamp"][a[0]-1]),
                print i, "idx=%d:"%a[0], "%d(0x%x)"%(dat[tmp_arg]["timestamp"][a[0]],dat[tmp_arg]["timestamp"][a[0]]),
                print "next:%d(0x%x)"%(dat[tmp_arg]["timestamp"][a[0]+1],dat[tmp_arg]["timestamp"][a[0]+1]),
                print "diff:0x%x"%(dat[tmp_arg]["timestamp"][a[0]+1] - dat[tmp_arg]["timestamp"][a[0]])
                if i ==10:
                    print "more...",len(arg)
                    break

        ########################
        ####### check ts data
        ts=dat[dat["col"]==0xFC]
        arg=np.argwhere(ts["timestamp"][1:] < ts["timestamp"][:-1])
        print 'event_builder.build_h5() - Check ts precise timestamp: increase only',len(arg)==0
        for i, a in enumerate(arg):
            print "ERROR! TLU must be ordered by timestamp. Fix the data!!!"
            print i, "idx%d="%a[0], "%d(0x%x)"%(ts["timestamp"][a[0]],ts["timestamp"][a[0]]),
            print "next= %d(0x%x)"%(ts["timestamp"][a[0]+1],ts["timestamp"][a[0]+1]),
            print "diff=0x%x"%(ts["timestamp"][a+1] - ts["timestamp"][a])
            if i ==10:
                print "more...",len(arg)
                break
        if debug & 0x1 == 0x1:
            print "event_builder.build_h5() - Check ts"
            plt.clf()
            print "event_builder.build_h5() - Check ts max=0x%x"%(np.max(ts["timestamp"]))
            print "event_builder.build_h5() - Check ts min=0x%x"%(np.min(ts["timestamp"]))
            print "event_builder.build_h5() - Check ts range=%.2fsec"%((np.max(ts["timestamp"])-np.min(ts["timestamp"]))/640.E6)
            plt.plot(ts["timestamp"],"b")
            plt.xlabel('Number of events')
            plt.ylabel('Time(640 MHz Clock)')
            plt.title("TLU timestamp 64bits")
            plt.savefig(fout[:-3]+"_ts.png", dpi=300)          

        ########################
        ####### check tlu number

        tlu=dat[dat["col"]==0xFF]
        arg=np.argwhere(tlu["cnt"][1:] - tlu["cnt"][:-1] & 0x7FFF !=1)
        print 'event_builder.build_h5() - Check TLU number: increased by 1 only',len(arg)==0
        for i,a in enumerate(arg):
            print i, "idx=%d"%a[0], "%d(ts=%d)"%(tlu["cnt"][a[0]],tlu["timestamp"][a[0]]),
            print "%d(ts=%d)"%(tlu["cnt"][a[0]+1],tlu["timestamp"][a[0]+1]),
            print "diff=0x%x"%(tlu["cnt"][a+1] - tlu["cnt"][a]),
            print "diff_ts=0x%x"%(tlu["timestamp"][a+1] - tlu["timestamp"][a])
            if i ==10:
                print "more...",len(a)
                break

        ########################
        ####### fix tlu timestamp
        if check_tlu_data(tlu[0],ts[0], tlu_offset) == 0:
                print ("00") 
                pass
        elif check_tlu_data(tlu[0],ts[1], tlu_offset) == 0:
                print ("01") 
                ts=ts[1:]
        elif check_tlu_data(tlu[1],ts[0], tlu_offset) == 0:
                print ("10") 
                tlu=tlu[1:]
        else:
            print "ERROR: Synchronize tlu and tlu_ts manually"
        
        fixed_tlu =np.empty(len(tlu),dtype=fixed_tlu_type)
        print "tlu before sync=%d ts before sync=%d"%(len(tlu),len(ts))
        e, i, tlu_i, ts_i, fixed_tlu = _sync_tlu_timestamp(tlu,ts,fixed_tlu, tlu_offset)
        print "sync=%d tlu_i after sync=%d ts_i after sync=%d"%(i, tlu_i, ts_i)

        ########################
        ####### check tlu timestamp
        arg=np.argwhere(fixed_tlu["ts_timestamp"][1:] < fixed_tlu["ts_timestamp"][:-1])[:,0]
        print "event_builder.build_h5() - Check ts timestamp (After sync): increase only",len(arg)==0
        if len(arg)!=0:
            print "ERROR! TS not ordered by timestamp after sync. Fix the data!!!"
            for i, a in enumerate(arg):
                print i, "idx=%d"%a[0], "%d(0x%x)"%(fixed_tlu["ts_timestamp"][a[0]],fixed_tlu["ts_timestamp"][a[0]]),
                print "%d(0x%x)"%(fixed_tlu["ts_timestamp"][a[0]+1],fixed_tlu["ts_timestamp"][a[0]+1]),
                print "diff=0x%x"%(fixed_tlu["ts_timestamp"][a[0]+1] - fixed_tlu["ts_timestamp"][a[0]])
                if i ==10:
                    print "more...",len(arg)
                    break
        if debug & 0x1 == 0x1:
            print "event_builder.build_h5() - Check ts-tlu sync"
            plt.clf()
            tmp = (fixed_tlu["tlu_timestamp"]-fixed_tlu["ts_timestamp"]) & np.uint64(0x7FFFF)
            print "event_builder.build_h5() check ts max=0x%x"%(np.max(tmp))
            print "event_builder.build_h5() check ts min=0x%x"%(np.min(tmp))
            print "event_builder.build_h5() check ts range=0x%x"%(np.max(tmp)-np.min(tmp))
            plt.hist(tmp,histtype="step")
            plt.xlabel("TLU_timestamp - ts_timestamp")
            plt.savefig(fout[:-3]+"_tlu_sync.png", dpi=300)   
        
        if debug & 0x04 ==0x04:
		    description=np.zeros((1,),dtype=fixed_tlu.dtype).dtype
		    fixed_tlu_table=f_o.create_table(f_o.root,name="fixed_tlu",description=description,title='fixed_tlu data')
		    fixed_tlu_table.append(fixed_tlu)
		    fixed_tlu_table.flush()

        ## Saving memory
        tlu=None  
        ts=None

        ########################
        ####### delete noise from MONOPIX
        dat=dat[np.bitwise_and(dat["col"]<COL,dat["cnt"]==0)]
        #dat=dat[dat["col"]<COL]
        arg=np.argwhere(dat["timestamp"][1:] < dat["timestamp"][:-1])[:,0]
        print 'event_builder.build_h5() - Check TJ-Monopix token timestamp: increase only',len(arg)==0
        if len(arg)!=0:
            print "ERROR! TJ-MONOPIX token must be ordered by timestamp. Fix the data!!!"
            for i, a in enumerate(arg):
                print i, "idx=%d"%a[0], "%d(0x%x)"%(dat["timestamp"][a[0]],dat["timestamp"][a[0]]),
                print "%d(0x%x)"%(dat["timestamp"][a[0]+1],dat["timestamp"][a[0]+1]),
                print "diff=0x%x"%(dat["timestamp"][a[0]+1] - dat["timestamp"][a[0]])
                if i ==10:
                    print "more...",len(arg)
                    break

        ########################
        ####### make token list
        te_offset=get_te_offset(dat,debug=fout[:-3]+'_token-te.png')   
        print "event_builder.build_h5() - te_offset=%d(0x%x)"%(te_offset,te_offset)
        tot=np.array( (dat["te"]-dat["le"]) & 0x3F,dtype=np.int64)
        uni,idx,cnt=np.unique(dat["timestamp"],return_index=True,return_counts=True)
        print "event_builder.build_h5() # of token=%d"%len(uni)
        token=np.empty(len(uni),dtype=token_dtype)
        for i,u in enumerate(uni):
            arg=np.argmin(np.abs(np.int8((u>>np.uint64(4))-dat["te"][idx[i]:idx[i]+cnt[i]]-te_offset)))
            token[i]['min_tot']= tot[idx[i]+arg]
            token[i]['min_te']= dat['te'][idx[i]+arg]
            token[i]['token_timestamp']= u >> np.uint64(4)
            dat[idx[i]:idx[i]+cnt[i]]["cnt"]=np.array(tot[idx[i]:idx[i]+cnt[i]] < token[i]['min_tot'],dtype=np.uint32)*8
            dat[idx[i]+arg]['cnt']=4
            token[i]['event_number']=i

        if debug & 0x04 ==0x04:
            description=np.zeros((1,),dtype=token_dtype).dtype
            token_table=f_o.create_table(f_o.root,name="Tokens_tmp",description=description,title='token_data')
            token_table.append(token)
            token_table.flush()

        ########################
        ####### assign tlu to token
        token=_corr(token,fixed_tlu,offset=0)
        
        if debug & 0x04 ==0x04:
            description=np.zeros((1,),dtype=token_dtype).dtype
            token_table=f_o.create_table(f_o.root,name="Tokens",description=description,title='token_data')
            token_table.append(token)
            token_table.flush()
        
        ########################
        ####### check assigned tlu timestamp  
        arg=np.argwhere(np.bitwise_and(token["tlu_timestamp"][1:] < token["tlu_timestamp"][:-1],
                                       token["token_timestamp"][1:] >= token["token_timestamp"][:-1]))
        print 'event_builder.build_h5() - TLU increase after assignment',len(arg)==0
        for i,a in enumerate(arg):
            print i, "ERROR!! idx=%d"%a[0], 
            print "tlu=%d(ts=%d,token_ts=%d)"%(token["tlu_number"][a[0]],token["tlu_timestamp"][a[0]],token["token_timestamp"][a[0]]),
            print "next_tlu=%d(ts=%d,token_ts=%d)"%(token["tlu_number"][a[0]+1],token["tlu_timestamp"][a[0]+1],token["token_timestamp"][a[0]+1])
            print "diff=0x%x"%(token["tlu_number"][a+1] - token["tlu_number"][a]),
            print "diff_ts=0x%x"%(token["tlu_timestamp"][a+1] - token["tlu_timestamp"][a])
            print "diff_token_ts=0x%x"%(token["token_timestamp"][a+1] - token["token_timestamp"][a])
            if i ==10:
                print "more...",len(arg)
                break
            
        ########################
        ####### calc peak of diff
        bins=np.arange(-100E2, 100E2, 1)
        hist=np.histogram(token["diff"][:],bins=bins);
        peak=hist[1][np.argmax(hist[0])]
        print "event_builder.build_h5() diff peak",peak
        
        if debug & 0x1 == 0x1:
            plt.clf()
            plt.step(hist[1][:-1],hist[0])
            plt.xlabel("LE-TLU")
            plt.title("peak %d"%peak)
            plt.yscale("log")
            plt.savefig(fout[:-3]+"_le-tlu.png", dpi=300)
            
        ########################
        ####### select only nearest token (1tlu vs 1token)
        uni,idx,cnt=np.unique(token["tlu_timestamp"],return_index=True,return_counts=True)
        corr=np.empty(len(uni),dtype=corr_dtype)
        for i,u in enumerate(uni):
            arg=np.argmin(np.abs(token[idx[i]:idx[i]+cnt[i]]['diff']-peak))
            corr[i]["token_timestamp"]= token[idx[i]+arg]["token_timestamp"]
            corr[i]["min_tot"]= token[idx[i]+arg]["min_tot"]
            corr[i]["event_timestamp"]= token[idx[i]+arg]["tlu_timestamp"]
            corr[i]["event_number"]= token[idx[i]+arg]["event_number"]
            corr[i]["trigger_number"]= token[idx[i]+arg]["tlu_number"]
            corr[i]["diff"]= token[idx[i]+arg]["diff"]
            token[i]['token_timestamp']=u
        print "event_builder.build_h5() #_of_corr=%d"%len(corr),"#_of_token=%d"%len(token),"%f%%"%(100.0*len(corr)/len(token))

        if debug & 0x04 == 0x04:
            description=np.zeros((1,),dtype=corr_dtype).dtype
            corr_table=f_o.create_table(f_o.root,name="Corr",description=description,title='corr_data')
            corr_table.append(corr)
            corr_table.flush()

        ########################
        ####### assign tlu to hits
        buf_out=np.empty(len(dat),dtype=hit_dtype)
        buf_out,m_i,c_i=_build(corr,dat,buf_out)
        
        buf_out["charge"]= np.uint16(buf_out["te"]-buf_out["le"] & 0x3F)
#        buf_out["frame"] =np.int64(buf_out["token_timestamp"]) - np.int64(buf_out["event_timestamp"])\
#                - np.int64(buf_out["charge"]) \
#                - np.int64((buf_out["token_timestamp"]-np.uint64(buf_out["te"])+np.uint64(0xF0)-te_offset) & np.uint64(0x3F))\
#                + np.int64(0x30) - peak + np.int64(0x20)
        buf_out["frame"] =np.int64(buf_out["token_timestamp"]) - np.int64(buf_out["event_timestamp"])\
                - np.int64(buf_out["charge"]) \
                - np.int64((buf_out["token_timestamp"]-np.uint64(buf_out["te"])+np.uint64(0x3F-3)-te_offset) & np.uint64(0x3F))\
                + np.int64(0x3F-3) - peak + np.int64(0x40) 
                
        if debug & 0x1 == 0x1:
            plt.clf()
            bins=np.arange(0,1000,1)
            plt.hist(buf_out["frame"],bins,histtype="step")
            plt.yscale("log")
            plt.xlim(0,256)
            plt.xlabel("Frame [40MHz clk]")
            plt.title("Frame assignment")
            plt.savefig(fout[:-3]+"_tlutohits.png", dpi=300)
        
        description=np.zeros((1,),dtype=hit_dtype).dtype
        hit_table=f_o.create_table(f_o.root,name="Hits",description=description,title='hit_data')
        hit_table.append(buf_out)
        hit_table.flush()
        hit_table.attrs.te_offset=te_offset
        hit_table.attrs.diff_peak=peak
        
if __name__ == "__main__":
    import sys

    fraw=sys.argv[1]

    fhit=fraw[:-3]+"_hit.h5"
    fout=fraw[:-3]+"_ev.h5"
    build_h5(fraw,fhit,fout,debug=0x1)



