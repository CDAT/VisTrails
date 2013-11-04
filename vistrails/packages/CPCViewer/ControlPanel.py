import sys
import os.path
import vtk, time
from PyQt4 import QtCore, QtGui
from compiler.ast import Name
from ColorMapManager import ColorMapManager
POS_VECTOR_COMP = [ 'xpos', 'ypos', 'zpos' ]
SLICE_WIDTH_LR_COMP = [ 'xlrwidth', 'ylrwidth', 'zlrwidth' ]
SLICE_WIDTH_HR_COMP = [ 'xhrwidth', 'yhrwidth', 'zhrwidth' ]


class ConfigParameter( QtCore.QObject ):
    
    @staticmethod
    def getParameter( config_name, **args ):
        if args.get('ctype') == 'Leveling':
            return LevelingConfigParameter( config_name, **args )
        else:
            return ConfigParameter( config_name, **args )

    def __init__(self, name, **args ):
        super( ConfigParameter, self ).__init__() 
        self.name = name 
        self.values = args
        
    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        return self.values.get( key, None )

    def __setitem__(self, key, value ):
        self.values[key] = value 
        self.emit( QtCore.SIGNAL("ValueChanged"), ( self.name, key, value ) )

    def __call__(self, **args ):
        self.values.update( args )
        args1 = [ self.name ]
        for item in args.items():
            args1.extend( list(item) )
        self.emit( QtCore.SIGNAL("ValueChanged"), args1 )
         
    def getName(self):
        return self.name
    
    def initialize( self, config_str ):
        self.values = eval( config_str )

    def serialize( self ):
        return str( self.values )

    def getValue( self, key='value', default_value=None ):
        return self.values.get( key, default_value )

    def setValue( self, key, val ):
        self.values[ key ] = val

    def incrementValue( self, index, inc ):
        self.values[ index ] = self.values[ index ] + inc
        
class LevelingConfigParameter( ConfigParameter ):
    
    def __init__(self, name, **args ):
        super( LevelingConfigParameter, self ).__init__( name, **args ) 
        self.wposSensitivity = args.get( 'pos_s', 0.05 )
        self.wsizeSensitivity = args.get( 'width_s', 0.05 )
        self.computeRange()
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

