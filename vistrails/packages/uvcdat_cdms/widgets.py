from PyQt4 import QtCore, QtGui
from core.utils import InstanceObject
from gui.uvcdat.graphicsMethodsWidgets import QBoxfillEditor, QIsofillEditor,\
   QIsolineEditor
from gui.common_widgets import QDockPushButton
class GraphicsMethodConfigurationWidget(QtGui.QWidget):
    def __init__(self, module, controller, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.module = module
        self.module_descriptor = self.module.module_descriptor.module
        self.controller = controller
        self.layout = QtGui.QVBoxLayout()
        self.fun_map = {}
        self.populate_fun_map()
        self.gmName = self.getValueFromFunction("graphicsMethodName")
        if self.gmName is None:
            self.gmName = self.module_descriptor().graphics_method_name
        self.mapAttributesToFunctions()
        self.tabWidget = QtGui.QTabWidget(self)
        
        self.tabWidget.setTabPosition(QtGui.QTabWidget.North)
        self.tabWidget.setDocumentMode(True)
        self.gmEditor = self.createEditor(self, self.gmName)
        self.tabWidget.insertTab(0,self.gmEditor, "Properties")
        self.wrldCoordEditor = self.tabWidget.widget(1)
        
        self.layout.addWidget(self.tabWidget)
        self.setupEditors()
        #default gmName can't be changed
        if str(self.gmName) == "default":
            self.gmEditor.setEnabled(False)
            self.wrldCoordEditor.setEnabled(False)
            
        self.buttonLayout = QtGui.QHBoxLayout()
        self.buttonLayout.setMargin(5)
        self.saveButton = QDockPushButton('&Save', self)
        self.saveButton.setFixedWidth(100)
        self.saveButton.setEnabled(True)
        self.buttonLayout.addWidget(self.saveButton)
        self.resetButton = QDockPushButton('&Reset', self)
        self.resetButton.setFixedWidth(100)
        self.resetButton.setEnabled(True)
        self.buttonLayout.addWidget(self.resetButton)
        
        self.layout.addLayout(self.buttonLayout)
        self.connect(self.saveButton, QtCore.SIGNAL('clicked(bool)'), 
                     self.saveTriggered)
        self.connect(self.resetButton, QtCore.SIGNAL('clicked(bool)'), 
                     self.resetTriggered)
        self.setLayout(self.layout)
      
    def createEditor(self, parent, gmName):
        plot_type = self.module.module_descriptor.module().plot_type
        if plot_type == "Boxfill":
            return QBoxfillEditor(self.tabWidget, gmName)
        elif plot_type == "Isofill":
            return QIsofillEditor(self.tabWidget, gmName)
        elif plot_type == "Isoline":
            return QIsolineEditor(self.tabWidget, gmName)
        
    def setupEditors(self):
        gm = InstanceObject(**self.attributes)
        self.gmEditor.initValues(gm)
        
    def getValueFromFunction(self, fun):
        if fun in self.fun_map:
            fid = self.fun_map[fun]
            f = self.module.functions[fid]
            return f.params[0].strValue
        else:
            return None
        
    def populate_fun_map(self):
        self.fun_map = {}
        for i in xrange(self.module.getNumFunctions()):
            self.fun_map[self.module.functions[i].name] = i
                
    def mapAttributesToFunctions(self):
        self.attributes = {}
        default = self.module_descriptor()
        default.set_default_values(self.gmName)
        for name in default.gm_attributes:
            self.attributes[name] = getattr(default, name)
            
        for fun in self.fun_map:
            if fun in self.module_descriptor.gm_attributes:
                self.attributes[fun] = self.getValueFromFunction(fun)
                
    def updateVistrail(self):
        functions = []
        gm = InstanceObject(**self.attributes)
        self.gmEditor.applyChanges(gm)
        
        for attr in self.attributes:
            if str(getattr(gm,attr)) != self.attributes[attr]:
                functions.append((attr,[str(getattr(gm,attr))]))
                
        action = self.controller.update_functions(self.module, 
                                                  functions)
        return (action, True)
    
    def saveTriggered(self, checked = False):
        """ saveTriggered(checked: bool) -> None
        Update vistrail controller and module when the user click Ok
        
        """
        (action, res) = self.updateVistrail()
        if res:
            self.emit(QtCore.SIGNAL('doneConfigure'), self.module.id)
            self.emit(QtCore.SIGNAL('plotDoneConfigure'), action)
            
    def resetTriggered(self):
        self.setupEditors()
        self.state_changed = False
        self.emit(QtCore.SIGNAL("stateChanged"))
        