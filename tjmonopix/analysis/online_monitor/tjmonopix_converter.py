from online_monitor.converter.transceiver import Transceiver
from zmq.utils import jsonapi
import numpy as np
from numba import njit

from online_monitor.utils import utils
from tjmonopix.analysis.interpreter import get_row, get_col, get_tot, is_tjmono_data0


@njit
def hist_occupancy(occ, tot, hits, pix):
    for hit_i in range(hits.shape[0]):
        occ[hits[hit_i]["col"], hits[hit_i]["row"]] += 1
        if pix[0] == 0xFFFF and pix[1] == 0xFFFF:
            tot[hits[hit_i]["tot"]] += 1
        elif pix[0] == hits[hit_i]["col"] and pix[1] == hits[hit_i]["row"]:
            tot[hits[hit_i]["tot"]] += 1


class TJMonopixConverter(Transceiver):
    def setup_transceiver(self):
        """ Called at the beginning

            We want to be able to change the histogrammmer settings
            thus bidirectional communication needed
        """

        self.set_bidirectional_communication()

    def setup_interpretation(self):

        self.noisy_pixel_threshold = self.config.get("noisy_pixel_threshold", 1)

        # Init result hists
        self.reset_hists()

        # Variables for meta data time calculations
        self.ts_last_readout = 0.0  # Time stamp last readout
        self.hits_last_readout = 0.0  # Number of hits
        self.events_last_readout = 0.0  # Number of events in last chunk
        self.fps = 0.0  # Readouts per second
        self.hps = 0.0  # Hits per second
        self.eps = 0.0  # Events per second

        self.mask_noisy_pixel = False

    def deserialize_data(self, data):
        return utils.simple_dec(data)

    def _add_to_meta_data(self, meta_data):
        """ Meta data interpratation is deducing timings """

        ts_now = float(meta_data["timestamp_stop"])

        # Calculate readout per second with smoothing
        recent_fps = 1.0 / (ts_now - self.ts_last_readout)
        self.fps = self.fps * 0.95 + recent_fps * 0.05

        # Calulate hits per second with smoothing
        recent_hps = self.hits_last_readout * recent_fps
        self.hps = self.hps * 0.95 + recent_hps * 0.05

        # Calulate events per second with smoothing
        recent_eps = self.events_last_readout * recent_fps
        self.eps = self.eps * 0.95 + recent_eps * 0.05

        self.ts_last_readout = ts_now

        # Add info to meta data
        meta_data.update(
            {
                "fps": self.fps,
                "hps": self.hps,
                "total_hits": self.total_hits,
                "eps": self.eps,
                "total_events": self.total_events,
            }
        )
        return meta_data

    def interpret_data(self, data):
        raw_data, meta_data = data[0][1]
        meta_data = self._add_to_meta_data(meta_data)

        selection = is_tjmono_data0(raw_data)
        hits = np.zeros(
            shape=np.count_nonzero(selection),
            dtype=[("col", "u1"), ("row", "<u2"), ("tot", "u1")],
        )
        hits["col"] = get_col(raw_data[selection])
        hits["row"] = get_row(raw_data[selection])
        hits["tot"] = get_tot(raw_data[selection])
        self.total_hits += hits.shape[0]

        hist_occupancy(self.hist_occ, self.tot, hits, self.pix)

        if self.mask_noisy_pixel:  # Improve
            self.hist_occ[
                self.hist_occ
                > np.percentile(self.hist_occ, 100 - self.noisy_pixel_threshold)
            ] = 0

        interpreted_data = {
            "meta_data": meta_data,
            "occupancy": self.hist_occ,
            "tot_hist": self.tot,
        }

        return [interpreted_data]

    def serialize_data(self, data):
        return utils.simple_enc(None, data)

    def handle_command(self, command):
        if command[0] == "RESET":
            self.reset_hists()
        elif "MASK" in command[0]:
            if "0" in command[0]:
                self.mask_noisy_pixel = False
            else:
                self.mask_noisy_pixel = True
        elif "PIX_X" in command[0]:  # TODO get pixel from command
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
            value = command[0].split()[1]
            if "-1" in value:
                self.pix[0] = 0xFFFF
                self.pix[1] = 0xFFFF
            else:
                self.pix[0] = int(value)
        elif "PIX_Y" in command[0]:  # TODO get pixel from command
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists
            value = command[0].split()[1]
            if "-1" in value:
                self.pix[0] = 0xFFFF
                self.pix[1] = 0xFFFF
            else:
                self.pix[1] = int(value)
        else:
            self.n_readouts = int(command[0])
            self.occupancy = np.zeros(
                shape=(112, 224), dtype=np.int32
            )  # Reset occ hists
            self.tot = np.zeros(64, dtype=np.int32)  # Reset occ hists

    def reset_hists(self):
        """ Reset the histograms """
        self.total_hits = 0
        self.total_events = 0
        # Readout number
        self.readout = 0
        self.hist_occ = np.zeros(shape=(112, 224), dtype=np.int32)
        self.tot = np.zeros(64, dtype=np.int32)
        # self.tdc = np.zeros(0xFFF, dtype=np.int32)
        self.pix = [
            0xFFFF,
            0xFFFF,
        ]  # [col,row] for single pixel, [0xFFFF,0xFFFF] for all pixel