class ConfigControl(QtGui.QWidget):
    
    def __init__(self, cparm, **args ):  
        super( ConfigControl, self ).__init__() 
        self.cparm = cparm
        self.tabWidget = None 
        self.connect( cparm, QtCore.SIGNAL('ValueChanged'), self.configValueChanged )
        
    def configValueChanged( self, args ): 
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
        
    def getButton(self):
        return self.control_button
        
    def open( self, bval ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Open" ) )
        self.updateTabPanel()
        
    def ok(self):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Close", True ) )
         
    def cancel(self):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Close", False ) )
      
class LabeledSliderWidget( QtGui.QWidget ):
    
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

    def getSliderValue( self, slider_value = None ):
        slider_value = self.slider.value() if not slider_value else slider_value
        if not self.useScaledValue: return slider_value
        fvalue = ( slider_value - self.minValue ) / float( self.maxValue - self.minValue ) 
        return self.scaledMinValue + fvalue * ( self.scaledMaxValue - self.scaledMinValue )

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

    def getTitle( self, widget_index ):
        w = self.widgets[widget_index]
        return w.getTitle()

    def addCheckbox(self, label, layout, **args ):
        cbox_index = len( self.widgets ) 
        checkBox = QtGui.QCheckBox(label)
        layout.addWidget( checkBox )
        self.connect( checkBox, QtCore.SIGNAL("stateChanged(int)"), lambda cbvalue, cbname=label: self.processWidgetConfigCmd(str(cbname),cbvalue) ) 
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
        self.addCheckbox( 'Smooth', cbox_layout  )

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
            print "Update Min Max sliders: %s " % str( ( rmin, rmax ) ); sys.stdout.flush()
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

class ConfigurationGui(QtGui.QDialog):

    def __init__(self, config_widget ):    
        QtGui.QDialog.__init__(self, None)
                
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(False)
        self.setWindowTitle('CPC Plot Config')
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        
        layout.addWidget( config_widget ) 
        self.config_widget = config_widget     
        self.resize(600, 450)

    def closeDialog( self ):
        self.config_widget.saveConfg()
        self.close()
        
class ConfigurationWidget(QtGui.QWidget):

    def __init__(self, parent=None):    
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.config_params = {}

        self.cfgFile = None
        self.cfgDir = None
        self.tagged_controls = {}
                        
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
        self.tagged_controls[ id ] = config_ctrl

    def addParameter( self, iCatIndex, config_name, **args ):
        categoryName = self.configContainer.getCategoryName( iCatIndex )
        cparm = ConfigParameter.getParameter( config_name, **args )
        key = ':'.join( [ categoryName, config_name ] )
        self.config_params[ key ] = cparm
        self.connect( cparm, QtCore.SIGNAL("ValueChanged"), self.parameterValueChanged )
        return cparm
    
    def parameterValueChanged( self, args ):
        pass
#        print "parameterValueChanged", str(args)
        
    def addConfigControl(self, iCatIndex, config_ctrl, id = None ):
        config_ctrl.build()
        self.addControl( iCatIndex, config_ctrl, id )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        
    def getConfigControl( self, id ):
        return self.tagged_controls.get( id, None )
        
    def configTriggered( self, args ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )

    def addControlRow( self, tab_index ):
        cfgList = self.configContainer.getCategoryConfigList( tab_index )
        cfgList.addControlRow()
   
    def activate(self):
        self.initParameters()
        self.configContainer.selectCategory( self.iSubsetCatIndex )
                    
    def build(self):
        pass

    def saveConfg( self ):
        try:
            f = open( self.cfgFile, 'w' )
            for config_item in self.config_params.items():
                cfg_str = " %s = %s " % ( config_item[0], config_item[1].serialize() )
                f.write( cfg_str )
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile

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
        
    def initParameters(self):
        if not self.cfgDir:
            self.cfgDir = os.path.join( os.path.expanduser( "~" ), ".cpc" )
            if not os.path.exists(self.cfgDir): 
                os.mkdir(  self.cfgDir )
        if not self.cfgFile:
            self.cfgFile = os.path.join( self.cfgDir, "cpcConfig.txt" )
        else:
            self.readConfg()
            
        for config_item in self.config_params.items():
            self.emit( QtCore.SIGNAL("ConfigCmd"), ( "InitParm",  config_item[0], config_item[1] ) )

class CPCConfigConfigurationWidget( ConfigurationWidget ):

    def __init__(self, parent=None): 
        super( CPCConfigConfigurationWidget, self ).__init__( parent )   

#    def externalUpdate( self, args ):   
#        if args[0] == "SetSlicePosition":
#            slicerCtrl = self.getConfigControl( "SlicerControl" )
#            slicerCtrl.setSlicePosition( args[1] )
        
    def build( self, **args ):
        self.iColorCatIndex = self.addCategory( 'Color' )
        cparm = self.addParameter( self.iColorCatIndex, "Color Scale", wpos=0.5, wsize=1.0, ctype = 'Leveling' )
        self.addConfigControl( self.iColorCatIndex, ColorScaleControl( cparm ) )       
        cparm = self.addParameter( self.iColorCatIndex, "Color Map", Colormap="jet", Invert=True, Stereo=False, Smooth=True  )
        self.addConfigControl( self.iColorCatIndex, ColormapControl( cparm ) )  
             
        self.iSubsetCatIndex = self.addCategory( 'Subsets' )
        cparm = self.addParameter( self.iSubsetCatIndex, "Slice Planes",  xpos=0.5, ypos=0.5, zpos=0.5, xhrwidth=0.0025, xlrwidth=0.005, yhrwidth=0.0025, ylrwidth=0.005 )
        self.addConfigControl( self.iSubsetCatIndex, SlicerControl( cparm, wrange=[ 0.0001, 0.02 ] ) ) # , "SlicerControl" )
        cparm = self.addParameter( self.iSubsetCatIndex, "Threshold Range", wpos=0.5, wsize=0.2, ctype = 'Leveling' )
        self.addConfigControl( self.iSubsetCatIndex, VolumeControl( cparm ) )
                
        self.iPointsCatIndex = self.addCategory( 'Points' )
        cparm = self.addParameter( self.iPointsCatIndex, "Point Size",  cats = [ ("Low Res", "# Pixels", 1, 20, 10 ), ( "High Res", "# Pixels",  1, 10, 3 ) ] )
        self.addConfigControl( self.iPointsCatIndex, PointSizeSliderControl( cparm ) )
        cparm = self.addParameter( self.iPointsCatIndex, "Max Resolution", value=1.0 )
        self.addConfigControl( self.iPointsCatIndex, SliderControl( cparm ) )


        self.GeometryCatIndex = self.addCategory( 'Geometry' )
        cparm = self.addParameter( self.GeometryCatIndex, "Projection", choices = [ "Lat/Lon", "Spherical" ], init_index=0 )
        self.addConfigControl( self.GeometryCatIndex, RadioButtonSelectionControl( cparm ) )
        cparm = self.addParameter( self.GeometryCatIndex, "Vertical Scaling", value=0.5 )
        self.addConfigControl( self.GeometryCatIndex, SliderControl( cparm ) )
        vertical_vars = args.get( 'vertical_vars', [] )
        vertical_vars.insert( 0, "Levels" )
        cparm = self.addParameter( self.GeometryCatIndex, "Vertical Variable", choices = vertical_vars, init_index=0  )
        self.addConfigControl( self.GeometryCatIndex, RadioButtonSelectionControl( cparm ) )

        self.AnalysisCatIndex = self.addCategory( 'Analysis' )
        cparm = self.addParameter( self.AnalysisCatIndex, "Animation" )
        self.addConfigControl( self.AnalysisCatIndex, AnimationControl( cparm ) )
 
class CPCConfigGui( ConfigurationGui ):

    def __init__(self):
        self.cfg_widget = CPCConfigConfigurationWidget()    
        ConfigurationGui.__init__(self,self.cfg_widget)
        self.cfg_widget.build()
        self.cfg_widget.activate()
        
    def getConfigWidget(self):
        return self.cfg_widget
       
if __name__ == '__main__':
    app = QtGui.QApplication(['CPC Config Dialog'])
    
    configDialog = CPCConfigGui()
    configDialog.show()
     
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), configDialog.closeDialog ) 
    app.exec_() 
 

