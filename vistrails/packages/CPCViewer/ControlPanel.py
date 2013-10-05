'''
Created on Sep 27, 2013

@author: tpmaxwel
'''
import sys
import os.path
import vtk, time
from PyQt4 import QtCore, QtGui
from compiler.ast import Name

class LevelingRange( QtCore.QObject ):
    
    def __init__(self, **args ):
        super( LevelingRange, self ).__init__()
        self.windowPosition = args.get( 'pos', 0.5 )
        self.windowWidth =  args.get( 'width', 0.5 )
        self.computeRange()
        self.windowPositionSensitivity = args.get( 'pos_s', 0.05 )
        self.windowWidthSensitivity = args.get( 'width_s', 0.05 )
        self.scaling_bounds = None
        
    def setScalingBounds( self, sbounds ):
        self.scaling_bounds = sbounds

    def shiftWindow( self, position_inc, width_inc ):
        if position_inc <> 0:
            self.windowPosition = self.windowPosition + position_inc * self.windowPositionSensitivity
        if width_inc <> 0:
            if self.windowWidth < 2 * self.windowWidthSensitivity:
                self.windowWidth = self.windowWidth *  2.0**width_inc 
            else:
                self.windowWidth = self.windowWidth + width_inc * self.windowWidthSensitivity 
        self.computeRange() 
                     
    def computeRange(self):
        window_radius = self.windowWidth/2.0    
        self.rmin = max( self.windowPosition - window_radius, 0.0 )
        self.rmin = min( self.rmin, 1.0 - self.windowWidth )
        self.rmax = min( self.windowPosition + window_radius, 1.0 )
        self.rmax = max( self.rmax, self.windowWidth )

    def computeWindow(self):
        wpos = ( self.rmax + self.rmin ) / 2.0
        wwidth = ( self.rmax - self.rmin ) 
        self.windowPosition =   min( max( wpos, 0.0 ), 1.0 )
        self.windowWidth =      max( min( wwidth, 1.0 ), 0.0 )
        
    def getRange(self):
        return ( self.rmin, self.rmax )

    def getScaledRange(self):
        ds = self.scaling_bounds[1] - self.scaling_bounds[0]
        return ( self.scaling_bounds[0] + self.rmin * ds, self.scaling_bounds[0] + self.rmax * ds )

    def getWindow(self):
        return ( self.windowPosition, self.windowWidth )
    
    def setWindow(self, wpos, wwidth):
        self.windowPosition =   min( max( wpos, 0.0 ), 1.0 )
        self.windowWidth =      max( min( wwidth, 1.0 ), 0.0 )
        self.computeRange()

    def setWindowSensitivity(self, pos_s, width_s):
        self.windowPositionSensitivity = pos_s
        self.windowWidthSensitivity = width_s

    def setRange(self, rmin, rmax):
        self.rmin = min( max( rmin, 0.0 ), 1.0 )
        self.rmax = max( min( rmax, 1.0 ), 0.0 )
        self.computeWindow()

class ConfigParameter( QtCore.QObject ):

    def __init__(self, config_control, name, **args ):
        super( ConfigParameter, self ).__init__() 
        self.name = name 
        self.values = args
        self.config_control = config_control
        
    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        return self.values.get( key, None )

    def __setitem__(self, key, value):
        self.values[key] = value
        
    def getName(self):
        return self.name
    
    def initialize( self, config_str ):
        self.values = eval( config_str )

    def serialize( self ):
        return str( self.values )


class ConfigControl(QtGui.QWidget):
    
    def __init__(self, title, **args ):  
        super( ConfigControl, self ).__init__() 
        self.parameters = {}
        self.title = title
        self.tabWidget = None 
        
    def getName(self):
        return self.title 
        
    def addParameter(self, name, **args ):
        parameter = ConfigParameter( self, name, **args )
        self.parameters[ name ] = parameter
        
    def getParameters(self):
        return self.parameters.values()
        
    def addTab( self, tabname ):
        self.tabWidget.setEnabled(True)
        tabContents = QtGui.QWidget( self.tabWidget )
        layout = QtGui.QVBoxLayout()
        tabContents.setLayout(layout)
        tab_index = self.tabWidget.addTab( tabContents, tabname )
        return tab_index, layout
    
    def addButtonLayout(self):
        self.buttonLayout = QtGui.QHBoxLayout()
        self.buttonLayout.setContentsMargins(-1, 3, -1, 3)
        
        self.btnOK = QtGui.QPushButton('OK')
        self.btnCancel = QtGui.QPushButton('Cancel')

        self.buttonLayout.addWidget(self.btnOK)
        self.buttonLayout.addWidget(self.btnCancel)
        
        self.layout().addLayout(self.buttonLayout)
        
        self.btnCancel.setShortcut('Esc')
        self.connect(self.btnOK, QtCore.SIGNAL('clicked(bool)'),      self.ok )
        self.connect(self.btnCancel, QtCore.SIGNAL('clicked(bool)'),  self.cancel )

       
    def build(self):
        if self.layout() == None:
            self.setLayout(QtGui.QVBoxLayout())
            title_label = QtGui.QLabel( self.title  )
            self.layout().addWidget( title_label  )
            self.tabWidget = QtGui.QTabWidget(self)
            self.layout().addWidget( self.tabWidget )
            self.addButtonLayout()
            self.control_button = QtGui.QPushButton( self.title )
            self.connect( self.control_button,  QtCore.SIGNAL('clicked(bool)'), self.open )
            self.setMinimumWidth(450)
        
    def getButton(self):
        return self.control_button
        
    def open( self, bval ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( "Open", self.title ) )
        
    def ok(self):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( "Close", True ) )
         
    def cancel(self):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( "Close", False ) )
      
