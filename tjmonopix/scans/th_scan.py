import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml

import tjmonopix.scans.injection_scan as injection_scan
INJCAP=2.7E-15

local_configuration={"injlist": np.arange(0.005,0.6,0.005),
                     'pix': [18,25]
}

class ThScan(injection_scan.InjectionScan):
    scan_id = "th_scan"
    
    def scan(self,**kwargs):
        """
        pix: list of pixels 
        injlist: array of injection voltage to scan (inj_high-inj_low)
        n_mask_pix: number of pixels which injected at once.
        Other configuration must be configured before scan.start()
        """
        kwargs["pix"]=kwargs.pop("pix",local_configuration['pix'])

        kwargs["injlist"]=kwargs.pop("injlist",local_configuration['injlist'])
        kwargs["phaselist"]=None

        kwargs["n_mask_pix"]=kwargs.pop("n_mask_pix",23)
        kwargs["with_mon"]=kwargs.pop("with_mon",False)
        super(ThScan, self).scan(**kwargs)

    def analyze(self):
        fraw = self.output_filename +'.h5'
        fhit=fraw[:-7]+'hit.h5'
        fev=fraw[:-7]+'ev.h5'

        super(ThScan, self).analyze()

        import tjmonopix.analysis.analyze_cnts as analyze_cnts
        ana=analyze_cnts.AnalyzeCnts(fev,fraw)
        ana.init_scurve()
        ana.init_scurve_fit()
        ana.init_th_dist()
        ana.init_noise_dist()
        ana.run()
        

    def plot(self):
        fev=self.output_filename[:-4]+'ev.h5'
        fraw = self.output_filename +'.h5'
        fpdf = self.output_filename +'.pdf'

        import tjmonopix.analysis.plotting_base as plotting_base
        with plotting_base.PlottingBase(fpdf,save_png=True) as plotting:
            with tb.open_file(fraw) as f:
                firmware=yaml.safe_load(f.root.meta_data.attrs.firmware)
                inj_n=firmware["inj"]["REPEAT"]
                ## DAC Configuration page
                dat=yaml.safe_load(f.root.meta_data.attrs.dac_status)
                dat.update(yaml.safe_load(f.root.meta_data.attrs.power_status))
                dat["inj_n"]=inj_n
                dat["inj_delay"]=firmware["inj"]["DELAY"]
                dat["inj_width"]=firmware["inj"]["WIDTH"]
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

                    
                ## Scurve
                for i in range(len(f.root.Scurve)):
                  dat=f.root.Scurve[i]["scurve"]
                  xbins=yaml.safe_load(f.root.Scurve.attrs.xbins)
                  ybins=yaml.safe_load(f.root.Scurve.attrs.ybins)
                  plotting.plot_2d_hist(dat,
                       bins=[xbins,ybins],
                       title=f.root.Scurve.title,
                       z_axis_title="",z_min=1,z_max="maximum",z_scale="log")

                ## Threshold distribution
                for i in range(len(f.root.ThDist)):
                    dat=f.root.ThDist[i]
                    plotting.plot_2d_pixel_hist(dat["mu"],title=f.root.ThDist.title,
                                                z_min=0.0,
                                                z_max=0.5)
                    plotting.plot_1d_pixel_hists([dat["mu"]],mask=injected,
                                             top_axis_factor=INJCAP/1.602E-19,
                                             top_axis_title="Threshold [e]",
                                             x_axis_title="Testpulse injection [V]",
                                             title=f.root.ThDist.title)
                ## Threshold distribution
                for i in range(len(f.root.NoiseDist)):
                    dat=f.root.NoiseDist[i]
                    plotting.plot_2d_pixel_hist(dat["sigma"],title=f.root.NoiseDist.title,
                                                z_min=0.0)
                    plotting.plot_1d_pixel_hists([dat["sigma"]],mask=injected,
                                             top_axis_factor=INJCAP/1.602E-19,
                                             top_axis_title="Noise [e]",
                                             x_axis_title="S-curve Sigma [V]",
                                             title=f.root.ThDist.title)

if __name__ == "__main__":
    from tjmonopix import tjmonopix
    import argparse
    
    parser = argparse.ArgumentParser(usage="analog_scan.py xxx_scan",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument('-t',"--th", type=float, default=None)

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

    m=tjmonopix.TJMonoPix()
    scan = ThScan(m,online_monitor_addr="tcp://127.0.0.1:6500")
    
    if args.config_file is not None:
        m.load_config(args.config_file)
    if args.th is not None:
        m.set_th(args.th)

    en=np.copy(m.dut.PIXEL_CONF["PREAMP_EN"][:,:])
    local_configuration["pix"]=list(np.argwhere(en))    

    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
