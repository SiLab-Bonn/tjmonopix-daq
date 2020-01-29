from zmq.utils import jsonapi
import numpy as np
import logging, time
import gc
from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils
from numba import njit

from tjmonopix.analysis.event_builder_mon import BuildEvents


#fe_dtype=[('event_number', '<i8'), ('trigger_number', '<u4'), ('relative_BCID', 'u1'), ('LVL1ID', '<u2'), ('column', 'u1'), 
#('row', '<u2'), ('tot', 'u1'), ('BCID', '<u2'), ('TDC', '<u2'), ('TDC_time_stamp', 'u1'), ('trigger_status', 'u1'), 
#('service_record', '<u4'), ('event_status', '<u2')]

def get_noisy_mask(cols_corr, rows_corr, percentage):
        mask_corr= (cols_corr < np.percentile(cols_corr, percentage))
        mask_row= (rows_corr < np.percentile(rows_corr, percentage))
        return mask_corr, mask_row

#@njit
def _correlate(fe, mono, corr_col, corr_row, tr=True):
    
    fe_idx=0
    mono_idx=0
    
    while len(fe)> fe_idx and len(mono)>mono_idx:
       if (fe[fe_idx]["trigger_number"] & 0x7FFF)==mono[mono_idx]["trigger_number"]:
            #print "trigger number",(fe[fe_idx]["trigger_number"] & 0x7FFF)
            trigger_number=mono[mono_idx]["trigger_number"]
            fe_i=fe_idx+1
            flg=0
            while len(fe) > fe_i:
                 if trigger_number!= (fe[fe_idx]["trigger_number"] & 0x7FFF):
                     flg=1
                     break
                 fe_i=fe_i+1
            if flg==0:
                return 2, corr_col,corr_row,fe_idx,mono_idx
            mono_i=mono_idx+1
            flg=0
            while len(mono) > mono_i:
                 if trigger_number!= mono[mono_i]["trigger_number"]: 
                     flg=1
                     break
                 mono_i=mono_i+1
            if flg==0:
                return 1, corr_col,corr_row,fe_idx,mono_idx
            for fe_ii in range(fe_idx,fe_i):
                for mono_ii in range(mono_idx,mono_i):
                    if tr:
                       corr_col[fe[fe_ii]["column"],mono[mono_ii]["row"]]== corr_col[fe[fe_ii]["column"],mono[mono_ii]["row"]] + 1
                       corr_row[fe[fe_ii]["row"],mono[mono_ii]["column"]]== corr_row[fe[fe_ii]["row"],mono[mono_ii]["column"]] + 1
                    else:
                       corr_col[fe[fe_ii]["column"],mono[mono_ii]["column"]]== corr_col[fe[fe_ii]["column"],mono[mono_ii]["column"]] + 1
                       corr_row[fe[fe_ii]["row"],mono[mono_ii]["row"]]== corr_row[fe[fe_ii]["row"],mono[mono_ii]["row"]] + 1
                mono_idx=mono_i
                fe_idx=fe_i 
       elif ((fe[fe_idx]["trigger_number"] & 0x7FFF)- mono[mono_idx]["trigger_number"]) & 0x4000 == 0:
           print (fe[fe_idx]["trigger_number"] & 0x7FFF),mono[mono_idx]["trigger_number"], ((fe[fe_idx]["trigger_number"] & 0x7FFF)- mono[mono_idx]["trigger_number"]) & 0x4000 
           mono_idx = mono_idx+1
       else:
           fe_idx= fe_idx+1
            
    return 0, corr_col, corr_row,fe_idx, mono_idx                    

