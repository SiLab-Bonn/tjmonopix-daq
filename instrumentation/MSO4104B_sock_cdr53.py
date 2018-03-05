import sys, os, string,time
import numpy as np
import socket
import visa
import logging
import matplotlib.pyplot as plt 

class Mso_sock():
    def __init__(self,addr='131.220.165.170'):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((addr,4000))
        self.debug=0
        
    def cdr53_ch2_freq_init(self):
        self.write('RECAll:SETUp FACtory')
        self.write('ACQuire:MODe SAMPLe')
        self.write('HORIZONTAL:SCALE 4E-9')
        time.sleep(1)
        self.write('SELECT:CH1 ON')
        self.write('CH1:SCAle 500e-3')
        self.write('CH1:TERMINATION 50.0E+0')
        self.write('CH1:POSition 3')
        self.write('CH1:LABel "CMD_OUT"')
        time.sleep(1)
        self.write('SELECT:CH2 ON')
        self.write('CH2:SCAle 500e-3')
        self.write('CH2:TERMINATION 50.0E+0')
        self.write('CH2:POSition 0')
        self.write('CH2:LABel "CMD_CLK"')
        time.sleep(1)
        self.write('SELECT:CH3 ON')
        self.write('CH3:SCAle 500e-3')
        self.write('CH3:TERMINATION 50.0E+0')
        self.write('CH3:POSition -2.5')
        self.write('CH3:LABel "TEST_CLK"')
        time.sleep(1)
        self.write('SELECT:CH4 ON')
        self.write('CH4:SCAle 200e-3')
        self.write('CH4:TERMINATION 50.0E+0')
        self.write('CH4:POSition -4')
        self.write('CH4:LABel "CML_N"')
        time.sleep(1)
        self.write('TRIGGER:A:TYPE EDGE')
        self.write('TRIGGER:A:EDGE:SOURCE CH3')
        self.write('TRIGGER:A:EDGE:SLOPE RISe')
        self.write('TRIGger:A:LEVel:CH3 0.5')

    def read_ch_freq(self, ch=2):
        self.write('MEASUrement:MEAS1:SOUrce1 CH' + str(ch))
        self.write('MEASUrement:MEAS1:TYPe FREQuency')
        self.write('MEASUrement:MEAS1:STATE ON')  #display mesurement on scope
        self.write('ACQuire:MODe AVErage')
        self.write('ACQuire:NUMAVg 64')
        self.write('MEASUrement:STATIstics RESET')
        time.sleep(5)
        freq = float(self.ask('MEASUrement:MEAS1:VALue?'))
        self.write("ACQuire:MODe SAMPLe")
        return freq
    
    def cdr53_tap_measure_setup(self):
        self.write('RECAll:SETUp FACtory')
        self.write('ACQuire:MODe SAMPLe')
        self.write('HORIZONTAL:SCALE 1e-9')
        time.sleep(1)
        self.write('SELECT:CH1 OFF')
        time.sleep(1)
        self.write('SELECT:CH2 ON')
        self.write('CH2:SCAle 100e-3')
        self.write('CH2:TERMINATION 50')
        self.write('CH2:POSition -4')
        self.write('CH2:LABel "TEST_CLK"')
        time.sleep(1)
        self.write('SELECT:CH3 ON')
        self.write('CH3:SCAle 100e-3')
        self.write('CH3:TERMINATION 50.0E+0')
        self.write('CH3:POSition 0.3')
        self.write('CH3:LABel "CML_P"')
        time.sleep(1)
        self.write('SELECT:CH4 ON')
        self.write('CH4:SCAle 100e-3')
        self.write('CH4:TERMINATION 50.0E+0')
        self.write('CH4:POSition -0.3')
        self.write('CH4:LABel "CML_N"')
        time.sleep(1)
        self.write('TRIGGER:A:TYPE EDGE')
        self.write('TRIGGER:A:EDGE:SOURCE CH2')
        self.write('TRIGGER:A:EDGE:SLOPE RISe')
        self.write('TRIGger:A:LEVel:CH2 0.5')
        time.sleep(1)
        self.write('SELECT:MATH1 ON')
        self.write('MATH1:TYPE DUAL')
        self.write('MATH1:DEFine "CH3-CH4"')
        self.write('MATH1:LABEL "CML"')
        
        return