class LabeledSliderWidget( QtGui.QWidget ):
    
    def __init__(self, index, label, **args ):  
        super( LabeledSliderWidget, self ).__init__()
        slider_layout = QtGui.QHBoxLayout()
        self.setLayout(slider_layout)
        self.maxValue = args.get( 'max_value', 100 )
        self.minValue = args.get( 'min_value', 0 )
        self.initValue = args.get( 'init_value', None )
        self.scaledMaxValue = args.get( 'scaled_max_value', 1.0 )
        self.scaledMinValue = args.get( 'scaled_min_value', 0.0 )
        self.scaledInitValue = args.get( 'scaled_init_value', None )
        self.useScaledValue = ( self.scaledInitValue <> None )
        self.slider_index = index
        self.title = label
        slider_layout.setMargin(2)
        slider_label = QtGui.QLabel( label  )
        slider_layout.addWidget( slider_label  ) 
        self.slider = QtGui.QSlider( QtCore.Qt.Horizontal )
        self.slider.setRange( int(self.minValue), int(self.maxValue) ) 
        if not self.initValue:
            if (self.scaledInitValue == None): raise Exception( "Must supply init value to LabeledSliderWidget")
            fvalue = ( self.scaledInitValue - self.scaledMinValue ) / float( self.scaledMaxValue - self.scaledMinValue )
            self.initValue = int( round( self.minValue + fvalue * ( self.maxValue - self.minValue ) ) )
        self.slider.setValue( int( self.initValue ) )
        self.connect( self.slider, QtCore.SIGNAL('sliderMoved(int)'), self.sliderMoved )
        slider_label.setBuddy( self.slider )
        slider_layout.addWidget( self.slider  ) 
        self.value_pane = QtGui.QLabel( str( self.getSliderValue() ) )         
        slider_layout.addWidget( self.value_pane  )         

    def getSliderValue( self, slider_value = None ):
        slider_value = self.slider.value() if not slider_value else slider_value
        if not self.useScaledValue: return slider_value
        fvalue = ( slider_value - self.minValue ) / float( self.maxValue - self.minValue ) 
        return self.scaledMinValue + fvalue * ( self.scaledMaxValue - self.scaledMinValue )

    def sliderMoved( self, slider_value ):
        value = self.getSliderValue( slider_value )
        self.value_pane.setText( str( value ) )
        self.emit( QtCore.SIGNAL("SliderMoved"),  self.slider_index, value )
        return value

class TabbedControl( ConfigControl ):
    
    def __init__(self, title, **args ):  
        ConfigControl.__init__( self, title, **args )
        self.args = args
        self.sliders = {}
        
    def addSlider(self, label, layout, **args ):
        slider_index = len( self.sliders ) 
        slider = LabeledSliderWidget( slider_index, label, **args )
        layout.addWidget( slider  ) 
        self.sliders[slider_index] = slider
        self.connect( slider, QtCore.SIGNAL("SliderMoved"), self.sliderMoved )
        return slider_index
    
    def sliderMoved( self, slider_index, value ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.title, slider_index, value ) )
        
class IndexedSlicerControl( TabbedControl ):

    def __init__(self, title, min_value, max_value, init_value, **args ):
        super( IndexedSlicerControl, self ).__init__( title, **args )  
        self.addParameter( 'Value', value=init_value )
        self.min_value = min_value
        self.max_value = max_value
        self.init_value = init_value

    def build(self):
        super( IndexedSlicerControl, self ).build()
        self.minmax_tab_index, tab_layout = self.addTab('Min/Max' )
        self.valIndex = self.addSlider( "Value:", tab_layout, max_value=self.max_value, min_value=self.min_value, init_value=self.init_value, **self.args )
               
    def sliderMoved( self, slider_index, value ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.title, value ) )
    
