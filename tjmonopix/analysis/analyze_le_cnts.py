import os, sys, time
import numpy as np
import tables as tb
import yaml
import logging
import matplotlib.pyplot as plt

import tjmonopix.analysis.utils as utils
#import tjmonopix.analysis.analysis_utils as utils
COL_SIZE = 112 
ROW_SIZE = 224


class AnalyzeLECnts():
    def __init__(self,fev,fraw):
        self.fdat=fev
        self.fraw=fraw
        self.res={}
        with tb.open_file(self.fraw) as f:
            param=f.root.scan_parameters[:]
            for i in range(0,len(f.root.kwargs),2):
                if f.root.kwargs[i]=="injlist":
                    self.injlist=np.sort(np.unique(yaml.load(f.root.kwargs[i+1])))
                elif f.root.kwargs[i]=="phaselist":
                    self.phaselist=np.sort(np.unique(yaml.load(f.root.kwargs[i+1])))
            self.inj_n=yaml.load(f.root.meta_data.attrs.status)["inj"]["REPEAT"]

    def run(self,n=10000000):
        with tb.open_file(self.fdat,"a") as f:
            end=len(f.root.LECnts)
            print "AnalyzeLECnts: n of LECounts",end
            start=0
            t0=time.time()
            hit_total=0
            while start<end:
                tmpend=min(end,start+n)
                hits=f.root.LECnts[start:tmpend]
                if tmpend!=end:
                    last=hits[-1]
                    for i,h in enumerate(hits[::-1][1:]):
                        if h["scan_param_id"]!= last["scan_param_id"]:
                            hits=hits[:len(hits)-i-1]
                            break
                    if last["scan_param_id"]==h["scan_param_id"]:
                        print "ERROR data chunck is too small increase n"
                self.analyze(hits,f.root)
                start=start+len(hits)
        self.save()
        
    def analyze(self, dat, fdat_root):
        if "scurve_fit" in self.res.keys():
            self.run_scurve_fit(dat,fdat_root)
        if "scurve" in self.res.keys():
            self.run_scurve(dat,fdat_root)
            
    def save(self):
        #print "========= save() start"
        #print "========= save() keys",self.res.keys()
        if "scurve_fit" in self.res.keys():
            self.save_scurve_fit()
        if "scurve" in self.res.keys():
            self.save_scurve()
        if "best_phase" in self.res.keys():
            self.save_best_phase()

    ######## best phase
    def init_best_phase(self):
        with tb.open_file(self.fdat,"a") as f:
            dat_dtype=f.root.LEHist.dtype.descr
            for c in ["LE","inj"]:
                for i in range(len(dat_dtype)):
                    if dat_dtype[i][0]==c:
                        dat_dtype.pop(i)
                        break
            self.res["best_phase"]=list(np.empty(0,dtype=dat_dtype).dtype.names)
            buf=np.empty(0,dtype=dat_dtype+[("LE","u1"),("phase","<i4"),("inj","<f4")])
            try:
                f.remove_node(f.root,"BestPhase")
            except:
                pass
            table=f.create_table(f.root,name="BestPhase",
                               description=buf.dtype,
                               title='BestPhase')
    def save_best_phase(self):
        #print "========= save_best_phase() start"
        with tb.open_file(self.fdat,"a") as f:
            end=len(f.root.LEHist)
            start=0
            tmpend=min(end,start+end)
            hist=f.root.LEHist[:]
            #print "========= save_best_phase() n of LEHist =%d"%len(hist)
            
            #print "========= save_best_phase()",self.res["best_phase"]
            #print "========= save_best_phase() hist.dtype",hist.dtype
            uni=np.unique(hist[self.res["best_phase"]])
            buf=np.empty(len(uni),dtype=f.root.BestPhase.dtype)
            print "save_best_phase() number of LEhist", len(uni)
            for u_i,u in enumerate(uni):
                dat=hist[hist[self.res["best_phase"]]==u]
                a=np.argmax(dat["inj"])
                buf[u_i]["inj"]=dat["inj"][a]
                flg=0
                le0=np.argmax(dat[a]["LE"][0,:])
                #print le0
                for ph_i,ph in enumerate(self.phaselist[1:]):
                    le=np.argmax(dat[a]["LE"][ph_i+1,:])
                    #print "get_le",le,"cnt",dat[a]["LE"][ph_i+1,le],
                    #print "phase_idx",ph_i+1,"phase",ph
                    if le0!=le:
                        flg=1
                    if flg==1 and dat[a]["LE"][ph_i+1,le]>=self.inj_n:
                        print "========= save_best_phase() [%d %d] phase=%d le=%d"%(u["col"],u["row"],ph,le)
                        break

                buf[u_i]["LE"]=le
                buf[u_i]["phase"]=ph
                for c in self.res["best_phase"]:
                    buf[u_i][c]=u[c]
            f.root.BestPhase.append(buf)
            f.root.BestPhase.flush()
        return le,ph
        
