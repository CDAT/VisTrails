import ast

try:
    import cPickle as pickle
except:
    import pickle
    
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
from core.utils import InstanceObject
import core.db.action
from gui.uvcdat.graphicsMethodsWidgets import QBoxfillEditor, QIsofillEditor,\
   QIsolineEditor, QMeshfillEditor, QOutfillEditor, QOutlineEditor, \
   QScatterEditor, QTaylorDiagramEditor, QVectorEditor, Q1DPlotEditor, Q3D_ScalarEditor, Q3D_VectorEditor
from gui.common_widgets import QDockPushButton
from gui.utils import show_question, SAVE_BUTTON, DISCARD_BUTTON
class GraphicsMethodConfigurationWidget(QtGui.QWidget):
    def __init__(self, module, controller, parent=None, show_buttons=True):
        QtGui.QWidget.__init__(self, parent)
        self.module = module
        self.module_instance = self.module.module_descriptor.module()
        self.controller = controller
        self.show_buttons = show_buttons
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(3)
        self.layout.setMargin(0)
        self.fun_map = {}
        self.populate_fun_map()
        self.gmName = self.getValueFromFunction("graphicsMethodName")
        if self.gmName is None:
            self.gmName = self.module_instance.graphics_method_name
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
            if self.wrldCoordEditor:
                self.wrldCoordEditor.setEnabled(False)
            
        if show_buttons:
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
        self.tabWidget.setCurrentIndex(0)
      
    def createEditor(self, parent, gmName):
        plot_type = self.module_instance.plot_type
        if plot_type == "Boxfill":
            return QBoxfillEditor(self.tabWidget, gmName)
        elif plot_type == "Isofill":
            return QIsofillEditor(self.tabWidget, gmName)
        elif plot_type == "Isoline":
            return QIsolineEditor(self.tabWidget, gmName)
        elif plot_type == "Meshfill":
            return QMeshfillEditor(self.tabWidget, gmName)
        elif plot_type == "Outfill":
            return QOutfillEditor(self.tabWidget, gmName)
        elif plot_type == "Outline":
            return QOutlineEditor(self.tabWidget, gmName)
        elif plot_type == "Scatter":
            return QScatterEditor(self.tabWidget, gmName)
        elif plot_type == "Taylordiagram":
            return QTaylorDiagramEditor(self.tabWidget, gmName)
        elif plot_type == "Vector":
            return QVectorEditor(self.tabWidget, gmName)
        elif plot_type == "XvsY":
            return Q1DPlotEditor(self.tabWidget, gmName, type="xvsy")
        elif plot_type == "Xyvsy":
            return Q1DPlotEditor(self.tabWidget, gmName, type="xyvsy")
        elif plot_type == "Yxvsx":
            return Q1DPlotEditor(self.tabWidget, gmName, type="yxvsx")
        elif ( plot_type == "3D_Scalar" ) or ( plot_type ==  '3D_Dual_Scalar' ):
            return Q3D_ScalarEditor(self.tabWidget, gmName, type="yxvsx")
        elif plot_type == "3D_Vector":
            return Q3D_VectorEditor(self.tabWidget, gmName, type="yxvsx")
        
    def setupEditors(self):
        gm = InstanceObject(**self.attributes)
        self.gmEditor.initValues(gm)
        
        #set continent
        self.continents = self.getValueFromFunction('continents')
        if self.continents:
            self.gmEditor.continents.setCurrentIndex(self.continents-1)
            
        #set aspect ratio
        self.ratio = self.getValueFromFunction('ratio')
        
        #taylor diagram does not have aspectAuto
        if hasattr(self.gmEditor, 'aspectAuto'):
            if self.ratio is None or self.ratio == 'autot':
                self.gmEditor.aspectAuto.setCheckState(Qt.Checked)
            else:
                #if the ratio cannot cast to float, check auto in gui
                try:
                    self.gmEditor.aspectRatio.setText(str(float(self.ratio)))
                    self.gmEditor.aspectAuto.setCheckState(Qt.Unchecked)
                except ValueError:
                    self.gmEditor.aspectAuto.setCheckState(Qt.Checked)
        
    def getValueFromFunction(self, fun):
        if fun in self.fun_map:
            fid = self.fun_map[fun]
            f = self.module.functions[fid]
            try:
                if fun == "skillColor":
                    value = int(f.params[0].strValue)
                else:
                    value = f.params[0].value()
                    if fun == 'Marker':
                        value = pickle.loads(value)
            except Exception, e:
                if fun == "skillColor":
                    #if skillColor failed to parse as int, it should be string
                    from init import get_canvas
                    value = get_canvas().match_color(f.params[0].strValue)
                else:
                    value = ast.literal_eval(f.params[0].strValue)
            return value
        else:
            return None
        
    def populate_fun_map(self):
        self.fun_map = {}
        for i in xrange(self.module.getNumFunctions()):
            self.fun_map[self.module.functions[i].name] = i
                
    def mapAttributesToFunctions(self):
        self.attributes = {}
        default = self.module_instance
        default.set_default_values(self.gmName)
        for name in default.gm_attributes:
            self.attributes[name] = getattr(default, name)
            
        for fun in self.fun_map:
            if fun in self.module_instance.gm_attributes:
                self.attributes[fun] = self.getValueFromFunction(fun)

    def getFunctionUpdates(self):
        functions = []
        gm = InstanceObject(**self.attributes)
        self.gmEditor.applyChanges(gm)

        for attr in self.attributes:
            newval = getattr(gm,attr)
            if newval != self.attributes[attr]:
                functions.append((attr,[str(getattr(gm,attr))]))
                self.attributes[attr] = newval

        # FIXME why can't these be rolled in with self.attributes?
        #continents
        if hasattr(self.gmEditor, 'continents') :
            gui_continent = self.gmEditor.continents.currentIndex() + 1
            if self.continents is None or gui_continent != self.continents:
                functions.append(('continents',[str(gui_continent)]))
                self.continents = gui_continent
            
        # aspect ratio
        gui_ratio = self.gmEditor.getAspectRatio()
        if self.ratio is None or gui_ratio != self.ratio:
            functions.append(('ratio', [str(gui_ratio)]))
            self.ratio = gui_ratio

        return functions
                
    def updateVistrail(self):
        functions = self.getFunctionUpdates()
        ops = self.controller.update_functions_ops(self.module, functions)
        action = core.db.action.create_action(ops)
        
        return (action, True)
    
    def checkForChanges(self):
        gm = InstanceObject(**self.attributes)
        self.gmEditor.applyChanges(gm)
        changed = False
        
        for attr in self.attributes:
            if getattr(gm,attr) != self.attributes[attr]:
                if str(getattr(gm,attr)) != str(self.attributes[attr]):
                    changed = True
                    break
        
        #check if continents or ratios changed
        if not changed and hasattr(self.gmEditor, 'continents'):
            if self.continents is None:
                if self.gmEditor.continents.currentIndex() != 0:
                    changed = True
            elif self.continents != self.gmEditor.continents.currentIndex()+1:
                changed = True
                
            if self.ratio is None:
                if self.gmEditor.getAspectRatio() != 'autot':
                    changed = True
            elif self.ratio != self.gmEditor.getAspectRatio():
                changed = True
            
        return changed
    
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
        
    def askToSaveChanges(self):
        if self.checkForChanges():
            message = ('Configuration panel contains unsaved changes. '
                      'Do you want to save changes before proceeding?' )
            res = show_question('VisTrails',
                                message,
                                buttons = [SAVE_BUTTON, DISCARD_BUTTON])
            if res == SAVE_BUTTON:
                self.saveTriggered()
                return True
            else:
                self.resetTriggered()
                return False
