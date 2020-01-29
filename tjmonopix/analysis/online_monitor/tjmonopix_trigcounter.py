''' Histograms the Mimosa26 hit table'''

import numpy as np
from numba import njit

# Online monitor imports
from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils

class TJMonopixTrigCounter(Transceiver):

    def setup_transceiver(self):
        self.set_bidirectional_communication()  # We want to be able to change the histogrammmer settings

    def setup_interpretation(self):
        self.n_tlu=0
        self.n_tlu_ts=0
        self.n_hit=0
        self.n_tdc=0
        self.tot = np.zeros(256, dtype=np.int32)

        # Variables for meta data time calculations
        self.readout = 0
        self.ts_last_readout = 0.  # Time stamp last readout
        self.hits_last_readout = 0.  # Number of hits
        self.events_last_readout = 0.  # Number of events
        self.fps = 0.  # Readouts per second
        self.hps = 0.  # Hits per second
        self.eps = 0.  # Events per second

        self.total_hits = 0
        self.total_events = 0

    def deserialze_data(self, data):
        # return jsonapi.loads(data, object_hook=utils.json_numpy_obj_hook)
        datar, meta = utils.simple_dec(data)
        if 'hits' in meta:
            meta['hits'] = datar
        return meta

    def interpret_data(self, data):
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
                self.n_tlu=0
                self.n_tlu_ts=0
                self.n_hit=0
                self.n_tdc=0
                self.tot = np.zeros(256, dtype=np.int32)
                self.readout = 0

        hit_data = data[0][1]['hits']
        self.n_hit = self.n_hit + len(np.argwhere(np.bitwise_and(hit_data["col"]<112,hit_data["cnt"]==0))) 
        self.n_tlu=self.n_tlu + len(np.argwhere(hit_data["col"]==255))
        self.n_tlu_ts=self.n_tlu_ts+ len(np.argwhere(hit_data["col"]==252))
        self.n_ts = self.n_ts + len(np.argwhere(hit_data["col"]==254))
        hit_data =hit_data[hit_data["col"]==253]
        self.n_tdc = self.n_tdc + len(hit_data)
        if len(hit_data)!=0:
            self.tot = self.tot + np.histogram(hit_data,bins=np.arange(0,256,1))[0]
        if self.mask_noisy_pixel:   #Improve
            self.occupancy[self.occupancy > np.percentile(self.occupancy, 100 - self.config['noisy_threshold'])] = 0

        histogrammed_data = {
            'tot': self.tot
        }
        
        return [histogrammed_data]

    def serialze_data(self, data):
        # return jsonapi.dumps(data, cls=utils.NumpyEncoder)

        if 'occupancies' in data:
            hits_data = data['tot']
            data['tot'] = None
            return utils.simple_enc(hits_data, data)
        else:
            return utils.simple_enc(None, data)

    def handle_command(self, command):
        if command[0] == 'RESET':
            self.tot = np.zeros(256, dtype=np.int32)  # Reset occ hists
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
