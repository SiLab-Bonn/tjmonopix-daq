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

@njit
def _sync_tlu_timestamp(tlu,ts,data_out,higher_lim=470,lower_lim=500): ##477-495
    tlu_i=0
    ts_i=0
    i=0
    while tlu_i<len(tlu) and ts_i<len(ts):
        ts_v=np.int64( ts[ts_i]['timestamp'] & np.uint64(0x7FFFF))
        tlu_v=np.int64( tlu[tlu_i]['timestamp'] & np.uint64(0x7FFFF))
        #print "ts",ts_i,ts_v,"tlu",tlu_i,tlu_v, "diff",tlu_v-ts_v
        if tlu_v-ts_v < lower_lim :
            tlu_i=tlu_i+1
            #print "next tlu"
        elif tlu_v-ts_v > higher_lim:
            ts_i=ts_i+1
            #print "next ts"
        else:
            data_out[i]["event_number"]=i
            data_out[i]["trigger_number"]=np.uint32(tlu[tlu_i]["cnt"]) 
            data_out[i]["tlu_timestamp"]=tlu[tlu_i]["timestamp"]
            data_out[i]["ts_timestamp"]=ts[ts_i]["timestamp"]
            ts_i=ts_i+1
            tlu_i=tlu_i+1
            i=i+1
    return 0, tlu_i, ts_i, data_out[:i]

@njit
def _build_event_token(dat,tmp,buf,ev,flg_mode):
    i=0
    ts=dat[0]['timestamp']
    while i<len(dat):
        for d_i,d in enumerate(dat[i:]):
            buf[i+d_i]['tot']= (d['te']-d['le']) & 0x3F
            buf[i+d_i]['col']= d['col']
            buf[i+d_i]['row']= d['row']
            buf[i+d_i]['flg']= d['cnt']
            buf[i+d_i]['token_timestamp']=d['timestamp']
            buf[i+d_i]['event_number']=ev
            if ts!=d['timestamp']:
                ts=d['timestamp']
                break
            elif d_i== len(dat[i:])-1:
                d_i=d_i+1
        #print "---",i,i+d_i,dat[i:i+d_i]["timestamp"],dat[i:i+d_i]["cnt"]
        if dat[i]['cnt']==0:
            ev=ev+1
            arg=np.argmin(np.abs(tmp[i:i+d_i]))
            buf[i+arg]['flg']=buf[i+arg]['flg']+0x2
            le_ts=dat["timestamp"][i+arg]-np.uint64(buf['tot'][i+arg]<<4)
            le0=np.int16(0x40)-np.int16(dat[i+arg]["le"])
        #print ev,arg,tmp[i:i+d_i],buf['tot'][i+arg],le_ts
        for d_ii in range(d_i):
            buf[i+d_ii]['le_timestamp']=le_ts
            if dat[i+d_ii]['cnt']==1 and flg_mode==0x80:
                buf[i+d_ii]['frame']=0x80
            else:
                buf[i+d_ii]['frame']=np.int16(dat[i+d_ii]["le"])+le0

        #print buf[i:i+d_i]["timestamp"],buf[i:i+d_i]['event_number'],buf[i:i+d_i]['frame']
        i=i+d_i
    return 0, buf

@njit
def _sync_tlu_token(buf,tlu):
    tlu_i=0
    i=0
    diff=0x7FFFFFFFFFFFFFFF
    while tlu_i<len(tlu) and i<len(buf):
        buf_v=np.int64( buf[i]['le_timestamp'])
        tlu_v=np.int64( tlu[tlu_i]['ts_timestamp'])
        #print "ts",token_i,buf_v,"tlu",tlu_i,tlu_v, "diff",tlu_v-buf_v
        if np.abs(tlu_v-buf_v) < diff:
            min_i=tlu_i
            diff=np.abs(tlu_v-buf_v)
            tlu_i=tlu_i+1
        else:
            buf[i]["event_number"]=tlu[min_i]["event_number"] 
            buf[i]["timestamp"]=tlu[min_i]["ts_timestamp"]
            i=i+1
            if np.int64(buf[i]['le_timestamp'])!=buf_v:
                diff=0x7FFFFFFFFFFFFFFF
    return 0, tlu_i, buf[:i]

def build_h5(fraw,fhit,fout,mode="frame128",debug=0x0):
    t0=time.time()
        
    with tables.open_file(fraw) as f_i:
        try:
            conf_s=f_i.root.meta_data.get_attr("status")
        except:
            conf_s=f_i.root.meta_data.get_attr("status_before")     
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
        ####### sync tlu and ts_tlu
        fixed_tlu=np.empty(len(tlu),dtype=[
            ("event_number","<i8"),("trigger_number","<u4"),
            ("tlu_timestamp","<u8"),("ts_timestamp","<u8")])
        print "after sync tlu=%d ts=%d"%(len(tlu),len(ts))
        e, tlu_i, ts_i, fixed_tlu = _sync_tlu_timestamp(tlu,ts,fixed_tlu)
        print "sync=%d tlu_i after sync=%d ts_i after sync=%d"%(len(fixed_tlu),tlu_i, ts_i)

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
        ####### check token timestamp
        dat=dat[dat["col"]<COL]
        if mode=="del":
            dat=dat[dat['cnt']==0]
            print "without flg1=%d"%len(dat)
            mode=0
        elif mode=="frame128":
            mode=0x80
        else:
            mode=0
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
        ####### make event by token
        tmp=( (np.int64(dat["timestamp"])>>4 )- np.int64(dat['te']) ) & 0x3F
        hist=np.histogram(tmp,bins=np.arange(0,0x41))
        te_offset=hist[1][np.argmax(hist[0])]
        tmp=tmp-te_offset
        print "event_builder_tlu.build_h5() %.3fs te_offset=%d"%(time.time()-t0,te_offset)
        hit_dtype=[('event_number','<i8'),('timestamp','<u8'),
                   ('token_timestamp','<u8'),('le_timestamp','<u8'),
                   ('frame','<u1'), ('col','<u1'),
                   ('row','<u1'),('tot','<u1'),('flg','<u1')]
        buf=None
        buf=np.empty(len(dat),dtype=hit_dtype)
        e, buf=_build_event_token(dat,tmp,buf,0,mode)
        print "event_builder.build_h5() calculation done %.3fs"%(time.time()-t0)

        ## Saving memory
        tmp=None
        dat=None
        
        ########################
        ####### assign tlu to token
        e,tlu_i,buf=_sync_tlu_token(buf,fixed_tlu)
        hit_table=f_o.create_table(f_o.root,name="Hits",description=buf.dtype,title='hit_data')
        hit_table.append(buf)
        hit_table.flush()
        hit_table.attrs.te_offset=te_offset

if __name__ == "__main__":
    import sys

    fraw=sys.argv[1]

    fhit=fraw[:-3]+"_hit.h5"
    fout=fraw[:-3]+"_ev.h5"
    build_h5(fraw,fhit,fout,mode="frame128",debug=0x1)



