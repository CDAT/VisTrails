from __future__ import with_statement
from __future__ import division
from GraphEditor import *

_TRY_PYSIDE = True

try:
    if not _TRY_PYSIDE:
        raise ImportError()
    import PySide.QtCore as _QtCore
    QtCore = _QtCore
    import PySide.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = True
except ImportError:
    import sip
    try: sip.setapi('QString', 2)
    except: pass
    try: sip.setapi('QVariant', 2)
    except: pass
    import PyQt4.QtCore as _QtCore
    QtCore = _QtCore
    import PyQt4.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = False

# def _pyside_import_module(moduleName):
#     pyside = __import__('PySide', globals(), locals(), [moduleName], -1)
#     return getattr(pyside, moduleName)
# 
# 
# def _pyqt4_import_module(moduleName):
#     pyside = __import__('PyQt4', globals(), locals(), [moduleName], -1)
#     return getattr(pyside, moduleName)
# 
# 
# if USES_PYSIDE:
#     import_module = _pyside_import_module
# 
#     Signal = QtCore.Signal
#     Slot = QtCore.Slot
#     Property = QtCore.Property
# else:
#     import_module = _pyqt4_import_module
# 
#     Signal = QtCore.pyqtSignal
#     Slot = QtCore.pyqtSlot
#     Property = QtCore.pyqtProperty

import sys, collections
import os.path
import vtk, time
from compiler.ast import Name
from ColorMapManager import ColorMapManager
import vtk.util.numpy_support as VN

POS_VECTOR_COMP = [ 'xpos', 'ypos', 'zpos' ]
SLICE_WIDTH_LR_COMP = [ 'xlrwidth', 'ylrwidth', 'zlrwidth' ]
SLICE_WIDTH_HR_COMP = [ 'xhrwidth', 'yhrwidth', 'zhrwidth' ]

def deserialize_value( sval ):
    if isinstance( sval, float ): 
        return sval
    try:
        return int(sval)
    except ValueError:
        try:
            return float(sval)
        except ValueError:
            return sval

def get_value_decl( val ):
    if isinstance( val, bool ): return "bool"
    if isinstance( val, int ): return "int"
    if isinstance( val, float ): return "float"
    return "str"
       
class ConfigParameter( QtCore.QObject ):
    
    @staticmethod
    def getParameter( config_name, **args ):
        if args.get('ctype') == 'Leveling':
            return LevelingConfigParameter( config_name, **args )
        if args.get('ctype') == 'Range':
            return RangeConfigParameter( config_name, **args )
        else:
            return ConfigParameter( config_name, **args )

    def __init__(self, name, **args ):
        super( ConfigParameter, self ).__init__() 
        self.name = name 
        self.values = args
        self.valueKeyList = list( args.keys() )
     
    def __str__(self):
        return " ConfigParameter[%s]: %s " % ( self.name, str( self.values ) )
   
    def addValueKey( self, key ):
        if not (key in self.valueKeyList):
            self.valueKeyList.append( key ) 
    
    def values_decl(self):
        decl = []
        for key in self.valueKeyList:
            val = self.values.get( key, None )
            if ( val <> None ): decl.append( get_value_decl( val )  ) 
        return decl
                            
    def pack( self ):
        try:
            return ( self.name, [ str( self.values[key] ) for key in self.valueKeyList ] )
        except KeyError:
            print "Error packing parameter %s%s. Values = %s " % ( self.name, str(self.valueKeyList), str(self.values))

    def unpack( self, value_strs ):
        if len( value_strs ) <> len( self.values.keys() ): 
            print>>sys.stderr, " Error: parameter structure mismatch in %s ( %d vs %d )" % ( self.name,  len( value_strs ), len( self.values.keys() ) ); sys.stderr.flush()
        for ( key, str_val ) in zip( self.valueKeyList, value_strs ):
            self.values[key] = deserialize_value( str_val ) 
#        print " && Unpack parameter %s: %s " % ( self.name, str( self.values ) ); sys.stdout.flush()
            
    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        return self.values.get( key, None )

    def __setitem__(self, key, value ):
        self.values[key] = value 
        self.emit( QtCore.SIGNAL("ValueChanged"), ( self.name, key, value ) )
        self.addValueKey( key )

    def __call__(self, **args ):
        self.values.update( args )
        args1 = [ self.name ]
        for item in args.items():
            args1.extend( list(item) )
            self.addValueKey( item[0] )
        self.emit( QtCore.SIGNAL("ValueChanged"), args1 )
         
    def getName(self):
        return self.name
    
    def initialize( self, config_str ):
        self.values = eval( config_str )
        self.sort()

    def serialize( self ):
        return str( self.values )

    def getValue( self, key='value', default_value=None ):
        return self.values.get( key, default_value )

    def setValue( self, key, val ):
        self.values[ key ] = val
        self.addValueKey( key )

    def incrementValue( self, index, inc ):
        self.values[ index ] = self.values[ index ] + inc
        
class LevelingConfigParameter( ConfigParameter ):
    
    def __init__(self, name, **args ):
        super( LevelingConfigParameter, self ).__init__( name, **args ) 
        self.wposSensitivity = args.get( 'pos_s', 0.05 )
        self.wsizeSensitivity = args.get( 'width_s', 0.05 )
        if 'rmin' in args:  self.computeWindow()
        else:               self.computeRange()
        self.scaling_bounds = None
        
    @property
    def rmin(self):
        return self['rmin']

    @rmin.setter
    def rmin(self, value):
        self['rmin'] = value
        self.computeWindow()
        
    @property
    def rmax(self):
        return self['rmax']

    @rmax.setter
    def rmax(self, value):
        self['rmax'] = value
        self.computeWindow()

    @property
    def wpos(self):
        return self['wpos']

    @wpos.setter
    def wpos(self, value):
        self['wpos'] = value
        self.computeRange()  
        
    @property
    def wsize(self):
        return self['wsize']

    @wsize.setter
    def wsize(self, value):
        self['wsize'] = value
        self.computeRange()  
        
    def setScalingBounds( self, sbounds ):
        self.scaling_bounds = sbounds

    def shiftWindow( self, position_inc, width_inc ):
        if position_inc <> 0:
            self.wpos = self.wpos + position_inc * self.wposSensitivity
        if width_inc <> 0:
            if self.wsize < 2 * self.wsizeSensitivity:
                self.wsize = self.wsize *  2.0**width_inc 
            else:
                self.wsize = self.wsize + width_inc * self.wsizeSensitivity 
        self.computeRange() 
                     
    def computeRange(self):
        window_radius = self.wsize/2.0    
        rmin = max( self.wpos - window_radius, 0.0 )
        rmax = min( self.wpos + window_radius, 1.0 )
        self( rmin = min( rmin, 1.0 - self.wsize ), rmax =  max( rmax, self.wsize ) )

    def computeWindow(self):
        wpos = ( self.rmax + self.rmin ) / 2.0
        wwidth = ( self.rmax - self.rmin ) 
        self( wpos = min( max( wpos, 0.0 ), 1.0 ), wsize = max( min( wwidth, 1.0 ), 0.0 ) )
        
    def getScaledRange(self):
        if self.scaling_bounds:
            ds = self.scaling_bounds[1] - self.scaling_bounds[0]
            return ( self.scaling_bounds[0] + self.rmin * ds, self.scaling_bounds[0] + self.rmax * ds )
        else:
            return self.getRange()

    
    def setWindowSensitivity(self, pos_s, width_s):
        self.wposSensitivity = pos_s
        self.wsizeSensitivity = width_s

    def setRange(self, range ):
        self.rmin = min( max( range[0], 0.0 ), 1.0 )
        self.rmax = max( min( range[1], 1.0 ), 0.0 )
        
    def setWindow( self, wpos, wwidth ):
        self.wpos =   min( max( wpos, 0.0 ), 1.0 )
        self.wsize =      max( min( wwidth, 1.0 ), 0.0 )      

    def getWindow(self):
        return ( self.wpos, self.wsize )

    def getRange( self ):
        return ( self.rmin, self.rmax )

