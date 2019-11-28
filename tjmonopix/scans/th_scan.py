import os,sys,time

import numpy as np
import bitarray
import tables as tb
import logging
import yaml

import tjmonopix.scans.injection_scan as injection_scan

local_configuration={"injlist": np.arange(0,33),
                     'rowlist': np.arange(0,224,1),
                     'collist': np.arange(0,112,1),
                     'n_mask_col':1,
}

class ThScan(injection_scan.InjectionScan):
    scan_id = "th_scan"
    
    def scan(self,**kwargs):
        """
        collist: list of columuns 
        row: list of rows
        injlist: array of injection voltage to scan (inj_high-inj_low). inj_low will be scanned
        n_mask_col: number of columns which injected at once.
        Other configuration must be configured before scan.start()
        """
        kwargs["injlist"]=kwargs.pop("injlist",local_configuration['injlist'])

        kwargs["collist"]=kwargs.pop("collist",local_configuration['collist'])
        kwargs["rowlist"]=kwargs.pop("rowlist",local_configuration['rowlist'])
        kwargs["n_mask_col"]=kwargs.pop("n_mask_pix",local_configuration['n_mask_col'])
        kwargs["with_mon"]=kwargs.pop("with_mon",False)

        kwargs["phaselist"]=None
        kwargs["thlist"]=None

        super(ThScan, self).scan(**kwargs)

    @classmethod
    def analyze(self,data_file):
        if data_file[-3:]==".h5":
           fraw=data_file
        else:
           fraw = data_file +'.h5'
        fev=fraw[:-7]+'ev.h5'

        super(ThScan, self).analyze(fraw)

        import tjmonopix.analysis.analyze_hits as analyze_hits
        ana=analyze_hits.AnalyzeHits(fev,fraw)
        ana.init_delete_noninjected()
        ana.init_delete_cetainvalue(delvalues={"inj":0.0})
        ana.init_hist_ev()
        ana.init_cnts()
        ana.run()

        import tjmonopix.analysis.analyze_cnts as analyze_cnts
        ana=analyze_cnts.AnalyzeCnts(fev,fraw)
        ana.init_scurve()
        ana.init_scurve_fit(x="inj")
        ana.init_th_dist()
        ana.init_noise_dist()
        ana.run()

    @classmethod
    def plot(self,data_file):
        fraw = data_file +'.h5'
        fev=fraw[:-7]+'ev.h5'
        fpdf = data_file +'.pdf'
        ### TODO implement!


if __name__ == "__main__":
    from tjmonopix import tjmonopix
    import argparse

    #### TODO implement!!
    
