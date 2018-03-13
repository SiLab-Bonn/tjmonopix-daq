import sys, os, string,time
import numpy as np
import socket
    
class Mso_sock():
    def __init__(self,addr='131.220.165.170'):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((addr,4000))
        self.debug=0
    def write(self,cmd):
        if self.debug!=0:
            print "Mso_sock.write()",repr(cmd)
        self.s.sendall("%s\r\n"%cmd)
    def read(self,size=1024):
        time.sleep(0.01)
        data=""
        i=0
        while i<100000000:
            ret=self.s.recv(size)
            if self.debug==2:
                print "%d:Mso_sock.read() ret(%d)="%(i,len(ret)),repr(ret)
            data="%s%s"%(data,ret)
            if ret[-1]=="\n":
                break
            # if ret[-1]=="\r":
            #    break
            i=i+1
        if i==100000000:
            print  "ERR increase read loop"
        if len(data)<2:
            data=""
        elif data[-1]=="\n" and data[-2]=="\r":
            data=data[:-2]
        elif data[-1]=="\r" and data[-2]=="\n":
            data=data[:-2]
        elif data[-1]=="\n":
            data=data[:-1]
        return data
    def ask(self,cmd,size=1024):
        if self.debug!=0:
            print "Mso_sock.ask() cmd=", repr(cmd)
        time.sleep(0.01)
        self.s.sendall("%s\r\n"%cmd)
        return self.read(size)

    def get_info(self):
        return self.ask("*IDN?")
    def query(self):
        time.sleep(0.1)
        for i in range(1000):
            tmp=self.ask("ACQ?")
            if self.debug==1:
                print "Mso_sock.query() recv=",tmp
            try:
                state=tmp.split(";")[1].split()[-1]
            except:
                state=1
            if int(state)!=1:
                break
            time.sleep(0.1)
    def start(self):
        self.write("ACQ:STOPAfter SEQuence")
        self.write("ACQ:STATE RUN")

    def measure(self,n=1,chs=[1,2,3,4],start=1,stop=-1,save=True):
        i=0
        self.init(chs,start,stop)
        if save==True:
            filename=time.strftime("mso_%y%m%d-%H%M%S.txt")
        while i<n:
            self.start()
            self.query()
            wave=self.get_alldata(chs)
            if save==True:
                with open(filename, "a") as f:
                      f.write(wave)
            i=i+1
        if save==True:
            return filename
        else:
            return wave
    def init(self,chs=[1,2,3,4],start=1,stop=-1):
        for i in chs:
            self.write('DATA:SOURCE CH%d'%i)
            self.write('DATA:WIDTH 2')
            self.write('DATA:ENC ASCII')
            self.write('DATA:START %d'%start)
            if self.debug:
               print "init() ch=",i, "stop=",stop
            if stop>0:
                self.write('DATA:STOP %d'%stop)
            else:
                stop=int(self.ask('HOR:RECO?'))
                self.write('DATA:STOP %d'%stop)
    
    def get_alldata(self,chs):
        dat=""
        for ch in chs:
            self.write('DATA:SOURCE CH%d'%ch)
            dat=dat+self.ask('WAVF?')
        dat=dat+'\n'
        return dat
 
    def get_hist(self,save=True):
        hist_setting=self.ask("HISTOGRAM?")
        hist_data=self.ask("HIS:DAT?")
        if save==True:
            filename=time.strftime("msohist_%y%m%d-%H%M%S.txt")
            with open(filename,"a") as f:
                f.write("%s\n%s"%(hist_setting,hist_data))
            return filename
        else:
            d=np.array(hist_data.split(","),int)
            tmp=hist_setting.split(";")
            b=float(tmp[-2])
            e=float(tmp[-1])
            s=(e-b)/len(dat)
            x=np.arange(b,e,s)
            return np.array([x,d])

    def save_ascii(self,wave,filename=""):
        if filename=="":
            filename=time.strftime("mso_%y%m%d-%H%M%S.npy")
        with open(filename,"w") as f:
            f.write(wave)
        
    def get_data(self):
      wave=np.empty([len(self.param),self.wave_len])
      i=1
      for k,v in self.param.iteritems():
          if k=="time":
              continue
          self.write('DATA:SOURCE %s'%k.upper())
          data = self.ask('CURVE?')
          if self.debug==1:
              print "len(data)=",len(data),data[:10],
          ADC_wave = np.array(data.split(","))
          if self.debug==1:
              print "wave=",len(ADC_wave)
          ADC_wave = ADC_wave.astype(np.float)
          wave[i]=(ADC_wave - v[2]) * v[0]  + v[1]
          i=i+1
      wave[0]=np.arange(0, self.param["time"][0] * (self.wave_len)+self.param["time"][0]*0.5, 
              self.param["time"][0])[:self.wave_len-1]
      return wave
      
    def get_data_slow(self, chs=[1,2,3,4]):
      for i in chs:
          self.write('DATA:SOURCE CH%d'%i)
          self.write('DATA:WIDTH 2')
          self.write('DATA:ENC ASCII')
          
          tmp=self.ask('WFMPRE:YMULT?').split()
          if self.debug==1:
              print i, tmp
          ymult = float(tmp[-1])
          tmp=self.ask('WFMPRE:YZERO?').split()
          if self.debug==1:
              print i, tmp
          yzero = float(tmp[-1])
          tmp=self.ask('WFMPRE:YOFF?').split()
          if self.debug==1:
              print i, tmp
          yoff = float(tmp[-1])
          tmp=self.ask('WFMPRE:XINCR?').split()
          if i==chs[0]:
              xincr = float(tmp[-1])
          elif xincr != float(tmp[-1]):
              raise ValueError("xincr must be the same %f, %f"%(xincr,float(tmp[-1])))
    
          self.write('CURVE?')
          data = self.read()
          if self.debug==1:
              print "len(data)=",len(data),data[:10]
          ADC_wave = np.array(string.split(data,","))
          if self.debug==1:
              print "wave=",len(ADC_wave)
          ADC_wave = ADC_wave.astype(np.float)
          if i==chs[0]:
              wave=np.zeros([5,len(ADC_wave)])
              wave[0,:] = np.arange(0, xincr * len(ADC_wave), xincr)
          wave[i,:] = (ADC_wave - yoff) * ymult  + yzero
      return wave
      
    def save_data(self,wave,filename=""):
        if filename=="":
            filename=time.strftime("mso_%y%m%d-%H%M%S.npy")
        np.save(filename,wave)
        return filename
    def get_screen(self):
        pass
    def save_screen(self):
        pass
    def close(self):
        self.s.close()
        