class RangeConfigParameter( ConfigParameter ):
    
    def __init__(self, name, **args ):
        super( RangeConfigParameter, self ).__init__( name, **args ) 
        self.scaling_bounds = None
        
    @property
    def rmin(self):
        return self['rmin']

    @rmin.setter
    def rmin(self, value):
        self['rmin'] = value
        
    @property
    def rmax(self):
        return self['rmax']

    @rmax.setter
    def rmax(self, value):
        self['rmax'] = value
        
    def setScalingBounds( self, sbounds ):
        self.scaling_bounds = sbounds
        
    def getScaledRange(self):
        if self.scaling_bounds:
            ds = self.scaling_bounds[1] - self.scaling_bounds[0]
            return ( self.scaling_bounds[0] + self.rmin * ds, self.scaling_bounds[0] + self.rmax * ds )
        else:
            return self.getRange()

    def setRange(self, range ):
        self.rmin = min( max( range[0], 0.0 ), 1.0 )
        self.rmax = max( min( range[1], 1.0 ), 0.0 )
        
    def getRange( self ):
        return ( self.rmin, self.rmax )

class ConfigControl(QtGui.QWidget):
    
    def __init__(self, cparm, **args ):  
        super( ConfigControl, self ).__init__() 
        self.cparm = cparm
        self.tabWidget = None 
        self.connect( cparm, QtCore.SIGNAL('ValueChanged'), self.configValueChanged )
        
    def configValueChanged( self, args ): 
        pass
    
    def processParameterChange( self, args ):
        pass

    def processExtConfigCmd( self, args ):
        pass
        
    def getName(self):
        return self.cparm.getName()
        
    def getParameter(self):
        return self.cparm
    
    def getTabLayout(self, tab_index ):
        return self.tabWidget.widget(tab_index).layout() 
                
    def addTab( self, tabname ):
        self.tabWidget.setEnabled(True)
        tabContents = QtGui.QWidget( self.tabWidget )
        layout = QtGui.QVBoxLayout()
        tabContents.setLayout(layout)
        tab_index = self.tabWidget.addTab( tabContents, tabname )
        return tab_index, layout
    
    def getCurrentTabIndex(self):
        return self.tabWidget.currentIndex() 

    def addControlRow( self, tab_index ):
        layout = self.getTabLayout( tab_index )
        widget_layout = QtGui.QHBoxLayout()
        layout.addLayout( widget_layout )
        return widget_layout
    
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
        
    def updateTabPanel(self, current_tab_index=-1 ):
        if current_tab_index == -1: current_tab_index = self.tabWidget.currentIndex() 
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.getName(), "UpdateTabPanel", current_tab_index ) )
      
    def build(self):
        if self.layout() == None:
            self.setLayout(QtGui.QVBoxLayout())
            title_label = QtGui.QLabel( self.getName()  )
            self.layout().addWidget( title_label  )
            self.tabWidget = QtGui.QTabWidget(self)
            self.layout().addWidget( self.tabWidget )
            self.connect( self.tabWidget,  QtCore.SIGNAL('currentChanged(int)'), self.updateTabPanel )
            self.addButtonLayout()
            self.control_button = QtGui.QPushButton( self.getName() )
            self.connect( self.control_button,  QtCore.SIGNAL('clicked(bool)'), self.open )
            self.setMinimumWidth(450)
            
    def refresh(self):
        pass
        
    def getButton(self):
        return self.control_button
        
    def open( self, bval ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Open" ) )
        self.updateTabPanel()
        
    def ok(self):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Close", True ) )
         
    def cancel(self):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Close", False ) )

class ConfigWidget( QtGui.QWidget ):

    def __init__(self, parent=None,  **args ): 
        QtGui.QWidget .__init__( self, parent ) 
        self.cparm = None
        
    def setParameters( self, cparm, widget_index, **args ):
        self.cparm = cparm
        self.widget_index = widget_index
        self.args = args
        
    def sendConfigCmd( self, cfg_cmd ):
        self.emit( QtCore.SIGNAL('ConfigCmd'), cfg_cmd )
        
    def processParameterChange( self, args ):
        pass

    def processExtConfigCmd( self, args ):
        pass
      
class LabeledSliderWidget( ConfigWidget ):
    
    def __init__(self, index, label, **args ):  
        super( LabeledSliderWidget, self ).__init__()
        slider_layout = QtGui.QHBoxLayout()
        self.setLayout(slider_layout)
        self.cparm = args.get( 'cparm', None )
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
        self.connect( self.slider, QtCore.SIGNAL('sliderPressed()'), self.configStart )
        self.connect( self.slider, QtCore.SIGNAL('sliderReleased()'), self.configEnd )
        slider_label.setBuddy( self.slider )
        slider_layout.addWidget( self.slider  ) 
        self.value_pane = QtGui.QLabel( str( self.getSliderValue() ) )         
        slider_layout.addWidget( self.value_pane  )  
        
    def getTitle(self):
        return self.title
        
    def setSliderValue( self, normailzed_slider_value ): 
        index_value = int( round( self.minValue + normailzed_slider_value * ( self.maxValue - self.minValue ) ) )
        scaled_slider_value = self.scaledMinValue + normailzed_slider_value * ( self.scaledMaxValue - self.scaledMinValue )
        self.value_pane.setText( str( scaled_slider_value ) )
        self.slider.setValue( index_value )      

    def getSliderValue( self, svalue = None ):
        slider_value = self.slider.value() if ( svalue == None ) else svalue
        if not self.useScaledValue: return slider_value
        fvalue = ( slider_value - self.minValue ) / float( self.maxValue - self.minValue ) 
        svalue = self.scaledMinValue + fvalue * ( self.scaledMaxValue - self.scaledMinValue )
#        print " getSliderValue: %s %d %f %f" % ( str(svalue), slider_value, fvalue, svalue )
        return svalue

    def sliderMoved( self, raw_slider_value ):
        scaled_slider_value = self.getSliderValue( raw_slider_value )
        self.value_pane.setText( str( scaled_slider_value ) )
        self.emit( QtCore.SIGNAL('ConfigCmd'), 'Moved', self.slider_index, ( raw_slider_value, scaled_slider_value ) )
        return scaled_slider_value
    
    def isTracking(self):
        return self.slider.isSliderDown()
    
    def configStart( self ):
        self.emit( QtCore.SIGNAL('ConfigCmd'), 'Start', self.slider_index ) 

    def configEnd( self ):
        self.emit( QtCore.SIGNAL('ConfigCmd'), 'End', self.slider_index ) 
        

class TabbedControl( ConfigControl ):
        
    def __init__(self, cparm, **args ):  
        ConfigControl.__init__( self, cparm, **args )
        self.args = args
        self.widgets = {}
       
    def addSlider(self, label, layout, **args ):
        slider_index = len( self.widgets ) 
        slider = LabeledSliderWidget( slider_index, label, cparm=self.cparm, **args )
        self.connect( slider, QtCore.SIGNAL('ConfigCmd'), self.processSliderConfigCmd )
        layout.addWidget( slider  ) 
        self.widgets[slider_index] = slider
        return slider_index

    def addConfigWidget(self, widget, layout, **args ):
        widget_index = len( self.widgets ) 
        widget.setParameters( self.cparm, widget_index, **args )
        self.connect( widget, QtCore.SIGNAL('ConfigCmd'), self.processConfigCmd )
        layout.addWidget( widget  ) 
        self.widgets[widget_index] = widget
        return widget_index

    def processParameterChange( self, args ):
        for cfg_widget in self.widgets.values():
            try: cfg_widget.processParameterChange( args )
            except: pass

    def processExtConfigCmd( self, args ):
        for cfg_widget in self.widgets.values():
            try: cfg_widget.processExtConfigCmd( args )
            except: pass

    def getTitle( self, widget_index ):
        w = self.widgets[widget_index]
        return w.getTitle()

    def addCheckbox(self, label, layout, **args ):
        cbox_index = len( self.widgets ) 
        checkBox = QtGui.QCheckBox(label)
        layout.addWidget( checkBox )
        self.connect( checkBox, QtCore.SIGNAL("stateChanged(int)"), lambda cbvalue, cbname=label: self.processWidgetConfigCmd( str(cbname), int(cbvalue) ) ) 
        ival = self.cparm.getValue( label, False )
        checkBox.setCheckState( QtCore.Qt.Checked if ival else QtCore.Qt.Unchecked )
        self.widgets[cbox_index] = checkBox
        return cbox_index
    
    def addRadioButtons(self, label_list, layout, **args):
        init_index = args.get( 'init_index', 0 )
        for rbindex, label in enumerate( label_list ):
            rbutton = QtGui.QRadioButton ( label, self )
            layout.addWidget( rbutton )
            self.connect( rbutton, QtCore.SIGNAL("pressed()"), lambda rbname=label: self.processWidgetConfigCmd(str(rbname)) ) 
            if rbindex == init_index: rbutton.setChecked(True)
                
    def addListSelection(self, label, list_items, layout ):
        list_index = len( self.widgets ) 
        list_layout = QtGui.QHBoxLayout()
        layout.addLayout( list_layout )
        list_label = QtGui.QLabel( label )
        list_layout.addWidget( list_label ) 
        listCombo =  QtGui.QComboBox ( self.parent() )
        list_label.setBuddy( listCombo )
        listCombo.setMaximumHeight( 30 )
        list_layout.addWidget( listCombo )
        for item in list_items: listCombo.addItem( str(item) )
        try:
            ival = self.cparm.getValue( label, "None" )
            current_index = list_items.index( ival )
            listCombo.setCurrentIndex ( current_index )
        except Exception, err: 
            print>>sys.stderr, "Can't find initial colormap: %s " % ival
        self.connect( listCombo, QtCore.SIGNAL("currentIndexChanged(QString)"), lambda lvalue, listname=label: self.processWidgetConfigCmd( str(listname), str(lvalue) ) )  
        self.widgets[list_index] = listCombo
        return list_index
    
    def sliderMoved(self, slider_index, raw_slider_value, scaled_slider_value):
        self.cparm.setValue( "CurrentIndex", slider_index )
        self.cparm[ slider_index ] = scaled_slider_value
        
    def processSliderConfigCmd(self, cmd, slider_index, values=None ):
        if cmd == 'Moved': 
            self.sliderMoved( slider_index, values[0], values[1] )
        if cmd == 'Start': 
            self.emit( QtCore.SIGNAL("ConfigCmd"),  [ self.getName(), "StartConfig", slider_index, self.getId(slider_index) ] )
        if cmd == 'End': 
            self.emit( QtCore.SIGNAL("ConfigCmd"),  [ self.getName(), "EndConfig", slider_index, self.getId(slider_index) ]  )

    def processWidgetConfigCmd(self, widget_name, widget_value=None ):
        if widget_value == None:
            self.cparm[ "selected" ] = widget_name
        else:
            self.cparm[ widget_name ] = widget_value
#        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.getName(), cbox_name, cbox_value ) )

    def processConfigCmd(self, cmd ):
#        self.cparm[ widget_index ] = values 
        self.emit( QtCore.SIGNAL("ConfigCmd"),  cmd ) #[ self.getName(), cmd, widget_index, values ] )


    def getId( self, slider_index ):
        return self.widgets[slider_index].getTitle() 
    
    def build(self):
        super( TabbedControl, self ).build()
        cats = self.cparm[ 'cats' ]
        if cats:
            for category_spec in cats:
                tab_index, tab_layout = self.addTab( category_spec[0] )
                init_value = category_spec[4] 
                self.addSlider( category_spec[1], tab_layout, max_value=category_spec[3], min_value=category_spec[2], init_value=init_value, **self.args )
                self.cparm.setValue( tab_index, init_value )
    
    def addWidgetBox( self, layout ):
        widget_layout = QtGui.QHBoxLayout()
        layout.addLayout( widget_layout )
        return widget_layout
               
    def addButtonBox(self, button_list, layout, **args ):
        button_layout = QtGui.QHBoxLayout()
        layout.addLayout( button_layout )
        
        for btnName in button_list:        
            button = QtGui.QPushButton( btnName )
            button_layout.addWidget( button )
            self.connect( button, QtCore.SIGNAL('clicked(bool)'), lambda bval, bName=btnName: self.buttonClicked(bName) )
            
    def buttonClicked( self, btnName ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.getName(), "ButtonClick", btnName ) )

