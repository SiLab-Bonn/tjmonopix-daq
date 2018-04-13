from online_monitor.receiver.receiver import Receiver
from zmq.utils import jsonapi
import numpy as np
import time

from PyQt5 import Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from pyqtgraph.dockarea import DockArea, Dock

from online_monitor.utils import utils

class HitCorrelator(Receiver):

    def setup_receiver(self):
        # We want to change converter settings
        self.set_bidirectional_communication()

        # Send name of Receiver Tab to converter to correlate only when looked at tab
        self.send_command('RECEIVER %s' % self.name)

    def setup_widgets(self, parent, name):

        self.occupancy_images_columns = {}
        self.occupancy_images_rows = {}

        dock_area = DockArea()
        parent.addTab(dock_area, name)
        # send active tab index to converter so it only does something when user is looking at corresponding receiver
        #parent.currentChanged.connect(lambda value: self.send_command('ACTIVETAB %s' % str(parent.tabText(value))))

        dock_status = Dock("status")
        dock_status.setMinimumSize(400, 90)
        dock_status.setMaximumHeight(110)
        dock_select_duts = Dock("Select DUT's")
        dock_select_duts.setMinimumSize(400, 90)
        dock_select_duts.setMaximumHeight(110)
        dock_corr_column = Dock('Column-correlation')
        dock_corr_column.setMinimumSize(400, 400)
        dock_corr_row = Dock('Row-correlation')
        dock_corr_row.setMinimumSize(400, 400)

        cb = QtGui.QWidget()
        layout0 = QtGui.QGridLayout()
        cb.setLayout(layout0)
        #self.combobox1 = Qt.QComboBox()
        #self.combobox1.addItems(DUTS)
        #self.combobox1.setMinimumSize(100, 50)
        #self.combobox1.setMaximumSize(200, 50)
        #self.combobox2 = Qt.QComboBox()
        #self.combobox2.addItems(DUTS)
        #self.combobox2.setMinimumSize(100, 50)
        #self.combobox2.setMaximumSize(200, 50)
        #self.select_label = QtGui.QLabel('Correlate:')
        #self.select_label1 = QtGui.QLabel('    to    ')
#        self.start_button = QtGui.QPushButton('Start')
#        self.stop_button = QtGui.QPushButton('Stop')
#        self.start_button.setMinimumSize(75, 38)
#        self.start_button.setMaximumSize(150, 38)
#        self.stop_button.setMinimumSize(75, 38)
#        self.stop_button.setMaximumSize(150, 38)
        layout0.setHorizontalSpacing(25)
        #layout0.addWidget(self.select_label, 0, 0, 0, 1)
        #layout0.addWidget(self.combobox1, 0, 1, 0, 1)
        #layout0.addWidget(self.select_label1, 0, 2, 0, 1)
        #layout0.addWidget(self.combobox2, 0, 3, 0, 1)
