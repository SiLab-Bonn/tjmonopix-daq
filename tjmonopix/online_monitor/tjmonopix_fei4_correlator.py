from zmq.utils import jsonapi
import numpy as np
import logging, time
import gc
from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils
from numba import njit
from monopix_daq.analysis.event_builder import BuildWithTlu


#fe_dtype=[('event_number', '<i8'), ('trigger_number', '<u4'), ('relative_BCID', 'u1'), ('LVL1ID', '<u2'), ('column', 'u1'), 
#('row', '<u2'), ('tot', 'u1'), ('BCID', '<u2'), ('TDC', '<u2'), ('TDC_time_stamp', 'u1'), ('trigger_status', 'u1'), 
#('service_record', '<u4'), ('event_status', '<u2')]


#@njit
def correlate_ff(fe_data, monopix_data, corr_col, corr_row):
    
    fe_index=0
    mono_index=0
    
    last_fe_index = len(fe_data) - 1
    last_mono_index = len(monopix_data) - 1
    
    #If one of the data sets is empty, return and keep both sets in buffer
    if len(fe_data)==0 or len(monopix_data)==0:
        return fe_index, mono_index, corr_col, corr_row
    
    else:
        for mono_index in range(len(monopix_data)): #Go through MONOPIX data
        
            #Get the TLU number corresponding to the current MONOPIX index
            mono_tlu = (monopix_data[mono_index]['event_number']) & 0x7FFF
            
            #If the FE index is smaller than the maximum FE index, and the FE TLU number is smaller than the one of the current MONOPIX index:
            #Increase FE index until catching up
            while fe_index < (last_fe_index) and (fe_data[fe_index]['trigger_number']) & 0x7FFF < mono_tlu:
                fe_index+=1
            
            #If the end of any data set is reached, return current indices and keep remaining data for the next data correlation
            if mono_index == (last_mono_index) or fe_index == (last_fe_index):
                return fe_index, mono_index, corr_col, corr_row
    
            for fe_i in range(fe_index, len(fe_data)): #Go through FE data, from the index that caught up with the latest MONOPIX index
                
                #Get the TLU number corresponding to the current FE index
                fe_tlu = (fe_data[fe_i]['trigger_number']) & 0x7FFF
                
                #If the end of the FE data is reached and the FE TLU number is equal to the one of the current MONOPIX index:
                #Return current indexes of both FE and MONOPIX and keep remaining data for the next data correlation     
                if fe_i == last_fe_index and fe_tlu == mono_tlu:
                    return fe_i, mono_index, corr_col, corr_row
                
                #Fill the histogram if the TLU numbers in both FE and MONOPIX indexes are equal
                if fe_tlu == mono_tlu:
#                    print "COLUMNS", monopix_data[mono_index]['column'], fe_data[fe_i]['column']
#                    print "ROWS", monopix_data[mono_index]['row'], fe_data[fe_i]['row']
                    
                    corr_col[ monopix_data[mono_index]['column'] , fe_data[fe_i]['column'] ] += 1
                    corr_row[ monopix_data[mono_index]['row'] , fe_data[fe_i]['row'] ] += 1
                else:
                    break
    
    return fe_index, mono_index, corr_col, corr_row                    
#    
#    while mono_index < len(monopix_data):
#         
#        mono_tlu=monopix_data[mono_index]["event_number"]
#        mono_col=monopix_data[mono_index]["column"]
#        mono_row=monopix_data[mono_index]["row"]
#        fe_i=fe_index
#         
#        if mono_tlu >= fe_data[-1]["trigger_number"]:
#            break
#         
#        while fe_i < len(fe_data):
#            if fe_data[fe_i]["trigger_number"] < mono_tlu:
#                fe_i=fe_i+1
#                fe_index=fe_index+1
#                pass
#            elif fe_data[fe_i]["trigger_number"] == mono_tlu:
#                corr_col[fe_data[fe_i]['column']][mono_col] += 1
#                corr_row[fe_data[fe_i]['row']][mono_row] += 1
#                fe_i=fe_i+1
#            else:
#                break
#            
#        mono_index=mono_index+1
#        
#    return fe_index,mono_index,corr_col,corr_row


class HitCorrelator(Transceiver):

    def setup_transceiver(self):

        self.set_bidirectional_communication()  # We want to be able to change the histogrammer settings

    def setup_interpretation(self):

        # variables to determine whether to do sth or not
        self.active_tab = None  # stores name (str) of active tab in online monitor
        self.hit_corr_tab = None  # store name (str) of hit_correlator tab FIXME: get name of receiver instead
        self.start_signal = 0  # will be set in handle_command function; correlation starts if this is set to 0
        # variables to store integer value of active duts
        self.active_dut1 = 0
        self.active_dut2 = 1
        # variables fps
        self.fps = 0
        self.updateTime = 0
        # remove noisy background
        self.remove_background = False
        self.remove_background_checkbox = 0
        self.remove_background_percentage = 99.0
        # transpose cols and rows due to fei4 rotation
        self.transpose = True  # this is true for our setup
        self.transpose_checkbox = 0
        # data buffer and histogramms
        # the data does not have to arrive at the same receive command
        # since ZMQ buffers data and the DUT can have different time behavior
        self.fe_buffer = None
        self.monopix_buffer = None
        # must be a np.array with dimensions cols x cols;
        # will be set by get_hist_size function in handle_command function
        if self.transpose == True:
            self.hist_cols_corr = np.zeros([self.config['max_n_rows_monopix'],self.config['max_n_columns_fei4']])
            self.hist_rows_corr = np.zeros([self.config['max_n_columns_monopix'],self.config['max_n_rows_fei4']])
        else:
            self.hist_cols_corr = np.zeros([self.config['max_n_columns_monopix'],self.config['max_n_columns_fei4']])
            self.hist_rows_corr = np.zeros([self.config['max_n_rows_monopix'],self.config['max_n_rows_fei4']])
        
        #self.hist_cols_corr = np.zeros([337,337])
        #self.hist_rows_corr = np.zeros([337,337])
        # must be a np.array with dimensions rows x rows; will be set by get_hist_size function in handle_command
        # function
        self.mono_builder=BuildWithTlu()