class RadioButtonSelectionControl( TabbedControl ):

    def __init__(self, cparm, **args ):
        super( RadioButtonSelectionControl, self ).__init__( cparm, **args )

    def build(self):
        super( RadioButtonSelectionControl, self ).build()
        tab_index, tab_layout = self.addTab( '' )   
        choices = self.cparm.getValue( 'choices', [] ) 
        init_selection_index = self.cparm.getValue( 'init_index', 0 ) 
        self.addRadioButtons( choices, tab_layout, init_index=init_selection_index )                         

class ColormapControl( TabbedControl ):   

       
    def __init__(self, cparm, **args ):
        TabbedControl.__init__( self, cparm, **args )
                
#    def getValue(self):
#        checkState = 1 if ( self.invertCheckBox.checkState() == QtCore.Qt.Checked ) else 0
#        stereoState = 1 if ( self.stereoCheckBox.checkState() == QtCore.Qt.Checked ) else 0
#        smoothState = 1 if ( self.smoothCheckBox.checkState() == QtCore.Qt.Checked ) else 0
#        return [ str( self.colormapCombo.currentText() ), checkState, stereoState, smoothState ]
#
#    def setValue( self, value ):
#        colormap_name = str( value[0] )
#        check_state = QtCore.Qt.Checked if int(float(value[1])) else QtCore.Qt.Unchecked
#        stereo_state = QtCore.Qt.Checked if int(float(value[2])) else QtCore.Qt.Unchecked
#        smooth_state = QtCore.Qt.Unchecked if ( len(value) > 3 ) and ( int(float(value[3])) == 0 ) else QtCore.Qt.Checked
#        itemIndex = self.colormapCombo.findText( colormap_name, QtCore.Qt.MatchFixedString )
#        if itemIndex >= 0: self.colormapCombo.setCurrentIndex( itemIndex )
#        else: print>>sys.stderr, " Can't find colormap: %s " % colormap_name
#        self.invertCheckBox.setCheckState( check_state )
#        self.stereoCheckBox.setCheckState( stereo_state )
#        self.smoothCheckBox.setCheckState( smooth_state )
                
    def build(self):
        super( ColormapControl, self ).build()
        tab_index, tab_layout = self.addTab( '' )      
        self.addListSelection( "Colormap", ColorMapManager.getColormapNames(), tab_layout )                         
        cbox_layout = self.addWidgetBox( tab_layout )
        self.addCheckbox( 'Invert', cbox_layout  )
        self.addCheckbox( 'Stereo', cbox_layout  )
        self.addCheckbox( 'Colorbar', cbox_layout  )