######### superimposed s-curve
    def init_scurve(self):
        with tb.open_file(self.fdat,"a") as f:
            dat_dtype=f.root.LECnts.dtype.descr
            for c in ["cnt", 'col', 'row', 'scan_param_id','inj']:
                for i in range(len(dat_dtype)):
                    if dat_dtype[i][0]==c:
                        dat_dtype.pop(i)
                        break
            #print list(np.empty(0,dtype=dat_dtype).dtype.names)
            self.res["scurve"]=list(np.empty(0,dtype=dat_dtype).dtype.names)
            
            s=self.injlist[1]-self.injlist[0]
            xbins=np.arange(np.min(self.injlist)-0.5*s,np.max(self.injlist)+0.5*s,s)
            ybins=np.arange(0.5,self.inj_n+9.5,1.0)
            
            dat_dtype=dat_dtype+[("scurve","<i4",(len(xbins)-1,len(ybins)-1))]
            buf=np.zeros(1,dtype=dat_dtype)
            try:
                f.remove_node(f.root,"LEScurve")
            except:
                pass
            table=f.create_table(f.root,name="LEScurve",
                               description=buf.dtype,
                               title='Superimposed scurve')
            table.attrs.xbins=yaml.dump(list(xbins))
            table.attrs.ybins=yaml.dump(list(ybins))

    def run_scurve(self,dat,fdat_root):
        xbins=yaml.load(fdat_root.LEScurve.attrs.xbins)
        ybins=yaml.load(fdat_root.LEScurve.attrs.ybins)
        uni=np.unique(dat[self.res["scurve"]])
        buf=np.zeros(len(uni),dtype=fdat_root.LEScurve.dtype)
        for u_i,u in enumerate(uni):
            tmp=dat[dat[self.res["scurve"]]==u]
            buf[u_i]["scurve"]=np.histogram2d(tmp["inj"],tmp["cnt"],bins=[xbins,ybins])[0]
            for c in self.res["scurve"]:
                buf[u_i][c]=u[c]
            fdat_root.LEScurve.append(buf)
            fdat_root.LEScurve.flush()
            
    def save_scurve(self):
        self.res["scurve"]=False