class Mso4104_sock(Mso_sock):
    def ask(self,cmd,size=1024):
        if self.debug!=0:
            print "Mso_sock.ask() cmd=", repr(cmd)
        time.sleep(0.01)
        self.s.sendall("%s\n"%cmd)
        return self.read(size)    
    def write(self,cmd):
        if self.debug!=0:
            print "Mso_sock.write()",repr(cmd)
        self.s.sendall("%s\n"%cmd)
    def read(self,size=1024):
        time.sleep(0.01)
        data=""
        i=0
        while i<100000000:
            ret=self.s.recv(size)
            if self.debug==2:
                print "%d:Mso_sock.read() ret(%d)="%(i,len(ret)),repr(ret)
            data="%s%s"%(data,ret)
            if ret[-1]=="\r":
                break
            i=i+1
        if i==100000000:
            print  "ERR increase read loop"
        if len(data)<2:
            data=""
        elif data[-1]=="\n" and data[-2]=="\r":
            data=data[:-2]
        elif data[-1]=="\r" and data[-2]=="\n":
            data=data[:-2]
        elif data[-1]=="\n":
            data=data[:-1]
        return data 
        
if __name__=="__main__":
    print "......start......"
    m=Mso_sock(addr="131.220.165.170")
    m.debug=1
    for i in range(2000):
        f=m.measure(chs=[1,2,4])
        print time.time(),i,f
    print "......done......"
#     