#        self.addCheckbox( 'Smooth', cbox_layout  )

class SliderControl( TabbedControl ):

    def __init__(self, cparm, **args ):
        super( SliderControl, self ).__init__( cparm, **args )  

    def sliderMoved(self, slider_index, raw_slider_value, scaled_slider_value):
        self.cparm[ "value" ] = scaled_slider_value 
        self.cparm[ "CurrentIndex" ] = slider_index

    def build(self):
        super( SliderControl, self ).build()
        ival = self.cparm.getValue( "value" , 0.5 )
        label = self.cparm.getValue( "label" , "Value:" )
        tab_name = self.cparm.getValue( "tab" , "" )
        self.leveling_tab_index, tab_layout = self.addTab( tab_name )
        self.sIndex = self.addSlider( label, tab_layout, scaled_init_value=ival, **self.args )
            
class IndexedSliderControl( TabbedControl ):

    def __init__(self, cparm, **args ):
        super( IndexedSliderControl, self ).__init__( cparm, **args )  

    def sliderMoved(self, slider_index, raw_slider_value, scaled_slider_value):
        self.cparm.setValue( slider_index, int( raw_slider_value ) )
        self.cparm[ "CurrentIndex" ] = slider_index

    def build(self):
        super( IndexedSliderControl, self ).build()

class PointSizeSliderControl( IndexedSliderControl ):

    def __init__(self, cparm, **args ):
        super( PointSizeSliderControl, self ).__init__( cparm, **args )  
           
class LevelingSliderControl( TabbedControl ):
    
    def __init__(self, cparm, **args ):  
        super( LevelingSliderControl, self ).__init__( cparm, **args )
        self.leveling_tab_index = None
        self.minmax_tab_index = None
        self.updatingTabPanel = False
        
    def getMinMax(self, wpos, wsize):
        smin = max( wpos - wsize/2.0, 0.0 ) 
        smax = min( wpos + wsize/2.0, 1.0 ) 
        return smin, smax
        
    def build(self):
        super( LevelingSliderControl, self ).build()
        wpos = self.cparm[ 'wpos' ]
        wsize = self.cparm[ 'wsize' ]
        smin, smax = self.getMinMax( wpos, wsize )
        self.leveling_tab_index, tab_layout = self.addTab( 'Leveling' )
        self.wsIndex = self.addSlider( "Window Size:", tab_layout, scaled_init_value=wsize, **self.args )
        self.wpIndex = self.addSlider( "Window Position:", tab_layout, scaled_init_value=wpos, **self.args )
        self.minmax_tab_index, tab_layout = self.addTab('Min/Max')
        self.minvIndex = self.addSlider( "Min Value:", tab_layout, scaled_init_value=smin, **self.args )
        self.maxvIndex = self.addSlider( "Max Value:", tab_layout, scaled_init_value=smax, **self.args )
        
    def updateTabPanel(self, current_tab_index = -1 ): 
        self.updatingTabPanel = True
        if current_tab_index == -1: 
            current_tab_index = self.tabWidget.currentIndex()
#        print "tabChanged: %s" % str( ( current_tab_index, self.leveling_tab_index, self.minmax_tab_index ) ); sys.stdout.flush()
        if ( self.leveling_tab_index <> None ) and ( current_tab_index == self.leveling_tab_index ):
            self.updateLevelingSliders()
        if ( self.minmax_tab_index <> None )  and ( current_tab_index == self.minmax_tab_index ):
            self.updateMinMaxSliders()
        self.updatingTabPanel = False
            
    def configValueChanged(self): 
        if not self.updatingTabPanel:
            self.updateTabPanel()
            
    def updateLevelingSliders(self):
        wsSlider = self.widgets[ self.wsIndex ]
        wpSlider = self.widgets[ self.wpIndex ]
        if not wpSlider.isTracking() and not wsSlider.isTracking():
            ( wpos, wsize ) = self.cparm.getWindow()
            print "Update Leveling sliders: %s " % str( ( wpos, wsize ) ); sys.stdout.flush()
            wsSlider.setSliderValue( wsize )
            wpSlider.setSliderValue( wpos )

    def updateMinMaxSliders(self):
        minSlider = self.widgets[ self.minvIndex ]
        maxSlider = self.widgets[ self.maxvIndex ]
        if not minSlider.isTracking() and not maxSlider.isTracking():
            ( rmin, rmax )  = self.cparm.getRange()
#            print "Update Min Max sliders: %s " % str( ( rmin, rmax ) ); sys.stdout.flush()
            minSlider.setSliderValue( rmin )
            maxSlider.setSliderValue( rmax )
                
    def getScaledRange(self, slider_index, value ):
        if ( slider_index == self.wsIndex ) or  ( slider_index == self.wpIndex ):
            wsize = self.widgets[self.wsIndex].getSliderValue() if slider_index <> self.wsIndex else value
            wpos  = self.widgets[self.wpIndex].getSliderValue() if slider_index <> self.wpIndex else value
            smin, smax = self.getMinMax( wpos, wsize )
        else:
            smin = self.widgets[self.minvIndex].getSliderValue() if slider_index <> self.minvIndex else value
            smax = self.widgets[self.maxvIndex].getSliderValue() if slider_index <> self.maxvIndex else value
        return ( smin, smax )

    def getLevelingRange(self, slider_index, value ):
        if ( slider_index == self.wsIndex ) or  ( slider_index == self.wpIndex ):
            wsize = self.widgets[self.wsIndex].getSliderValue() if slider_index <> self.wsIndex else value
            wpos  = self.widgets[self.wpIndex].getSliderValue() if slider_index <> self.wpIndex else value
        else:
            smin = self.widgets[self.minvIndex].getSliderValue() if slider_index <> self.minvIndex else value
            smax = self.widgets[self.maxvIndex].getSliderValue() if slider_index <> self.maxvIndex else value
            wsize =  ( smax - smin )
            wpos =  ( smax + smin ) / 2.0
        return ( wsize, wpos )

    def sliderMoved( self, slider_index, raw_slider_value, scaled_slider_value ):
        ( wsize, wpos ) = self.getLevelingRange( slider_index, scaled_slider_value )
        self.cparm.setWindow( wpos, wsize )
        