#     def read_in_out_delay(self, tap='pre'):
#         self.write('ACQuire:MODe SAMPLe')
#         
#         time.sleep(1)
#         self.write('ACQuire:MODe AVErage')
#         self.write('ACQuire:NUMAVg 512')
#         self.write('MEASUrement:MEAS1:TYPe DELay')
#         self.write('MEASUrement:MEAS1:SOUrce1 MATH')
#         self.write('MEASUrement:MEAS1:SOUrce2 CH2')
#         self.write('MEASUREMENT:MEAS1:DELAY:DIRECTION FORWards')
#         if (tap == 'pre'):
#             self.write('MEASUREMENT:MEAS1:DELAY:EDGE1 FALl')
#             self.write('MATH:VERTICAL:SCALE 100E-03')
#             self.write('MATH:VERTICAL:POSITION -1')
#         elif (tap == 'post'):
#             self.write('MEASUREMENT:MEAS1:DELAY:EDGE1 RISe')
#             self.write('MATH:VERTICAL:SCALE 50E-03')
#             self.write('MATH:VERTICAL:POSITION 1')
#         time.sleep(1)
#         self.write('MEASUREMENT:MEAS1:DELAY:EDGE2 RISE')
#         self.write('MEASUrement:MEAS1:STATE ON')  #display mesurement on scope
#         self.write('MEASUrement:STATIstics RESET')
#         time.sleep(10)
#         delay = float(self.ask('MEASUrement:MEAS1:VALue?'))
#         return delay

    def read_in_out_delay(self, tap='pre', meas_count=100):
        self.write('ACQuire:MODe SAMPLe')
        
        time.sleep(1)
        self.write('ACQuire:MODe AVErage')
        self.write('ACQuire:NUMAVg 512')
        self.write('MEASUrement:MEAS1:TYPe DELay')
        self.write('MEASUrement:MEAS1:SOUrce1 CH2')
        self.write('MEASUrement:MEAS1:SOUrce2 MATH')
        self.write('MEASUREMENT:MEAS1:DELAY:DIRECTION FORWards')
        self.write('MATH:VERTICAL:POSITION 0')
        if (tap == 'pre'):
            self.write('MEASUREMENT:MEAS1:DELAY:EDGE2 RISe')
            self.write('MATH:VERTICAL:SCALE 100E-03')
        elif (tap == 'post'):
            self.write('MEASUREMENT:MEAS1:DELAY:EDGE2 FALl')
            self.write('MATH:VERTICAL:SCALE 50E-03')
        time.sleep(1)
        self.write('MEASUREMENT:MEAS1:DELAY:EDGE1 RISe')
        self.write('MEASUrement:MEAS1:STATE ON')  #display mesurement on scope
        self.write('MEASUrement:STATIstics RESET')
        time.sleep(3)
        delay = []
        for i in range(0,meas_count):
            delay.append(float(self.ask('MEASUrement:MEAS1:VALue?')))
            time.sleep(0.1)
        delay_avg = np.average(delay)
#         print np.std(delay)
        return delay_avg

    def take_screenshot(self, addr='192.168.10.2', filename=""):
        self.s.close()
        time.sleep(1)
        rm = visa.ResourceManager('@py')
        scope_visa_addr = 'TCPIP::' + addr
        scope_visa = rm.open_resource(scope_visa_addr)
        time.sleep(1)
        scope_visa.write("SAVe:IMAGe:FILEF PNG")
        scope_visa.write("HARDCOPY START")
        raw_data = scope_visa.read_raw()
        if filename == "":
            filename = time.strftime("/home/piotr/Desktop/scope_screenshots/mso_%y%m%d-%H%M%S.png")
        fid = open(filename, 'wb')
        fid.write(raw_data)
        fid.close()
        time.sleep(0.1)
        rm.close()
        time.sleep(0.1)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((addr,4000))
        return
    
    def eye_histogram_init(self):
        
        self.write('ACQuire:MODe SAMPLe')
        self.write('HORIZONTAL:SCALE 400E-12')
        time.sleep(1)
        self.write('SELECT:CH1 OFF')
        self.write('SELECT:CH2 OFF')
        self.write('SELECT:CH3 OFF')
        time.sleep(1)
        self.write('SELECT:CH4 ON')
        self.write('CH4:SCAle 50e-3')
        self.write('CH4:TERMINATION 50.0E+0')
        self.write('CH4:POSition 0')
        self.write('CH4:LABel "CML_N"')
        time.sleep(1)
        self.write('TRIGGER:A:TYPE EDGE')
        self.write('TRIGGER:A:EDGE:SOURCE CH3')
        self.write('TRIGGER:A:EDGE:SLOPE RISe')
        self.write('TRIGger:A:LEVel:CH3 0.5')
        time.sleep(1)
        self.write('DISplay:PERSistence CLEAR')
        self.write('DISplay:PERSistence INFInite')
        return
    
    def setup_histogram(self, ch=4, mode='h', left=55.0, top=0.0, right=55.1, bottom=100.0):
