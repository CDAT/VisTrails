
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
        #// Contour values
        qstr_list = QtCore.QStringList()

        if(not self.firstValueLineEdit.text().isEmpty() and
           not self.lastValueLineEdit.text().isEmpty() and
           not self.stepValueLineEdit.text().isEmpty()):

            first_val = self.firstValueLineEdit.text().toDouble()[0]
            last_val = self.lastValueLineEdit.text().toDouble()[0]
            steps = self.stepValueLineEdit.text().toDouble()[0]
            count = int((last_val - first_val) / steps)
            values = [ (first_val + i * steps) for  i in range(count + 1)]

            for value in values:
                value = str(value).strip()
                if len(value) > 0:
                    qstr_list.append(value)

        if(not self.valuesLineEdit.text().isEmpty()):
            values = self.valuesLineEdit.text().split(',')
            for value in values:
                value = value.trimmed()
                if not value.isEmpty():
                    qstr_list.append(value)

        #// Remove any duplicates and sort the list
        qstr_list.removeDuplicates()
        qstr_list.sort()

        self.list_model.reset()
        self.list_model.setStringList(qstr_list)

    def clear_inputs(self):
        self.firstValueLineEdit.clear()
        self.lastValueLineEdit.clear()
        self.stepValueLineEdit.clear()
        self.valuesLineEdit.clear()

    def apply_changes(self):
        self.update_contour_values()
        #// Now clear the inputs
        self.clear_inputs()
        self.requestedApplyChagnes.emit()

    def set_contour_values(self, contour_values_str):
        qstr_list = QtCore.QStringList()
        values = contour_values_str.split(',')
        for value in values:
            qstr_list.append(value.strip())
        self.list_model.reset()
        self.list_model.setStringList(qstr_list)

    def get_contour_values(self):
        return [value.toDouble()[0] for value in self.list_model.stringList()]