class OpacityGraphWidget( ConfigWidget ):

    def __init__( self, parent ):
        ConfigWidget.__init__( self, parent )  
        self.graph = GraphWidget( size=(400,300), nticks=(5,5) )
        self.connect( self.graph, GraphWidget.transferFunctionEditedSignal, self.transferFunctionEdited )
#        self.connect( self.graph, GraphWidget.nodeMovedSignal, self.graphAdjusted )
#        self.connect( self.graph, GraphWidget.moveCompletedSignal, self.doneConfig )
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget( self.graph )         
        self.trange = [ 0.0, 1.0 ]
        
    def processParameterChange( self, args ):
#        print "OpacityGraphWidget.parameterValueChanged: ", str(args)
        if ( args[0] == 'Threshold Range' ) and ( len(args) >= 5 ):
            trange = [ None, None ]
            for iArg in range(1,5):
                if args[iArg] == 'rmin':
                    trange[0] = args[iArg+1]
                elif args[iArg] == 'rmax':
                    trange[1] = args[iArg+1]
            if trange[0] <> None:
                self.graph.updateThresholdRange( trange )

    def processExtConfigCmd( self, args ):
        pass
    
    def doneConfig( self ):
        self.emit( QtCore.SIGNAL('doneConfig()') )    
    
    def transferFunctionEdited(self, tfData ):
        self.sendConfigCmd( [ 'Opacity Graph', tfData ] )
            
    def updateGraph( self, xbounds, ybounds, data=[] ):
        self.graph.redrawGraph( xbounds, ybounds, data )

class OpacityScaleControl( TabbedControl ):
    
    def __init__(self, cparm, tcparm, **args ):  
        super( OpacityScaleControl, self ).__init__( cparm, **args )
        self.threshold_cparm = tcparm
        self.opacity_ramp_tab_index = -1
        self.vbounds = args.get('vbounds', [ 0.0, 1.0 ] )
        self.computeTBounds()
        self.graph_widget = None
        
    def computeTBounds(self):
        vrng = self.vbounds[1] - self.vbounds[0]
        self.tbounds = [ self.vbounds[0] + vrng*self.threshold_cparm.rmin, self.vbounds[0] + vrng*self.threshold_cparm.rmax ]
                           
    def build(self):
        super( OpacityScaleControl, self ).build()
        rmax = self.cparm[ 'rmax' ]
        rmin = self.cparm[ 'rmin' ]
        self.opacity_ramp_tab_index, tab_layout = self.addTab('Opacity Ramp Function')
        self.minvIndex = self.addSlider( "Bottom Opacity Value:", tab_layout, scaled_init_value=rmin, **self.args )
        self.maxvIndex = self.addSlider( "Top Opacity Value:", tab_layout, scaled_init_value=rmax, **self.args )
        self.opacity_graph_tab_index, tab_layout = self.addTab('Opacity Graph Function')
        self.graph_widget = OpacityGraphWidget(self)
        self.build_graph()
        self.graphIndex = self.addConfigWidget( self.graph_widget, tab_layout )
                
    def build_graph(self):
        if self.tbounds[0]*self.tbounds[1] < 0.0:
            midpoint = ( 0.0, 0.0, { 'xbound': True } ) 
            if ( self.tbounds[1] > abs(self.tbounds[0]) ):
                startpoint = ( self.tbounds[0], abs(self.tbounds[0]/self.tbounds[1]), { 'xbound': True }  ) 
                end_point = ( self.tbounds[1], 1.0, { 'xbound': True }  ) 
            else: 
                startpoint = ( self.tbounds[0], 1.0, { 'xbound': True }  )
                end_point =  ( self.tbounds[1], abs(self.tbounds[1]/self.tbounds[0]), { 'xbound': True }  ) 
        else:
            midpoint = ( (self.tbounds[0]+self.tbounds[1])/2.0, 0.5, {} ) 
            startpoint = ( self.tbounds[0], 0.0, { 'xbound': True }  ) 
            end_point = ( self.tbounds[1], 1.0, { 'xbound': True }  )
        data = [ startpoint, midpoint,  end_point ]
        print " Build Graph, tbounds = %s, data = %s " % ( str(self.tbounds), str(data) )
        self.graph_widget.updateGraph( self.tbounds, [ 0.0, 1.0 ], data )
        
    def refresh(self):
        self.computeTBounds()
        self.build_graph()

#    def processParameterChange( self, args ):
#        TabbedControl.processParameterChange( self, args )
#        if ( args[0] == 'Threshold Range' ) and ( len(args) >= 5 ):
#            trange = [ None, None ]
#            for iArg in range(1,5):
#                if args[iArg] == 'rmin':
#                    self.trange[0] = args[iArg+1]
#                elif args[iArg] == 'rmax':
#                    self.trange[1] = args[iArg+1]
#            if self.trange[0] <> None: self.computeTBounds()
        
    def updateTabPanel(self, current_tab_index = -1 ): 
        self.updatingTabPanel = True
        if self.opacity_ramp_tab_index >= 0:
            self.updateMinMaxSliders()
        self.updatingTabPanel = False
            
    def configValueChanged(self): 
        if not self.updatingTabPanel:
            self.updateTabPanel()
            
    def updateMinMaxSliders(self):
        minSlider = self.widgets[ self.minvIndex ]
        maxSlider = self.widgets[ self.maxvIndex ]
        if not minSlider.isTracking() and not maxSlider.isTracking():
            srange  = self.cparm.getRange()
            print "Update Min Max sliders: %s " % str( srange ); 
            minSlider.setSliderValue( srange[0] )
            maxSlider.setSliderValue( srange[1] )

    def getRange(self, slider_index, value ):
        vmin = self.widgets[self.minvIndex].getSliderValue() if slider_index <> self.minvIndex else value
        vmax = self.widgets[self.maxvIndex].getSliderValue() if slider_index <> self.maxvIndex else value
        return ( vmin, vmax )

    def sliderMoved( self, slider_index, raw_slider_value, scaled_slider_value ):
        vbounds = self.getRange( slider_index, scaled_slider_value )
        self.cparm.setRange( vbounds )

class ColorScaleControl( LevelingSliderControl ):
 
    def __init__(self, cparm, **args ):  
        super( ColorScaleControl, self ).__init__( cparm, **args )

    def build(self):
        super( ColorScaleControl, self ).build()
        layout = self.getTabLayout( self.minmax_tab_index )
        self.addButtonBox( [ "Match Threshold Range", "Reset"], layout )

class AnimationControl( TabbedControl ):
 
    def __init__(self, cparm, **args ):  
        super( AnimationControl, self ).__init__( cparm, **args )

    def build(self):
        super( AnimationControl, self ).build()
        self.x_tab_index, tab_layout = self.addTab('Run Controls')
        self.addButtonBox( [ "Run", "Step", "Stop" ], tab_layout )
 
class InfoGridControl( TabbedControl ): 
    
    def __init__(self, cparm, **args ):  
        super( InfoGridControl, self ).__init__( cparm, **args )

    def build(self):
        super( InfoGridControl, self ).build()
        self.x_tab_index, tab_layout = self.addTab('Run Controls')
        self.addButtonBox( [ "Run", "Step", "Stop" ], tab_layout )
              
class VolumeControl( LevelingSliderControl ):
 
    def __init__(self, cparm, **args ):  
        super( VolumeControl, self ).__init__( cparm, **args )
              
