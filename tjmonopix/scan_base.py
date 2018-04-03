import os
import logging
import basil
import yaml
import time
import numpy as np
import tables as tb

from contextlib import contextmanager
from tjmonopix import TJMonoPix
from fifo_readout import FifoReadout
import online_monitor.sender


class ScanBase(object):
    """
    Basic run meta class
    """

    def __init__(self, dut=None, filename=None, send_addr="tcp://127.0.0.1:5500"):
        # if DUT instance is not passed as argument, initialize it
        if isinstance(dut, TJMonoPix):
            self.dut = dut
        else:
            self.dut = TJMonoPix(conf=dut)
            # Initialize self.dut and power up
            self.dut.init()
            #self.dut['CONF']['DEF_CONF_N'] = 0
            #self.dut['CONF']['AB_SELECT'] = 1
            #self.dut['CONF'].write()

            #self.dut['data_rx'].CONF_START_FREEZE = 15 #default 3
            #self.dut['data_rx'].CONF_STOP_FREEZE = 100 #default 40
            ##self.dut['data_rx'].CONF_STOP_FREEZE = 250 #default 40
            #self.dut['data_rx'].CONF_START_READ = 35 #default 6
            #self.dut['data_rx'].CONF_STOP_READ = 37 #default 7
            #self.dut['data_rx'].CONF_STOP = 105 #default 45
            ##self.dut['data_rx'].CONF_STOP = 255 #default 45

            #self.dut.power_on()

            #self.dut['CONF']['RESET_BCID'] = 1
            #self.dut['CONF']['RESET'] = 1
            #self.dut['CONF'].write()

            #self.dut['CONF']['EN_BX_CLK'] = 1
            #self.dut['CONF']['EN_OUT_CLK'] = 1
            #self.dut['CONF'].write()
             
            #self.dut['CONF']['RESET_BCID'] = 0
            #self.dut['CONF']['RESET'] = 0
            #self.dut['CONF'].write()

            #self.dut.default_conf()

            #-------------------------------------------------#
            #self.dut.set_icasn_dacunits(0,0)
            #self.dut.set_vreset_dacunits(35,0)
            #self.dut.set_ireset_dacunits(5,1,0)
            #self.dut.set_ithr_dacunits(30,0)
            #self.dut.set_idb_dacunits(50,0)

            #self.dut['CONF_SR']['EN_HV'].setall(False)
            #self.dut['CONF_SR']['EN_COMP'].setall(False)
            #self.dut['CONF_SR']['EN_PMOS'].setall(False)
            #self.dut['CONF_SR']['EN_PMOS_NOSF'].setall(False)
            #self.dut['CONF_SR']['EN_TEST_PATTERN'].setall(False)

            #self.dut['CONF_SR']['MASKD'].setall(False)
            #self.dut['CONF_SR']['MASKH'].setall(False)
            #self.dut['CONF_SR']['MASKV'].setall(False)

            #self.dut.write_conf()

            #self.dut['CONF']['DEF_CONF_N'] = 1
            #self.dut['CONF'].write()

            # SELECT WHICH DOUBLE COLUMNS TO ENABLE
            #self.dut['CONF_SR']['EN_PMOS_NOSF'].setall(False)
            #self.dut['CONF_SR']['EN_PMOS'].setall(False)
            #self.dut['CONF_SR']['EN_COMP'].setall(False)
            #self.dut['CONF_SR']['EN_HV'].setall(False)
            #self.dut['CONF_SR']['EN_OUT'].setall(False) #ENABLES OR DISABLES THE NORMAL OUTPUT PADS, ACTIVE LOW
            #self.dut['CONF_SR']['nEN_OUT'].setall(True) #ENABLES OR DISABLES THE COMPLEMENTARY OUTPUT PADS, ACTIVE LOW
            #self.dut['CONF_SR']['EN_HITOR_OUT'].setall(True) #ENABLES OR DISABLES THE NORMAL HITOR PADS, HITOR0-3 =  1-4 flavor, ACTIVE LOW
            #self.dut['CONF_SR']['nEN_HITOR_OUT'].setall(True) #ENABLES OR DISABLES THE COMPLEMENTARY HITOR PADS, ACTIVE LOW

            #self.dut['CONF_SR']['EN_PMOS'][9] = 1
            self.dut['CONF_SR']['EN_PMOS'].setall(True)
            #self.dut['CONF_SR']['EN_HITOR_OUT'][1] = 0

            # SELECT WHICH PHYSICAL COLUMNS, ROWS, DIAGONALS TO MASK
            # TO MASK ONE PIXEL, MASKV, MASKH and MASKD OF THIS PIXEL SHOULD BE 0 (FALSE)
            # THE MASKD NUMBER OF THE PIXEL WE WANT TO MASK (or UNMASK), IS GIVEN BY: MASKD = PHYSCOL- PHYSROW
            # IF PHYSCOL-PHYSROW<0, then MASKD = 448+PHYSCOL-PHYSROW
            self.dut['CONF_SR']['MASKD'].setall(True)
            self.dut['CONF_SR']['MASKH'].setall(True)
            self.dut['CONF_SR']['MASKV'].setall(True)

            # TO USE THE MASK FUNCTION YOU MUST INPUT THE FLAVOR, COLUMN AND ROW
            # THE FLAVOR NUMERS IS: 0 FOR PMOS_NOSF, 1 FOR PMOS, 2 FOR COMP, 3 FOR HV
            self.dut.mask(1, 33, 72)
            self.dut.mask(1, 17, 30)
            self.dut.mask(1, 19, 31)
            self.dut.mask(1, 41, 66)
            self.dut.mask(1, 97, 94)
            self.dut.mask(1, 34, 151)
            self.dut.mask(1, 40, 123)
            self.dut.mask(1, 82, 193)
            self.dut.mask(1, 71, 31)
            self.dut.mask(1, 71, 111)
            self.dut.mask(1, 38, 188)
            self.dut.mask(1, 97, 214)
            self.dut.mask(1, 86, 104)
            self.dut.mask(1, 35, 212)
            self.dut.mask(1, 35, 88)
            self.dut.mask(1, 43, 14)
            self.dut.mask(1, 38, 177)
            self.dut.mask(1, 17, 57)
            self.dut.mask(1, 54, 1)
            self.dut.mask(1, 38, 21)
            self.dut.mask(1, 71, 9)
            self.dut.mask(1, 58, 46)
            self.dut.mask(1, 74, 84)
            self.dut.mask(1, 53, 167)
            self.dut.mask(1, 35, 158)
            self.dut.mask(1, 72, 77)
            self.dut.mask(1, 14, 54)
            self.dut.mask(1, 78, 196)
            self.dut.mask(1, 88, 96)
            self.dut.mask(1, 78, 209)

            # SELECT WHICH PHYSICAL COLUMS TO INJECT
            # INJ_IN_MON_L AND INJ_IN_MON_L SELECT THE LEFT AND RIGHT SPECIAL ANALOG MONITORING PIXELS
            #self.dut['CONF_SR']['COL_PULSE_SEL'].setall(False)

            #self.dut['CONF_SR']['INJ_IN_MON_L'] = 0 # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS LEFT SIDE
            #self.dut['CONF_SR']['INJ_IN_MON_R'] = 0 # ENABLE INJECTION FOR THE ANALOG MONITORING PIXELS RIGHT SIDE

            # SELECT WHICH PHYSICAL ROWS TO INJECT
            # THE SPEXIAL PIXELS OUTA_MON3 to OUTA_MON0 CORRESPONT TO ROWS 223 to 220 FOR INJECTION
            #self.dut['CONF_SR']['INJ_ROW'].setall(False)
            #self.dut['CONF_SR']['INJ_ROW'][223:220] = True # FOR THE ANALOG MONITORING TOP PIXEL

            # SELECT PHYSICAL COLUMNS AND ROWS FOR INJECTION WITH FUNCTION
            #self.dut.enable_injection(1,18,99)

            # SELECT PHYSICAL COLUMN(S) FOR HITOR OUTPUT
            # nMASKH (SO SETTING MASKH TO FALSE) ENABLES HITOR FOR THE SPECIFIC ROW
            #self.dut['CONF_SR']['DIG_MON_SEL'].setall(False)
            #self.dut.enable_column_hitor(1,18)

            self.dut.write_conf()

            ## SET THE INJECTION PULSE AMPLITUDE
            ## 128-bit DAC (7-bit binary equivalent)
            ## SET THE VOLTAGES IN ONE HOT ENCODING, ONLY ONE BIT ACTIVE AT A TIME.
            ## V = (127/1.8)*#BIT
            # The default values are VL=44, VH=79, VH-VL=35
            # VDAC LSB=14.17mV, Cinj=230aF, 1.43e-/mV, ~710e-
            #self.dut.set_vl_dacunits(44,1)
            #self.dut.set_vh_dacunits(79,1)

            ####### CONFIGURE THE FRONT END ######

            # SET VRESET_P, THIS IS THE BASELINE OF THE FRONT END INPUT, ONE HOT ENCODING
            self.dut.set_vreset_dacunits(35,1) #1V

            ## 128-bit DAC (7-bit binary equivalent)
            ## SET THE CURRENTS USING THERMOMETER ENCODING, I = #BITS_ACTIVE*140nA*SCALING, SCALING IS DIFFERENT FOR EACH CURRENT
            ## SCALING: IBIAS=10, IDB=16, ITHR=0.125, ICASN=4, IRESET=0.03125
            ## ACTIVE BITS SHOULD BE SET STARTING FROM THE MIDDLE e.g. for 15 active bits, (128-15)/2=56,5 so 56zeros,15ones,57zeros
            ## Thus, Ix[71:57] = True

            # SET ICASN, THIS CURRENT CONTROLS THE OUTPUT BASELINE, BE CAREFUL NOT TO SET IT TO HIGH
            # ALWAYS MONITOR THE POWER AFTER SETTING ICASN. IF VDDD IS SEVERAL mA, REDUCE IT UNTIL IT RETURNS TO 0
            # ICASN MAINLY CONTROLS THE THRESHOLD
            self.dut.set_icasn_dacunits(0,1) #4.375nA # approx 1.084V at -3V backbias, 600mV at 0V backbias

            # SET IRESET, THIS CURRENT CONTROLS THE RESET RATE OF THE FRONT END INPUT (ALSO THE THRESHOLD)
            self.dut.set_ireset_dacunits(2,1,1) #270pA, HIGH LEAKAGE MODE, NORMAL SCALING, 0 = LOW LEAKAGE MODE, SCALING*0.01

            # SET ITHR, THIS CURRENT CONTROLS THE RESET RATE OF THE OUTPUT (AND THE THRESHOLD)
            self.dut.set_ithr_dacunits(5,1) #680pA

            # SET ITHR, THIS CURRENT CONTROLS THE BIASING OF THE DISCRIMINATOR (AND THE THRESHOLD)
            self.dut.set_idb_dacunits(15,1) #500nA

            # SET IBIAS, THIS CURRENT IS THE DC CURRENT OF THE MAIN BRANCH
            self.dut.set_ibias_dacunits(50,1) #500nA OF THE FRONT END THAT PROVIDES AMPLIFICATION
            # IT CONTROLS MAINLY THE RISE TIME
            self.dut.set_ibias_dacunits(50,1) #500nA

            ############ ENABLE THE DAC CURRENT MONITORING ###########
            # self.dut['CONF_SR']['SWCNTL_DACMONI'] = 0

            ########## SET THE BIAS CURRENTS OF THE TWO STAGE SOURCE FOLLOWER THAT BUFFERS THE ANALOG MONITORING VOLTAGES #########
            # CONTROLS THE RESPONSE TIME AND THE LEVEL SHIFT OF THE BUFFER
            # self.dut['CONF_SR']['SET_IBUFN_L'] = 0b1001
            # self.dut['CONF_SR']['SET_IBUFP_L'] = 0b0101

            self.dut.write_conf()

            
        if filename == None:
            self.working_dir = os.path.join(os.getcwd(), "output_data")
            self.run_name = time.strftime("%Y%m%d_%H%M%S_") + self.scan_id
        else:
            self.working_dir = os.path.dirname(os.path.realpath(filename))
            self.run_name = os.path.basename(os.path.realpath(filename))
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.output_filename = os.path.join(self.working_dir, self.run_name)

        #### Online Monitor
        self.socket=send_addr

        self.logger = logging.getLogger()
        flg=0
        for l in self.logger.handlers:
            if isinstance(l, logging.FileHandler):
               flg=1
               fh=l
        if flg==0:
            fh = logging.FileHandler(self.output_filename + '.log')
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s"))
            fh.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        logging.info("Initializing {0}".format(self.__class__.__name__))

    def start(self, **kwargs):

        #### open file
        self.h5_file = tb.open_file(self.output_filename+'.h5' , mode="w", title="")
        self.raw_data_earray = self.h5_file.create_earray(
            self.h5_file.root,
            name="raw_data",
            atom=tb.UIntAtom(),
            shape=(0,),
            title="Raw data",
            filters=tb.Filters(complib="blosc", complevel=5, fletcher32=False))
        self.meta_data_table = self.h5_file.create_table(
            self.h5_file.root,
            name='meta_data',
            description=MetaTable,
            title='meta_data',
            filters=tb.Filters(complib='zlib', complevel=5, fletcher32=False))
        self.meta_data_table.attrs.kwargs = yaml.dump(kwargs)

        ### open socket for monitor
        if (self.socket==""): 
            self.socket=None
        else:
            try:
                self.socket=online_monitor.sender.init(self.socket)
                self.logger.info('ScanBase.start:data_send.data_send_init connected')
            except:
                self.logger.warn('ScanBase.start:data_send.data_send_init failed addr=%s'%self.socket)
                self.socket=None

        ### save kwargs       
        self.logger.info('self.dut Status: %s', str(self.dut.get_power_status()))
        self.meta_data_table.attrs.kwargs = yaml.dump(kwargs)

        ### execute scan       

        self.fifo_readout = FifoReadout(self.dut)
        self.scan(**kwargs)
        self.fifo_readout.print_readout_status()

        ### execute scan 
        status=self.dut.get_power_status()
        self.logger.info('self.dut Status: %s', str(status))
        self.meta_data_table.attrs.status=yaml.dump(status)
        self.meta_data_table.attrs.status=yaml.dump(self.dut.get_configuration())

        ### close file
        self.h5_file.close()

        ### close socket
        if self.socket!=None:
           try:
               online_monitor.sender.close(self.socket)
           except:
               pass
        return self.output_filename 

    @contextmanager
    def readout(self, *args, **kwargs):
        """

        """
        self._start_readout(*args, **kwargs)
        yield
        self._stop_readout()

    def _start_readout(self,*args, **kwargs):
        callback = kwargs.pop('callback', self._handle_data)
        clear_buffer = kwargs.pop('clear_buffer', False)
        fill_buffer = kwargs.pop('fill_buffer', False)
        reset_sram_fifo = kwargs.pop('reset_sram_fifo', False)
        errback = kwargs.pop('errback', self._handle_err)
        no_data_timeout = kwargs.pop('no_data_timeout', None)
        self.scan_param_id = kwargs.pop('scan_param_id', 0)
        self.fifo_readout.start(reset_sram_fifo=reset_sram_fifo,
                                fill_buffer=fill_buffer,
                                clear_buffer=clear_buffer,
                                callback=callback,
                                errback=errback,
                                no_data_timeout=no_data_timeout)

    def _stop_readout(self):
        self.fifo_readout.stop()

    def _handle_data(self, data_tuple):

        total_words = self.raw_data_earray.nrows
        len_raw_data = data_tuple[0].shape[0]

        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()

        len_raw_data = data_tuple[0].shape[0]
        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['error'] = data_tuple[3]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row['scan_param_id'] = self.scan_param_id
        self.meta_data_table.row.append()
        self.meta_data_table.flush()

        if self.socket!=None:
            try:
                online_monitor.sender.send_data(self.socket,data_tuple)
            except:
                self.logger.warn('ScanBase.hadle_data:sender.send_data failed')
                try:
                    online_monitor.sender.close(self.socket)
                except:
                    pass
                self.socket=None

    def _handle_err(self, exc):
        msg = str(exc[1])
        if msg:
            self.logger.error(msg)
        else:
            self.logger.error("Aborting run...")


class MetaTable(tb.IsDescription):
    index_start = tb.UInt32Col(pos=0)
    index_stop = tb.UInt32Col(pos=1)
    data_length = tb.UInt32Col(pos=2)
    timestamp_start = tb.Float64Col(pos=3)
    timestamp_stop = tb.Float64Col(pos=4)
    scan_param_id = tb.UInt16Col(pos=5)
    error = tb.UInt32Col(pos=6)
