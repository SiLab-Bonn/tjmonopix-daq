import glob
import os
import logging

def AnalysisAndPlot(ScanClass,fin=None):
    def __init__(self,fin=None):
        self.scan_id=ScanClass.scan_id
        if fin==None:
            self.working_dir = os.path.join(os.getcwd(),"output_data")
            flist=glob.glob(os.path.join(self.working_dir,"*_%s.h5"%self.scan_id))
            if len(flist)==0:
                print "cannot find %s file in %s"%(self.scan_id, self.working_dir)
                return None
            latest= max(flist, key=os.path.getctime)
            self.output_filename = latest[:-3]
            self.run_name = os.path.basename(self.output_filename)
        else:
            self.working_dir = os.path.dirname(os.path.realpath(fin))
            self.run_name = os.path.basename(os.path.realpath(fin))
            self.output_filename = os.path.join(self.working_dir, self.run_name)
            
        ### set logger
        self.logger = logging.getLogger()
        flg=0
        for l in self.logger.handlers:
            if isinstance(l, logging.FileHandler):
               flg=1
        if flg==0:
            fh = logging.FileHandler(self.output_filename + '.log')
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s"))
            fh.setLevel(logging.WARNING)
            self.logger.addHandler(fh)
        self.logger.info("filename:%s"%self.output_filename)
        
    newclass = type("AnalysisAndPlot", (ScanClass,),{"__init__": __init__})
    inst=newclass(fin)
    #if inst is not None:
    #    inst.logger.info("instanciated %s"%ScanClass.__name__)
    return inst

if __name__ == "__main__":
    import sys
    import importlib
    import inspect
    import argparse
    
    parser = argparse.ArgumentParser(usage="analysis_and_plot.py xxx_scan",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("scan_module_name", metavar="scan_module_name", type=str)
    parser.add_argument("-p","--plot_only", action='store_const',const=True, default=False)
    parser.add_argument("-a","--analysis_only", action='store_const',const=True, default=False)
    parser.add_argument("--fin", metavar="fin", type=str, default=None)
    args=parser.parse_args()

    x=importlib.import_module('tjmonopix.scans.%s'%args.scan_module_name)
    #print './scans/%s.py'%args.scan_module_name
    #x=imp.load_source('monopix_daq.scans.%s'%args.scan_module_name,'./scans/%s.py'%args.scan_module_name)
    for name, ScanClass in inspect.getmembers(x):
        if inspect.isclass(ScanClass):
            break
    a=AnalysisAndPlot(ScanClass,fin=args.fin)
    if not args.plot_only:
        a.analyze()
    if not args.analysis_only:
        a.plot()