class SlicerControl( TabbedControl ):
    
    def __init__(self, cparm, **args ):  
        super( SlicerControl, self ).__init__( cparm, **args )
        self.wrange = args.get( 'wrange', [ 0.0001, 0.02 ])
        
    def build(self):
        super( SlicerControl, self ).build()
        self.x_tab_index, tab_layout = self.addTab('x')
        self.xhsw = self.addSlider( "High Res Slice Width:", tab_layout, scaled_init_value=self.cparm['xhrwidth'], scaled_min_value= self.wrange[0], scaled_max_value= self.wrange[1], **self.args )
        self.xlsw = self.addSlider( "Low Res Slice Width:", tab_layout, scaled_init_value=self.cparm['xlrwidth'], scaled_min_value= self.wrange[0], scaled_max_value= self.wrange[1], **self.args )
        self.xsp  = self.addSlider( "Slice Position:", tab_layout, scaled_init_value=self.cparm['xpos'], **self.args )
        self.y_tab_index, tab_layout = self.addTab('y')
        self.yhsw = self.addSlider( "High Res Slice Width:", tab_layout, scaled_init_value=self.cparm['yhrwidth'], scaled_min_value= self.wrange[0], scaled_max_value= self.wrange[1], **self.args )
        self.ylsw = self.addSlider( "Low Res Slice Width:", tab_layout, scaled_init_value=self.cparm['ylrwidth'], scaled_min_value= self.wrange[0], scaled_max_value= self.wrange[1], **self.args )
        self.ysp  = self.addSlider( "Slice Position:", tab_layout, scaled_init_value=self.cparm['ypos'], **self.args )
        self.z_tab_index, tab_layout = self.addTab('z')
#         self.zhsw = self.addSlider( "High Res Slice Width:", tab_layout, scaled_init_value=0.005, **self.args )
#         self.zlsw = self.addSlider( "Low Res Slice Width:", tab_layout , scaled_init_value=0.01, **self.args)
        self.zsp  = self.addSlider( "Slice Position:", tab_layout, scaled_init_value=0.5, **self.args )
        self.connect( self.tabWidget, QtCore.SIGNAL("currentChanged(int)"), self.sliceSelected )
                        
    def sliderMoved( self, slider_index, raw_val, norm_val ):
#        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.getName(), self.getTitle( slider_index ),  slider_index, raw_val, norm_val ) )  
        id = self.getId( slider_index )       
        self.cparm[id] = norm_val

    def getId( self, slider_index ):
        if   slider_index == self.xhsw: return 'xhrwidth'
        elif slider_index == self.xlsw: return 'xlrwidth'
        elif slider_index == self.xsp:  return 'xpos'
        elif slider_index == self.yhsw: return 'yhrwidth'
        elif slider_index == self.ylsw: return 'ylrwidth'
        elif slider_index == self.ysp:  return 'ypos'
        elif slider_index == self.zsp:  return 'zpos'
        
#         slice_specs = self.cparm.getValue('specs',{})
#         slice_specs[ slider_index ] = norm_val
        
#         elif slider_index == self.zhsw: self.cparm['zhrwidth'] = raw_val
#         elif slider_index == self.zlsw: self.cparm['zlrwidth'] = raw_val
        
    def sliceSelected( self, slice_index ):
        self.emit( QtCore.SIGNAL("ConfigCmd"),  ( self.getName(), 'SelectSlice', slice_index ) ) 
        
    def setSlicePosition( self, pos ): 
        tab_index = self.getCurrentTabIndex()
        slider_index = -1 
        if   tab_index==self.x_tab_index: slider_index = self.xsp           
        elif tab_index==self.y_tab_index: slider_index = self.ysp           
        elif tab_index==self.z_tab_index: slider_index = self.zsp           
        if slider_index >= 0:   
            slicer = self.widgets[slider_index] 
            slicer.setSliderValue( pos )  

    def configValueChanged( self, args ): 
        super( SlicerControl, self ).configValueChanged( args )
        op = args[1]
        if op in POS_VECTOR_COMP:
            self.setSlicePosition( args[2] )
              
class ConfigControlList(QtGui.QWidget):

    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.setLayout( QtGui.QVBoxLayout() )
        self.buttonBox = QtGui.QGridLayout()
        self.layout().addLayout( self.buttonBox )
        self.current_control_row = 0
        self.current_control_col = 0
        self.controls = {}
#        self.scrollArea = QtGui.QScrollArea(self) 
#        self.layout().addWidget(self.scrollArea)
        self.stackedWidget =   QtGui.QStackedWidget( self )
        self.layout().addWidget( self.stackedWidget )
        self.blank_widget = QtGui.QWidget() 
        self.blankWidgetIndex = self.stackedWidget.addWidget( self.blank_widget )
        
    def clear(self):
        self.stackedWidget.setCurrentIndex ( self.blankWidgetIndex )
        
    def refresh(self):
        for ctrl in self.controls.values():
            try: ctrl.refresh()
            except: pass
        
    def addControlRow(self):
        self.current_control_row = self.current_control_row + 1
        self.current_control_col = 0

    def addControl( self, iCatIndex, config_ctrl ):
        control_name = config_ctrl.getName()
        control_index = self.stackedWidget.addWidget( config_ctrl )
        self.controls[ control_name ] = config_ctrl
        self.buttonBox.addWidget( config_ctrl.getButton(), self.current_control_row, self.current_control_col ) 
        self.connect( config_ctrl,  QtCore.SIGNAL('ConfigCmd'), self.configOp )
        self.current_control_col = self.current_control_col + 1
        self.clear()
        
    def configOp( self, args ):
        if ( len(args) > 1 ) and ( args[1] == "Open"):
            config_ctrl = self.controls.get(  args[0], None  )
            if config_ctrl: self.stackedWidget.setCurrentWidget ( config_ctrl )
            else: print>>sys.stderr, "ConfigControlList Can't find control: %s " % args[1]
            self.updateGeometry()
#            self.scrollArea.updateGeometry()
    
class ConfigControlContainer(QtGui.QWidget):
    
    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
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
    
    def getCategoryConfigList( self, iCatIndex ):
        return self.tabWidget.widget( iCatIndex )        
        
    def categorySelected( self, iCatIndex ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( "CategorySelected",  self.tabWidget.tabText(iCatIndex) ) )
        config_list = self.tabWidget.widget ( iCatIndex ) 
        config_list.refresh()

class CPCConfigGui(QtGui.QDialog):

    def __init__(self, metadata={} ):    
        QtGui.QDialog.__init__( self )     
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(False)
        self.setWindowTitle('CPC Plot Config')
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.config_widget = ConfigurationWidget( self, metadata )
        self.layout().addWidget( self.config_widget ) 
        self.config_widget.build()
        self.resize(700, 700)

    def closeDialog( self ):
        self.config_widget.saveConfig()
        self.close()

    def activate(self):
        self.config_widget.activate()
        
    def getConfigWidget(self):
        return self.config_widget

class CPCInfoVisGui(QtGui.QDialog):

    def __init__(self, metadata={} ):    
        QtGui.QDialog.__init__( self )     
                
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(False)
        self.setWindowTitle('CPC InfoVis Config')
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.config_widget = InfoVisWidget( self, metadata )
        self.layout().addWidget( self.config_widget ) 
        self.config_widget.build()
        self.resize(600, 450)

    def closeDialog( self ):
        self.config_widget.saveConfig()
        self.close()

    def activate(self):
        self.config_widget.activate()
        
    def getConfigWidget(self):
        return self.config_widget

