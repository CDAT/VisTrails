
#// PyQt is required
from PyQt4 import QtCore, QtGui

#// Import widget
from ui_pvcontour_widget import Ui_PVContourWidget

class PVContourWidget(QtGui.QWidget, Ui_PVContourWidget):
    def __init__(self, parent=None):
        super(PVContourWidget, self).__init__(parent)
        self.setupUi(self)
