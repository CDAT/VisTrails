from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem

from ui_cdmsCacheWidget import Ui_cdmsCacheWidget

class CdmsCache(object):
    d = {}

class CdmsCacheWidget(QtGui.QDialog, Ui_cdmsCacheWidget):

    def __init__(self, parent=None):
        super(CdmsCacheWidget, self).__init__(parent)
        self.setupUi(self)
        
        #setup signals
        self.connect(self.btnAll, QtCore.SIGNAL("clicked()"), self.listWidget.selectAll)
        self.connect(self.btnNone, QtCore.SIGNAL("clicked()"), self.listWidget.clearSelection)
        self.connect(self.btnClear, QtCore.SIGNAL("clicked()"), self.clearSelectedCacheItems)
        self.connect(self.btnClose, QtCore.SIGNAL("clicked()"), self.close)
        
    def showEvent(self, event):
        super(CdmsCacheWidget, self).showEvent(event)
        self.setListFromCache()
            
    def setListFromCache(self):
        self.listWidget.clear()
        for key in CdmsCache.d:
            item = QListWidgetItem(QString(key), self.listWidget)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.listWidget.addItem(item)
            
    def clearSelectedCacheItems(self): 
        for i in reversed(range(self.listWidget.count())):
            item =self.listWidget.item(i) 
            if item.isSelected():
                del CdmsCache.d[str(item.text())]
        self.setListFromCache()
                
            