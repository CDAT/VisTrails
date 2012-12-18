#// PyQt is required
from PyQt4 import QtCore, QtGui

#// Import widget
from ui_pvslice_widget import Ui_PVSliceWidget

class PVSliceWidget(QtGui.QWidget, Ui_PVSliceWidget):
    #// This has to be at the class level
    requestedApplyChagnes = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(PVSliceWidget, self).__init__(parent)
        self.setupUi(self)
        self.connect(self.applyButton, QtCore.SIGNAL('clicked(bool)'), self.apply_changes)

    def update_slice_offset_values(self):
        self.sliceOffsetListWidget.clear()

        #// Slice values
        qstr_list = QtCore.QStringList()

        if(not self.csvLineEdit.text().isEmpty()):
            values = self.csvLineEdit.text().split(',')
            for value in values:
                value = value.trimmed()
                if not value.isEmpty():
                    qstr_list.append(value)

        #// Remove any duplicates and sort the list
        qstr_list.removeDuplicates()
        qstr_list.sort()
        for i in range(qstr_list.count()):
            self.sliceOffsetListWidget.addItem(qstr_list[i])

    def clear_inputs(self):
        self.csvLineEdit.clear()

    def apply_changes(self):
        self.update_slice_offset_values()
        #// Now clear the inputs
        self.clear_inputs()
        self.requestedApplyChagnes.emit()

    def set_slice_offset_values(self, contour_values_str):
        if contour_values_str is None:
          return

        qstr_list = QtCore.QStringList()
        values = contour_values_str.split(',')
        for value in values:
            qstr_list.append(value.strip())

        #// Remove any duplicates and sort the list
        qstr_list.removeDuplicates()
        qstr_list.sort()

        self.sliceOffsetListWidget.clear()
        for i in range(qstr_list.count()):
            self.sliceOffsetListWidget.addItem(qstr_list[i])

    def get_slice_offset_values(self):
        slice_offset_values = []

        for i in range(self.sliceOffsetListWidget.count()):
            item = self.sliceOffsetListWidget.item(i)
            slice_offset_values.append(item.data(QtCore.Qt.EditRole).toReal()[0])

        return slice_offset_values

    def set_slice_origin(self, origin_str):
        if origin_str is None:
            return
        origin =  origin_str.split(',')
        self.sliceOriginXLineEdit.setText(origin[0].strip())
        self.sliceOriginYLineEdit.setText(origin[1].strip())
        self.sliceOriginZLineEdit.setText(origin[2].strip())

    def get_slice_origin(self):
        slice_origin = []
        slice_origin.append(float( self.sliceOriginXLineEdit.text().toDouble()[0] ) )
        slice_origin.append(float( self.sliceOriginYLineEdit.text().toDouble()[0] ) )
        slice_origin.append(float( self.sliceOriginZLineEdit.text().toDouble()[0] ) )

        return slice_origin

    def set_slice_normal(self, normal_str):
        if normal_str is None:
            return
        normal =  normal_str.split(',')
        self.sliceNormalXLineEdit.setText(normal[0].strip())
        self.sliceNormalYLineEdit.setText(normal[1].strip())
        self.sliceNormalZLineEdit.setText(normal[2].strip())

    def get_slice_normal(self):
        slice_normal = []
        slice_normal.append(float( self.sliceNormalXLineEdit.text().toDouble()[0] ) )
        slice_normal.append(float( self.sliceNormalYLineEdit.text().toDouble()[0] ) )
        slice_normal.append(float( self.sliceNormalZLineEdit.text().toDouble()[0] ) )

        return slice_normal
