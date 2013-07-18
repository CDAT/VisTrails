from PyQt4 import QtCore, QtGui
from gui.modules.python_source_configure import PythonEditor
from gui.common_widgets import QDockPushButton

class PlotSource(QtGui.QDialog):
    def __init__(self, parent=None):
        super(PlotSource, self).__init__(parent)
        #self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Visualization Source")
        #self.main_widget = QtGui.QWidget()
        self.btn_copy_to_clipboard = QDockPushButton("Copy to clipboard")
        self.btn_save_to_file = QDockPushButton("Save to file")
        btnlayout = QtGui.QHBoxLayout()
        btnlayout.addStretch()
        btnlayout.addWidget(self.btn_copy_to_clipboard)
        btnlayout.addWidget(self.btn_save_to_file)
        self.tabWidget = QtGui.QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setDocumentMode(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.tabWidget)
        layout.addLayout(btnlayout)
        self.setLayout(layout)
#        self.main_widget.setLayout(layout)
#        self.setWidget(self.main_widget)
        self.btn_copy_to_clipboard.clicked.connect(self.copyToClipboard)
        self.btn_save_to_file.clicked.connect(self.saveToFile)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)
        
        
    @classmethod
    def instance(klass, parent=None):
        if not hasattr(klass, '_instance'):
            klass._instance = klass(parent)
        return klass._instance
        
    def set_controller(self, controller):
        self.controller = controller
        self.updateProperties(None)

    def sizeHint(self):
        return QtCore.QSize(512, 512)
    
    def showSource(self, source, sheetName=None, row=-1, col=-1, rowSpan=1, 
                   colSpan=1):
        if source is not None:
            editor = PythonEditor(self)
            editor.setPlainText(source)
            name = sheetName + ' @ %s%s' % (chr(ord('A') + col),
                                        row+1)
            if rowSpan > 1 or colSpan > 1:  
                name += ' to %s%s' % (chr(ord('A') + col + colSpan-1), row + rowSpan)
            self.tabWidget.addTab(editor, name)
            self.tabWidget.setCurrentWidget(editor)
            if editor.__class__.__name__ != '_PythonEditor':
                editor.document().setModified(False)
            else:
                editor.setModified(False)
            editor.setFocus()
      
    def copyToClipboard(self, checked):
        contents = self.tabWidget.currentWidget().toPlainText()
        cb = QtGui.QApplication.clipboard()
        cb.setText(contents)
        
    def saveToFile(self, checked):
        contents = self.tabWidget.currentWidget().toPlainText()
        fileName = QtGui.QFileDialog.getSaveFileName(self.parent(),
                                                     "Save Script...",
                                                     filter = "Python file (*.py)")
        if not fileName.isEmpty():
            f = open(str(fileName), "w")
            f.write(contents)
            f.close()

    def closeTab(self, index):
        self.tabWidget.removeTab(index)
            