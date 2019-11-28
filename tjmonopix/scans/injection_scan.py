import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml

import tjmonopix.scan_base as scan_base

local_configuration={"injlist": None, #np.arange(0.1,0.6,0.05),
                     "thlist": None, # None, [0.82], np.arange(),
                     "phaselist": None, # np.arange(0,16,1),
                     "collist": [0,1,60,61],
                     "rowlist": np.arange(0,224,1),
                     "n_mask_col":1,
                     "with_mon": False
}

class InjectionScan(scan_base.ScanBase):
    scan_id = "injection_scan"
            
    def scan(self,**kwargs):
        """ List of kwargs
            pix: list of pixel
            n_mask_pix: number of pixels injected at onece
            injlist: list of inj (inj_high-inj_low)
            thlist: list of th
            phaselist: list of phase
            with_mon: get timestamp of mon (mon will be enabled)
        """
        ####################
        ## get scan params from args
        
        collist=kwargs.pop("collist")
        if isinstance(collist,int):
            collist=[collist]
        collist=np.array(collist)
        n_mask_col = min(kwargs.pop("n_mask_col"),len(collist))
        mask_n=int((len(collist)-0.5)/n_mask_col+1)

        injlist=kwargs.pop("injlist")
        inj_low=self.dut.get_vl_dacunits()
        inj_high=self.dut.get_vh_dacunits()
        if injlist is None or len(injlist)==0:
            injlist=[inj_high-inj_low]

        thlist=kwargs.pop("thlist")
        if thlist is None or len(thlist)==0:
            thlist=[self.dut.get_idb_dacunits()]

        phaselist=kwargs.pop("phaselist")
        if phaselist is None or len(phaselist)==0:
            phaselist=[self.dut["inj"].get_phase()]
            
        rowlist=kwargs.pop("rowlist")
        inj_th_phase = np.reshape(np.stack(np.meshgrid(thlist,rowlist,injlist,phaselist),axis=4),[-1,4])
        
        with_mon=kwargs.pop("with_mon")
        
        debug=kwargs.pop("debug",0)
        
        if (debug & 0x1)==1:
            print "++++++++ injlist",len(injlist),injlist
            print "++++++++ thlist",len(thlist),thlist
            print "++++++++ phaselist",len(phaselist),phaselist
            print "++++++++ collist",len(collist),collist
            print "++++++++ with_mon",with_mon

        param_dtype=[("scan_param_id","<i4"),("collist","<i4",(n_mask_col,))]

        glist=[]
        #for k,v in kwargs.iteritems():  TODO
        #    param_dtype.append((k,"<u1"))
        #    for v_e in v:
        #        glist.append({k:v_e})
        if len(glist)==0:
            glist=[None]

        ####################
        ## create a table for scan_params
        description=np.zeros((1,),dtype=param_dtype).dtype
        self.scan_param_table = self.h5_file.create_table(self.h5_file.root, 
                      name='scan_parameters', title='scan_parameters',
                      description=description, 
                      filters=tb.Filters(complib='zlib', complevel=5, fletcher32=False))
        self.kwargs.append("thlist")
        self.kwargs.append(yaml.safe_dump(inj_th_phase[:,0].tolist()))
        self.kwargs.append("injlist")
        self.kwargs.append(yaml.safe_dump(inj_th_phase[:,2].tolist()))
        self.kwargs.append("phaselist")
        self.kwargs.append(yaml.safe_dump(inj_th_phase[:,3].tolist()))
        self.kwargs.append("rowlist")
        self.kwargs.append(yaml.safe_dump(inj_th_phase[:,1].tolist()))
        
        t0=time.time()
        scan_param_id=0
        inj_delay_org=self.dut["inj"].DELAY
        inj_width_org=self.dut["inj"].WIDTH
        for g in glist:
            #if g is not None:
            #   self.monopix.set_global(**g)
            #if with_mon:  TODO
            #    self.monopix.set_mon_en(mask_pix)

            ####################
            ## start readout
            self.dut.set_monoread()
            self.dut.set_timestamp("inj")
            if with_mon:
                self.dut.set_timestamp("mon")
            self.dut.cleanup_fifo(n=5)
            ####################
            ## save scan_param
            #if g is not None:  TODO
            #  for g_key in g.keys():
            #    self.scan_param_table.row[g_key]=g[g_key]
            
            ####################
            ## start read fifo 
            cnt=0
            for mask_i in range(mask_n):
                self.dut['CONF_SR']['INJ_ROW'].setall(False)
                self.dut['CONF_SR']['COL_PULSE_SEL'].setall(False)
                c_tmp=np.ones(n_mask_col,dtype=int)*-1
                for c_i,c in enumerate(collist[mask_i::mask_n]):
                    self.dut['CONF_SR']['COL_PULSE_SEL'][(self.dut.fl_n * 112) + c ] = 1
                    c_tmp[c_i]=c
                self.scan_param_table.row['collist'] = c_tmp
                self.scan_param_table.row['scan_param_id'] = scan_param_id
                self.scan_param_table.row.append()
                self.scan_param_table.flush()
                with self.readout(scan_param_id=scan_param_id,fill_buffer=False,clear_buffer=True,
                              readout_interval=0.001):
                    for th,row,inj,phase in inj_th_phase:
                        #if row>0 and self.dut['CONF_SR']['INJ_ROW'][row]!=True:
                        self.dut['CONF_SR']['INJ_ROW'].setall(False)
                        self.dut['CONF_SR']['INJ_ROW'][row] = True
                        #if th>0 and th!=self.dut.get_idb_dacunits():
                        self.dut.set_idb_dacunits(th,(debug & 0x1))
                        #if inj>0 and inj!=self.dut.get_vh_dacunits()-self.dut.get_vl_dacunits():
                        inj_low=inj_high-inj
                        self.dut.set_vl_dacunits(inj_low,(debug & 0x1))
                        self.dut.write_conf()
                        if phase>0 and self.dut["inj"].get_phase()!=phase:
                            self.dut["inj"].set_phase(int(phase)%16)
                            self.dut["inj"].DELAY=inj_delay_org+int(phase)/16
                            self.dut["inj"].WIDTH=inj_width_org-int(phase)/16
                            if (debug & 0x1)==1:
                               self.logger.info("inj phase=%x,period=%d"%(
                               self.dut["inj"].PHASE_DES,self.dut["inj"].DELAY+self.dut["inj"].WIDTH))
                        self.dut["inj"].start()
                        while self.dut["inj"].is_done()!=1:
                            time.sleep(0.001)
                        if (debug & 0x2)==2:
                            pre_cnt=cnt
                            cnt=self.fifo_readout.get_record_count()
                            self.logger.info('scan_param_id=%d dat=%d: th=%d inj=%d phase=%d row=%d'%(
                                scan_param_id,cnt-pre_cnt,th,inj,self.dut["inj"].get_phase(),row))
                    if (debug & 0x4)==4:
                        pre_cnt=cnt
                        cnt=self.fifo_readout.get_record_count()
                        self.logger.info('scan_param_id=%d dat=%d: cols=%s'%(scan_param_id,cnt-pre_cnt,str(c_tmp[:c_i+1])))    
                    ####################
                    ## wait before closing fifo
                    time.sleep(0.5)
                    scan_param_id=scan_param_id+1   
            self.dut.stop_all()
            pre_cnt=cnt
            cnt=self.fifo_readout.get_record_count()
            self.logger.info('g=%s, dat=%d'%(str(g),cnt-pre_cnt))
            scan_param_id=scan_param_id+1

    @classmethod
    def analyze(self,data_file=None):

        if data_file[-3:]!=".h5":
            fraw=data_file+'.h5'
        else:
            fraw=data_file
        fhit=fraw[:-7]+'hit.h5'
        fev=fraw[:-7]+'ev.h5'
        
        ##interpret and event_build
        import tjmonopix.analysis.interpreter_idx as interpreter_idx
        interpreter_idx.interpret_idx_h5(fraw,fhit,debug=0x8+0x3)
        #self.logger.info('interpreted %s'%(fhit))
        import tjmonopix.analysis.event_builder_inj as event_builder_inj
        event_builder_inj.build_inj_h5(fhit,fraw,fev,n=10000000)
        #self.logger.info('timestamp assigned %s'%(fev))
        
        ##analyze
        import tjmonopix.analysis.analyze_hits as analyze_hits
        ana=analyze_hits.AnalyzeHits(fev,fraw)
        ana.init_hist_ev()
        ana.init_cnts()
        ana.run()
        return fev

    @classmethod    
    def plot(self,data_file=None):
        if data_file[-3:]!=".h5":
            fraw=self.output_filename+'.h5'
        else:
            fraw=data_file

        fev=fraw[:-7]+'ev.h5'
        fpdf = fraw[:-3] +'.pdf'


if __name__ == "__main__":
    from monopix_daq import monopix
    m=monopix.Monopix()
    
    #fname=time.strftime("%Y%m%d_%H%M%S_simples_can")
    #fname=(os.path.join(monopix_extra_functions.OUPUT_DIR,"simple_scan"),fname)
    
    scan = ThScan(m,online_monitor_addr="tcp://127.0.0.1:6500")
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
