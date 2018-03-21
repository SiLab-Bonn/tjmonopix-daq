import sys,os,time

import tables
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import yaml
from numba import njit

token_dtype=[('event_number','<i8'),('token_timestamp','<u8'),('min_tot','<u1'),('min_te','<u1'),
          ('tlu_timestamp','<u8'),('tlu','<u4'),('diff','<i8')]
corr_dtype=[('event_number','<i8'),('token_timestamp','<u8'),('min_tot','<u1'),('flg','<u1'),('diff','<i8'),
          ('event_timestamp','<u8'),('trigger_number','<u4')]
hit_dtype=[('event_number','<i8'),('token_timestamp','<u8'),('flg','<u1'),('diff','<i8'),
          ('col','<u1'),('row','<u1'),('le','<u1'),('te','<u1'),('charge','<u1'),('frame','<i8'),
          ('event_timestamp','<u8'),('trigger_number','<u4')]
@njit
def _corr(token,tlu,offset):
    tlu_idx=0
    for t_i,t in enumerate(token):
        diff=np.int64(0x7FFFFFFFFFFFFFFF)
        mintot_e=np.int64(t['min_tot'])
        token_e=np.int64(t['token_timestamp'])
        for l_i,l_e in enumerate(tlu[tlu_idx:]):
            tlu_e=np.int64(l_e['timestamp'])
            
            #if t_i%1000000 < 100: 
            #    print t_i, l_i, "pre_diff=%d"%diff,tlu_e,token_e,mintot_e,           
            if np.abs(diff)>=np.abs(token_e-mintot_e-tlu_e+offset):
                diff = token_e-mintot_e-tlu_e
                token[t_i]['diff']=diff
                token[t_i]['tlu_timestamp']=l_e['timestamp']
                token[t_i]['tlu']=l_e['cnt']
                token[t_i]['event_number']=np.int64(tlu_idx)+np.int64(l_i)
            #if t_i%1000000 < 100:
            #    print "diff=%d"%(token_e-tlu_e-mintot_e), "new_diff=%d"%diff
            else: #if token_e < tlu_e:
                tlu_idx=max(0,tlu_idx+l_i-1)
                break
    return token

def _build(corr,dat,buf):
    c_i=0
    buf_i=0
    m_i=0
    while m_i<len(dat) and c_i<len(corr):
        if dat[m_i]["timestamp"]<corr[c_i]["token_timestamp"]:
            m_i=m_i+1
        elif dat[m_i]["timestamp"]==corr[c_i]["token_timestamp"]:
            buf[buf_i]['event_number']=corr[c_i]["event_number"]
            buf[buf_i]['trigger_number']=corr[c_i]["trigger_number"]
            buf[buf_i]['event_timestamp']=corr[c_i]["event_timestamp"]
            buf[buf_i]['diff']=corr[c_i]["diff"]
            buf[buf_i]['token_timestamp']=dat[m_i]["timestamp"]
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

@njit
def _fix_timestamp(dat,overflow=np.uint64(0x8000),decrease=True):
    pre_timestamp=dat[0]
    mask=overflow-np.uint64(1)
    not_mask=~mask
    half_mask = mask >> np.uint64(int(decrease))
    #print hex(mask),hex(not_mask),hex(half_mask)
    for d_i,d in enumerate(dat):
        d= (mask  & d) | (not_mask  & pre_timestamp)
        #print d_i, hex(d), hex(pre_timestamp),hex(d +half_mask), d > pre_timestamp + half_mask,d +half_mask < pre_timestamp,
        if d > pre_timestamp + half_mask and decrease:
            #print "sub"
            d=d - overflow
        elif d +half_mask < pre_timestamp and decrease:
            #print "add"
            d=d + overflow
        elif pre_timestamp > d and not decrease:
            d=d+overflow
        else:
            #print "keep"
            pass
        dat[d_i]=d
        pre_timestamp=d
    return dat

def get_te_offset(dat,debug=None,field="timestamp"):
     hist=np.histogram((dat[field]-np.uint64(dat["te"])) & 0xFF, bins=np.arange(0,0x101))
     offset=np.int64(hist[1][np.argmax(hist[0])])
     if debug!=None:
         plt.clf()
         plt.step(hist[1][:-1],hist[0])
         plt.xlabel("TOKEN-TE")
         plt.title("offset %d"%offset)
         plt.yscale("log")
         plt.savefig(debug)
     return offset

