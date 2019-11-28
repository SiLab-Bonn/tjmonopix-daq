import time
import yaml

from tjmonopix.scan_base import ScanBase

class SourceScan(ScanBase):
    scan_id = "source_scan"

    def scan(self, **kwargs):
        with_tj = kwargs.pop('with_tj', True)
        with_tlu = kwargs.pop('with_tlu', True)
        with_rx1 = kwargs.pop('with_rx1', True)
        with_mon = kwargs.pop('with_mon', True)
        scan_timeout = kwargs.pop('scan_time', 10)

        cnt = 0
        scanned = 0

        # Stop readout and clean FIFO
        self.dut.stop_all()
        self.dut['fifo'].reset()

        # Start readout
        if with_tj:
            self.dut.set_monoread()
        for _ in range(5):  # Reset FIFO to clean up
            time.sleep(0.05)
            self.dut['fifo'].reset()
        if with_mon:
            self.dut.set_timestamp("mon")
        if with_tlu:
            tlu_delay = kwargs.pop('tlu_delay', 8)
            self.dut.set_tlu(tlu_delay)
        if with_rx1:
            self.dut.set_timestamp("rx1")

        self.dut.reset_ibias()

        # Start FIFO readout
        with self.readout(scan_param_id=0, fill_buffer=False, clear_buffer=True, readout_interval=0.2, timeout=0):
            t0 = time.time()
            self.logger.info(
                "*****{} is running **** don't forget to start tlu ****".format(self.__class__.__name__))
            while True:
                pre_cnt = cnt
                cnt = self.fifo_readout.get_record_count()
                pre_scanned = scanned
                scanned = time.time() - t0
                temp = self.dut.get_temperature()
                # TODO: log this to file only, let tqdm handle stdout
                self.logger.info('time=%.0fs dat=%d rate=%.3fk/s temp=%.2fC' %
                                 (scanned, cnt, (cnt - pre_cnt) / (scanned - pre_scanned) / 1024, temp))
                if scanned + 2 > scan_timeout and scan_timeout > 0:
                    break
                elif scanned < 30 or scanned + 60 > scan_timeout:
                    time.sleep(1)
                else:
                    time.sleep(60)
            time.sleep(max(0, scan_timeout - scanned))

        # Stop FIFO readout
        self.dut.stop_all()
        if with_rx1:
            self.meta_data_table.attrs.timestamp_status = yaml.dump(
                self.dut["timestamp_rx1"].get_configuration())
        if with_tlu:
            self.meta_data_table.attrs.tlu_status = yaml.dump(
                self.dut["tlu"].get_configuration())
            self.meta_data_table.attrs.timestamp_status = yaml.dump(
                self.dut["timestamp_tlu"].get_configuration())
        if with_mon:
            self.meta_data_table.attrs.timestamp_status = yaml.dump(
                self.dut["timestamp_mon"].get_configuration())
                
    @classmethod
    def analyze(self, data_file=None, event_build="none", clusterize=False):
        if data_file[-3:] ==".h5":
            fraw=data_file
        else:
            fraw = data_file + '.h5'
        print fraw
        analyzed_data_file=fraw[:-7]+"hit.h5"
        import tjmonopix.analysis.interpreter_old as interpreter
        interpreter.interpret_h5(fraw,analyzed_data_file)
        
        if event_build=="token":
            fhit=analyzed_data_file
            analyzed_data_file=fraw[:-7]+"ev.h5"
            import tjmonopix.analysis.event_builder_token as event_builder
            event_builder.build_h5(fhit,analyzed_data_file)
        elif event_build=="tlu":
            fhit=analyzed_data_file
            analyzed_data_file=fraw[:-7]+"ev.h5"
            import tjmonopix.analysis.event_builder2 as event_builder
            build_h5(fhit,analyzed_data_file,debug=0x0)
        
        if clusterize and (event_build=="token" or event_build=="tlu"):
           fev=analyzed_data_file
           analyzed_data_file=fraw[:-7]+"cl.h5"
           import tjmonopix.analysis.clusterizer as clusterizer
           clusterizer.clusterize_h5(fev,analyzed_data_file,col=3,row=3,frame=3)

        return analyzed_data_file

    @classmethod
    def plot(self, analyzed_data_file=None):
        if analyzed_data_file is None:
            analyzed_data_file = self.analyzed_data_file
        with plotting.Plotting(analyzed_data_file=analyzed_data_file) as p:
            p.create_standard_plots()


if __name__ == "__main__":
    scan = SimpleScan()
    scan.scan()
    scan.analyze()
    # SimpleScan.analyze("/media/silab/Maxtor/tjmonopix-data/measurements/source_scan/modified_process/pmos/W04R08_-6_-6_idb30.h5", create_plots=True)
