import os, sys, time
import numpy as np
import tables as tb
import yaml
import logging
import matplotlib.pyplot as plt

import tjmonopix.analysis.utils as utils
COL_SIZE = 112
ROW_SIZE = 224


class AnalyzeCnts():
    def __init__(self,fev,fraw):
        self.fdat=fev
        self.fraw=fraw
        self.res={}
        with tb.open_file(self.fraw) as f:
            param=f.root.scan_parameters[:]
            for i in range(0,len(f.root.kwargs),2):
                if f.root.kwargs[i]=="injlist":
                    self.injlist=np.sort(np.unique(yaml.safe_load(f.root.kwargs[i+1])))
                elif f.root.kwargs[i]=="phaselist":
                    self.phaselist=np.sort(np.unique(yaml.safe_load(f.root.kwargs[i+1])))
            self.inj_n=yaml.safe_load(f.root.meta_data.attrs.status)["inj"]["REPEAT"]
 
    def run(self,n=10000000):
        with tb.open_file(self.fdat,"a") as f:
            end=len(f.root.Cnts)
            start=0
            t0=time.time()
            hit_total=0
            while start<end:
                tmpend=min(end,start+n)
                hits=f.root.Cnts[start:tmpend]
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
        if "le_scurve_fit" in self.res.keys():
            self.run_scurve_fit(dat,fdat_root)
        if "scurve" in self.res.keys():
            self.run_scurve(dat,fdat_root)
            
    def save(self):
        if "scurve_fit" in self.res.keys():
            self.save_scurve_fit()
        if "scurve" in self.res.keys():
            self.save_scurve()
        if "th_dist" in self.res.keys():
            self.save_th_dist()
        if "noise_dist" in self.res.keys():
            self.save_noise_dist()

######### superimposed s-curve
    def init_scurve(self):
        with tb.open_file(self.fdat,"a") as f:
            dat_dtype=f.root.Cnts.dtype.descr
            for c in ["cnt", 'col', 'row', 'scan_param_id','inj']:
                for i in range(len(dat_dtype)):
                    if dat_dtype[i][0]==c:
                        dat_dtype.pop(i)
                        break
            if len(self.injlist)<2:
                 print "too short injlist",self.injlist
                 return
            s=self.injlist[1]-self.injlist[0]
            xbins=np.arange(np.min(self.injlist)-0.5*s,np.max(self.injlist)+0.5*s,s)
            ybins=np.arange(0.5,self.inj_n+9.5,1.0)
            
            self.res["scurve"]=list(np.empty(0,dtype=dat_dtype).dtype.names)
            dat_dtype=dat_dtype+[("scurve","<i4",(len(xbins)-1,len(ybins)-1))]
            buf=np.zeros(1,dtype=dat_dtype)
            try:
                f.remove_node(f.root,"Scurve")
            except:
                pass
            t=f.create_table(f.root,name="Scurve",
                               description=buf.dtype,
                               title='Superimposed scurve')
            t.attrs.xbins=list(xbins)
            t.attrs.ybins=list(ybins)

    def run_scurve(self,dat,fdat_root):
        xbins=fdat_root.Scurve.attrs.xbins
        ybins=fdat_root.Scurve.attrs.ybins
        uni=np.unique(dat[self.res["scurve"]])
        buf=np.zeros(len(uni),dtype=fdat_root.Scurve.dtype)
        for u_i,u in enumerate(uni):
            tmp=dat[dat[self.res["scurve"]]==u]
            
            buf[u_i]["scurve"]=np.histogram2d(tmp["inj"],tmp["cnt"],bins=[xbins,ybins])[0]
            for c in self.res["scurve"]:
                buf[u_i][c]=u[c]
        fdat_root.Scurve.append(buf)
        fdat_root.Scurve.flush()
            
    def save_scurve(self):
        self.res["scurve"]=False

######### Threshold distribution
    def init_th_dist(self):
        self.res["th_dist"]=True
    def save_th_dist(self):
        with tb.open_file(self.fdat,"a") as f:
           dat=f.root.ScurveFit[:]
           dat_type=f.root.ScurveFit.dtype.descr
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
               f.remove_node(f.root,"ThDist")
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
               f.remove_node(f.root,"NoiseDist")
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
            dat_dtype=f.root.Cnts.dtype.descr
            for c in [x,"cnt"]:
              for i in range(len(dat_dtype)):
                if dat_dtype[i][0]==c:
                    dat_dtype.pop(i)
                    break
            self.res["scurve_fit"]={"cols":list(np.empty(0,dtype=dat_dtype).dtype.names),
                                    "x": x}
            dat_dtype = dat_dtype + [('A', "<f4"),('A_err', "<f4"),
                        ('mu', "<f4"),('mu_err', "<f4"),('sigma',"<f4"),('sigma_err', "<f4"),
                        #("cnt","<i4",(len(self.injlist),))
                        ]
            try:
                f.remove_node(f.root,"ScurveFit")
            except:
                pass
            t=f.create_table(f.root,name="ScurveFit",
                           description=np.empty(0,dtype=dat_dtype).dtype,
                           title='scurve_fit %s'%x)
            if x=="inj":
                t.attrs.injlist=self.injlist
            elif x=="th":
                t.attrs.thlist=self.thlist

    def run_scurve_fit(self,dat,fdat_root):
        uni=np.unique(dat[self.res["scurve_fit"]["cols"]])
        buf=np.empty(len(uni),dtype=fdat_root.ScurveFit.dtype)
        for u_i,u in enumerate(uni):
            args=np.argwhere(dat[self.res["scurve_fit"]["cols"]]==u)
            if len(args)==0:
                fit=[float("nan")]*6
            else:
                x=dat[self.res["scurve_fit"]["x"]][args]
                cnt=dat["cnt"][args]
                if self.res["scurve_fit"]["x"]=="inj":
                    reverse=False
                    x=np.append(self.injlist[self.injlist<np.min(x)],x)
                elif self.res["scurve_fit"]["x"]=="th":
                    reverse=True
                    x=np.append(self.thlist[self.thlist>np.max(x)],x)
                cnt=np.append(np.zeros(len(x)-len(cnt)),cnt)
                fit=utils.fit_scurve1(x,cnt,A=self.inj_n,reverse=reverse)
                #for a in args:
                #    buf[u_i]["cnt"][np.argmin(np.abs(self.injlist-dat[a]["inj"]))]=dat["cnt"][a]
                #fit=utils.fit_scurve(self.injlist,buf[u_i]["cnt"],A=self.inj_n,reverse=False)
            for i in self.res["scurve_fit"]["cols"]:
                buf[u_i][i]=u[i]
            buf[u_i]["A"]=fit[0]
            buf[u_i]["A_err"]=fit[3]
            buf[u_i]["mu"]=fit[1]
            buf[u_i]["mu_err"]=fit[4]
            buf[u_i]["sigma"]=fit[2]
            buf[u_i]["sigma_err"]=fit[5]
        #print buf["col"]
        fdat_root.ScurveFit.append(buf)
        fdat_root.ScurveFit.flush()

    def save_scurve_fit(self):
        self.res["scurve_fit"]=False
        
