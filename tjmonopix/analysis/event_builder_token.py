import numpy as np
import tables as tb
import time
import numba
import yaml

COL=112

@numba.njit
def _build_event(dat,tmp,buf,ev,flg_mode):
    i=0
    ts=dat[0]['timestamp']
    while i<len(dat):
        for d_i,d in enumerate(dat[i:]):
            buf[i+d_i]['tot']= (d['te']-d['le']) & 0x3F
            buf[i+d_i]['col']= d['col']
            buf[i+d_i]['row']= d['row']
            buf[i+d_i]['flg']= d['cnt']
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
            buf[i+d_ii]['timestamp']=le_ts
            if dat[i+d_ii]['cnt']==1 and flg_mode==0x80:
                buf[i+d_ii]['frame']=0x80
            else:
                buf[i+d_ii]['frame']=np.int16(dat[i+d_ii]["le"])+le0

        #print buf[i:i+d_i]["timestamp"],buf[i:i+d_i]['event_number'],buf[i:i+d_i]['frame']
        i=i+d_i
    return buf
     
def build_h5(fin,fout,flg_mode="del",debug=0x0): #flg_mode=del,keep,frame128

    ####### read data
    print "event_builder_token.build_h5() fin:",fin
    with tb.open_file(fin) as f:
        dat=f.root.Hits[:] ## TODO big file?
    print "event_builder.build_h5() # of data:total=%d"%len(dat),"ERR=%d"%len(dat[(dat["col"] & 0xF0)==0xE0]),
    print "TLU=%d"%len(dat[dat["col"]==0xFF]),"TS1=%d"%len(dat[dat["col"]==0xFE]),
    print "TS2=%d"%len(dat[dat["col"]==0xFD]),"TS3=%d"%len(dat[dat["col"]==0xFC]),
    dat=dat[dat["col"]<COL]
    print "TJ=%d"%len(dat)
    
    if flg_mode=="del":
        dat=dat[dat['cnt']==0]
        print "without flg1=%d"%len(dat)
        flg_mode=0
    elif flg_mode=="frame128":
        flg_mode=0x80
    else:
        flg_mode=0
 
    with tb.open_file(fout, "w") as f_o:
        ####### check monopix timestamp
        arg=np.argwhere(np.diff(dat['timestamp'])<0)
        if len(arg)==0:
            print 'event_builder.build_h5() check timestamp: increase only True'
        else:
            print "event_builder.build_h5() check MONO timestamp: decreased %d times"%len(arg)
            for a_i, a in enumerate(arg):
               print a
               if a_i>10:
                   break
            return
        ####### check flg
        arg=np.argwhere(np.bitwise_and(dat['cnt']!=1,dat['cnt']!=0))
        if len(arg)==0:
            print 'event_builder.build_h5() check flg: no strange value'
        else:
            print "event_builder.build_h5() check flg: %d strange values"%len(arg)
            for a_i, a in enumerate(arg):
               print a
               if a_i>10:
                   break
            dat=dat[np.bitwise_or(dat['cnt']==1,dat['cnt']==0)]

        t0=time.time()
        tmp=( (np.int64(dat["timestamp"])>>4 )- np.int64(dat['te']) ) & 0x3F
        hist=np.histogram(tmp,bins=np.arange(0,0x41))
        te_offset=hist[1][np.argmax(hist[0])]
        tmp=tmp-te_offset
        print "event_builder.build_h5() %.3fs te_offset=%d"%(time.time()-t0,te_offset)
        hit_dtype=[('event_number','<i8'),('timestamp','<u8'), ('frame','<u1'), ('col','<u1'),
                   ('row','<u1'),('tot','<u1'),('flg','<u1')]
        buf=None
        buf=np.empty(len(dat),dtype=hit_dtype)
        buf=_build_event(dat,tmp,buf,0,flg_mode)
        print "event_builder.build_h5() calculation done %.3fs"%(time.time()-t0)
        
        hit_table=f_o.create_table(f_o.root,name="Hits",description=buf.dtype,title='Hits')
        hit_table.append(buf)
        hit_table.flush()
        if debug==1:
            off_table=f_o.create_table(f_o.root,name="LEoffset",description=tmp.dtype,title='LE offset')
            off_table.append(buf)
            off_table.flush()
        print "event_builder.build_h5() %.3fs DONE"%(time.time()-t0)


