
#// PyQt is required
from PyQt4 import QtCore, QtGui

#// Import widget
from ui_pvcontour_widget import Ui_PVContourWidget

class PVContourWidget(QtGui.QWidget, Ui_PVContourWidget):
    #// This has to be at the class level
    requestedApplyChagnes = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(PVContourWidget, self).__init__(parent)
        self.setupUi(self)

        self.list_model = QtGui.QStringListModel()
        self.isoValuesListView.setModel(self.list_model)
        self.connect(self.applyButton, QtCore.SIGNAL('clicked(bool)'), self.apply_changes)

    def update_contour_values(self):
        first_val = self.firstValueLineEdit.text().toDouble()[0]
        last_val = self.lastValueLineEdit.text().toDouble()[0]
        steps = self.stepValueEdit.text().toInt()[0]
        count = int((last_val - first_val) / steps)
        values = [ (first_val + i * steps) for  i in range(count + 1)]
        qstr_list = QtCore.QStringList()
        for value in values:
            qstr_list.append(QtCore.QString("%1").arg(value))

        self.list_model.reset()
        self.list_model.setStringList(qstr_list)

    def apply_changes(self):
        self.update_contour_values()
        self.requestedApplyChagnes.emit()

    def get_contour_values(self):
        return [value.toDouble()[0] for value in self.list_model.stringList()]