#       # make measurements of avg cpu load and memory
#       self.procss = psutil.Process(self.ident)
#       self.prs_avg_cpu = 0
#       self.avg_cpu = 0
#       self.n = 1.0
#       self.avg_ram = 0

    def deserialize_data(self, data):  # According to pyBAR data serialization

        datar, meta = utils.simple_dec(data)
        if 'hits' in meta:
            meta['hits'] = datar
        return meta

    def interpret_data(self, data):

#        if self.active_tab != self.hit_corr_tab:  # if active tab in online monitor is not hit correlator, return
#            return

        #print "data[0][0]", data[0][0]
        if 'meta_data' in data[0][1]:

            meta_data = data[0][1]['meta_data']
            now = float(meta_data['timestamp_stop'])

            # FIXME: sometimes = ZeroDivisionError: because of https://github.com/SiLab-Bonn/pyBAR/issues/48
            if now != self.updateTime:

                recent_fps = 1.0 / (now - self.updateTime)  # FIXME: shows recorded data rate not current rate
                self.updateTime = now
                self.fps = self.fps * 0.7 + recent_fps * 0.3
                meta_data.update({'fps': self.fps})
                return [data[0][1]]

        # loop over data and determine whether it is fe or monopix data
        for actual_dut_data in data:

            if 'meta_data' in actual_dut_data[1]:  # meta_data is skipped
                continue

            if actual_dut_data[1]['hits'].shape[0] == 0:  # empty array is skipped
                continue
        
            if 'te' in actual_dut_data[1]['hits'].dtype.names:  # MONOPIX data has keyword 'te'
                tmp = actual_dut_data[1]['hits']
                monopix_hits=self.mono_builder.run(tmp,rx_shift=3,rx_stop=96,
                             row_offset=1,row_factor=1,col_offset=1,col_factor=1,tr=self.transpose,debug=0)
                
                #print "MONO DATA====",len(tmp[tmp["col"]==0xFF]), len(monopix_hits)
 
                if self.monopix_buffer==None:
                     self.monopix_buffer=monopix_hits
                else:
                     self.monopix_buffer = np.append(self.monopix_buffer, monopix_hits)

            else:  # fe data
                fe_hits = actual_dut_data[1]['hits']
                #print "FEI4 data ====", len(fe_hits)
                if self.fe_buffer==None:
                     self.fe_buffer=fe_hits
                else:
                     self.fe_buffer = np.append(self.fe_buffer, fe_hits)

        # if one of the data buffer keys data is empty return

        if isinstance(self.fe_buffer,type(None)) or isinstance(self.monopix_buffer,type(None)):
            return
        elif len(self.fe_buffer) == 0 or len(self.monopix_buffer) == 0:
            return
#        print "============== corr buffersize",self.fe_buffer[0],self.fe_buffer[-1],  
#        print self.monopix_buffer[0],self.monopix_buffer[-1], 
#        print len(self.fe_buffer), len(self.monopix_buffer)
        
        def remove_background(cols_corr, rows_corr, percentage):
            cols_corr[cols_corr < np.percentile(cols_corr, percentage)] = 0
            rows_corr[rows_corr < np.percentile(rows_corr, percentage)] = 0

        

        # make correlation
        (fe_index,mono_index,self.hist_cols_corr, self.hist_rows_corr
             ) = correlate_ff(
            self.fe_buffer,self.monopix_buffer,self.hist_cols_corr, self.hist_rows_corr)
        
        self.fe_buffer = np.delete(self.fe_buffer, np.arange(0, fe_index))
        self.monopix_buffer = np.delete(self.monopix_buffer, np.arange(0, mono_index))

        if self.remove_background:
            remove_background(self.hist_cols_corr, self.hist_rows_corr, self.remove_background_percentage)
        
#        print "============== corr send data",np.sum(self.hist_cols_corr),np.sum(self.hist_rows_corr)
        return [{'column': self.hist_cols_corr, 'row': self.hist_rows_corr}]


    def serialize_data(self, data):

        return jsonapi.dumps(data, cls=utils.NumpyEncoder)
        # return utils.simple_enc(None, data)

    def handle_command(self, command):

        # declare functions
        # reset histogramms and data buffer, call garbage collector
        def reset():

            self.hist_cols_corr = np.zeros_like(self.hist_cols_corr)
            self.hist_rows_corr = np.zeros_like(self.hist_rows_corr)
            self.fe_buffer = None
            self.monopix_buffer = None
            self.mono_builder.reset()
            gc.collect()  # garbage collector is called to free unused memory

        
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

            self.remove_background_percentage = float(command[0].split()[1])

            if self.remove_background:

                reset()

        elif 'TRANSPOSE' in command[0]:

            self.transpose_checkbox = int(command[0].split()[1])

            if self.active_dut1 == 0 or self.active_dut2 == 0:

                if self.transpose_checkbox == 0:  # transpose_checkbox is not checked

                    self.transpose = True

                elif self.transpose_checkbox == 2:  # transpose_checkbox is checked

                    self.transpose = False

                #get_hist_size(self.active_dut1, self.active_dut2, self.transpose)