def build_h5(fin,fout,debug=0x0):
    ########################
    ####### read data
    print "event_builder.build_h5() fin:",fin
    with tables.open_file(fin) as f:
        dat=f.root.Hits[:]
    print "event_builder.build_h5() # of data:total=%d"%len(dat),"TLU=%d"%len(dat[dat["col"]==0xFF]),"TS1=%d"%len(dat[dat["col"]==0xFE]),
    print "TS2=%d"%len(dat[dat["col"]==0xFD]),"MONO=%d"%len(dat[dat["col"]<36])
    
    with tables.open_file(fout, "w") as f_o:
        ########################
        ####### delete data
        description=np.zeros((1,),dtype=dat.dtype)
        del_table=f_o.create_table(f_o.root,name="Del_dat",description=description,title='inter_data')
        
        arg=np.argwhere(np.bitwise_or(dat["col"]==0xFE,dat["col"]==0xFD))
        if len(arg)!=0:
            print "event_builder.build_h5() delete data before 2nd mframe idx=%d"%arg[1]
            print "event_builder.build_h5() delete data after last mframe idx=%d"%(arg[-1]),"n_of_del_data=%d"%(len(dat)-arg[-1])
            print "event_builder.build_h5() 1st=%x,%x"%(dat["timestamp"][arg[0]-1],dat["timestamp"][arg[0]]),
            print "2nd=%x,%x"%(dat["timestamp"][arg[1]-1],dat["timestamp"][arg[1]])
            del_table.append(dat[:arg[1][0]])
            del_table.append(dat[arg[-1][0]:])
            del_table.flush()
            dat=dat[arg[1][0]:arg[-1][0]]

        ########################
        ####### check monopix timestamp
        tmp_arg=np.argwhere(dat["col"]<36)
        tmp=dat[tmp_arg]["timestamp"]
        arg=np.argwhere(tmp[1:] < tmp[:-1])
        if len(arg)==0:
            print 'event_builder.build_h5() check MONO timestamp: increase only True'
        elif len(arg)==1:
            print "event_builder.build_h5() check MONO timestamp: decrease once"
            idx=tmp_arg[arg[0][0]]
            idx1=tmp_arg[arg[0][0]+1]
            print "idx=%d"%idx, "%d(0x%x)"%(dat["timestamp"][idx],dat["timestamp"][idx]),
            print "%d(0x%x)"%(dat["timestamp"][idx1],dat["timestamp"][idx1]),
            print "diff=0x%x"%(dat["timestamp"][idx1] - dat["timestamp"][idx])
            print "event_builder.build_h5() cut data before tlu decrease",idx1
            del_table.append(dat[:idx1])
            del_table.flush()         
            dat=dat[idx1:]
            print "event_builder.build_h5() after cut #_data=%d"%len(dat)
        else:
            print "ERROR! Data must be ordered by timestamp. Fix the data!!!!!"
            for i, a in enumerate(arg):
                print i, "idx=%d"%a[0], "%d(0x%x)"%(dat["timestamp"][a[0]],dat["timestamp"][a[0]]),
                print "%d(0x%x)"%(dat["timestamp"][a[0]+1],dat["timestamp"][a[0]+1]),
                print "diff=0x%x"%(dat["timestamp"][a[0]+1] - dat["timestamp"][a[0]])
                if i ==10:
                    print "more...",len(a)
                    break

        if debug & 0x08 ==0x80:
            ##or np.any(np.uint64(dat["timestamp"][1:] - dat["timestamp"][:-1]) & np.uint64(0x8000) != 0):
            print "event_builder.build_h5() fix timestamp"
            dat["timestamp"][:]=_fix_timestamp(dat["timestamp"],overflow=np.uint64(0x8000),decrease=True)

        ########################
        ####### check tlu timestamp
        tlu=dat[dat["col"]==0xFF]
        arg=np.argwhere(tlu["timestamp"][1:] < tlu["timestamp"][:-1])
        print 'event_builder.build_h5() check TLU timestamp: increase only',len(arg)==0
        for i, a in enumerate(arg):
            print "ERROR! TLU must be ordered by timestamp. Fix the data!!!!!"
            print i, "idx%d="%a[0], "%d(0x%x)"%(tlu["timestamp"][a[0]],tlu["timestamp"][a[0]]),
            print "next= %d(0x%x)"%(tlu["timestamp"][a[0]+1],tlu["timestamp"][a[0]+1]),
            print "diff=0x%x"%(tlu["timestamp"][a+1] - tlu["timestamp"][a])
            if i ==10:
                print "more...",len(arg)
                break
        if np.any(tlu["timestamp"][1:] < tlu["timestamp"][:-1]) and debug & 0x10 ==0x00:  ##TODO some cases, this does not work
            print "event_builder.build_h5() fix timestamp of tlu"
            tmp=np.copy(dat["timestamp"])
            tmp=_fix_timestamp(tmp,overflow=np.uint64(0x8000),decrease=True)
            tlu["timestamp"]=tmp[dat["col"]==0xFF]
            arg=np.argwhere(tlu["timestamp"][1:] < tlu["timestamp"][:-1])
            print 'event_builder.build_h5() check TLU timestamp again: increase only',len(arg)==0
            for i, a in enumerate(arg):
                print "ERROR! TLU must be ordered by timestamp. Fix the data!!!!!"
                print i, "idx%d="%a[0], "%d(0x%x)"%(tlu["timestamp"][a[0]],tlu["timestamp"][a[0]]),
                print "next= %d(0x%x)"%(tlu["timestamp"][a[0]+1],tlu["timestamp"][a[0]+1]),
                print "diff=0x%x"%(tlu["timestamp"][a+1] - tlu["timestamp"][a])
                if i ==10:
                    print "more...",len(arg)
                    break
        ########################
        ####### check tlu number
        arg=np.argwhere(tlu["cnt"][1:] - tlu["cnt"][:-1] & 0x7FFF !=1)
        print 'event_builder.build_h5() check TLU number: increased by 1 only',len(arg)==0
        for i,a in enumerate(arg):
            print i, "idx=%d"%a[0], "%d(ts=%d)"%(tlu["cnt"][a[0]],tlu["timestamp"][a[0]]),
            print "%d(ts=%d)"%(tlu["cnt"][a[0]+1],tlu["timestamp"][a[0]+1]),
            print "diff=0x%x"%(tlu["cnt"][a+1] - tlu["cnt"][a]),
            print "diff_ts=0x%x"%(tlu["timestamp"][a+1] - tlu["timestamp"][a])
            if i ==10:
                print "more...",len(a)
                break

        ########################
        ####### delete noise from MONOPIX
        dat=dat[np.bitwise_and(dat["col"]<36,dat["cnt"]==0)]
        arg=np.argwhere(dat["timestamp"][1:] < dat["timestamp"][:-1])
        if len(arg)!=0:
            print "ERROR! MONOPIX token must be ordered by timestamp. Fix the data!!!!!"
            for i, a in enumerate(arg):
                print i, "idx=%d"%a[0], "%d(0x%x)"%(dat["timestamp"][a[0]],dat["timestamp"][a[0]]),
                print "%d(0x%x)"%(dat["timestamp"][a[0]+1],dat["timestamp"][a[0]+1]),
                print "diff=0x%x"%(dat["timestamp"][a[0]+1] - dat["timestamp"][a[0]])
                if i ==10:
                    print "more...",len(arg)
                    break

        ########################
        ####### make token list
        te_offset=get_te_offset(dat,debug=fout[:-3]+'.png')   
        print "event_builder.build_h5() te_offset=%d"%te_offset
        tot=np.array(dat["te"]-dat["le"],dtype=np.int64)
        uni,idx,cnt=np.unique(dat["timestamp"],return_index=True,return_counts=True)
        print "event_builder.build_h5() # of token=%d"%len(uni)
        token=np.empty(len(uni),dtype=token_dtype)
        for i,u in enumerate(uni):
            arg=np.argmin(np.abs(np.int8(u-dat["te"][idx[i]:idx[i]+cnt[i]]-te_offset)))
            token[i]['min_tot']= tot[idx[i]+arg]
            token[i]['min_te']= dat['te'][idx[i]+arg]
            token[i]['token_timestamp']=u
            dat[idx[i]:idx[i]+cnt[i]]["cnt"]=np.array(tot[idx[i]:idx[i]+cnt[i]] < token[i]['min_tot'],dtype=np.uint32)*8
            dat[idx[i]+arg]['cnt']=4
            token[i]['event_number']=i
            #if np.any(dat["timestamp"][idx[i]:idx[i]+cnt[i]]!=u):
            #    print "ERROR!!", i,u,idx[i],cnt[i],dat[idx[i]:idx[i]+cnt[i]]
            #    break 

        if debug & 0x04 ==0x04:
            description=np.zeros((1,),dtype=token_dtype).dtype
            token_table=f_o.create_table(f_o.root,name="Tokens_tmp",description=description,title='token_data')
            token_table.append(token)
            token_table.flush()
        
        #if debug & 0x04 == 0x04:
          #print "DEBUG4: t_i, token_arg, token_timestamp, tlu_timestamp, tlu, diff"
          #for t_i,t_e in enumerate(tlu[0:100]):   
          #   arg=np.argmin(np.abs(np.int64(token["token_timestamp"])-token["min_tot"]-np.int64(t_e["timestamp"])))
          #   print t_i,arg,token[arg]["token_timestamp"],"tlu",t_e["timestamp"],t_e["cnt"],
          #   print np.int64(token[arg-1:arg+2]["token_timestamp"])-token[arg-1:arg+2]["min_tot"]-np.int64(t_e["timestamp"])
          #for t_i,t_e in enumerate(token[164100:164200]):   
          #   arg=np.argmin(np.abs(np.int64(t_e["token_timestamp"])-t_e["min_tot"]-np.int64(tlu["timestamp"])))
          #   print t_i,arg,t_e["token_timestamp"],"tlu",tlu[arg]["timestamp"],tlu[arg]["cnt"],
          #   print np.int64(t_e["token_timestamp"])-t_e["min_tot"]-np.int64(tlu[arg-1:arg+2]["timestamp"])

        ########################
        ####### assign tlu to token
        token=_corr(token,tlu,offset=0)
        
        if debug & 0x04 ==0x04:
            description=np.zeros((1,),dtype=token_dtype).dtype
            token_table=f_o.create_table(f_o.root,name="Tokens",description=description,title='token_data')
            token_table.append(token)
            token_table.flush()
        
        ########################
        ####### check assigned tlu timestamp  
        arg=np.argwhere(np.bitwise_and(token["tlu_timestamp"][1:] < token["tlu_timestamp"][:-1],
                                       token["token_timestamp"][1:] >= token["token_timestamp"][:-1]))
        print 'event_builder.build_h5() TLU increase after assingment',len(arg)==0
        for i,a in enumerate(arg):
            print i, "ERROR!! idx=%d"%a[0], 
            print "tlu=%d(ts=%d,token_ts=%d)"%(token["tlu"][a[0]],token["tlu_timestamp"][a[0]],token["token_timestamp"][a[0]]),
            print "next_tlu=%d(ts=%d,token_ts=%d)"%(token["tlu"][a[0]+1],token["tlu_timestamp"][a[0]+1],token["token_timestamp"][a[0]+1])
            print "diff=0x%x"%(token["tlu"][a+1] - token["tlu"][a]),
            print "diff_ts=0x%x"%(token["tlu_timestamp"][a+1] - token["tlu_timestamp"][a])
            print "diff_token_ts=0x%x"%(token["token_timestamp"][a+1] - token["token_timestamp"][a])
            if i ==10:
                print "more...",len(arg)
                break

        ########################
        ####### calc peak of diff
        bins=np.arange(-2E4,2E4,1)
        hist=np.histogram(token["diff"][:],bins=bins);
        peak=hist[1][np.argmax(hist[0])]
        print "event_builder.build_h5() diff peak",peak
        
        if debug & 0x04 ==0x04:
            plt.clf()
            plt.step(hist[1][:-1],hist[0])
            plt.xlabel("LE-TLU")
            plt.title("peak %d"%peak)
            plt.yscale("log")
            plt.savefig(fout[:-3]+"2.png")

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
            corr[i]["trigger_number"]= token[idx[i]+arg]["tlu"]
            corr[i]["diff"]= token[idx[i]+arg]["diff"]
            token[i]['token_timestamp']=u
            #if np.any(token["tlu_timestamp"][idx[i]:idx[i]+cnt[i]]!=u):
            #    print i,u,idx[i],cnt[i],token[idx[i]:idx[i]+cnt[i]]
            #    break
        print "event_builder.build_h5() #_of_corr=%d"%len(corr),"#_of_token=%d"%len(token),"%f%%"%(100.0*len(corr)/len(token))

        if debug & 0x04 == 0x04:
            description=np.zeros((1,),dtype=corr_dtype).dtype
            corr_table=f_o.create_table(f_o.root,name="Corr",description=description,title='corr_data')
            corr_table.append(corr)
            corr_table.flush()

        ########################
        ####### assign tlu to hits
        buf=np.empty(len(dat),dtype=hit_dtype)
        buf_out,m_i,c_i=_build(corr,dat,buf)

        buf["charge"]= np.uint16(buf["te"]-buf["le"] & 0xFF)
        buf["frame"] =np.int64(buf["token_timestamp"]) - np.int64(buf["event_timestamp"])\
                - np.int64(buf["charge"]) \
                - np.int64((buf["token_timestamp"]-np.uint64(buf["te"])+np.uint64(0xF0)-te_offset) & np.uint64(0xFF))\
                + np.int64(0xF0) - peak + np.int64(0x80)

        description=np.zeros((1,),dtype=hit_dtype).dtype
        hit_table=f_o.create_table(f_o.root,name="Hits",description=description,title='hit_data')
        hit_table.append(buf_out)
        hit_table.flush()
        hit_table.attrs.te_offset=te_offset
        hit_table.attrs.diff_peak=peak
        
if __name__ == "__main__":
    import sys

    fraw=sys.argv[1]
    fref=sys.argv[2]

    fhit=fraw[:-3]+"_hit.h5"
    fout=fraw[:-3]+"_tlu.h5"
    build_h5(fhit,fout,debug=0x04)