class HitCorrelator(Transceiver):

    def setup_transceiver(self):

        self.set_bidirectional_communication()  # We want to be able to change the histogrammer settings

    def setup_interpretation(self):

        # variables to determine whether to do sth or not
        self.active_tab = None  # stores name (str) of active tab in online monitor
        self.hit_corr_tab = None  # store name (str) of hit_correlator tab FIXME: get name of receiver instead
        self.start_signal = 0  # will be set in handle_command function; correlation starts if this is set to 0
        # variables fps
        self.fps = 0
        self.updateTime = 0
        # remove noisy background
        self.remove_background= False
        self.remove_background_percentage = 99.0
        # transpose cols and rows due to fei4 rotation
        self.tr = True
        # data buffer and histogramms
        self.fe_buf = None
        self.mono_buf = None
        self.fe_buf = None
        self.mono_tmp1_buf = None
        self.mono_tmp0_buf = None
        # must be a np.array with dimensions cols x cols;
        # will be set by get_hist_size function in handle_command function
        if self.tr == True:
            #self.hist_cols_corr = np.zeros([self.config['max_n_rows_monopix'],self.config['max_n_columns_fei4']])
            #self.hist_cols_corr = np.zeros([self.config['max_n_rows_monopix'],self.config['max_n_columns_fei4']])
            self.corr_col = np.zeros([81,224])
            self.corr_row = np.zeros([336,112])
            self.mask_col = np.zeros([81,224],dtype=bool)
            self.mask_row = np.zeros([336,112],dtype=bool)
        else:
            self.corr_col = np.zeros([self.config['max_n_columns_monopix'],self.config['max_n_columns_fei4']])
            self.corr_row = np.zeros([self.config['max_n_rows_monopix'],self.config['max_n_rows_fei4']])
        
        self.mono_builder=BuildEvents(upper=0x80,lower=-0x100,WAIT_CYCLES=20,data_format=0x0)

    def deserialze_data(self, data):  # According to pyBAR data serialization
        datar, meta = utils.simple_dec(data)
        if 'hits' in meta:
            meta['hits'] = datar
        return meta

    def interpret_data(self, data):
        #if 'meta_data' in data[0][1]:
        #    meta_data = data[0][1]['meta_data']
        #    now = float(meta_data['timestamp_stop'])
        # 
        #    if now != self.updateTime:
        #        recent_fps = 1.0 / (now - self.updateTime)  # FIXME: shows recorded data rate not current rate
        #        self.updateTime = now
        #        self.fps = self.fps * 0.7 + recent_fps * 0.3
        #        meta_data.update({'fps': self.fps})
        #        return [data[0][1]]

        # loop over data and determine whether it is fe or monopix data
        for d in data:
            if 'meta_data' in d[1]:  # meta_data is skipped
                continue

            if d[1]['hits'].shape[0] == 0:  # empty array is skipped
                continue

            if 'te' in d[1]['hits'].dtype.names:  # MONOPIX data has keyword 'te'
                print len(d[1]['hits'])
                if self.mono_buf is None:
                    self.mono_buf=self.mono_builder.run(d[1]['hits'])
                else:
                    self.mono_buf = np.append(self.mono_buf, self.mono_builder.run(d[1]['hits']))
            else:  # fe data
                if self.fe_buf==None:
                     self.fe_buf=d[1]['hits']
                else:
                     print d[1]['hits'][0]["trigger_number"] & 0x7FFF
                     self.fe_buf = np.append(self.fe_buf, d[1]['hits'])
        #print "============== buf size",self.fe_buf, self.mono_buf
        if (self.fe_buf is None) or (self.mono_buf is None):
            return
        print "============== buf size",len(self.fe_buf),len(self.mono_buf)
        if len(self.fe_buf) == 0 or len(self.mono_buf) == 0:
            return
#        print "============== buf size",len(self.fe_buf),len(self.mono_buf),
#        print self.monopix_buffer[0],self.monopix_buffer[-1], 
#        print len(self.fe_buffer), len(self.monopix_buffer)
        
        # make correlation
        err,self.corr_col, self.corr_row, fe_idx, mono_idx = _correlate(self.fe_buf,self.mono_buf,self.corr_col, self.corr_row)
        
        self.fe_buf = self.fe_buf[fe_idx:]
        self.mono_buf = self.mono_buf[mono_idx:]

        if self.remove_background:
            self.corr_col[self.mask_col]=0
            self.corr_row[self.mask_col]=0
        
        return [{'column': self.corr_col, 'row': self.corr_row}]


    def serialze_data(self, data):
        return jsonapi.dumps(data, cls=utils.NumpyEncoder)
        # return utils.simple_enc(None, data)

    def handle_command(self, command):
        # declare functions
        # reset histogramms and data buffer, call garbage collector
        def reset():
            self.corr_col = np.zeros_like(self.corr_col)
            self.corr_row = np.zeros_like(self.corr_row)
            self.fe_buf = None
            self.mono_buffer = None
            self.mask_col = np.zeros_like(self.mask_col)
            self.mask_row = np.zeros_like(self.mask_row)
            self.mono_builder.reset()
            gc.collect()  # garbage collector is called to free unused memory
        
        print "!!!!!!!!!!!!!!!!!",command
        # commands
        if command[0] == 'RESET':
            reset()

        # Get name of receiver's tab
        elif 'RECEIVER' in command[0]:
            self.hit_corr_tab = command[0].split()[1]

        # First choose two telescope planes and then press start button to correlate
        elif 'START' in command[0]:
            self.start_signal = int(command[0].split()[1])
            print '\n'
            print '#######################', ' START ', '#######################\n'

        # Received signal is 'ACTIVETAB tab' where tab is the name (str) of the selected tab in online monitor
        elif 'ACTIVETAB' in command[0]:
            self.active_tab = str(command[0].split()[1])

        elif 'STOP' in command[0]:  # received whenever 'Stop'-button is pressed; set start signal to 1
            self.start_signal = int(command[0].split()[1]) + 1
            print '\n'
            print '#######################', ' STOP ', '#######################\n'
#           print "AVERAGE CPU ==", self.avg_cpu / self.n
#           print "AVERAGE PROCESS CPU ==", self.prs_avg_cpu / self.n
#           print "AVERAGE RAM ==", self.avg_ram / self.n
            reset()

        elif 'BACKGROUND' in command[0]:
            self.remove_background_checkbox = int(command[0].split()[1])
            if self.remove_background_checkbox == 0:
                self.remove_background = False
                reset()
            elif self.remove_background_checkbox == 2:
                self.remove_background = True

        elif 'PERCENTAGE' in command[0]:
            percentage = float(command[0].split()[1])
            self.mask_corr= (self.cols_corr < np.percentile(self.cols_corr, percentage))
            self.mask_row= (self.rows_corr < np.percentile(self.rows_corr, percentage))

        elif 'TRANSPOSE' in command[0]:
            checkbox = int(command[0].split()[1])
            if self.active_dut1 == 0 or self.active_dut2 == 0:
                if checkbox == 0:  # transpose_checkbox is not checked
                    self.tr = True
                elif checkbox == 2:  # transpose_checkbox is checked
                    self.tr = False