class LevelingSliderControl( TabbedControl ):
    
    def __init__(self, title, wpos_init, wsize_init, **args ):  
        super( LevelingSliderControl, self ).__init__( title, **args )
        self.addParameter( 'Range', wpos=wpos_init, wsize=wsize_init )
        
    def getMinMax(self, wpos, wsize):
        smin = max( wpos - wsize/2.0, 0.0 ) 
        smax = min( wpos + wsize/2.0, 1.0 ) 
        return smin, smax
        
    def build(self):
        super( LevelingSliderControl, self ).build()
        parm = self.parameters[ 'Range' ]
        wpos = parm[ 'wpos' ]
        wsize = parm[ 'wsize' ]
        smin, smax = self.getMinMax( wpos, wsize )
        self.leveling_tab_index, tab_layout = self.addTab( 'Leveling' )
        self.wsIndex = self.addSlider( "Window Size:", tab_layout, scaled_init_value=wsize, **self.args )
        self.wpIndex = self.addSlider( "Window Position:", tab_layout, scaled_init_value=wpos, **self.args )
        self.minmax_tab_index, tab_layout = self.addTab('Min/Max')
        self.minvIndex = self.addSlider( "Min Value:", tab_layout, scaled_init_value=smin, **self.args )
        self.maxvIndex = self.addSlider( "Max Value:", tab_layout, scaled_init_value=smax, **self.args )
        
    def getScaledRange(self, slider_index, value ):
        if ( slider_index == self.wsIndex ) or  ( slider_index == self.wpIndex ):
            wsize = self.sliders[self.wsIndex].getSliderValue() if slider_index <> self.wsIndex else value
            wpos  = self.sliders[self.wpIndex].getSliderValue() if slider_index <> self.wpIndex else value
            smin, smax = self.getMinMax( wpos, wsize )
        else:
            smin = self.sliders[self.minvIndex].getSliderValue() if slider_index <> self.minvIndex else value
            smax = self.sliders[self.maxvIndex].getSliderValue() if slider_index <> self.maxvIndex else value
        return ( smin, smax )
               
    def sliderMoved( self, slider_index, value ):
        scaled_range = self.getScaledRange( slider_index, value )
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.title, scaled_range ) )
        
class VolumeControl( LevelingSliderControl ):
 
    def __init__(self, title, maxval_init, minval_init, **args ):  
        super( VolumeControl, self ).__init__( title, maxval_init, minval_init, **args )
       
       
class SlicerControl( TabbedControl ):
    
    def __init__(self, title, initval_x, initval_y, initval_z, **args ):  
        super( SlicerControl, self ).__init__( title, **args )
        self.addParameter( 'Position', x=initval_x, y=initval_y, z=initval_z )
        
    def build(self):
        super( SlicerControl, self ).build()
        self.x_tab_index, tab_layout = self.addTab('x')
        self.xhsw = self.addSlider( "High Res Slice Width:", tab_layout, scaled_init_value=0.005, **self.args )
        self.xlsw = self.addSlider( "Low Res Slice Width:", tab_layout, scaled_init_value=0.01, **self.args )
        self.y_tab_index, tab_layout = self.addTab('y')
        self.yhsw = self.addSlider( "High Res Slice Width:", tab_layout, scaled_init_value=0.005, **self.args )
        self.ylsw = self.addSlider( "Low Res Slice Width:", tab_layout, scaled_init_value=0.01, **self.args )
        self.z_tab_index, tab_layout = self.addTab('z')
        self.zhsw = self.addSlider( "High Res Slice Width:", tab_layout, scaled_init_value=0.005, **self.args )
        self.zlsw = self.addSlider( "Low Res Slice Width:", tab_layout , scaled_init_value=0.01, **self.args)
        self.connect( self.tabWidget, QtCore.SIGNAL("currentChanged(int)"), self.sliceSelected )
                        
    def sliderMoved( self, slider_index, value ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.title, 'SliceWidth', slider_index, value ) )        

    def sliceSelected( self, slice_index ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.title, 'SelectSlice', slice_index ) )        
              
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
        self.connect( config_ctrl,  QtCore.SIGNAL('ConfigCmd'), self.configOp )
        
    def configOp( self, args ):
        if  args[0] == "Open":
            config_ctrl = self.controls[  args[1] ] 
            self.scrollArea.setWidget( config_ctrl )
    
