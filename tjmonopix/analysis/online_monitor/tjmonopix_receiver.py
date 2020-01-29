from online_monitor.receiver.receiver import Receiver
from zmq.utils import jsonapi
import numpy as np
import time

from PyQt5 import Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime
from pyqtgraph.dockarea import DockArea, Dock


from online_monitor.utils import utils


class TJMonopixReceiver(Receiver):
    def setup_receiver(self):
        self.set_bidirectional_communication()  # We want to change converter settings

    def setup_widgets(self, parent, name):
        dock_area = DockArea()
        parent.addTab(dock_area, name)
        # parent.setTabsClosable(True)

        # color occupancy plot
        poss = np.array([0.0, 0.6, 1.0])
        color = np.array(
            [[25, 25, 112, 255], [173, 255, 47, 255], [255, 0, 0, 255]], dtype=np.ubyte
        )  # [RED,GREEN,BLUE,BLACK/WHITE]
        cmap = pg.ColorMap(poss, color)
        lutt = cmap.getLookupTable(0.0, 1.0, 100)

        dock_occcupancy = Dock("Occupancy plane", size=(400, 800))
        dock_tot = Dock("ToT", size=(400, 800))
        dock_area.addDock(dock_occcupancy)
        dock_area.addDock(dock_tot, "right", dock_occcupancy)

        occupancy_graphics = pg.GraphicsLayoutWidget()  # Plot docks
        occupancy_graphics.show()
        view = occupancy_graphics.addViewBox()
        self.occupancy_image = pg.ImageItem(border="w")
        view.addItem(self.occupancy_image)
        self.occupancy_image.setLookupTable(lutt, update=True)
        # make plot with axes
        self.plot = pg.PlotWidget(
            viewBox=view, labels={"bottom": "Column", "left": "Row"}
        )
        self.plot.addItem(self.occupancy_image)
        dock_occcupancy.addWidget(self.plot)

        tot_plot_widget = pg.PlotWidget(background="w")
        self.tot_plot = tot_plot_widget.plot(
            np.linspace(-0.5, 15.5, 17), np.zeros((16)), stepMode=True
        )
        tot_plot_widget.showGrid(y=True)
        dock_tot.addWidget(tot_plot_widget)

        dock_status = Dock("Status", size=(800, 20))
        dock_area.addDock(dock_status, "top")

        # Status dock on top
        cw = QtGui.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        self.rate_label = QtGui.QLabel("Readout Rate\n0 Hz")
        self.hit_rate_label = QtGui.QLabel("Hit Rate\n0 Hz")
        self.event_rate_label = QtGui.QLabel("Event Rate\n0 Hz")
        self.timestamp_label = QtGui.QLabel("Data Timestamp\n")
        self.plot_delay_label = QtGui.QLabel("Plot Delay\n")
        self.scan_parameter_label = QtGui.QLabel("Scan Parameters\n")
        self.spin_box = Qt.QSpinBox(value=0)
        self.spin_box.setMaximum(1000000)
        self.spin_box.setSuffix(" Readouts")

        # Pixel selection
        self.xpixel_label = QtGui.QLabel("Pixel column: (-1 for all)")
        self.ypixel_label = QtGui.QLabel("Pixel row: (-1 for all)")

        self.xpixel = Qt.QSpinBox(value=-1)
        self.xpixel.setMaximum(112)
        self.xpixel.setMinimum(-1)
        self.xpixel.setSingleStep(1)

        self.ypixel = Qt.QSpinBox(value=-1)
        self.ypixel.setMaximum(224)
        self.ypixel.setMinimum(-1)
        self.ypixel.setSingleStep(1)

        self.reset_button = QtGui.QPushButton("Reset")
        self.noisy_checkbox = QtGui.QCheckBox("Mask noisy pixels")
        self.convert_checkbox = QtGui.QCheckBox("Axes in " + u"\u03BC" + "m")
        layout.addWidget(self.timestamp_label, 0, 0, 0, 1)
        layout.addWidget(self.plot_delay_label, 0, 1, 0, 1)
        layout.addWidget(self.rate_label, 0, 2, 0, 1)
        layout.addWidget(self.hit_rate_label, 0, 3, 0, 1)
        layout.addWidget(self.event_rate_label, 0, 4, 0, 1)
        layout.addWidget(self.scan_parameter_label, 0, 5, 0, 1)
        layout.addWidget(self.spin_box, 0, 6, 0, 1)
        layout.addWidget(self.noisy_checkbox, 0, 7, 0, 1)
        layout.addWidget(self.convert_checkbox, 0, 8, 0, 1)
        layout.addWidget(self.xpixel_label, 0, 9, 1, 1)
        layout.addWidget(self.xpixel, 1, 9, 1, 1)
        layout.addWidget(self.ypixel_label, 0, 10, 1, 1)
        layout.addWidget(self.ypixel, 1, 10, 1, 1)
        layout.addWidget(self.reset_button, 0, 11, 0, 1)
        dock_status.addWidget(cw)

        # Connect widgets
        self.reset_button.clicked.connect(lambda: self.send_command("RESET"))
        self.spin_box.valueChanged.connect(lambda value: self.send_command(str(value)))
        self.xpixel.valueChanged.connect(
            lambda value: self.send_command("PIX_X %d" % value)
        )
        self.ypixel.valueChanged.connect(
            lambda value: self.send_command("PIX_Y %d" % value)
        )
        self.noisy_checkbox.stateChanged.connect(
            lambda value: self.send_command("MASK %d" % value)
        )

        # Change axis scaling
        def scale_axes(scale_state):
            if scale_state == 0:
                self.plot.getAxis("bottom").setScale(1.0)
                self.plot.getAxis("left").setScale(1.0)
                self.plot.getAxis("bottom").setLabel("Columns")
                self.plot.getAxis("left").setLabel("Rows")
            elif scale_state == 2:
                self.plot.getAxis("bottom").setScale(250)
                self.plot.getAxis("left").setScale(50)
                self.plot.getAxis("bottom").setLabel("Columns / " + u"\u03BC" + "m")
                self.plot.getAxis("left").setLabel("Rows / " + u"\u03BC" + "m")

        self.convert_checkbox.stateChanged.connect(lambda value: scale_axes(value))
        self.plot_delay = 0

    def deserialize_data(self, data):
        return utils.simple_dec(data)[1]

    def _update_rate(self, fps, hps, recent_total_hits, eps, recent_total_events):
        self.rate_label.setText("Readout Rate\n{:.0f} Hz".format(fps))
        if self.spin_box.value() == 0:  # show number of hits, all hits are integrated
            self.hit_rate_label.setText("Total Hits\n%d" % int(recent_total_hits))
        else:
            self.hit_rate_label.setText("Hit Rate\n%d Hz" % int(hps))
        if self.spin_box.value() == 0:  # show number of events
            self.event_rate_label.setText("Total Events\n%d" % int(recent_total_events))
        else:
            self.event_rate_label.setText("Event Rate\n%d Hz" % int(eps))

    def handle_data(self, data):
        self.occupancy_image.setImage(data["occupancy"], autoDownsample=True)
        self.tot_plot.setData(
            x=np.linspace(-0.5, 63.5, 65),
            y=data["tot_hist"],
            fillLevel=0,
            brush=(0, 0, 255, 150),
        )

        self._update_rate(
            data["meta_data"]["fps"],
            data["meta_data"]["hps"],
            data["meta_data"]["total_hits"],
            data["meta_data"]["eps"],
            data["meta_data"]["total_events"],
        )
        self.timestamp_label.setText(
            "Data Timestamp\n%s"
            % time.asctime(time.localtime(data["meta_data"]["timestamp_stop"]))
        )
        # self.scan_parameter_label.setText("Scan Parameters\n%s" % ', '.join('%s: %s' % (str(key), str(val)) for key, val in data['meta_data']['scan_par_id'].iteritems()))
        now = ptime.time()
        self.plot_delay = (
            self.plot_delay * 0.9 + (now - data["meta_data"]["timestamp_stop"]) * 0.1
        )
        self.plot_delay_label.setText(
            "Plot Delay\n%s" % "not realtime"
            if abs(self.plot_delay) > 5
            else "%1.2f ms" % (self.plot_delay * 1.0e3)
        )