class InfoVisWidget(QtGui.QWidget):

    def __init__(self, parent=None, metadata={} ):    
        QtGui.QWidget.__init__(self, parent)
        self.metadata = metadata 
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.cfgManager = ConfigManager( self )

        self.tagged_controls = []
                        
        self.scrollArea = QtGui.QScrollArea(self) 
        self.scrollArea.setFrameStyle(QtGui.QFrame.NoFrame)      
        self.scrollArea.setWidgetResizable(True)
        
        self.configContainer = ConfigControlContainer( self.scrollArea )
        self.scrollArea.setWidget( self.configContainer )
        self.scrollArea.setSizePolicy( QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding )
        layout.addWidget(self.scrollArea)       
        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )

    def addControl( self, iCatIndex, config_ctrl, id = None ):
        config_list = self.configContainer.getCategoryConfigList( iCatIndex )
        config_list.addControl( iCatIndex, config_ctrl )
        self.tagged_controls.append( config_ctrl )
    
    def parameterValueChanged( self, args ):
#        print "parameterValueChanged: ", str(args)
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processParameterChange( args )
                    
    def addConfigControl(self, iCatIndex, config_ctrl, id = None ):
        config_ctrl.build()
        self.addControl( iCatIndex, config_ctrl, id )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        self.connect( config_ctrl.getParameter(), QtCore.SIGNAL("ValueChanged"), self.parameterValueChanged )
                
    def configTriggered( self, args ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processExtConfigCmd( args )

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )

    def addControlRow( self, tab_index ):
        cfgList = self.configContainer.getCategoryConfigList( tab_index )
        cfgList.addControlRow()
        
    def activate(self):
        self.cfgManager.initParameters()
        self.configContainer.selectCategory( self.iVariableCatIndex )
                           
    def getCategoryName( self, iCatIndex ):
        return self.configContainer.getCategoryName( iCatIndex )
    
    def askToSaveChanges(self):
        self.emit( QtCore.SIGNAL("Close"), self.getParameterPersistenceList() )

    def build( self, **args ):
        self.iVariablesCatIndex = self.addCategory( 'Variables' )

    def saveConfig(self):
        self.cfgManager.saveConfig()

    def generateParallelCoordinatesChart( self ):
        input = self.inputModule().getOutput() 
        ptData = input.GetPointData()
        narrays = ptData.GetNumberOfArrays()
        arrays = []
        # Create a table with some points in it...
        table = vtk.vtkTable()
        for iArray in range( narrays ):
            table.AddColumn(  ptData.GetArray( iArray ) )                  
        
        # Set up a 2D scene, add an XY chart to it
        view = vtk.vtkContextView()
#        view.SetRenderer( self.renderer )    
#        view.SetRenderWindow( self.renderer.GetRenderWindow() )
        view.GetRenderer().SetBackground(1.0, 1.0, 1.0)
        view.GetRenderWindow().SetSize(600,300)
        
        chart = vtk.vtkChartParallelCoordinates()
        
        brush = vtk.vtkBrush()
        brush.SetColorF (0.1,0.1,0.1)
        chart.SetBackgroundBrush(brush)
        
        # Create a annotation link to access selection in parallel coordinates view
        annotationLink = vtk.vtkAnnotationLink()
        # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
        # See vtkSelectionNode doc for field and content type enum values
        annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
        annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
        # Connect the annotation link to the parallel coordinates representation
        chart.SetAnnotationLink(annotationLink)
        
        view.GetScene().AddItem(chart)
                
        
        chart.GetPlot(0).SetInput(table)
        
        def selectionCallback(caller, event):
                annSel = annotationLink.GetCurrentSelection()
                if annSel.GetNumberOfNodes() > 0:
                        idxArr = annSel.GetNode(0).GetSelectionList()
                        if idxArr.GetNumberOfTuples() > 0:
                                print VN.vtk_to_numpy(idxArr)
        
        # Set up callback to update 3d render window when selections are changed in 
        #       parallel coordinates view
        annotationLink.AddObserver("AnnotationChangedEvent", selectionCallback)
                
#        view.ResetCamera()
#        view.Render()       
#        view.GetInteractor().Start()
        return view 


        
class ConfigurationWidget(QtGui.QWidget):

    def __init__(self, parent=None, metadata={} ):    
        QtGui.QWidget.__init__(self, parent)
        self.metadata = metadata 
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.cfgManager = ConfigManager( self )

        self.tagged_controls = []
                        
        self.scrollArea = QtGui.QScrollArea(self) 
        self.scrollArea.setFrameStyle(QtGui.QFrame.NoFrame)      
        self.scrollArea.setWidgetResizable(True)
        
        self.configContainer = ConfigControlContainer( self.scrollArea )
        self.scrollArea.setWidget( self.configContainer )
        self.scrollArea.setSizePolicy( QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding )
        layout.addWidget(self.scrollArea)       
        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )

    def addControl( self, iCatIndex, config_ctrl, id = None ):
        config_list = self.configContainer.getCategoryConfigList( iCatIndex )
        config_list.addControl( iCatIndex, config_ctrl )
        self.tagged_controls.append( config_ctrl )
    
    def parameterValueChanged( self, args ):
