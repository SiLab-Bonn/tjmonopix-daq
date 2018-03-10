''' Histograms the Mimosa26 hit table'''

import numpy as np
from numba import njit

# Online monitor imports
from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils


@njit
def fill_occupancy_hist(occ, tot, hits, pix):
    for hit_i in range(hits.shape[0]):
        occ[hits[hit_i]['col'], hits[hit_i]['row']] += 1
        if pix[0] == 0xFFFF and pix[1] == 0xFFFF:
              tot[hits[hit_i]['tot']] += 1
        elif pix[0] == hits[hit_i]['col'] and pix[1] == hits[hit_i]['row']:
              tot[hits[hit_i]['tot']] += 1

def apply_noisy_pixel_cut(hists, noisy_threshold):
     hists = hists[hists < noisy_threshold]

class TJMonopixHistogrammer(Transceiver):

    def setup_transceiver(self):
        self.set_bidirectional_communication()  # We want to be able to change the histogrammmer settings

    def setup_interpretation(self):
        self.occupancy = np.zeros(shape=(112,224), dtype=np.int32)
        self.tot = np.zeros(64, dtype=np.int32)
        # self.tdc = np.zeros(0xFFF, dtype=np.int32)
        self.pix= [0xFFFF,0xFFFF] #[25,64] #[0xFFFF,0xFFFF] ########[col,row] for single pixel [0xFFFF,0xFFFF] for all pixel
        # Variables
        self.n_readouts = 0
        self.readout = 0

        # Variables for meta data time calculations
        self.ts_last_readout = 0.  # Time stamp last readout
        self.hits_last_readout = 0.  # Number of hits
        self.events_last_readout = 0.  # Number of events
        self.fps = 0.  # Readouts per second
        self.hps = 0.  # Hits per second
        self.eps = 0.  # Events per second

        self.plot_delay = 0
        self.total_hits = 0
        self.total_events = 0
        self.updateTime = 1 # was 0 before adding timestamp_start_fornext
        self.mask_noisy_pixel = False
        self.timestamp_start_fornext = 0
        # Histogrammes from interpretation stored for summing
#         self.error_counters = None
#         self.trigger_error_counters = None

    def deserialze_data(self, data):
        # return jsonapi.loads(data, object_hook=utils.json_numpy_obj_hook)
        datar, meta = utils.simple_dec(data)
        if 'hits' in meta:
            meta['hits'] = datar
#            print "datar"
#            print len(datar)
#            print "-----"
        return meta


    def interpret_data(self, data):
        
#        print "data[0][1]"
#        print data
#        print "////////"
        if 'meta_data' in data[0][1]:  # Meta data is directly forwarded to the receiver, only hit data, event counters are histogramed; 0 from frontend index, 1 for data dict
            meta_data = data[0][1]['meta_data']
            ts_now = float(meta_data['timestamp_stop'])

            # Calculate readout per second with smoothing
            recent_fps = 1.0 / (ts_now - self.ts_last_readout)
            self.fps = self.fps * 0.95 + recent_fps * 0.05

            # Calulate hits per second with smoothing
            recent_hps = self.hits_last_readout * recent_fps
            self.hps = self.hps * 0.95 + recent_hps * 0.05

            # Calulate hits per second with smoothing
            recent_eps = self.events_last_readout * recent_fps
            self.eps = self.eps * 0.95 + recent_eps * 0.05

            self.ts_last_readout = ts_now

            meta_data.update({'fps': self.fps, 'hps': self.hps, 'total_hits': self.total_hits, 'eps': self.eps, 'total_events': self.total_events})
            return [data[0][1]]

        self.readout += 1

        if self.n_readouts != 0:  # 0 for infinite integration
            if self.readout % self.n_readouts == 0:
                self.occupancy = np.zeros(shape=(112,224), dtype=np.int32)  # Reset occ hists
                self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
                self.readout = 0

        hit_data = data[0][1]['hits']
        tmp = hit_data[hit_data["cnt"]==0] ## remove noise
        tmp = tmp[tmp["col"]<112] ## remove TLU and timestamp
        hits = np.recarray(len(tmp), dtype=[('col','u2'),('row','u2'),('tot','u1')]) 
        hits['tot'][:] = (tmp["te"] - tmp["le"]) & 0x3F
        hits['col'][:] = tmp["col"]
        hits['row'][:] = tmp["row"]

        #print hit_data

        tdc = hit_data[hit_data["cnt"] > 1]
        # print 'histogrammer tdc: ', tdc

        if hits.shape[0] == 0:  # Empty array
            return
        fill_occupancy_hist(self.occupancy, self.tot, hits, self.pix)
        #print "occupancy", np.sum(self.occupancy)
        

        if self.mask_noisy_pixel:   #Improve
            self.occupancy[self.occupancy > np.percentile(self.occupancy, 100 - self.config['noisy_threshold'])] = 0

        histogrammed_data = {
            'occupancies': self.occupancy,
            'tot': self.tot,
            'tdc': tdc
        }

        return [histogrammed_data]

    def serialze_data(self, data):
        # return jsonapi.dumps(data, cls=utils.NumpyEncoder)

        if 'occupancies' in data:
            hits_data = data['occupancies']
            data['occupancies'] = None
            return utils.simple_enc(hits_data, data)
        else:
            return utils.simple_enc(None, data)

    def handle_command(self, command):
        if command[0] == 'RESET':
            self.occupancy = np.zeros(shape=(112,224), dtype=np.int32)  # Reset occ hists
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
            self.total_hits = 0
            self.total_events = 0
        elif 'MASK' in command[0]:
            if '0' in command[0]:
                self.mask_noisy_pixel = False
            else:
                self.mask_noisy_pixel = True
        elif 'PIX_X' in command[0]: ### TODO get pixel from command
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
            value=command[0].split()[1]
            if '-1' in value:
                self.pix[0]=0xFFFF
                self.pix[1]=0xFFFF
            else:
                self.pix[0]=int(value)
        elif 'PIX_Y' in command[0]: ### TODO get pixel from command
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
            value=command[0].split()[1]
            if '-1' in value:
                self.pix[0]=0xFFFF
                self.pix[1]=0xFFFF
            else:
                self.pix[1]=int(value)
        else:
            self.n_readouts = int(command[0])
            self.occupancy = np.zeros(shape=(112,224), dtype=np.int32)  # Reset occ hists
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