######### Threshold distribution
    def init_th_dist(self):
        self.res["th_dist"]=True
    def save_th_dist(self):
        with tb.open_file(self.fdat,"a") as f:
           dat=f.root.ScurveFit[:]
           dat_type=f.root.LEScurveFit.dtype.descr
           for c in ["col","row","scan_param_id","mu","mu_err","A","A_err","sigma","sigma_err"]:
                for i in range(len(dat_type)):
                    if dat_type[i][0]==c:
                        dat_type.pop(i)
                        break
           
           p_names=[]
           for d in dat_type:
              p_names.append(d[0])

           uni=np.unique(dat[p_names])
           dat_type=np.empty(0,dtype=dat_type+[("mu","<f4",(COL_SIZE,ROW_SIZE))]).dtype
           try:
               f.root.remove_node("ThDist")
           except:
               pass
           table=f.create_table(f.root,name="ThDist",
                               description=dat_type,
                               title='Threshold distribution')
           buf=np.zeros(1,dtype=dat_type)
           for u in uni:
             tmp=dat[dat[p_names]==u]
             for d in tmp:
               buf[0]["mu"][d["col"],d["row"]]=d["mu"]
             for p in p_names:
               buf[0][p]=u[p]
             table.append(buf)
             table.flush()
    def init_noise_dist(self):
        self.res["noise_dist"]=True
    def save_noise_dist(self):
        with tb.open_file(self.fdat,"a") as f:
           dat=f.root.ScurveFit[:]
           dat_type=f.root.ScurveFit.dtype.descr
           for c in ["col","row","scan_param_id","mu","mu_err","A","A_err","sigma","sigma_err"]:
                for i in range(len(dat_type)):
                    if dat_type[i][0]==c:
                        break
                dat_type.pop(i)
           
           p_names=[]
           for d in dat_type:
              p_names.append(d[0])

           uni=np.unique(dat[p_names])
           dat_type=np.empty(0,dtype=dat_type+[("sigma","<f4",(COL_SIZE,ROW_SIZE))]).dtype
           try:
               f.root.remove_node("ThDist")
           except:
               pass
           table=f.create_table(f.root,name="NoiseDist",
                               description=dat_type,
                               title='Noise distribution')
           buf=np.zeros(1,dtype=dat_type)
           for u in uni:
             tmp=dat[dat[p_names]==u]
             for d in tmp:
               buf[0]["sigma"][d["col"],d["row"]]=d["sigma"]
             for p in p_names:
               buf[0][p]=u[p]
             table.append(buf)
             table.flush()

######### s-curve fit
    def init_scurve_fit(self,x="inj"):
        with tb.open_file(self.fdat,"a") as f:
            dat_dtype=f.root.LECnts.dtype.descr
            for c in [x,"cnt"]:
              for i in range(len(dat_dtype)):
                if dat_dtype[i][0]==c:
                    dat_dtype.pop(i)
                    break
            self.res["scurve_fit"]=list(np.empty(0,dtype=dat_dtype).dtype.names)

            dat_dtype = dat_dtype + [('n','<i4'),('A', "<f4"),('A_err', "<f4"),
                        ('mu', "<f4"),('mu_err', "<f4"),('sigma',"<f4"),('sigma_err', "<f4")]
            try:
                f.remove_node(f.root,"LEScurveFit")
            except:
                pass
            t=f.create_table(f.root,name="LEScurveFit",
                           description=np.empty(0,dtype=dat_dtype).dtype,
                           title='scurve_fit %s'%x)
            if x=="inj":
                t.attrs.injlist=self.injlist
            elif x=="th":
                t.attrs.thlist=self.thlist

    def run_scurve_fit(self,dat,fdat_root):
        print("### Fit scurves ###")
        uni=np.unique(dat[self.res["scurve_fit"]])
        buf=np.empty(len(uni),dtype=fdat_root.LEScurveFit.dtype)
        for u_i,u in enumerate(uni):
            args=np.argwhere(dat[self.res["scurve_fit"]]==u)
            if len(args)==0:
                fit=[float("nan")]*6
            else:
                inj=dat["inj"][args]
                cnt=dat["cnt"][args]
                inj=np.append(self.injlist[self.injlist<np.min(inj)],inj)
                cnt=np.append(np.zeros(len(inj)-len(cnt)),cnt)
                if len(inj)<3:
                     print "strange data", u_i,uni.dtype.names,u,inj,cnt
                     fit=[float("nan")]*6
                else:
                     fit = utils.fit_scurve(inj, cnt, A=self.inj_n, reverse=False) ##TODO go back to better one
            for c in self.res["scurve_fit"]:
                buf[u_i][c]=u[c]
            buf[u_i]["n"]=len(args)
            buf[u_i]["A"]=fit[0]
            buf[u_i]["A_err"]=fit[3]
            buf[u_i]["mu"]=fit[1]
            buf[u_i]["mu_err"]=fit[4]
            buf[u_i]["sigma"]=fit[2]
            buf[u_i]["sigma_err"]=fit[5]
        fdat_root.LEScurveFit.append(buf)
        fdat_root.LEScurveFit.flush()

    def save_scurve_fit(self):
        self.res["scurve_fit"]=False
        