#         default values are for vertical histogram
        self.write('HIStogram:SOUrce CH'+ str(ch))
        if mode == 'h':
            self.write('HIStogram:MODe HORizontal')
        else:
            self.write('HIStogram:MODe VERTical')
        self.write('HIStogram:BOXPcnt ' + str(left) + ' ,' + str(top) + ' ,' + str(right) + ' ,' + str(bottom))
        
        return
    
    def get_hist_all(self, data_taking_time=10):
        self.write('DISplay:PERSistence CLEAR')
        time.sleep(data_taking_time)
        hist_setting=self.ask("HISTOGRAM?")
        hist_data=self.ask("HIS:DAT?")
        d=np.array(hist_data.split(","),int)
        tmp=hist_setting.split(";")
        b=float(tmp[-2])
        e=float(tmp[-1])
        s=(e-b)/len(d)
        x=np.arange(b,e,s)
        return [hist_setting, hist_data, x, d]
    
    def take_eye_histograms(self, file_path, interactive = False, data_taking_time=10):
        self.eye_histogram_init()
        self.setup_histogram(ch=4, mode='h', left=15.0, top=50.0, right=75.0, bottom=50.1)
        if interactive == True:
            raw_input('\nDoing HORIZONTAL histogram - line should go through middle of 2 eyes - adjust if needed, press enter to continue')
        [hor_hist_setting, hor_hist_data_raw, hor_hist_x, hor_hist_y] = self.get_hist_all(data_taking_time)
        self.take_screenshot(filename=(file_path + '_screenshot_horizontal_hist.png'))
        logging.debug('horizontal histogram settings: %s', hor_hist_setting)
        logging.debug('horizontal histogram raw data: %s', hor_hist_data_raw)
        time.sleep(5)
        self.setup_histogram(ch=4, mode='v', left=58.0, top=0.0, right=58.1, bottom=100.0)
        if interactive == True:
            raw_input('\nDoing VETICAL histogram - line should go through middle of 1 eye - adjust if needed, press enter to continue')
        [vert_hist_setting, vert_hist_data_raw, vert_hist_x, vert_hist_y] = self.get_hist_all(data_taking_time)
        self.take_screenshot(filename=(file_path + '_screenshot_vertical_hist.png'))
        logging.debug('vertical histogram settings: %s', vert_hist_setting)
        logging.debug('vertical histogram raw data: %s', vert_hist_data_raw)
        time.sleep(5)
        
        plt.subplot(2, 1, 1)
        plt.plot(hor_hist_x[0:999], hor_hist_y[0:999])
        plt.xlabel('time')
        plt.ylabel('counts')
        plt.title('histogram of horizontal eye opening (two consecutive eyes)')
        
        plt.subplot(2, 1, 2)
        plt.plot(vert_hist_x[0:255], vert_hist_y[0:255])
        plt.xlabel('voltage')
        plt.ylabel('counts')
        plt.title('histogram of vertical eye opening')
        
        plt.tight_layout()
        fig = plt.gcf()  # using this, so after show() the same figure is still saved to file
        if interactive == True:
            plt.show()
        plot_filename = file_path + '_eye_histograms.png'
        fig.savefig(plot_filename)
        plt.close()
        
        logging.info('made plot: %s', plot_filename)
        return
    
    def write(self,cmd):
        if self.debug==1:
            print "Mso_sock.write() %s"%cmd
        self.s.sendall("%s\r\n"%cmd)
    def read(self,size=1024):
        data=""
        i=0
        while i<100000000:
            ret=self.s.recv(size)
            if self.debug==2:
                print "%d:Mso_sock.read() ret(%d)="%(i,len(ret)),repr(ret)
            data="%s%s"%(data,ret)
            if ret[-1]=="\n" or ret[-1]=="\r":
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
    def ask(self,cmd):
        if self.debug==1:
            print "Mso_sock.ask() cmd=", cmd
        self.s.sendall("%s\r\n"%cmd)
        for i in range(5):
           time.sleep(0.1*i)
           ret=self.read(1024)
           if len(ret)!=0: ## TODO give size if it is fixed
               break
        return ret

    def get_info(self):
        return self.ask("*IDN?")
    def query(self):
        for i in range(1000):
            tmp=self.ask("ACQ?")
            if self.debug==1:
                print "Mso_sock.query() acq=%s"%tmp
            state=tmp.split(";")[1].split()[-1]
            if int(state)!=1:
                break
    def start(self):
        self.write("ACQ:STOPAfter SEQuence")
        self.write("ACQ:STATE RUN")

    def measure(self,n=1,chs=[1,2,3,4],save=True,start=1,stop=-1):
        i=0
        self.init(chs,start,stop)
        if save==True:
            filename=time.strftime("mso_%y%m%d-%H%M%S.txt")
        while i!=n:
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
                #pass
                stop=int(self.ask('HOR:RECO?'))
                self.write('DATA:STOP %d'%stop)
    
    def get_alldata(self,chs):
        dat=""
        for ch in chs:
            self.write('DATA:SOURCE CH%d'%ch)
            time.sleep(0.1)
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

