from PyQt4 import QtCore, QtGui
from gui.common_widgets import QDockPushButton
class AliasesPlotWidget(QtGui.QWidget):
    def __init__(self,controller, version, plot_obj, parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.controller = controller
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
            self.plot.loadWidget()
            self.plot_widget = self.plot.widget
            self.layout().insertWidget(0,self.plot_widget)
        self.adjustSize()
                
    def updateVistrail(self):
        aliases = {}
        pipeline = self.controller.vistrail.getPipeline(self.version)
        for name in pipeline.aliases:
            aliases[name] = pipeline.get_alias_str_value(name)
        for a,w in self.plot.alias_widgets.iteritems():
            aliases[a] = w.contents()
        
        actions = self.plot.applyChanges(aliases)
        action = actions.pop()
        
        #get the most recent action that is not None
        while action == None:
            action = actions.pop()
        
        return action
    
    def saveTriggered(self, checked):
        action = self.updateVistrail()
        self.emit(QtCore.SIGNAL('plotDoneConfigure'), action)
        
    def resetTriggered(self, checked):
        self.updateWidgets(self.plot)
        self.emit(QtCore.SIGNAL("stateChanged"))