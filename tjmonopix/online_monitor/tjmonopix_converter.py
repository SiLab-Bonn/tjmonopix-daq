from online_monitor.converter.transceiver import Transceiver
from zmq.utils import jsonapi
import numpy as np

from online_monitor.utils import utils
from tjmonopix.analysis.interpreter import InterRaw

class TJMonopixConverter(Transceiver):

    def setup_interpretation(self):
        self.n_hits = 0
        self.n_events = 0
        self.inter=InterRaw()

    def deserialze_data(self, data):
        try:
            self.meta_data = jsonapi.loads(data)
        except ValueError:
            try:
                dtype = self.meta_data.pop('dtype')
                shape = self.meta_data.pop('shape')
                if self.meta_data:
                    try:
                        raw_data_array = np.frombuffer(buffer(data), dtype=dtype).reshape(shape)
                        return raw_data_array
                    except (KeyError, ValueError):  # KeyError happens if meta data read is omitted; ValueError if np.frombuffer fails due to wrong sha
                        return None
            except AttributeError:  # Happens if first data is not meta data
                return None
        return {'meta_data': self.meta_data}

    def interpret_data(self, data):
        if isinstance(data[0][1], dict):  # Meta data is omitted, only raw data is interpreted
            # Add info to meta data
            data[0][1]['meta_data'].update({'n_hits': self.n_hits, 'n_events': self.n_events})
            return [data[0][1]]
        
        hits=self.inter.run(data[0][1],data_format=3)
        self.n_hits = hits.shape[0]
        
        interpreted_data = {
            'hits': hits
        }

        return [interpreted_data]

    def serialze_data(self, data):
        # return jsonapi.dumps(data, cls=utils.NumpyEncoder)
    
        if 'hits' in data:
            hits_data = data['hits']
            data['hits'] = None
            return utils.simple_enc(hits_data, data)
        else:
            return utils.simple_enc(None, data)
