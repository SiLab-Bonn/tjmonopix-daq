import os,time,sys
def get_run():
    #for d in open("/home/silab/tjmonopix/pyBAR/pybar/configuration.yaml").readlines():
    #  if "module_id :"==d[:11]:
    #    module_id=d.split()[2] 
    #run=open("/home/silab/tjmonopix/pyBAR/pybar/%s/run.cfg"%module_id).readlines()[-1].split()[0]
    run=open("/media/silab/HDD11/Testbeam/ELSA_26_03_2018/fei4/run.cfg").readlines()[-1].split()[0]
    #print "Run", int(run)+1
    return int(run)+1
if __name__ =="__main__":
    run=get_run()
    print '%d'%run
    #sys.exit('%d'%run)