############### old functions  
    def init_old(self,chs=[1,2,3,4]):
      self.param={}

      tmp=self.ask('WFMPRE:XINCR?').split()
      if self.debug==1:
              print "XINCR",tmp
      self.param["time"]=[float(tmp[-1]),0,0]
      for i in chs:
          self.write('DATA:SOURCE CH%d'%i)
          self.write('DATA:WIDTH 2')
          self.write('DATA:ENC ASCII')
          #time.sleep(0.1)
          tmp=self.ask('WFMPRE:YMULT?').split()
          if self.debug==1:
              print 'YMULT',i, tmp
          ymult = float(tmp[-1])
          #time.sleep(0.1)
          tmp=self.ask('WFMPRE:YZERO?').split()
          if self.debug==1:
              print "YZERO",i, tmp
          yzero = float(tmp[-1])
          #time.sleep(0.1)
          tmp=self.ask('WFMPRE:YOFF?').split()
          if self.debug==1:
              print "YOFF",i, tmp
          yoff = float(tmp[-1])
          self.param["ch%d"%i]=[ymult,yzero,yoff]
    def init_old2(self,chs=[1,2,3,4],start=1,stop=-1):
        self.param={}

        tmp=self.ask('WFMPRE:XINCR?')
        if self.debug==1:
              print "XINCR",tmp
        s=tmp
        self.param["time"]=[float(tmp.split()[-1]),0,0]

        for i in chs:
            self.write('DATA:SOURCE CH%d'%i)
            tmp=self.ask(":WFMO?")
            s=s+" "+tmp
            tmp=tmp.split(";")
            self.parasendallm["ch%d"%i]=[float(tmp[14]),float(tmp[16]),float(tmp[15])]
            if stop==-1:
                stop=int(tmp[5].split()[5])
            self.wave_len=stop-start+1
            self.write('DATA:WIDTH 2')
            self.write('DATA:ENC ASCII')
            self.write('DATA:START %d'%start)
            self.write('DATA:STOP %d'%stop)
        return s
        
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
        #self.s.shutdown('SHUT_RDWR') # from manual - used for "closing connection in timely fashion" 
        self.s.close()
        
if __name__=="__main__":
    print "......start......"
    m=Mso_sock(addr="131.220.165.170")
    m.debug=1
    for i in range(2000):
        f=m.measure(chs=[1,2,4])
        print time.time(),i,f
    print "......done......"
#     