class ConfigControlContainer(QtGui.QWidget):
    
    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.config_params = {}
        self.cfgFile = None
        self.cfgDir = None
        self.setLayout(QtGui.QVBoxLayout())
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setEnabled(True)
        self.layout().addWidget( self.tabWidget )
        self.connect( self.tabWidget, QtCore.SIGNAL("currentChanged(int)"), self.categorySelected )
        
    def addCategory( self, cat_name ):
        config_list = ConfigControlList( self.tabWidget )
        tab_index = self.tabWidget.addTab( config_list, cat_name )
        return tab_index
    
    def selectCategory(self, catIndex ):
        self.tabWidget.setCurrentIndex(catIndex)
    
    def getCategoryName( self, iCatIndex ):
        return str( self.tabWidget.tabText( iCatIndex ) )
        
    def addControl( self, iCatIndex, config_ctrl ):
        config_list = self.tabWidget.widget( iCatIndex )
        config_list.addControl( iCatIndex, config_ctrl )
        self.addParameters( self.getCategoryName( iCatIndex ), config_ctrl )
        
    def addParameters( self, categoryName, config_ctrl ):
        config_name = config_ctrl.getName()
        cparms = config_ctrl.getParameters() 
        for cparm in cparms:
            key = ':'.join( [ categoryName, config_name, cparm.getName() ] )
            self.config_params[ key ] = cparm
        
    def categorySelected( self, iCatIndex ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( "CategorySelected",  self.tabWidget.tabText(iCatIndex) ) )
        
    def readConfg( self ):
        try:
            f = open( self.cfgFile, 'r' )
            while( True ):
                config_str = f.readline()
                if not config_str: break
                cfg_tok = config_str.split('=')
                parm = self.config_params.get( cfg_tok[0].strip(), None )
                if parm: parm.initialize( cfg_tok[1] )
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile

    def saveConfg( self ):
        try:
            f = open( self.cfgFile, 'w' )
            for config_item in self.config_params.items():
                cfg_str = " %s = %s " % ( config_item[0], config_item[1].serialize() )
                f.write( cfg_str )
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile
                       
        
    def init(self):
        if not self.cfgDir:
            self.cfgDir = os.path.join( os.path.expanduser( "~" ), ".cpc" )
            if not os.path.exists(self.cfgDir): 
                os.mkdir(  self.cfgDir )
        if not self.cfgFile:
            self.cfgFile = os.path.join( self.cfgDir, "cpcConfig.txt" )
        else:
            self.readConfg()
            
        for config_item in self.config_params.items():
            self.emit( QtCore.SIGNAL("ConfigCmd"), ( "InitParm",  config_item[0], config_item[1].serialize() ) )

class CPCConfigDialog(QtGui.QDialog):

    def __init__(self, parent=None):    
        QtGui.QDialog.__init__(self, parent)
                
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(False)
        self.setWindowTitle('CPC Plot Config')
        self.setLayout(QtGui.QVBoxLayout())
        
        self.scrollArea = QtGui.QScrollArea(self) 
        self.scrollArea.setFrameStyle(QtGui.QFrame.NoFrame)      
        self.scrollArea.setWidgetResizable(True)
        
        self.configContainer = ConfigControlContainer( self.scrollArea )
        self.scrollArea.setWidget( self.configContainer )
        self.scrollArea.setSizePolicy( QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding )
        self.layout().addWidget(self.scrollArea)       
        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        self.resize(600, 600)
        
        
    def addConfigControl(self, iCatIndex, config_ctrl ):
        config_ctrl.build()
        self.configContainer.addControl( iCatIndex, config_ctrl )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        
    def configTriggered( self, args ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )
    
    def activate(self):
        self.initParameters()
        self.configContainer.selectCategory( self.iSlicerCatIndex )
        self.show()
            
    def closeDialog( self ):
        self.configContainer.saveConfg()
        self.close()
        
    def initParameters(self):
        self.configContainer.init()
        
    def build(self):
        self.iColorCatIndex = self.addCategory( 'Color' )
        self.addConfigControl( self.iColorCatIndex, LevelingSliderControl("Color Scale", 0.5, 1.0 ) )
        self.iSlicerCatIndex = self.addCategory( 'Slicer' )
        self.addConfigControl( self.iSlicerCatIndex, SlicerControl("Slice Planes", 0.5, 0.5, 0.5 ) )
        self.iThresholdingCatIndex = self.addCategory( 'Volume' )
        self.addConfigControl( self.iThresholdingCatIndex, VolumeControl("Threshold Range", 0.5, 0.2 ) )
        self.iPointsCatIndex = self.addCategory( 'Points' )
        self.addConfigControl( self.iPointsCatIndex, IndexedSlicerControl("PointSize",  1, 10, 2 ) )
        
if __name__ == '__main__':
    app = QtGui.QApplication(['CPC Config Dialog'])
    
    configDialog = CPCConfigDialog()
    configDialog.build()   
    configDialog.show()
    
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), configDialog.closeDialog ) 
    app.exec_() 
 

