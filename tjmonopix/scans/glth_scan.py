import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml

import monopix_daq.scans.injection_scan as injection_scan
INJCAP=2.7E-15

def get_inj_high(e,inj_low=0.1,factor=1):
    print("factor of %.2f is applied"%factor)
    return factor*e*1.602E-19/INJCAP+inj_low

local_configuration={"thlist": np.arange(0.8,0.75,-0.0005),
                     'pix': [18,25]
}

class GlthScan(injection_scan.InjectionScan):
    scan_id = "glth_scan"
    def scan(self,**kwargs):
        """
           pix: [col,row]
           thlist: array of threshold voltage
           all other parameters should be configured before scan.start()
        """
        kwargs["pix"]=kwargs.pop("pix",local_configuration['pix'])

        kwargs["thlist"]=kwargs.pop("thlist",local_configuration['thlist'])
        kwargs["injlist"]=None
        kwargs["phaselist"]=None

        kwargs["n_mask_pix"]=kwargs.pop("n_mask_pix",23)
        kwargs["with_mon"]=kwargs.pop("with_mon",False)
        super(GlthScan, self).scan(**kwargs)

    def analyze(self):
        fraw = self.output_filename +'.h5'
        fhit=fraw[:-7]+'hit.h5'
        fev=fraw[:-7]+'ev.h5'
        super(GlthScan, self).analyze()
        
        import monopix_daq.analysis.analyze_cnts as analyze_cnts
        ana=analyze_cnts.AnalyzeCnts(fev,fraw)
        ana.init_scurve_fit("th")
        ana.run()
        
        with tb.open_file(fev) as f:
           dat=f.root.ScurveFit[:]
        return dat

    def plot(self,save_png=False):
        fev=self.output_filename[:-4]+'ev.h5'
        fraw = self.output_filename +'.h5'
        fpdf = self.output_filename +'.pdf'

        import monopix_daq.analysis.plotting_base as plotting_base
        with plotting_base.PlottingBase(fpdf,save_png=save_png) as plotting:
            with tb.open_file(fraw) as f:
                firmware=yaml.safe_load(f.root.meta_data.attrs.firmware)
                inj_n=firmware["inj"]["REPEAT"]
                ## DAC Configuration page
                dat=yaml.safe_load(f.root.meta_data.attrs.dac_status)
                dat.update(yaml.safe_load(f.root.meta_data.attrs.power_status))
                dat["inj_n"]=inj_n
                dat["inj_delay"]=firmware["inj"]["DELAY"]
                dat["inj_width"]=firmware["inj"]["WIDTH"]
                inj=dat["INJ_HIset"]-dat["INJ_LOset"]
                plotting.table_1value(dat,page_title="Chip configuration")

                dat=yaml.safe_load(f.root.meta_data.attrs.pixel_conf)
                
            with tb.open_file(fev) as f:
                ## Pixel configuration page
                injected=f.root.Injected[:]
                plotting.plot_2d_pixel_4(
                    [injected,injected,dat["MONITOR_EN"],dat["TRIM_EN"]],
                    page_title="Pixel configuration",
                    title=["Preamp","Inj","Mon","TDAC"], 
                    z_min=[0,0,0,0], z_max=[1,1,1,15])
            
                for p in np.argwhere(injected):
                    res,col,row=get_scurve(f.root,p[0],p[1])
                    plotting.plot_scurve(res,
                            dat_title=["mu=%.4f sigma=%.4f"%(res[0]["mu"],res[0]["sigma"])],
                            title="Pixel [%d %d], Inj=%.4f"%(col,row,inj),
                            y_min=0,
                            y_max=inj_n*1.5,
                            reverse=True)
                            
def get_scurve(fhit_root,col,row):
    x=fhit_root.ScurveFit.attrs.thlist
    dat=fhit_root.Cnts[:]
    cnt=np.zeros(len(x))
    for d in dat:
        a=np.argwhere(np.isclose(x,d["th"]))
        cnt[a[0][0]]=d["cnt"]
    res=[{}]
    dat=fhit_root.ScurveFit[:]
    dat=dat[np.bitwise_and(dat["col"]==col,dat["row"]==row)]
    if len(dat)!=1:
        print "onepix_scan.get_scurve() 1error!!"
    res[0]["x"]=x
    res[0]["y"]=cnt
    res[0]["A"]=dat[0]["A"]
    res[0]["mu"]=dat[0]["mu"]
    res[0]["sigma"]=dat[0]["sigma"]
    col=dat[0]["col"]
    row=dat[0]["row"]
    return res,col,row

if __name__ == "__main__":
    from monopix_daq import monopix
    import argparse
    
    parser = argparse.ArgumentParser(usage="analog_scan.py xxx_scan",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument('-t',"--th", type=float, default=None)
    parser.add_argument("--tdac", type=float, default=None)
    parser.add_argument('-ib',"--inj_start", type=float, 
         default=local_configuration["injlist"][0])
    parser.add_argument('-ie',"--inj_stop", type=float, 
         default=local_configuration["injlist"][-1])
    parser.add_argument('-is',"--inj_step", type=float, 
         default=local_configuration["injlist"][1]-local_configuration["injlist"][0])
    parser.add_argument("-n","--n_mask_pix",type=int,default=local_configuration["n_mask_pix"])
    args=parser.parse_args()
    local_configuration["injlist"]=np.arange(args.inj_start,args.inj_stop,args.inj_step)
    local_configuration["n_mask_pix"]=args.n_mask_pix

    m=monopix.Monopix()
    scan = ThScan(m,online_monitor_addr="tcp://127.0.0.1:6500")
    
    if args.config_file is not None:
        m.load_config(args.config_file)
    if args.th is not None:
        m.set_th(args.th)
    if args.tdac is not None:
        m.set_tdac(args.tdac)
    en=np.copy(m.dut.PIXEL_CONF["PREAMP_EN"][:,:])
    local_configuration["pix"]=np.argwhere(en)    
    
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