#        layout0.addWidget(self.start_button, 0, 4, 0, 1)
#        layout0.addWidget(self.stop_button, 0, 5, 0, 1)
        dock_select_duts.addWidget(cb)
        #self.combobox1.activated.connect(lambda value: self.send_command('combobox1 %d' % value))
        #self.combobox2.activated.connect(lambda value: self.send_command('combobox2 %d' % value))
        #self.start_button.clicked.connect(lambda value: self.send_command('START %d' % value))
        #self.stop_button.clicked.connect(lambda value: self.send_command('STOP %d' % value))

        cw = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        reset_button = QtGui.QPushButton('Reset')
        reset_button.setMinimumSize(100, 30)
        reset_button.setMaximumSize(300, 30)
        layout.setHorizontalSpacing(25)
        layout.addWidget(reset_button, 0, 1, 0, 1)
        remove_background_checkbox = QtGui.QCheckBox('Remove background:')
        layout.addWidget(remove_background_checkbox, 0, 2, 1, 1)
        remove_background_spinbox = QtGui.QDoubleSpinBox()
        remove_background_spinbox.setRange(0.0, 100.0)
        remove_background_spinbox.setValue(99.0)
        remove_background_spinbox.setSingleStep(1.0)
        remove_background_spinbox.setDecimals(1)
        remove_background_spinbox.setPrefix('< ')
        remove_background_spinbox.setSuffix(' % maximum occupancy')
        layout.addWidget(remove_background_spinbox, 0, 3, 1, 1)
        self.transpose_checkbox = QtGui.QCheckBox('Transpose columns and rows (FE-I4)')
        layout.addWidget(self.transpose_checkbox, 1, 3, 1, 1)
        self.rate_label = QtGui.QLabel("Readout Rate: Hz")
        layout.addWidget(self.rate_label, 0, 4, 1, 1)
        dock_status.addWidget(cw)
        reset_button.clicked.connect(lambda: self.send_command('RESET'))
        self.transpose_checkbox.stateChanged.connect(lambda value: self.send_command('TRANSPOSE %d' % value))
        remove_background_checkbox.stateChanged.connect(lambda value: self.send_command('BACKGROUND %d' % value))
        remove_background_spinbox.valueChanged.connect(lambda value: self.send_command('PERCENTAGE %f' % value))

        # Add plot docks for column corr
        occupancy_graphics1 = pg.GraphicsLayoutWidget()
        occupancy_graphics1.show()
        view1 = occupancy_graphics1.addViewBox()
        occupancy_img_col = pg.ImageItem(border='w')
        # color occupancy
        poss = np.array([0.0, 0.6, 1.0])
        color = np.array([[25, 25, 112, 255], [173, 255, 47, 255], [255, 0, 0, 255]], dtype=np.ubyte)
        mapp = pg.ColorMap(poss, color)
        lutt = mapp.getLookupTable(0.0, 1.0, 100)

        occupancy_img_col.setLookupTable(lutt, update=True)
        # make plotwidget with axis
        self.plot1 = pg.PlotWidget(viewBox=view1)  # ,labels={'left': 'Column','bottom':'Column'})
        self.plot1.getAxis('bottom').setLabel(text='MONOPIX Rows')
        self.plot1.getAxis('left').setLabel(text='FE-I4 Columns')
        self.plot1.addItem(occupancy_img_col)
        dock_corr_column.addWidget(self.plot1)
        self.occupancy_images_columns = occupancy_img_col
        # Add plot docks for row corr
        occupancy_graphics2 = pg.GraphicsLayoutWidget()
        occupancy_graphics2.show()
        view2 = occupancy_graphics2.addViewBox()
        occupancy_img_rows = pg.ImageItem(border='w')
        # color occupancy
        occupancy_img_rows.setLookupTable(lutt, update=True)
        # make plotwidget with axis
        self.plot2 = pg.PlotWidget(viewBox=view2)  # , labels={'left': 'Row','bottom':'Row'})
        self.plot2.getAxis('bottom').setLabel(text='MONOPIX Columns')
        self.plot2.getAxis('left').setLabel(text='FE-I4 Rows')
        self.plot2.addItem(occupancy_img_rows)
        dock_corr_row.addWidget(self.plot2)
        self.occupancy_images_rows = occupancy_img_rows
        #
        dock_area.addDock(dock_status, 'top')
        dock_area.addDock(dock_select_duts, 'left')
        dock_area.addDock(dock_corr_column, 'bottom')
        dock_area.addDock(dock_corr_row, 'right', dock_corr_column)

    def deserialze_data(self, data):

        return jsonapi.loads(data, object_hook=utils.json_numpy_obj_hook)

    def handle_data(self, data):
        if 'meta_data' not in data:
            self.occupancy_images_columns.setImage(data['column'][:, :], autoDownsample=True)
            self.occupancy_images_rows.setImage(data['row'][:, :], autoDownsample=True)
        else:
            self.rate_label.setText('Readout Rate: %d Hz' % data['meta_data']['fps'])
