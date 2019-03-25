import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml

import monopix_daq.scans.injection_scan as injection_scan
INJCAP=2.7E-15

local_configuration={"phaselist": np.arange(0,17,1),
                     'pix': [18,25],
                     "with_mon": False
}

class InjTimeScan(injection_scan.InjectionScan):
    scan_id = "inj_time_scan"
    
    def scan(self,**kwargs):
        kwargs["pix"]=kwargs.pop("pix",local_configuration['pix'])

        kwargs["thlist"]=None
        kwargs["injlist"]=None
        kwargs["phaselist"]=kwargs.pop("phaselist",local_configuration['phaselist'])

        kwargs["n_mask_pix"]=kwargs.pop("n_mask_pix",23)
        kwargs["with_mon"]=kwargs.pop("with_mon",local_configuration['with_mon'])
        super(InjTimeScan, self).scan(**kwargs)

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
        ana.init_apply_ts_inj_window()
        ana.init_delete_noise()
        ana.init_hist_ev()
        ana.init_injected()
        ana.init_cnts()
        ana.init_le_hist()
        ana.init_le_cnts()
        ana.run()
        
        import monopix_daq.analysis.analyze_le_cnts as analyze_le_cnts
        ana=analyze_le_cnts.AnalyzeLECnts(fev,fraw)
        ana.init_best_phase()
        ana.init_best_phase()
        ana.run()
        
        with tb.open_file(fev) as f:
            dat=f.root.BestPhase[:]
        return dat

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
                
                ## Phase plots
                phaselist=f.root.LEHist.attrs.phaselist
                le=f.root.BestPhase[0]["LE"]
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
