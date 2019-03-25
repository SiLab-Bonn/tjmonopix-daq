import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml

import monopix_daq.scans.injection_scan as injection_scan
INJCAP=2.7E-15

local_configuration={"phaselist": np.arange(0,17,1),
                     "injlist": np.arange(0.05,3,0.05),
                     'pix': [18,25],
                     "with_mon": False
}

class TwScan(injection_scan.InjectionScan):
    scan_id = "tw_scan"
    
    def scan(self,**kwargs):
        kwargs["pix"]=kwargs.pop("pix",local_configuration['pix'])

        kwargs["thlist"]=None
        kwargs["injlist"]=kwargs.pop("injlist",local_configuration['injlist'])
        kwargs["phaselist"]=kwargs.pop("phaselist",local_configuration['phaselist'])

        kwargs["n_mask_pix"]=kwargs.pop("n_mask_pix",23)
        kwargs["with_mon"]=kwargs.pop("with_mon",local_configuration['with_mon'])
        super(TwScan, self).scan(**kwargs)

    def analyze(self):
        fraw = self.output_filename +'.h5'
        fhit=fraw[:-7]+'hit.h5'
        fev=fraw[:-7]+'ev.h5'
        
        ##interpret and event_build
        import monopix_daq.analysis.interpreter_idx as interpreter_idx
        interpreter_idx.interpret_idx_h5(fraw,fhit,debug=0x8+0x3)
        self.logger.info('interpreted %s'%(fhit))
        import monopix_daq.analysis.event_builder_inj as event_builder_inj
        event_builder_inj.build_inj_h5(fhit,fraw,fev,n=10000000)
        self.logger.info('timestamp assigned %s'%(fev))
        
        ##analyze
        import monopix_daq.analysis.analyze_hits as analyze_hits
        ana=analyze_hits.AnalyzeHits(fev,fraw)
        ana.init_hist_ev()
        ana.init_injected()
        ana.init_cnts()
        ana.init_le_hist()
        ana.init_le_cnts()
        ana.run()

        import monopix_daq.analysis.analyze_cnts as analyze_cnts
        ana=analyze_cnts.AnalyzeCnts(fev,fraw)
        ana.init_scurve_fit()
        ana.run()

        import monopix_daq.analysis.analyze_le_cnts as analyze_le_cnts
        ana=analyze_le_cnts.AnalyzeLECnts(fev,fraw)
        ana.init_scurve_fit()
        ana.init_best_phase()
        ana.run()

    def plot(self):
        fev=self.output_filename[:-4]+'ev.h5'
        fraw = self.output_filename +'.h5'
        fpdf = self.output_filename +'.pdf'

        import monopix_daq.analysis.plotting_base as plotting_base
        with plotting_base.PlottingBase(fpdf,save_png=True) as plotting:
            with tb.open_file(fraw) as f:
                firmware=yaml.load(f.root.meta_data.attrs.firmware)
                inj_n=firmware["inj"]["REPEAT"]
                ## DAC Configuration page
                dat=yaml.load(f.root.meta_data.attrs.dac_status)
                dat.update(yaml.load(f.root.meta_data.attrs.power_status))
                dat["inj_n"]=inj_n
                dat["inj_delay"]=firmware["inj"]["DELAY"]
                dat["inj_width"]=firmware["inj"]["WIDTH"]
                plotting.table_1value(dat,page_title="Chip configuration")

                dat=yaml.load(f.root.meta_data.attrs.pixel_conf)
            with tb.open_file(fev) as f:
                ## Pixel configuration page
                injected=f.root.Injected[:]
                plotting.plot_2d_pixel_4(
                    [injected,injected,dat["MONITOR_EN"],dat["TRIM_EN"]],
                    page_title="Pixel configuration",
                    title=["Preamp","Inj","Mon","TDAC"], 
                    z_min=[0,0,0,0], z_max=[1,1,1,15])
                
                ## S-curve
                res,le,ph=get_scurve(f.root,inj_n)
                plotting.plot_scurve(res[0:2],
                            dat_title=["all mu=%.4f sigma=%.4f"%(res[0]["mu"],res[0]["sigma"]),
                            "25ns mu=%.4f sigma=%.4f"%(res[1]["mu"],res[1]["sigma"]),
                            "",""],
                            title="Phase=%d LE=%d"%(ph,le),
                            y_max=inj_n*1.5,
                            y_min=0,
                            reverse=False)

                ## Phase plots
                phaselist=f.root.LEHist.attrs.phaselist
                for i in range(len(f.root.LEHist)/4+1):
                    hist=["","","",""]
                    title=["","","",""]
                    for ii in range(4):
                       if i+ii<len(f.root.LEHist):
                           hist[ii]=f.root.LEHist[i+ii]["LE"][:,int(le)-10:int(le)+10]
                           title[ii]="inj%.4f"%f.root.LEHist[i+ii]["inj"]
                       else:
                           hist[ii]=np.zeros([1,1])
                    plotting.plot_2d_hist_4(hist,
                           title=title,
                           bins=[phaselist,np.arange(le-10,le+10)],
                           z_max=["maximum","maximum","maximum","maximum"]
                           )
                           
