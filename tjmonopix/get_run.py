import os,time,sys
def get_run():
	for d in open("/home/silab/tjmonopix/pyBAR/pybar/configuration.yaml").readlines():
	  if "module_id :"==d[:11]:
	    module_id=d.split()[2] 
	run=open("/home/silab/tjmonopix/pyBAR/pybar/%s/run.cfg"%module_id).readlines()[-1].split()[0]
	print int(run)+1
        return int(run)+1
if __name__ =="__main__":
    get_run()