#        print "parameterValueChanged: ", str(args)
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processParameterChange( args )
                    
    def addConfigControl(self, iCatIndex, config_ctrl, id = None ):
        config_ctrl.build()
        self.addControl( iCatIndex, config_ctrl, id )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        self.connect( config_ctrl.getParameter(), QtCore.SIGNAL("ValueChanged"), self.parameterValueChanged )
                
    def configTriggered( self, args ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processExtConfigCmd( args )

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )

    def addControlRow( self, tab_index ):
        cfgList = self.configContainer.getCategoryConfigList( tab_index )
        cfgList.addControlRow()
        
    def activate(self):
        self.cfgManager.initParameters()
        self.configContainer.selectCategory( self.iSubsetCatIndex )
                           
    def getCategoryName( self, iCatIndex ):
        return self.configContainer.getCategoryName( iCatIndex )
    
    def askToSaveChanges(self):
        self.emit( QtCore.SIGNAL("Close"), self.getParameterPersistenceList() )

    def build( self, **args ):
        self.iColorCatIndex = self.addCategory( 'Color' )
        cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Color Scale", wpos=0.5, wsize=1.0, ctype = 'Leveling' )
        self.addConfigControl( self.iColorCatIndex, ColorScaleControl( cparm ) )       
        cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Color Map", Colormap="jet", Invert=1, Stereo=0, Colorbar=0  )
        self.addConfigControl( self.iColorCatIndex, ColormapControl( cparm ) )  
             
        self.iSubsetCatIndex = self.addCategory( 'Subsets' )
        cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "Slice Planes",  xpos=0.5, ypos=0.5, zpos=0.5, xhrwidth=0.0025, xlrwidth=0.005, yhrwidth=0.0025, ylrwidth=0.005 )
        self.addConfigControl( self.iSubsetCatIndex, SlicerControl( cparm, wrange=[ 0.0001, 0.02 ] ) ) # , "SlicerControl" )
        thresh_cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "Threshold Range", rmin=0.6, rmax=1.0, ctype = 'Leveling' )
        self.addConfigControl( self.iSubsetCatIndex, VolumeControl( thresh_cparm ) )

        op_cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Opacity Scale", rmin=0.0, rmax=1.0, ctype = 'Range'  )
        self.addConfigControl( self.iColorCatIndex, OpacityScaleControl( op_cparm, thresh_cparm, vbounds=self.metadata.get('vbounds', [ 0.0, 1.0 ] ) ) )       
                
        self.iPointsCatIndex = self.addCategory( 'Points' )
        cparm = self.cfgManager.addParameter( self.iPointsCatIndex, "Point Size",  cats = [ ("Low Res", "# Pixels", 1, 20, 10 ), ( "High Res", "# Pixels",  1, 10, 3 ) ] )
        self.addConfigControl( self.iPointsCatIndex, PointSizeSliderControl( cparm ) )
        cparm = self.cfgManager.addParameter( self.iPointsCatIndex, "Max Resolution", value=1.0 )
        self.addConfigControl( self.iPointsCatIndex, SliderControl( cparm ) )
        self.GeometryCatIndex = self.addCategory( 'Geometry' )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Projection", choices = [ "Lat/Lon", "Spherical" ], init_index=0 )
        self.addConfigControl( self.GeometryCatIndex, RadioButtonSelectionControl( cparm ) )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Vertical Scaling", value=0.5 )
        self.addConfigControl( self.GeometryCatIndex, SliderControl( cparm ) )
        vertical_vars = args.get( 'vertical_vars', [] )
        vertical_vars.insert( 0, "Levels" )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Vertical Variable", choices = vertical_vars, init_index=0  )
        self.addConfigControl( self.GeometryCatIndex, RadioButtonSelectionControl( cparm ) )

        self.AnalysisCatIndex = self.addCategory( 'Analysis' )
        cparm = self.cfgManager.addParameter( self.AnalysisCatIndex, "Animation" )
        self.addConfigControl( self.AnalysisCatIndex, AnimationControl( cparm ) )
        cparm = self.cfgManager.addParameter( self.AnalysisCatIndex, "InfoGrid" )
        self.addConfigControl( self.AnalysisCatIndex, InfoGridControl( cparm ) )
        
    def saveConfig(self):
        self.cfgManager.saveConfig()

              
class ConfigManager(QtCore.QObject):
    
    def __init__( self, controller=None ): 
        QtCore.QObject.__init__( self )
        self.cfgFile = None
        self.cfgDir = None
        self.controller = controller
        self.config_params = {}
        self.iCatIndex = 0
        self.cats = {}

    def addParam(self, key ,cparm ):
        self.config_params[ key ] = cparm
#        print "Add param[%s]" % key
                     
    def saveConfig( self ):
        try:
            f = open( self.cfgFile, 'w' )
            for config_item in self.config_params.items():
                cfg_str = " %s = %s " % ( config_item[0], config_item[1].serialize() )
                f.write( cfg_str )
            f.close()
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile

    def addParameter( self, iCatIndex, config_name, **args ):
        categoryName = self.controller.getCategoryName( iCatIndex ) if self.controller else self.cats[ iCatIndex ]
        cparm = ConfigParameter.getParameter( config_name, **args )
        key = ':'.join( [ categoryName, config_name ] )
        self.addParam( key, cparm )
        return cparm

    def readConfig( self ):
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
        
    def initParameters(self):
        if not self.cfgDir:
            self.cfgDir = os.path.join( os.path.expanduser( "~" ), ".cpc" )
            if not os.path.exists(self.cfgDir): 
                os.mkdir(  self.cfgDir )
        if not self.cfgFile:
            self.cfgFile = os.path.join( self.cfgDir, "cpcConfig.txt" )
        else:
            self.readConfig()            
        emitter = self.controller if self.controller else self
        for config_item in self.config_params.items():
            emitter.emit( QtCore.SIGNAL("ConfigCmd"), ( "InitParm",  config_item[0], config_item[1] ) )

    def getParameterPersistenceList(self):
        plist = []
        for cfg_item in self.config_params.items():
            key = cfg_item[0]
            cfg_spec = cfg_item[1].pack()
            plist.append( ( key, cfg_spec[1] ) )
        return plist

    def initialize( self, parm_name, parm_values ):
        if not ( isinstance(parm_values,list) or isinstance(parm_values,tuple) ):
            parm_values = [ parm_values ]
        cfg_parm = self.config_params.get( parm_name, None )
        if cfg_parm: cfg_parm.unpack( parm_values )

    def getPersistentParameterSpecs(self):
        plist = []
        for cfg_item in self.config_params.items():
            key = cfg_item[0]
            values_decl = cfg_item[1].values_decl()
            plist.append( ( key, values_decl ) )
        return plist
    
    def addCategory(self, cat_name ):
        self.iCatIndex = self.iCatIndex + 1
        self.cats[ self.iCatIndex ] = cat_name
        return self.iCatIndex
    
        
#     def build( self, **args ):
#         self.iColorCatIndex = self.addCategory( 'Color' )
#         cparm = self.addParameter( self.iColorCatIndex, "Color Scale", wpos=0.5, wsize=1.0, ctype = 'Leveling' )
#         cparm = self.addParameter( self.iColorCatIndex, "Opacity Scale", rmin=0.0, rmax=1.0, ctype = 'Range'  )
#         cparm = self.addParameter( self.iColorCatIndex, "Color Map", Colormap="jet", Invert=1, Stereo=0, Colorbar=0  )
#         self.iSubsetCatIndex = self.addCategory( 'Subsets' )
#         cparm = self.addParameter( self.iSubsetCatIndex, "Slice Planes",  xpos=0.5, ypos=0.5, zpos=0.5, xhrwidth=0.0025, xlrwidth=0.005, yhrwidth=0.0025, ylrwidth=0.005 )
#         cparm = self.addParameter( self.iSubsetCatIndex, "Threshold Range", wpos=0.5, wsize=0.2, ctype = 'Leveling' )   
#         self.iPointsCatIndex = self.addCategory( 'Points' )     
#         cparm = self.addParameter( self.iPointsCatIndex, "Point Size",  cats = [ ("Low Res", "# Pixels", 1, 20, 10 ), ( "High Res", "# Pixels",  1, 10, 3 ) ] )
#         cparm = self.addParameter( self.iPointsCatIndex, "Max Resolution", value=1.0 )
#         self.GeometryCatIndex = self.addCategory( 'Geometry' )
#         cparm = self.addParameter( self.GeometryCatIndex, "Projection", choices = [ "Lat/Lon", "Spherical" ], init_index=0 )
#         cparm = self.addParameter( self.GeometryCatIndex, "Vertical Scaling", value=0.5 )
#         cparm = self.addParameter( self.GeometryCatIndex, "Vertical Variable", choices = [], init_index=0  )
#         self.AnalysisCatIndex = self.addCategory( 'Analysis' )
#         cparm = self.addParameter( self.AnalysisCatIndex, "Animation" )
               
if __name__ == '__main__':
    app = QtGui.QApplication(['CPC Config Dialog'])
    
    configDialog = CPCConfigGui()
    configDialog.show()
     
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), configDialog.closeDialog ) 
    app.exec_() 
 