def get_scurve(fhit_root,inj_n):
    injlist=fhit_root.LEScurveFit.attrs.injlist
    phaselist=fhit_root.LEHist.attrs.phaselist
    end=len(fhit_root.LEHist)
    start=0
    tmpend=min(end,start+end)
    hist=fhit_root.LEHist[:]
    
    uni=np.unique(hist[['scan_param_id','col','row','th']])
    if len(uni)!=1:
        return None
    for u in uni:
        dat=hist[hist[['scan_param_id','col','row','th']]==u]
        a=np.argmax(dat["inj"])

        flg=0
        le0=np.argmax(dat[a]["LE"][0,:])
        #print le0
        for ph_i,ph in enumerate(phaselist[1:]):
            le=np.argmax(dat[a]["LE"][ph_i+1,:])
            #print ph_i,ph,le,dat[a]["LE"][ph_i+1,le]
            if le0!=le:
                flg=1
            if flg==1 and dat[a]["LE"][ph_i+1,le]==inj_n:
                break
        #print "get_scurve()============ le",le,"phase_idx",ph_i+1,"phase",ph

        cnt_1bin=np.zeros(len(injlist))
        cnt=np.zeros(len(injlist))
        for d in dat:
            a=np.argmin(np.abs(injlist-d["inj"]))
            if np.abs(injlist-d["inj"])[a] > 1E-4:
                print "ERROR injlist is wrong"
            cnt_1bin[a]=d["LE"][ph_i+1,le]
            cnt[a]=np.sum(d["LE"][ph_i+1,:])
            injlist[a]=d["inj"]

    res=[{},{}]
    u0=np.empty(1,dtype=uni.dtype.descr+[("tof","u1"),("phase",'<i4')])
    u0[0]["tof"]=le
    u0[0]["phase"]=ph
    for c in uni.dtype.names:
        u0[0][c]=u[c]
    hist=fhit_root.LEScurveFit[:]
    hist=hist[np.bitwise_and(hist["phase"]==ph, hist["tof"]==le)]
    if len(hist)!=1:
        print "tw_scan.get_scurve() 1error!!"
    res[0]["x"]=injlist
    res[0]["y"]=cnt_1bin
    res[0]["A"]=hist[0]["A"]
    res[0]["mu"]=hist[0]["mu"]
    res[0]["sigma"]=hist[0]["sigma"]
    
    ### debug
    #dat=fhit_root.LECnts[:]
    #dat=dat[np.bitwise_and(dat["phase"]==ph, dat["tof"]==le)]
    #res[2]["x"]=dat["inj"]
    #res[2]["y"]=dat["cnt"]
    #res[2]["A"]=hist[0]["A"]
    #res[2]["mu"]=hist[0]["mu"]
    #res[2]["sigma"]=hist[0]["sigma"]
    

    hist=fhit_root.ScurveFit[:]
    u0=np.empty(1,dtype=uni.dtype.descr+[("phase",'<i4')])
    u0[0]["phase"]=ph
    for c in uni.dtype.names:
        u0[0][c]=u[c]
    hist=hist[hist['phase']==ph]
    if len(hist)!=1:
        print "tw_scan.get_scurve() 2error!!"
    res[1]["x"]=injlist
    res[1]["y"]=cnt
    res[1]["A"]=hist[0]["A"]
    res[1]["mu"]=hist[0]["mu"]
    res[1]["sigma"]=hist[0]["sigma"]
    
    ### debug
    #dat=fhit_root.Cnts[:]
    #dat=dat[dat["phase"]==ph]
    #res[3]["x"]=dat["inj"]
    #res[3]["y"]=dat["cnt"]
    #res[3]["A"]=hist[0]["A"]
    #res[3]["mu"]=hist[0]["mu"]
    #res[3]["sigma"]=hist[0]["sigma"]
    
    return res,le,ph

if __name__ == "__main__":
    from monopix_daq import monopix
    import argparse
    
    parser = argparse.ArgumentParser(usage="tw_scan.py xxx_scan",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument('-t',"--th", type=float, default=None)
    parser.add_argument('-in',"--inj_n", type=float, default=100)
    #parser.add_argument('-ib',"--inj_start", type=float, 
    #     default=local_configuration["injlist"][0])
    #parser.add_argument('-ie',"--inj_stop", type=float, 
    #     default=local_configuration["injlist"][-1])
    #parser.add_argument('-is',"--inj_step", type=float, 
    #     default=local_configuration["injlist"][1]-local_configuration["injlist"][0])
    args=parser.parse_args()
    #local_configuration["injlist"]=np.arange(args.inj_start,args.inj_stop,args.inj_step)

    m=monopix.Monopix()
    scan = TwScan(m,online_monitor_addr="tcp://127.0.0.1:6500")
    
    if args.config_file is not None:
        m.load_config(args.config_file)
    if args.th is not None:
        m.set_th(args.th)
    if args.inj_n is not None:
        m.set_inj_all(inj_n=args.inj_n)
    m.set_th(0.82)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
