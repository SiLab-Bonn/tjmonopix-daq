#!/usr/bin/env python
import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml
import matplotlib.pyplot as plt

import monopix_daq.scan_base as scan_base
import monopix_daq.analysis.interpreter as interpreter

local_configuration={"exp_time": 1.0,
                     "cnt_th": 1,
                     "n_pix": 512,
                     "th_start": 0.85,
                     "th_stop": 0.5,
                     "th_step":[-0.01,-0.002,-0.0005]
}

class EnTune(scan_base.ScanBase):
    scan_id = "en_tune"
    def scan(self,**kwargs):
        th=kwargs.pop("th_start",0.85)
        th_stop=kwargs.pop("th_stop",0.5)
        th_step=kwargs.pop("th_step",[-0.01,-0.002,-0.0005])
        cnt_th=kwargs.pop("cnt_th",1)
        exp_time=kwargs.pop("exp_time",1.0)
        n_pix=kwargs.pop("n_pix",512)

        ####################
        ## create a table for scan_params
        param_dtype=[("scan_param_id","<i4"),("th","<f2")]
        description=np.zeros((1,),dtype=param_dtype).dtype
        self.scan_param_table = self.h5_file.create_table(self.h5_file.root,
                      name='scan_parameters', title='scan_parameters',
                      description=description, filters=self.filter_tables)
        
        scan_param_id=0
        en_org=np.copy(self.dut.PIXEL_CONF["PREAMP_EN"][:,:])
        th_step_i=0
        fig,ax=plt.subplots(2,2)
        plt.ion()
        while th > th_stop or th_step_i==len(th_step): 
            self.monopix.set_th(th)
            en=np.copy(self.dut.PIXEL_CONF["PREAMP_EN"][:,:])
            self.monopix.set_monoread()

            with self.readout(scan_param_id=scan_param_id,fill_buffer=True,clear_buffer=True,
                              readout_interval=0.005):
                time.sleep(exp_time)
                self.monopix.stop_monoread()
            scan_param_id=scan_param_id+1
            
            ##########################
            ### get data from buffer
            buf = self.fifo_readout.data
            if len(buf)==0:
                self.logger.info("th_tune:th=%.4f pix=%d, no data"%(th,len(np.argwhere(en))))
                th=th+th_step[th_step_i]
                continue
            elif th_step_i!=(len(th_step)-1):
                self.logger.info("th_tune:th=%.4f step=%.4f "%(th,th_step[th_step_i]))
                th=th-th_step[th_step_i]
                th_step_i=th_step_i+1
                continue
            data = np.concatenate([buf.popleft()[0] for i in range(len(buf))])
            img=interpreter.raw2img(data)
            
            ##########################
            ## showing status
            self.logger.info("th_tune:==== %.4f===data %d=====cnt %d======en %d====="%(
                th,len(data),np.sum(img), len(en[en])))
            ax[0,0].cla()
            ax[0,0].imshow(np.transpose(img),vmax=min(np.max(img),100),origin="low",aspect="auto")
            ax[0,0].set_title("th=%.4f"%th)
            ax[1,0].cla()
            ax[1,0].imshow(np.transpose(self.monopix.get_tdac_memory()),vmax=16,vmin=0,origin="low",aspect="auto")
            ax[0,1].cla()
            ax[0,1].imshow(np.transpose(en),vmax=1,vmin=0,origin="low",aspect="auto")
            ax[0,1].set_title("en=%d"%len(np.where(en)))
            fig.tight_layout()
            fig.savefig(os.path.join(self.working_dir,"last_scan.png"),format="png")
            plt.pause(0.003)
            
            ##########################
            ### find noisy
            arg=np.argwhere(img>cnt_th)
            s="th_tune:noisy pixel %d"%len(arg)
            for a in arg:
                s="[%d,%d]=%d"%(a[0],a[1],img[a[0],a[1]]),
            self.logger.info(s)
            self.logger.info("th_tune:th=%.4f en=%d"%(th,len(np.argwhere(en))))
            en=np.bitwise_and(en,img<=cnt_th)
            if n_pix >= len(np.argwhere(en)):
                self.monopix.set_th(th-th_step[th_step_i])
                break
            else:
                th=th+th_step[th_step_i]
                self.monopix.set_preamp_en(en)
        self.logger.info("th_tune:th=%.4f en=%d"%(
                         self.dut.SET_VALUE["TH"],
                         len(np.argwhere(self.dut.PIXEL_CONF["PREAMP_EN"][:,:]))
                         ))
    def analyze(self):
        pass
    def plot(self):
        fraw = self.output_filename +'.h5'
        fpdf = self.output_filename +'.pdf'

        import monopix_daq.analysis.plotting_base as plotting_base
        with plotting_base.PlottingBase(fpdf,save_png=True) as plotting:
            with tb.open_file(fraw) as f:
                firmware=yaml.safe_load(f.root.meta_data.attrs.firmware)
                ## DAC Configuration page
                dat=yaml.safe_load(f.root.meta_data.attrs.dac_status)
                dat.update(yaml.safe_load(f.root.meta_data.attrs.power_status))
                plotting.table_1value(dat,page_title="Chip configuration")
                
                ## Pixel Configuration page (before tuning)
                dat=yaml.safe_load(f.root.meta_data.attrs.pixel_conf_before)
                plotting.plot_2d_pixel_4(
                    [dat["PREAMP_EN"],dat["INJECT_EN"],dat["MONITOR_EN"],dat["TRIM_EN"]],
                    page_title="Pixel configuration before tuninig",
                    title=["Preamp","Inj","Mon","TDAC"], 
                    z_min=[0,0,0,0], z_max=[1,1,1,15])

                ## Preamp Configuration
                dat=yaml.safe_load(f.root.meta_data.attrs.pixel_conf)
                plotting.plot_2d_pixel_hist(np.array(dat["PREAMP_EN"]),
                        title="Enabled preamp",
                        z_max=1)

if __name__ == "__main__":
    from monopix_daq import monopix
    import argparse

    parser = argparse.ArgumentParser(usage="analog_scan.py xxx_scan",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument('-e',"--exp_time", type=float, default=local_configuration["exp_time"])
    parser.add_argument('-n',"--n_pix", type=float, default=local_configuration["n_pix"])
    parser.add_argument('-t',"--th_start", type=float, default=local_configuration["th_start"])
    parser.add_argument("-f","--flavor", type=str, default="16:20")
    parser.add_argument("--tdac", type=int, default=None)
    parser.add_argument("--LSBdacL", type=int, default=None)
    args=parser.parse_args()
    local_configuration["exp_time"]=args.exp_time
    local_configuration["n_pix"]=args.n_pix
    local_configuration["th_start"]=args.th_start
    
    m=monopix.Monopix()

    if args.config_file is not None:
        m.load_config(args.config_file) 
    if args.flavor is not None:
        m.set_preamp_en("none")
        if args.flavor=="all":
          collist=np.arange(0,36,1)
        else:
          tmp=args.flavor.split(":")
          collist=np.arange(int(tmp[0]),int(tmp[1]),1)
        en=np.copy(m.dut.PIXEL_CONF["PREAMP_EN"][:,:])
        en[c,:]=True
        m.set_preamp_en(en)
    if args.tdac is not None:
        m.set_tdac(args.tdac)
    if args.LSBdacL is not None:
        m.set_global(LSBdacL=args.LSBdacL)
    
    scan = EnTune(m,online_monitor_addr="tcp://127.0.0.1:6500")
    scan.start(**local_configuration)
    #scan.analyze()
    scan.plot()