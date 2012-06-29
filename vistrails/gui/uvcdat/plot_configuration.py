from PyQt4 import QtCore, QtGui
from gui.common_widgets import QDockPushButton
from gui.modules import get_widget_class
from core.modules.module_registry import get_module_registry
from gui.modules.constant_configuration import StandardConstantWidget

class AliasesPlotWidget(QtGui.QWidget):
    def __init__(self,controller, version, plot_obj, parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.proj_controller = controller
        self.controller = controller.vt_controller
        self.version = version
        self.plot = plot_obj
        self.state_changed = False
        self.plot_widget = None
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
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.alias_widgets = {}
        self.updateWidgets(plot_obj)
        layout.addLayout(self.buttonLayout)
        self.connect(self.saveButton, QtCore.SIGNAL('clicked(bool)'), 
                     self.saveTriggered)
        self.connect(self.resetButton, QtCore.SIGNAL('clicked(bool)'), 
                     self.resetTriggered)
        
    def updateWidgets(self, plot_obj=None):
        self.plot = plot_obj
        if self.plot_widget is not None:
            self.layout().removeWidget(self.plot_widget)
            self.plot_widget.deleteLater()
            self.plot_widget = None
        if self.plot:
            pipeline = self.controller.vistrail.getPipeline(self.version)
            self.plot_widget = self.loadWidget(pipeline)
            self.layout().insertWidget(0,self.plot_widget)
        self.adjustSize()
                
    def updateVistrail(self):
        aliases = {}
        pipeline = self.controller.vistrail.getPipeline(self.version)
        for name in pipeline.aliases:
            aliases[name] = pipeline.get_alias_str_value(name)
        for a,w in self.alias_widgets.iteritems():
            aliases[a] = w.contents()
            print a, aliases[a]
        action = self.applyChanges(pipeline, aliases)
        
        return action
    
    def applyChanges(self, pipeline, aliases):
        print " @@ Pipeline aliases: ", str( pipeline.aliases )
        self.plot.addMergedAliases( aliases, pipeline )
        action = self.plot.addParameterChangesFromAliasesAction(pipeline, 
                                        self.controller, 
                                        self.controller.vistrail, 
                                        self.version, aliases)
        return action
    
    def saveTriggered(self, checked):
        action = self.updateVistrail()
        self.emit(QtCore.SIGNAL('plotDoneConfigure'), action)
        
    def resetTriggered(self, checked):
        self.updateWidgets(self.plot)
        self.emit(QtCore.SIGNAL("stateChanged"))
        
    def loadWidget( self, pipeline):
        from PyQt4 import QtGui
        aliases = pipeline.aliases
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        hidden_aliases = self.plot.computeHiddenAliases()
        for name, (type, oId, parentType, parentId, mId) in aliases.iteritems():
            if name not in hidden_aliases:
                p = pipeline.db_get_object(type, oId)
                if p.identifier == '':
                    idn = 'edu.utah.sci.vistrails.basic'
                else:
                    idn = p.identifier
                reg = get_module_registry()
                p_module = reg.get_module_by_name(idn, p.type, p.namespace)
                if p_module is not None:
                    widget_type = get_widget_class(p_module)
                else:
                    widget_type = StandardConstantWidget
                p_widget = widget_type(p, None)
                a_layout = QtGui.QHBoxLayout()
                label = QtGui.QLabel(name)
                a_layout.addWidget(label)
                a_layout.addWidget(p_widget)
                
                layout.addLayout(a_layout)
                self.alias_widgets[name] = p_widget
                
        widget.setLayout(layout)
        return widget