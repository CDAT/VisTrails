from PyQt4 import QtCore, QtGui
from gui.module_configuration import QConfigurationWidget
from gui.common_widgets import QToolWindowInterface

class PlotProperties(QtGui.QScrollArea, QToolWindowInterface):
    def __init__(self, parent=None):
        super(PlotProperties, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Visualization Properties")
        self.setWidgetResizable(True)
        self.confWidget = QConfigurationWidget()
        self.setWidget(self.confWidget)
        self.controller = None
        self.updateLocked = False
        self.hasChanges = False
        self.sheetName = None
        self.row = -1
        self.col = -1
        
    @classmethod
    def instance(klass):
        if not hasattr(klass, '_instance'):
            klass._instance = klass()
        return klass._instance
        
    def set_controller(self, controller):
        self.controller = controller
        self.updateProperties(None)

    def sizeHint(self):
        return QtCore.QSize(512, 512)
    
    def updateProperties(self, widget=None, sheetName=None, row=-1, col=-1):
        if self.updateLocked: return
        self.sheetName = sheetName
        self.row = row
        self.col = col
        self.confWidget.setUpdatesEnabled(False)    
        self.confWidget.setVisible(False)
        self.confWidget.clear()
        if widget and self.controller:
            self.confWidget.setUpWidget(widget)
            self.connect(widget, QtCore.SIGNAL("plotDoneConfigure"),
                         self.configureDone)
            self.connect(widget, QtCore.SIGNAL("stateChanged"),
                         self.stateChanged)
        self.confWidget.setUpdatesEnabled(True)
        self.confWidget.setVisible(True)
        self.hasChanges = False
        # we need to reset the title in case there were changes
        self.setWindowTitle("Module Configuration")
    
    def configureDone(self, action):
        self.controller.plot_properties_were_changed(self.sheetName,
                                                     self.row, self.col,
                                                     action)
    
    def stateChanged(self):
        self.hasChanges = self.confWidget.widget.state_changed
        # self.setWindowModified seems not to work here
        # self.setWindowModified(self.hasChanges)
        title = str(self.windowTitle())
        if self.hasChanges:
            if not title.endswith("*"):
                self.setWindowTitle(title + "*")
        else:
            if title.endswith("*"):
                self.setWindowTitle(title[:-1])
        
    def lockUpdate(self):
        """ lockUpdate() -> None
        Do not allow updateModule()
        
        """
        self.updateLocked = True
        
    def unlockUpdate(self):
        """ unlockUpdate() -> None
        Allow updateModule()
        
        """
        self.updateLocked = False
        
    def closeEvent(self, event):
        self.confWidget.askToSaveChanges()
        event.accept()
        
    def activate(self):
        if self.isVisible() == False:
            # self.toolWindow().show()
            self.show()
        self.activateWindow()
        self.confWidget.activate()
        
    def set_visible(self, enabled):
        #print "set_visible ", self, enabled
        if hasattr(self, 'main_window') and self.main_window is not None:
            self.main_window.show()
            self.main_window.raise_()

        if enabled:
            self.toolWindow().show()
            self.toolWindow().raise_()
            
    def set_action(self, action):
        self.action = action
        self.connect(self.toolWindow(), 
                     QtCore.SIGNAL("visibilityChanged(bool)"),
                     self.visibility_changed)
        
    def visibility_changed(self, visible):
        self.action.setChecked(visible)