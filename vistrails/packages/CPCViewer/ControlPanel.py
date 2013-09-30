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
        self.tabWidget = None 
        
    def getName(self):
        return self.title 
        
    def addParameter(self, name, **args ):
        parameter = ConfigParameter( name, **args )
        self.parameters[ name ] = parameter
        
    def addTab( self, tabname ):
        if self.tabWidget == None:
            self.tabWidget = QtGui.QTabWidget(self)
            self.tabWidget.setEnabled(True)
            self.layout().addWidget( self.tabWidget )
        tabContents = QtGui.QWidget( self.tabWidget )
        layout = QtGui.QVBoxLayout()
        tabContents.setLayout(layout)
        tab_index = self.tabWidget.addTab( tabContents, tabname )
        return tab_index, layout
       
    def build(self):
        if self.layout() == None:
            self.setLayout(QtGui.QVBoxLayout())
            title_label = QtGui.QLabel( self.title  )
            self.layout().addWidget( title_label  )
            self.control_button = QtGui.QPushButton( self.title )
            self.connect( self.control_button,  QtCore.SIGNAL('clicked(bool)'), self.triggered )
            self.setMinimumWidth(450)
        
    def getButton(self):
        return self.control_button
        
    def triggered( self, bval ):
        self.emit( QtCore.SIGNAL("Triggered"), self.title )
        
class LabeledSliderWidget( QtGui.QWidget ):
    
    def __init__(self, index, label, **args ):  
        super( LabeledSliderWidget, self ).__init__()
        slider_layout = QtGui.QHBoxLayout()
        self.setLayout(slider_layout)
        self.maxValue = args.get( 'max_value', 100 )
        self.minValue = args.get( 'min_value', 0 )
        self.initValue = args.get( 'init_value', 0 )
        self.scaledMaxValue = args.get( 'scaled_max_value', self.maxValue )
        self.scaledMinValue = args.get( 'scaled_min_value', self.minValue )
        self.slider_index = index
        self.title = label
        slider_layout.setMargin(2)
        slider_label = QtGui.QLabel( label  )
        slider_layout.addWidget( slider_label  ) 
        self.slider = QtGui.QSlider( QtCore.Qt.Horizontal )
        self.slider.setRange( self.minValue, self.maxValue )
        self.slider.setSliderPosition( self.initValue )
        self.connect( self.slider, QtCore.SIGNAL('sliderMoved(int)'), self.sliderMoved )
        slider_label.setBuddy( self.slider )
        slider_layout.addWidget( self.slider  )  
        self.value_pane = QtGui.QLabel( str( self.getScaledSliderValue( self.initValue ) ) )         
        slider_layout.addWidget( self.value_pane  )         

    def getScaledSliderValue( self, slider_value = None ):
        if slider_value == None: slider_value = self.slider.value()
        fvalue = ( slider_value - self.minValue ) / float( self.maxValue - self.minValue )
        return self.scaledMinValue + fvalue * ( self.scaledMaxValue - self.scaledMinValue )

    def sliderMoved( self, slider_value ):
        value = self.getScaledSliderValue( slider_value )
        self.value_pane.setText( str( value ) )
        self.emit( QtCore.SIGNAL("SliderMoved"),  self.slider_index, value )
        return value

class SliderControl( ConfigControl ):
    
    def __init__(self, title, **args ):  
        ConfigControl.__init__( self, title, **args )
        self.args = args
        self.sliders = []
        
    def addSlider(self, label, layout = None ):
        if layout == None: layout = self.layout()
        slider_index = len( self.sliders ) 
        slider = LabeledSliderWidget( slider_index, label )
        layout.addWidget( slider  ) 
        self.sliders.append(slider)
        self.connect( slider, QtCore.SIGNAL("SliderMoved"), self.sliderMoved )
        return slider_index
    
    def sliderMoved( self, slider_index, value ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.title, slider_index, value ) )
    
class LevelingSliderControl( SliderControl ):
    
    def __init__(self, title, **args ):  
        super( LevelingSliderControl, self ).__init__( title, **args )
        
    def build(self):
        super( LevelingSliderControl, self ).build()
        self.leveling_tab_index, tab_layout = self.addTab('Leveling')
        self.addSlider( "Window Size:", tab_layout )
        self.addSlider( "Window Position:", tab_layout )
        self.minmax_tab_index, tab_layout = self.addTab('Min/Max')
        self.addSlider( "Min Value:", tab_layout )
        self.addSlider( "Max Value:", tab_layout )
        
    def sliderMoved( self, slider_index, value ):
        super( LevelingSliderControl, self ).sliderMoved( slider_index, value )
              
class ConfigControlList(QtGui.QWidget):

    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.setLayout( QtGui.QVBoxLayout() )
        self.buttonBox = QtGui.QGridLayout()
        self.layout().addLayout( self.buttonBox )
        self.num_button_cols = 4
        self.controls = {}
        self.scrollArea = QtGui.QScrollArea(self) 
        self.layout().addWidget(self.scrollArea)

    def addControl( self, iCatIndex, config_ctrl ):
        control_name = config_ctrl.getName()
        control_index = len( self.controls )
        self.controls[ control_name ] = config_ctrl 
        self.buttonBox.addWidget( config_ctrl.getButton(), control_index % self.num_button_cols, control_index / self.num_button_cols ) 
        self.connect( config_ctrl,  QtCore.SIGNAL('Triggered'), self.configTriggered )
        
    def configTriggered( self, control_name ):
        config_ctrl = self.controls[ control_name ] 
        self.scrollArea.setWidget( config_ctrl ) 
    
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
        config_list = self.tabWidget.widget( iCatIndex )
        config_list.addControl( iCatIndex, config_ctrl )

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
        self.resize(600, 600)
        
        
    def addConfigControl(self, iCatIndex, config_ctrl ):
        config_ctrl.build()
        self.configContainer.addControl( iCatIndex, config_ctrl )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        
    def configTriggered( self, args ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )
        
    def okTriggered( self ):
        print "OK"
        self.close()
    
    def cancel( self ):
        print "Cancel"
        self.close()

if __name__ == '__main__':
    app = QtGui.QApplication(['CPC Config Dialog'])
    
    configDialog = CPCConfigDialog()
    iColorCatIndex = configDialog.addCategory( 'Color' )
    configDialog.addConfigControl( iColorCatIndex, LevelingSliderControl("Color Scale") )
    
    configDialog.show()
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), configDialog.cancel ) 
    app.exec_() 
 

