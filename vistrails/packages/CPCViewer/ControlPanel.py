'''
Created on Sep 27, 2013

@author: tpmaxwel
'''
import sys
import os.path
import vtk, time
from PyQt4 import QtCore, QtGui
from compiler.ast import Name

class ConfigParameter( QtCore.QObject ):

    def __init__(self, name, **args ):
        QtCore.QObject.__init_( self ) 
        self.name = name 
        self.values = args
        
    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        return self.values.get( key, None )

    def __setitem__(self, key, value):
        self.values[key] = value


class ConfigControl(QtGui.QWidget):
    
    def __init__(self, title, **args ):  
        QtGui.QWidget.__init__( self )
        self.parameters = {}
        self.title = title 
        
    def addParameter(self, name, **args ):
        parameter = ConfigParameter( name, **args )
        self.parameters[ name ] = parameter
        
    def build(self):
        self.setLayout(QtGui.QVBoxLayout())
        title_label = QtGui.QLabel( self.title  )
        self.layout().addWidget( title_label  )

class SliderControl( ConfigControl ):
    
    def __init__(self, title, **args ):  
        ConfigControl.__init__( self, title, **args )
        self.maxValue = args.get( 'max_value', 100 )
        self.minValue = args.get( 'min_value', 0 )
        self.initValue = args.get( 'init_value', 0 )
        self.sliders = []
        
    def addSlider(self, label ):
        slider_index = len( self.sliders )
        slider_layout = QtGui.QHBoxLayout()
        slider_layout.setMargin(5)
        slider_label = QtGui.QLabel( label  )
        slider_layout.addWidget( slider_label  ) 
        slider = QtGui.QSlider( QtCore.Qt.Horizontal )
        slider.setRange( self.minValue, self.maxValue )
        slider.setSliderPosition( self.initValue )
        self.connect( slider, QtCore.SIGNAL('valueChanged()'), lambda: self.valueChanged( slider_index ) )
        slider_label.setBuddy( slider )
        slider_layout.addWidget( slider  )         
        self.layout().addLayout( slider_layout )
        self.sliders.append(slider)
        return slider_index
        
    def valueChanged( self, slider_index ):
        print " setValue1: %d %s " % ( slider_index, str( self.sliders[slider_index].getSliderPosition() ) )
    
class RangeSliderControl( SliderControl ):
    
    def __init__(self, title, **args ):  
        super( RangeSliderControl, self ).__init__( title, **args )
        
    def build(self):
        super( RangeSliderControl, self ).build()
        self.addSlider( "Min Value:" )
        self.addSlider( "Max Value:" )
        
    def valueChanged( self, slider_index, value ):
        print " setValue: %d %s " % ( slider_index, str( self.sliders[slider_index].getSliderPosition() ) )
          
class ConfigControlList(QtGui.QWidget):

    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.setLayout(QtGui.QVBoxLayout())

    def addControl( self, iCatIndex, config_ctrl ):
        self.layout().addWidget( config_ctrl )
    
class ConfigControlContainer(QtGui.QWidget):
    
    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.setLayout(QtGui.QVBoxLayout())
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setEnabled(True)
        self.layout().addWidget( self.tabWidget )
        
    def addCategory( self, cat_name ):
        config_list = ConfigControlList( self.tabWidget )
        tab_index = self.tabWidget.addTab( config_list, cat_name )
        return tab_index
        
    def addControl( self, iCatIndex, config_ctrl ):
        config_list = self.tabWidget.getTab( iCatIndex )
        config_list.addControl( config_ctrl )

class CPCConfigDialog(QtGui.QDialog):

    def __init__(self, parent=None):    
        QtGui.QDialog.__init__(self, parent)
                
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(True)
        self.setWindowTitle('CPC Plot Config')
        self.setLayout(QtGui.QVBoxLayout())
        
        self.scrollArea = QtGui.QScrollArea(self) 
#        self.scrollArea.setFrameStyle(QtGui.QFrame.NoFrame)      
        self.scrollArea.setWidgetResizable(True)
        
        self.configContainer = ConfigControlContainer( self.scrollArea )
        self.scrollArea.setWidget( self.configContainer )
        self.layout().addWidget(self.scrollArea)

        self.buttonLayout = QtGui.QHBoxLayout()
        self.buttonLayout.setContentsMargins(-1, 3, -1, 3)
        
        self.btnOK = QtGui.QPushButton('OK')
        self.btnCancel = QtGui.QPushButton('Cancel')

        self.buttonLayout.addWidget(self.btnOK)
        self.buttonLayout.addWidget(self.btnCancel)
        
        self.layout().addLayout(self.buttonLayout)
        
        self.btnCancel.setShortcut('Esc')
        self.connect(self.btnOK, QtCore.SIGNAL('clicked(bool)'),      self.okTriggered )
        self.connect(self.btnCancel, QtCore.SIGNAL('clicked(bool)'),  self.cancel )
        
    def addConfigControl(self, config_ctrl ):
        self.configContainer.addControl( config_ctrl )
        
    def okTriggered(self):
        print "OK"
        self.close()
    
    def cancel(self):
        print "Cancel"
        self.close()

if __name__ == '__main__':
    app = QtGui.QApplication(['CPC Config Dialog'])
    
    configDialog = CPCConfigDialog()
    config_ctrl = RangeSliderControl("Color Scale")
    config_ctrl.build()
    configDialog.addConfigControl(config_ctrl)
    configDialog.show()

    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), configDialog.cancel ) 
    app.exec_() 
 

