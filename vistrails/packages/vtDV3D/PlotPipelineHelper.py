'''

PlotPipelineHelper:
Created on Nov 30, 2011
@author: emanuele

DV3DPipelineHelper:
Created on Feb 29, 2012
@author: tpmaxwel

'''

import core.db.io, sys, traceback, api
import core.modules.basic_modules
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from packages.vtDV3D.CDMS_VariableReaders import CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader, CDMS_VectorReader
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.vtDV3D.DV3DCell import MapCell3D, CloudCell3D
from packages.vtDV3D import ModuleStore
from packages.vtDV3D.InteractiveConfiguration import *
from packages.uvcdat_cdms.init import CDMSVariableOperation, CDMSVariable 
from packages.vtDV3D.vtUtilities import *
from core.uvcdat.plot_registry import get_plot_registry
from core.modules.module_registry import get_module_registry
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from packages.vtDV3D import HyperwallManager

class LevelingType:
    GUI = 0
    LEVELING = 1
    NONE = 2

def getFormattedQString( value ):
    val = float( value )
    if val > 99999 or val < 0.001:  sval = "%.2g" % val
    if val > 1:                     sval = "%.2f" % val
    else:                           sval = "%.4f" % val
    return QString( sval )


class PlotListItem( QListWidgetItem ):

    def __init__( self, label, module, parent=None):
        QListWidgetItem.__init__(self, label, parent)
        self.modules = [ module ]
        
    def addModule( self, module ):
        self.modules.append( module )
        

class DV3DParameterSliderWidget(QWidget):
    
    def __init__( self, label, parent=None):
        QWidget.__init__(self,parent)
        self.range = [ 0.0, 1.0 ]
        
        main_layout = QVBoxLayout()  
        
        label_layout = QHBoxLayout()                     
        self.label = QLabel( label, self )
        self.label.setAlignment( Qt.AlignLeft )
        self.label.setFont( QFont( "Arial", 12 ) )
        label_layout.addWidget( self.label )
        label_layout.addStretch()
        main_layout.addLayout( label_layout )
        
        data_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange( 0, 100 )
        data_layout.addWidget(self.slider)
        data_layout.addStrut(2)
        self.textbox = QLineEdit(self)
        data_layout.addWidget( self.textbox )  
        main_layout.addLayout( data_layout )
              
        self.setLayout(main_layout)
        
    def setLabel( self, text ):
        self.label.setText( text )
        
    def setDisplayValue( self, fval ):
        qsval = getFormattedQString( fval ) 
        self.textbox.setText( qsval )
        
    def setRange( self, fmin, fmax ):
#        print " Parameter Slider Widget: set Range= %s " % str( (fmin, fmax) )
        if fmin >= fmax:
            if fmax > 0.0: fmin = fmax * 0.99
            else: fmax = 1.0
        self.range = [ fmin, fmax ]

    def setValue( self, value ):
        sliderVal = int( 100 * ( value-self.range[0] ) / ( self.range[1]-self.range[0] ) ) 
        self.slider.setValue( sliderVal )
        qsval = getFormattedQString( value ) 
        self.textbox.setText( qsval  )

    def enable(self, enabled ): 
        self.setVisible( enabled )

class DV3DParameterLabelWidget(QWidget):
    
    def __init__( self, label, parent=None):
        QWidget.__init__(self,parent)
        self.range = [ 0.0, 1.0, 1.0 ]
        
        main_layout = QVBoxLayout()  
        
        data_layout = QHBoxLayout()                     
        self.label = QLabel( label, self )
        self.label.setAlignment( Qt.AlignLeft )
        self.label.setFont( QFont( "Arial", 12 ) )
        data_layout.addWidget( self.label )        
        data_layout.addStrut(2)
        self.textbox = QLineEdit(self)
        data_layout.addWidget( self.textbox )  
        main_layout.addLayout( data_layout )
              
        self.setLayout(main_layout)
        
    def setLabel( self, text ):
        self.label.setText( text )
        
    def setDisplayValue( self, fval ):
        qsval = getFormattedQString( fval ) 
        self.textbox.setText( qsval )
        
    def setRange( self, fmin, fmax ):
        self.range = [ fmin, fmax, (fmax-fmin) ]

    def setValue( self, value ):
        qsval = getFormattedQString( value ) 
        self.textbox.setText( qsval  )

    def enable(self, enabled ): 
        self.setVisible( enabled )

class DV3DRangeConfigTab(QWidget):
    MIN_SLIDER = 0
    MAX_SLIDER = 1
    
    def __init__( self, controller, parent=None):
        QWidget.__init__( self, parent )
        gui_layout = QVBoxLayout()         
        self.cfg_action_label = QLabel("Configuration:")
        self.cfg_action_label.setFont( QFont( "Arial", 14, QFont.Bold ) )
        gui_layout.addWidget( self.cfg_action_label )
        self.controller = controller
        
        self.rangeMinEditor = DV3DParameterSliderWidget( 'Range Min:', self )
        self.rangeMaxEditor = DV3DParameterSliderWidget( 'Range Max:', self )
        self.connect( self.rangeMinEditor.slider, SIGNAL("sliderMoved(int)"), lambda ival: self.controller.sliderValueChanged(self.MIN_SLIDER,ival) ) 
        self.connect( self.rangeMaxEditor.slider, SIGNAL("sliderMoved(int)"), lambda ival: self.controller.sliderValueChanged(self.MAX_SLIDER,ival) ) 
        self.connect( self.rangeMinEditor.textbox, SIGNAL("returnPressed()"),  lambda: self.controller.processTextValueEntry(self.MIN_SLIDER) ) 
        self.connect( self.rangeMaxEditor.textbox, SIGNAL("returnPressed()"),  lambda: self.controller.processTextValueEntry(self.MAX_SLIDER) ) 
        self.sliders = [ self.rangeMinEditor, self.rangeMaxEditor ]
               
        gui_layout.addWidget( self.rangeMinEditor )
        gui_layout.addWidget( self.rangeMaxEditor )
        self.rangeMinEditor.setValue( 0.5 )
        self.rangeMaxEditor.setValue( 0.5 )
        
        button_layout = QHBoxLayout() 
        revert_button = QPushButton("Revert", self)
        save_button = QPushButton("Save", self)
        button_layout.addWidget( revert_button )
        button_layout.addWidget( save_button )
        revert_button.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Minimum  )
        save_button.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Minimum  )
        self.connect( revert_button, SIGNAL("clicked()"), lambda: self.revertConfig() ) 
        self.connect( save_button, SIGNAL("clicked()"), lambda: self.finalizeConfig() ) 
        
        gui_layout.addLayout( button_layout )
        gui_layout.addStretch()  
        self.setLayout(gui_layout) 
        
    def finalizeConfig(self):
        self.controller.finalizeConfig()

    def revertConfig(self):
        self.controller.revertConfig()

    def enable(self, minEnabled, maxEnabled ): 
        self.rangeMinEditor.enable( minEnabled )
        self.rangeMinEditor.setLabel( 'Value: ' if not maxEnabled else 'Range Min: ' )
        self.rangeMaxEditor.enable( maxEnabled )
        self.rangeMaxEditor.setLabel( 'Value: ' if not minEnabled else 'Range Max: ' )

    def setTitle(self, title ):
        self.cfg_action_label.setText( title )

    def setDataValue(self, parm_range, range_bounds ):
        for iSlider in range(2):
            dval = parm_range[iSlider]
            slider = self.sliders[iSlider]
            slider.setDisplayValue( dval )   
            slider.setRange( range_bounds[0], range_bounds[1] )       
            slider.setValue( dval ) 
            
    def processTextValueEntry( self, iSlider ):
        slider = self.sliders[iSlider]
        textbox = slider.textbox
        fval = float( textbox.text() )            
        slider.setValue( fval ) 
        return fval

    def setDisplayValue( self, fval, iSlider ):
        self.sliders[iSlider].setDisplayValue( fval )

class DV3DRangeDisplayTab(QWidget):
    MIN_SLIDER = 0
    MAX_SLIDER = 1
    
    def __init__( self, controller, parent=None):
        QWidget.__init__( self, parent )
        gui_layout = QVBoxLayout()         
        self.cfg_action_label = QLabel("Configuration:")
        self.cfg_action_label.setFont( QFont( "Arial", 14, QFont.Bold ) )
        gui_layout.addWidget( self.cfg_action_label )
        self.controller = controller
        
        self.rangeMinEditor = DV3DParameterLabelWidget( 'Range Min:', self )
        self.rangeMaxEditor = DV3DParameterLabelWidget( 'Range Max:', self )
        self.connect( self.rangeMinEditor.textbox, SIGNAL("returnPressed()"),  lambda: self.controller.processTextValueEntry(self.MIN_SLIDER) ) 
        self.connect( self.rangeMaxEditor.textbox, SIGNAL("returnPressed()"),  lambda: self.controller.processTextValueEntry(self.MAX_SLIDER) ) 
        self.widgets = [ self.rangeMinEditor, self.rangeMaxEditor ]
               
        gui_layout.addWidget( self.rangeMinEditor )
        gui_layout.addWidget( self.rangeMaxEditor )
        self.rangeMinEditor.setValue( 0.5 )
        self.rangeMaxEditor.setValue( 0.5 )
        
        gui_layout.addStretch()  
        self.setLayout(gui_layout) 

    def enable(self, minEnabled, maxEnabled ): 
        self.rangeMinEditor.enable( minEnabled )
        self.rangeMinEditor.setLabel( 'Value: ' if not maxEnabled else 'Range Min: ' )
        self.rangeMaxEditor.enable( maxEnabled )
        self.rangeMaxEditor.setLabel( 'Value: ' if not minEnabled else 'Range Max: ' )

    def setTitle(self, title ):
        self.cfg_action_label.setText( title )
 
    def setDataValue(self, parm_range, range_bounds ):
        for iWidget in range(2):
            dval = parm_range[iWidget]
            widget = self.widgets[iWidget]
            widget.setDisplayValue( dval )   
            widget.setRange( range_bounds[0], range_bounds[1] )       
            widget.setValue( dval ) 

    def processTextValueEntry( self, iWidget ):
        widget = self.sliders[iWidget]
        textbox = widget.textbox
        fval = float( textbox.text() )            
        widget.setValue( fval ) 
        return fval

    def setDisplayValue( self, fval, iWidget ):
        self.widgets[iWidget].setDisplayValue( fval )
                                        
class DV3DRangeConfigWidget(QFrame):
    
    def __init__( self, parent=None):
        QFrame.__init__( self, parent )
        self.active_cfg_cmd = None
#        print ' ----------------------------------------- create new widget: %x ----------------------------------------- ----------------------------------------- ----------------------------------------- ' % id( self )
#        self.setStyleSheet("QWidget#RangeConfigWidget { border-style: outset; border-width: 2px; border-color: blue; }" )
        self.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        self.setLineWidth(2)
        self.setObjectName('RangeConfigWidget') 
        self.initialRange = [ 0, 0, 0 ]
        self.initialize()
        main_layout = QVBoxLayout()         
       
        self.tabView = QTabWidget()
        self.tabView.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.tabView)
        
        self.guiWidget = DV3DRangeConfigTab( self )
        self.tabView.insertTab( LevelingType.GUI, self.guiWidget, "GUI")
        self.levelingConfigWidget = DV3DRangeDisplayTab(self)
        self.tabView.insertTab( LevelingType.LEVELING, self.levelingConfigWidget, "Leveling" )
        self.tabView.setCurrentIndex( DV3DPipelineHelper.getConfigMode() )
        self.tabView.currentChanged.connect(self.switchTab)
          
        self.setLayout(main_layout)
        self.disable()

    def clearInteractionState( self ):
        if self.active_cfg_cmd:
            self.active_cfg_cmd.persisted = True
        
    def getConfigTab(self): 
        if DV3DPipelineHelper.isGuiConfigMode(): return self.guiWidget
        if DV3DPipelineHelper.isLevelingConfigMode(): return self.levelingConfigWidget
        return None

    @pyqtSlot(int)    
    def switchTab( self, index ):
        DV3DPipelineHelper.setConfigMode( index )
        print "Setting config_mode = %d" % index
        self.updateSliderValues()
        if DV3DPipelineHelper.isLevelingConfigMode():  
            self.active_cfg_cmd.postInstructions( "Left-click, mouse-move, left-click in this cell." )

    def setTab( self, index ):
        DV3DPipelineHelper.setConfigMode( index )
        self.tabView.setCurrentIndex( index )
        
    def __del__(self):
        self.deactivate_current_command()
        QFrame.__del__(self)
        
    def initialize(self):
        self.active_cfg_cmd = None
        self.active_modules = set()

    def getInteractionState( self ):   
        return ( self.active_cfg_cmd.name, self.active_cfg_cmd.persisted ) if self.active_cfg_cmd else ( "None", True )     
        
    def processTextValueEntry( self, iSlider ):
        if self.active_cfg_cmd:
            fval = self.getConfigTab().processTextValueEntry( iSlider )
            parm_range = list( self.active_cfg_cmd.range ) 
            parm_range[ iSlider ] = fval
            self.active_cfg_cmd.broadcastLevelingData( parm_range,  active_modules = DV3DPipelineHelper.getActivePlotList() ) 
            if len( self.active_modules ):            
                for module in self.active_modules: 
                    if DV3DPipelineHelper.getPlotActivation( module ): module.render()
                HyperwallManager.getInstance().processGuiCommand( [ "pipelineHelper", 'text-%d' % iSlider, fval ]  )
        
        
    def sliderValueChanged( self, iSlider, iValue = None ):
        if self.active_cfg_cmd:
            rbnds = self.active_cfg_cmd.range_bounds
            parm_range = list( self.active_cfg_cmd.range )
            fval = rbnds[0] + (rbnds[1]-rbnds[0]) * ( iValue / 100.0 )
            parm_range[ iSlider ] = fval
            self.getConfigTab().setDisplayValue( fval, iSlider )
#            print " sliderValueChanged[%d], bounds=%s, range=%s, fval=%f" % ( self.active_cfg_cmd.module.moduleID, str(rbnds), str(parm_range), fval )
            self.active_cfg_cmd.broadcastLevelingData( parm_range, active_modules = DV3DPipelineHelper.getActivePlotList( )  ) 
            if len( self.active_modules ):            
                for module in self.active_modules:
                    if DV3DPipelineHelper.getPlotActivation( module ): module.render()
                HyperwallManager.getInstance().processGuiCommand( [ "pipelineHelper", 'slider-%d' % iSlider, fval ]  )
        
    def updateSliderValues( self, initialize=False ): 
        if self.active_cfg_cmd and hasattr( self.active_cfg_cmd, 'range' ):
#            print ' update Slider Values, widget = %x ' % id( self )
            try:
                self.active_cfg_cmd.updateWindow()
                rbnds = self.active_cfg_cmd.range_bounds
                parm_range = list( self.active_cfg_cmd.range )
    #            print " Update Slider Values-> range: %s, bounds: %s " % ( str(parm_range), str(rbnds) )
                self.getConfigTab().setDataValue( parm_range, rbnds )
                if initialize: self.initialRange = parm_range[0:2]
            except Exception, err:
                print>>sys.stderr, " Error in updateSliderValues: %s " % str(err)
                
    def updateRange(self, min, max ): 
        pass     
     
    def enable(self): 
        self.setVisible(True)
        maxEnabled = self.active_cfg_cmd and self.active_cfg_cmd.activeBound in [ 'both', 'max' ]
        minEnabled = self.active_cfg_cmd and self.active_cfg_cmd.activeBound in [ 'both', 'min' ]
        self.getConfigTab().enable( minEnabled, maxEnabled )


    def disable(self): 
        self.setVisible(False)
        self.deactivate_current_command()
        
    def isEligibleCommand( self, cmd ):
        return (self.active_cfg_cmd == None) or ( cmd == self.active_cfg_cmd )
       
    def deactivate_current_command(self):
        if self.active_cfg_cmd:
            self.active_cfg_cmd.updateWindow()
            self.disconnect( self.active_cfg_cmd, SIGNAL('updateLeveling()'), self.updateSliderValues )
            self.active_cfg_cmd = None
          
    def startConfig(self, qs_action_key, qs_cfg_key ):
        cfg_key = str(qs_cfg_key)
        action_key = str(qs_action_key)
        self.getConfigTab().setTitle( action_key )
        self.active_modules = set()
        try:
            cmd_list = DV3DPipelineHelper.getConfigCmd ( cfg_key )
            if cmd_list:
                self.deactivate_current_command()
                active_renwin_ids = DV3DPipelineHelper.getActiveRenWinIds()
                for cmd_entry in cmd_list:
                    module = cmd_entry[0]
                    cfg_cmd = cmd_entry[1] 
                    self.active_modules.add( module )
                    if ( self.active_cfg_cmd == None ) or ( module.GetRenWinID() in active_renwin_ids ):
                        self.active_cfg_cmd = cfg_cmd
                self.updateSliderValues(True)
                if self.active_cfg_cmd:
                    self.connect( self.active_cfg_cmd, SIGNAL('updateLeveling()'), self.updateSliderValues ) 
                    self.active_cfg_cmd.updateActiveFunctionList()
                self.enable()
        except RuntimeError:
            print "RuntimeError"
            
    def endConfig( self ):
        self.disable()
        if DV3DPipelineHelper.isLevelingConfigMode(): 
            self.setTab( LevelingType.GUI )
        
    def finalizeConfig( self ):
        if len( self.active_modules ) and self.active_cfg_cmd and hasattr( self.active_cfg_cmd, 'range' ):
            interactionState = self.active_cfg_cmd.name
            parm_range = list( self.active_cfg_cmd.range )
            for module in self.active_modules:
                if DV3DPipelineHelper.getPlotActivation( module ):
                    config_data = module.getParameter( interactionState  ) 
                    if config_data: 
                        config_data[0:2] = parm_range[0:2]
                    else:
                        config_data = parm_range
                    module.writeConfigurationResult( interactionState, config_data ) 
            HyperwallManager.getInstance().setInteractionState( None )               
        self.endConfig()

    def revertConfig(self):
        if len( self.active_modules ):
            try:
                self.initialRange[2] = self.active_cfg_cmd.range[2]
            except: pass
            self.active_cfg_cmd.broadcastLevelingData( self.initialRange )  
            interactionState = self.active_cfg_cmd.name
            for module in self.active_modules:
                if DV3DPipelineHelper.getPlotActivation( module ): 
                    module.finalizeConfigurationObserver( interactionState ) 
            HyperwallManager.getInstance().setInteractionState( None )  
        self.endConfig()
        

class DV3DConfigControlPanel(QWidget):
    
    def __init__( self, configMenu, optionsMenu, controller, version, plot_obj, parent=None):
        QWidget.__init__(self,parent)
        self.showActivePlotsPanel = True
        self.proj_controller = controller
        self.controller = controller.vt_controller
        self.version = version
        self.plot = plot_obj

#        self.active_module = None
        self.configWidget = None
#        print "Creating DV3DConfigControlPanel: id = %x " % id( self )
           
        main_layout = QVBoxLayout()        
        button_layout = QHBoxLayout()
        button_layout.setMargin(1)
        button_layout.setSpacing(1)

        self.cfg_frame = QFrame()
        cfg_layout = QVBoxLayout() 
        cfg_layout.setMargin(2)
        cfg_layout.setSpacing(1)
        self.cfg_frame.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        self.cfg_frame.setLineWidth(2)
        self.cfg_frame.setLayout(cfg_layout)
                
        cfg_label = QLabel("Configuration Commands:")
        cfg_label.setFont( QFont( "Arial", 14, QFont.Bold ) )
        cfg_label.setAlignment( Qt.AlignHCenter )
        cfg_layout.addWidget(cfg_label)
        cfg_layout.addWidget( configMenu )
        cfg_layout.addStretch()

        self.opt_frame = QFrame()
        opt_layout = QVBoxLayout() 
        opt_layout.setMargin(2)
        opt_layout.setSpacing(1)
        self.opt_frame.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        self.opt_frame.setLineWidth(2)
        self.opt_frame.setLayout(opt_layout)
                
        opt_label = QLabel("Options:")
        opt_label.setFont( QFont( "Arial", 14, QFont.Bold ) )
        opt_label.setAlignment( Qt.AlignHCenter )
        opt_layout.addWidget(opt_label)
        opt_layout.addWidget( optionsMenu )
        opt_layout.addStretch()
               
        button_layout.addWidget( self.cfg_frame )
        button_layout.addWidget( self.opt_frame )
        main_layout.addLayout( button_layout )
        main_layout.addStrut(2)

        self.config_layout = QVBoxLayout() 
        main_layout.addLayout( self.config_layout )        
#        print "DV3DConfigControlPanel: %x %x " % ( id(self), id( self.configWidget) )

        self.modules_frame = QFrame()
        modules_layout = QVBoxLayout() 
        modules_layout.setMargin(2)
        modules_layout.setSpacing(1)
        self.modules_frame.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        self.modules_frame.setLineWidth(2)
        self.modules_frame.setLayout(modules_layout)
                
        modules_label = QLabel("Active Plots:")
        modules_label.setFont( QFont( "Arial", 14, QFont.Bold ) )
        modules_label.setAlignment( Qt.AlignHCenter )
        modules_layout.addWidget(modules_label)

        main_layout.addWidget( self.modules_frame )
        self.modules_frame.setVisible(False)
        self.plot_list = QListWidget()
        modules_layout.addWidget( self.plot_list )
        modules_layout.addStretch()
        self.connect( self.plot_list, SIGNAL("itemClicked(QListWidgetItem *)"),  self.processPlotListEvent ) 
                    
        main_layout.addStretch()                       
        self.setLayout(main_layout)

#    def __del__(self):
##        print "Deleting DV3DConfigControlPanel: id = %x " % id( self )
#        if self.configWidget: 
#            self.config_layout.removeWidget( self.configWidget )
#            self.configWidget = None

    def getPlot(self):
        return self.plot

    def getPipeline( self, pipeline_version=None ):
        if (pipeline_version == None) or (pipeline_version < 0): pipeline_version = self.version
        return self.controller.vistrail.getPipeline( pipeline_version )

    def getProjectController(self):
        return self.proj_controller

    def getController(self, controller_version=None):
        if (controller_version <> None) and (controller_version >= 0): 
            self.controller.change_selected_version( controller_version )
        return self.controller

    def getVersion(self):
        return self.version
                        
    def getConfigWidget( self, configFunctionList ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper    
        if configFunctionList:
            for configFunction in configFunctionList:
                renWinID = configFunction.module.GetRenWinID()
                activeRenWinIds = DV3DPipelineHelper.getActiveRenWinIds()
                if renWinID in activeRenWinIds:
#                   print " Got Config Widget: using cfg fn %s from module %d " % ( configFunction.name, configFunction.module.moduleID )
                    if configFunction.type == "leveling":
                        return DV3DRangeConfigWidget(self) 
                    if configFunction.type == "uvcdat-gui":
                        return configFunction.getWidget(self) 
        return None
        
    def init( self, configFunctionList ):
#        print "Init DV3DConfigControlPanel: id = %x " % id( self )
        cfgWidget = self.getConfigWidget( configFunctionList )
        if cfgWidget:
            if self.configWidget: 
                self.configWidget.finalizeConfig( )
                self.configWidget.setVisible ( False )
                self.config_layout.removeWidget( self.configWidget )
            self.configWidget = cfgWidget    
            self.config_layout.addWidget( cfgWidget ) 
#            print "Adding config widget, visible = ", str( cfgWidget.isVisible() ) 
        return cfgWidget        
        
    def isEligibleCommand( self, cmd ):
        return self.configWidget.isEligibleCommand( cmd )

    def addActivePlot( self, module, config_fn ):
        if self.showActivePlotsPanel and self.configWidget:
            active_renwin_ids = DV3DPipelineHelper.getActiveRenWinIds()
            if self.configWidget.active_cfg_cmd <> None and self.configWidget.active_cfg_cmd.isCompatible( config_fn ):
                cellsOnly = self.configWidget.active_cfg_cmd.activateByCellsOnly
                isActive = ( module.GetRenWinID() in active_renwin_ids )
                cell_addr = module.getCellAddress()
                if cell_addr:
                    if cellsOnly:
                        label = cell_addr     
                        existing_items = self.plot_list.findItems ( label, Qt.MatchFixedString )  
                    else:
                        plot_type = module.__class__.__name__
                        if plot_type[0:3] == "PM_": plot_type = plot_type[3:]
                        label = "%s: %s" % ( cell_addr, plot_type )   
                        existing_items = []
                    if len( existing_items ):
                        plot_list_item = existing_items[0]
                        plot_list_item.addModule( module )
                    else:
                        plot_list_item = PlotListItem( label, module, self.plot_list )
                    plot_list_item.setCheckState( Qt.Checked if isActive else Qt.Unchecked )
                    DV3DPipelineHelper.setModulesActivation( [ module ] , isActive, False ) 
            else:
                DV3DPipelineHelper.activationMap[ module ] = False
                    
    def  processPlotListEvent( self, list_item ): 
        DV3DPipelineHelper.setModulesActivation( list_item.modules, ( list_item.checkState() == Qt.Checked ) ) 
                           
    def startConfig(self, qs_action_key, qs_cfg_key ):
        self.plot_list.clear()
        self.modules_frame.setVisible(True)
        if self.configWidget:
            self.configWidget.startConfig( qs_action_key, qs_cfg_key )

    def stopConfig( self, module ):       
        ( interactionState, persisted ) = self.configWidget.getInteractionState()
        if not persisted:
            module.finalizeConfigurationObserver( interactionState, notifyHelper=False ) 
            module.render()
            self.configWidget.clearInteractionState()
        
    def persistParameter(self, module):
        ( interactionState, persisted ) = self.configWidget.getInteractionState()
        if not persisted:
            module.finalizeParameter( interactionState, notifyHelper=False )
            self.configWidget.clearInteractionState()

    def endConfig( self ):
        self.modules_frame.setVisible(False)
        if self.configWidget:
            self.configWidget.endConfig()
            
class ConnectionType:
    INPUT = 0
    OUTPUT = 1
    BOTH = 2

   
class DV3DPipelineHelper( PlotPipelineHelper, QObject ):
    '''
    This will take care of pipeline manipulation for plots.
    '''

    config_widget = None
    cfg_cmds = {}
    actionMap = {}
    activationMap = {}
    moduleMap = {} 
    actionMenu = None
    _config_mode = LevelingType.GUI

    def __init__(self):
        QObject.__init__( self )
        PlotPipelineHelper.__init__( self )
        '''
        Constructor
        '''

#    @staticmethod                         
#    def updateCell( action, key=0 ):
#        current_cell = DV3DPipelineHelper.cellMap.get( key, None )
#        if current_cell:
#            print " ^^^^^^^ Updating cell version from %d to %d."  % ( current_cell.current_parent_version, action.id )
#            current_cell.current_parent_version = action.id

    @staticmethod
    def find_variables_connected_to_operation_module(controller, pipeline, op_id):
        from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper
        return CDMSPipelineHelper.find_variables_connected_to_operation_module(controller, pipeline, op_id)
    
    @staticmethod                         
    def isLevelingConfigMode():
        return DV3DPipelineHelper._config_mode == LevelingType.LEVELING

    @staticmethod                         
    def isGuiConfigMode():
        return DV3DPipelineHelper._config_mode == LevelingType.GUI

    @staticmethod                         
    def setConfigMode( config_mode ):
        DV3DPipelineHelper._config_mode = config_mode

    @staticmethod                         
    def getConfigMode():
        return DV3DPipelineHelper._config_mode

    @staticmethod                         
    def getValidModuleIdList( ):
        module_id_list = []
        for pipeline in DV3DPipelineHelper.pipelineMap.values():
            for module in pipeline.module_list:
                module_id_list.append( module.id )
        return module_id_list
           
    @staticmethod                         
    def addAction( module, action_key, config_key, isActive=True ):
        actionList = DV3DPipelineHelper.actionMap.setdefault( action_key[1], [] )
        fn = module.configurableFunctions.get( action_key[1], None )
        actionList.append( ( module, config_key, fn ) )
        DV3DPipelineHelper.addConfigCommand( module, fn, config_key ) 
        if isActive:
            actions = DV3DPipelineHelper.actionMenu.actions() 
            for action in actions:
                if str(action.text()) == str(action_key[0]): return
            menuItem = DV3DPipelineHelper.actionMenu.addAction( action_key[0] )
            menuItem.connect ( menuItem, SIGNAL("triggered()"), lambda akey=action_key[1]: DV3DPipelineHelper.execAction( akey ) )
    
    @staticmethod
    def getConfigCmd( cfg_key ):   
        return DV3DPipelineHelper.cfg_cmds.get( cfg_key, None )

    @staticmethod
    def addConfigCommand( pmod, cmd, key = None ):
        if not key: key = cmd.key
        cmd_list = DV3DPipelineHelper.cfg_cmds.setdefault( key, [] )
        cmd_list.append( ( pmod, cmd ) )
    
    @staticmethod    
    def getPlotActivation( module ):
        return DV3DPipelineHelper.activationMap.get( module, False )

    @staticmethod    
    def removeModuleFromActivationMap( module ):
        if module in DV3DPipelineHelper.activationMap:
            del DV3DPipelineHelper.activationMap[module]
#            print "Removing Module %s (%d) from activation map" % ( module.__class__.__name__, module.moduleID )

    @staticmethod    
    def getActivePlotList( ):
        active_plots = []
        for module in DV3DPipelineHelper.activationMap.keys():
            if DV3DPipelineHelper.activationMap[ module ]:
                active_plots.append( module )
        return active_plots
 
    @staticmethod
    def setModulesActivation( modules, isActive, updateConfig=True ):
        for module in modules:
            DV3DPipelineHelper.activationMap[ module ] = isActive 
#            print " ** Set module activation: module[%d] -> %s (** persist parameters? **)" % ( module.moduleID, str(isActive) )
            if updateConfig and not isActive:
                config_fn = module.getCurrentConfigFunction()
                if config_fn and not config_fn.persisted:
                    module.finalizeParameter( config_fn.name )
                    config_fn.persisted = True
                    
    @staticmethod
    def getConfigCmdType( key ):                
        cmdRecList = DV3DPipelineHelper.cfg_cmds.get(key,[])
        for cmdRec in cmdRecList:
            cmd = cmdRec[1]
            if cmd: return cmd.type
        return 'untyped'
             
    @staticmethod
    def execAction( action_key ):
        from packages.vtDV3D.PersistentModule import PersistentVisualizationModule 
#        print " execAction: ", action_key
        currentActionList  =  DV3DPipelineHelper.actionMap[ action_key ]
        
        actionList = [] 
        configFunctionList = []
        validModuleIdList = ModuleStore.getModuleIDs() # DV3DPipelineHelper.getValidModuleIdList( )
        for ( module, key, fn ) in currentActionList:
            if module.moduleID in validModuleIdList:
                actionList.append( ( module, key, fn ) )
                if fn <> None: configFunctionList.append( fn )

#        DV3DPipelineHelper.actionMap[ action_key ] = actionList
        w = DV3DPipelineHelper.config_widget.init( configFunctionList )
                                         
        for ( module, key, f ) in actionList:
            module.processKeyEvent( key )

        if  ( key in DV3DPipelineHelper.cfg_cmds ) and ( DV3DPipelineHelper.getConfigCmdType( key ) in [ 'leveling', 'uvcdat-gui' ] ): 
            DV3DPipelineHelper.config_widget.startConfig( action_key, key )
        
        for ( module, key, f ) in actionList:
            DV3DPipelineHelper.activationMap[ module ] = True 
            DV3DPipelineHelper.config_widget.addActivePlot( module, f )
            
        if w: w.setVisible( True )

    @staticmethod
    def endInteraction():
        if DV3DPipelineHelper.config_widget:
            DV3DPipelineHelper.config_widget.endConfig()
     
    @staticmethod           
    def reset( ):
        if DV3DPipelineHelper.config_widget and DV3DPipelineHelper.config_widget.configWidget:
            ( interactionState, persisted ) = DV3DPipelineHelper.config_widget.configWidget.getInteractionState()
            if not persisted:
                DV3DPipelineHelper.config_widget.configWidget.clearInteractionState()
                for item in DV3DPipelineHelper.activationMap.items():
                    if item[1]: 
                        module =  item[0]          
                        module.finalizeParameter( interactionState, notifyHelper=False )
        DV3DPipelineHelper.actionMap = {}
        DV3DPipelineHelper.cfg_cmds = {}
     
    @staticmethod          
    def startNewMenu():
        DV3DPipelineHelper.actionMenu = QMenu()
        return DV3DPipelineHelper.actionMenu

#    @staticmethod
#    def build_plot_pipeline_action(controller, version, var_modules, plot_obj, row, col, template=None):
#        if controller is None:
#            controller = api.get_current_controller()
#            version = 0L
#        reg = get_module_registry()
#        ops = []
#
#        plot_module = controller.create_module_from_descriptor(plot_descriptor)
#        plot_functions =  [('graphicsMethodName', [plot_gm])]
#        if template is not None:
#            plot_functions.append(('template', [template]))
#        initial_values = desc.get_initial_values(plot_gm)
#        for attr in desc.gm_attributes:
#            plot_functions.append((attr,[getattr(initial_values,attr)]))
#            
#        functions = controller.create_functions(plot_module,plot_functions)
#        for f in functions:
#            plot_module.add_function(f)
#        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
#            ops.append(('add', var_modules[0]))
#        ops.append(('add', plot_module)) 
#        
#        if issubclass(var_modules[0].module_descriptor.module, CDMSVariable):
#            conn = controller.create_connection(var_modules[0], 'self',
#                                                plot_module, 'variable')
#        else:
#            conn = controller.create_connection(var_modules[0], 'output_var',
#                                                plot_module, 'variable')
#        ops.append(('add', conn))
#        if len(var_modules) > 1:
#            if issubclass(var_modules[1].module_descriptor.module, CDMSVariable):
#                conn2 = controller.create_connection(var_modules[1], 'self',
#                                                     plot_module, 'variable2')
#                ops.append(('add', var_modules[1]))
#            else:
#                conn2 = controller.create_connection(var_modules[1], 'output_var',
#                                                     plot_module, 'variable')
#            ops.append(('add', conn2))
#             
#        cell_module = controller.create_module_from_descriptor(
#            reg.get_descriptor_by_name('gov.llnl.uvcdat.cdms', 'CDMSCell'))
#        cell_conn = controller.create_connection(plot_module, 'self',
#                                                         cell_module, 'plot')
#        loc_module = controller.create_module_from_descriptor(
#            reg.get_descriptor_by_name('edu.utah.sci.vistrails.spreadsheet', 
#                                       'CellLocation'))
#        functions = controller.create_functions(loc_module,
#            [('Row', [str(row+1)]), ('Column', [str(col+1)])])
#        for f in functions:
#            loc_module.add_function(f)
#        loc_conn = controller.create_connection(loc_module, 'self',
#                                                        cell_module, 'Location')
#        ops.extend([('add', cell_module),
#                    ('add', cell_conn),
#                    ('add', loc_module),
#                    ('add', loc_conn)])
#        action = core.db.action.create_action(ops)
#        controller.change_selected_version(version)
#        controller.add_new_action(action)
#        controller.perform_action(action)
#        return action

    @staticmethod
    def update_plot_pipeline_action(controller, version, var_modules, plot_objs,
                                    row, col):
        """update_plot_pipeline_action(controller: VistrailController,
                                      version: long,
                                      var_modules: [list of modules],
                                      plot_objs: [list of Plot objects],
                                      row: int,
                                      col: int) -> Action 
        
        This function will update the workflow and add it to the
        provenance. It will reuse the plot configurations that are already in 
        the pipeline. You should make sure to update the state of the controller
        so its current_version is version before adding the VisTrails action to 
        the provenance.
        row and col contain the position of the cell in the spreadsheet the 
        workflow should be displayed, but as we keep a single cell, we don't
        use those parameters.
         
        """
        # FIXME want to make sure that nothing changes if var_module
        # or plot_module do not change
        added_vars = []
        if controller is None:
            controller = api.get_current_controller()
        # action = CDMSPipelineHelper.remove_variables_from_pipeline_action(controller, version)
        # version = action.id
        version = controller.current_version
        pipeline = controller.vistrail.getPipeline(version)
        ops = []
#        plot_modules = DV3DPipelineHelper.find_modules_by_type(pipeline, [CDMSPlot])
#        cell_module = DV3DPipelineHelper.find_module_by_name(pipeline, 'CDMSCell')
#        
#        for plot in plot_objs:
#            found = False
#            for plot_module in plot_modules:
#                gm = DV3DPipelineHelper.get_graphics_method_name_from_module(plot_module)
#                plot_type = plot_module.name[4:] #strip off CDMS
#                if plot.parent == plot_type and plot.name == gm:
#                    found = True
#                    ops2 = DV3DPipelineHelper.connect_variables_to_plots(controller, 
#                                                                         var_modules, 
#                                                                         plot, 
#                                                                         plot_module)
#            if not found:
#                ops2 = DV3DPipelineHelper.create_actions_from_plot_obj(controller, 
#                                                                       var_modules, 
#                                                                       cell_module, 
#                                                                       plot, 
#                                                                       added_vars)
#            ops.extend(ops2)
#        
        action = core.db.action.create_action(ops)
        controller.change_selected_version(version)
        controller.add_new_action(action)
        controller.perform_action(action)
        return action
     
    @staticmethod
    def add_additional_plot_to_pipeline( controller, version, plot, cell_addresses ):
        workflow = plot.workflow
        if not workflow: return
        pipeline = controller.current_pipeline
        cell_module = None
        reader_module = None
        for module in pipeline.module_list:
            pmod = module.module_descriptor.module
            if hasattr( pmod, "PersistentModuleClass" ) and issubclass( pmod.PersistentModuleClass, SpreadsheetCell ):
                cell_module = module
            elif issubclass( pmod, ( CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader, CDMS_VectorReader ) ):
                reader_module = module
        ops = []
        added_modules = []
        for module in workflow.module_list:
            pmod = module.module_descriptor.module
            if issubclass( pmod.PersistentModuleClass, SpreadsheetCell ):
                connected_module_ids = workflow.get_inputPort_modules( module.id, 'volume' )
                for connected_module_id in connected_module_ids:
                    connected_module = workflow.modules[ connected_module_id ]
                    plot_module = controller.create_module_from_descriptor( connected_module.module_descriptor )
                    ops.append( ('add', plot_module) )
                    if reader_module:
                        conn0 = controller.create_connection( reader_module, 'volume', plot_module, 'volume' )
                        ops.append( ('add', conn0) )
                    else: print>>sys.stderr, " Warning: Can't find reader module in plot pipeline."
                    if cell_module:
                        conn1 = controller.create_connection( plot_module, 'volume', cell_module, 'volume' )
                        ops.append(('add', conn1))
                    else: print>>sys.stderr, " Warning: Can't find cell module in plot pipeline."
            elif issubclass( pmod, ( CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader, CDMS_VectorReader ) ):
                pass # Check data type compatibility
            else:
                pass
                
        action2 = core.db.action.create_action(ops)
        controller.add_new_action(action2)
        controller.perform_action(action2)

        sheetTabWidget = getSheetTabWidget()
        sheetName = sheetTabWidget.getSheetName()        
        for cell_address in cell_addresses:
#            if len( pipeline.module_list ) == 0:
#                print "Attempt to add empty pipeline to %s " % ( str(( sheetName, cell_address )) )
#            else:
#                DV3DPipelineHelper.pipelineMap[ ( sheetName, cell_address ) ] = controller.current_pipeline           
            for mid in controller.current_pipeline.modules:
                module = ModuleStore.getModule( mid ) 
                if module: 
                    module.setCellLocation( sheetName, cell_address )   
                    DV3DPipelineHelper.moduleMap[mid] = ( sheetName, cell_address )

        return action2
    
    @staticmethod
    def get_project_controller():
        from gui.application import get_vistrails_application
        VistrailsApplication = get_vistrails_application()
        return VistrailsApplication.uvcdatWindow.current_controller
                                        
    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, plot_objs, row, col, templates=[]):
#        project_controller =  DV3DPipelineHelper.get_project_controller()
#        current_cell = project_controller.sheet_map[sheetName][(row,col)]
        
#        from packages.uvcdat_cdms.init import CDMSVariableOperation 
#        ConfigurableFunction.clear()
        controller.change_selected_version(version)
#        print "[%d,%d] ~~~~~~~~~~~~~~~>> build_plot_pipeline_action, version=%d, controller.current_version=%d" % ( row, col, version, controller.current_version )
#        print " --> plot_modules = ",  str( controller.current_pipeline.modules.keys() )
#        print " --> var_modules = ",  str( [ var.id for var in var_modules ] )
        plots = list( plot_objs )
        #Considering that plot_objs has a single plot_obj
        plot_obj = plots.pop()
        action = None
        if len( plot_obj.cells ) > 0: 
            plot_obj.current_parent_version = version
            plot_obj.current_controller = controller
            aliases = {}
            for i in range(len(var_modules)):
                if issubclass( var_modules[i].module_descriptor.module, CDMSVariableOperation):
                    varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'varname' )
                    python_command = PlotPipelineHelper.get_value_from_function( var_modules[i], 'python_command' )
                    aliases[plot_obj.vars[i]] = varname
                    aliases[ "%s.cmd" % plot_obj.vars[i] ] = python_command
                else:
                    try:
                        filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'filename')
                        if filename is None:
                            filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'file')
                        if isinstance( filename, core.modules.basic_modules.File ):
                            filename = filename.name
                        url = PlotPipelineHelper.get_value_from_function( var_modules[i], 'url')            
                        varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'name')
                        file_varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'varNameInFile')
                        axes = PlotPipelineHelper.get_value_from_function( var_modules[i], 'axes')
                        aliases[ ".".join( [plot_obj.files[i],"url"] )  ] = url if url else ""
                        aliases[plot_obj.vars[i]] = varname
                        aliases[ "%s.file" % plot_obj.vars[i] ] = file_varname if file_varname else ""
                        if len(plot_obj.axes) > i:
                            aliases[plot_obj.axes[i]] = axes
                        aliases[plot_obj.files[i]] = filename
                    except Exception, err:
                        print>>sys.stderr,  "Error setting aliases: %s" % ( str(err) )
    
            #FIXME: this will always spread the cells in the same row
            cell_specs = []
            cell_addresses = []
            for j in range(plot_obj.cellnum):
                try:
                    cell = plot_obj.cells[j] 
                    location = cell.address_name if cell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
                    cell_addr = "%s%s" % ( chr(ord('A') + col+j ), row+1)
                    cell_specs.append( '%s!%s' % ( location, cell_addr ) )
                    cell_addresses.append( cell_addr )
                except Exception, err:
                    print>>sys.stderr, " Error producing cell specs: %s " % str( err )
    #            aliases[ location ] = cell_spec
    #            cell_specs.append( 'location%d!%s' % ( j, cell_spec ) )
    #            
    #        for a,w in plot_obj.alias_widgets.iteritems():
    #            try:    aliases[a] = w.contents()
    #            except Exception, err: print>>sys.stderr, "Error updating alias %s:" % str( a ), str(err)
    
            if plot_obj.serializedConfigAlias and var_modules: aliases[ plot_obj.serializedConfigAlias ] = ';;;' + ( '|'.join( cell_specs ) )
            pip_str = core.db.io.serialize(plot_obj.workflow)
            controller.paste_modules_and_connections(pip_str, (0.0,0.0))
            
            for plot_obj in plots:
                plot_obj.current_parent_version = version
                plot_obj.current_controller = controller
                DV3DPipelineHelper.add_additional_plot_to_pipeline( controller, version, plot_obj, cell_addresses )
    
    #        Disable File Reader, get Variable from UVCDAT
    #        plot_obj.addMergedAliases( aliases, controller.current_pipeline )
            action = DV3DPipelineHelper.addParameterChangesAction( controller.current_pipeline,  controller,  controller.vistrail, controller.current_version, aliases, iter(cell_specs) )        
    #        if action: controller.change_selected_version( action.id )   
            
            reader_1v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader ] )
            reader_3v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VectorReader ] )
            reader_modules = reader_1v_modules + reader_3v_modules
            iVarModule = 0
            ops = []           
            for module in reader_modules:
                nInputs = 1 if module in reader_1v_modules else 3
                for iInput in range( nInputs ):
                    if iInput < len( var_modules ):
                        try:
                            var_module = var_modules[ iVarModule ]
                            var_module_in_pipeline = PlotPipelineHelper.find_module_by_id( controller.current_pipeline, var_module.id )
                            if var_module_in_pipeline == None: 
                                ops.append( ( 'add', var_module ) )
                            inputPort = 'variable' if (iInput == 0) else "variable%d" % ( iInput + 1)
                            conn1 = controller.create_connection( var_module, 'self', module, inputPort )
                            ops.append( ( 'add', conn1 ) )
                            iVarModule = iVarModule+1
                        except Exception, err:
                            print>>sys.stderr, "Exception adding CDMSVariable input:", str( err)
                            break
                                           
            try:
                action = core.db.action.create_action(ops)
                controller.add_new_action(action)
                controller.perform_action(action)
            except Exception, err:
                print " Error connecting CDMSVariable to workflow: ", str(err)
                traceback.print_exc()
            
            sheetTabWidget = getSheetTabWidget()
            sheetName = sheetTabWidget.getSheetName() 
            for cell_address in cell_addresses: 
                for mid in controller.current_pipeline.modules:   
                    DV3DPipelineHelper.moduleMap[mid] = ( sheetName, cell_address )       
#            pipeline =  controller.current_pipeline        
#            for cell_address in cell_addresses:
#                if len( pipeline.module_list ) == 0:
#                    print "Attempt to add empty pipeline to %s " % ( str(( sheetName, cell_address )) )
#                else:
#                    DV3DPipelineHelper.pipelineMap[ ( sheetName, cell_address ) ] = controller.current_pipeline                   
        return action

    @staticmethod
    def getPipeline( cell_address, sheetName = None ):
        if sheetName == None:    
            sheetTabWidget = getSheetTabWidget()
            sheetName = sheetTabWidget.getSheetName() 
            proj_controller = api.get_current_project_controller()
            controller =  proj_controller.vt_controller
            cell_coords = get_coords_from_cell_address( cell_address[1], cell_address[0] ) if isStr( cell_address ) else cell_address
            cell = proj_controller.sheet_map[ sheetName ][ ( cell_coords[1], cell_coords[0] ) ]
            current_version = cell.current_parent_version 
            controller.change_selected_version( current_version )
            pipeline = controller.vistrail.getPipeline( current_version )  
        return pipeline       

    @staticmethod
    def getCellAddress( pipeline ):
        proj_controller = api.get_current_project_controller()
        controller =  proj_controller.vt_controller 
        for sheet_item in proj_controller.sheet_map.items(): 
            sheetName = sheet_item[0]
            cellMap = sheet_item[1]
            for cell_item in cellMap.items():
                cell_address = cell_item[0]
                cell = cell_item[1]
                current_version = cell.current_parent_version 
                controller.change_selected_version( current_version )
                cell_pipeline = controller.vistrail.getPipeline( current_version )  
                if cell_pipeline == pipeline: return( sheetName, ( cell_address[1], cell_address[0] ) )
        return ( None, None ) 

    @staticmethod
    def getCellCoordinates( mid ):
        ( sheetName, cell_addr ) = DV3DPipelineHelper.moduleMap.get( mid, ( None, None ) )
        coords = ( int( cell_addr[1] ) - 1, ord(cell_addr[0])-ord('A') ) if cell_addr else None
        if sheetName == None:
            sheetTabWidget = getSheetTabWidget()
            sheetName = sheetTabWidget.getSheetName()          
        return ( sheetName, coords )

#        for item in  DV3DPipelineHelper.pipelineMap.items():
#            if mid in item[1].modules: return item[0]
#        sheetTabWidget = getSheetTabWidget()
#        sheetName = sheetTabWidget.getSheetName()          
#        return ( sheetName, None )

    @staticmethod
    def addParameterChangesAction( pipeline, controller, vistrail, parent_version, aliases, cell_spec_iter ):
        param_changes = []
        newid = parent_version
#        print "addParameterChangesAction()"
#        print "Aliases: %s " % str( aliases )
#        print "Pipeline Aliases: %s " % str( pipeline.aliases )
        aliasList = aliases.iteritems()
        for k,value in aliasList:
            alias = pipeline.aliases.get(k,None) # alias = (type, oId, parentType, parentId, mId)
            if alias:
                module = pipeline.modules[alias[4]]
                function = module.function_idx[alias[3]]
                old_param = function.parameter_idx[alias[1]]
                #print alias, module, function, old_param
                if old_param.strValue != value:
                    new_param = controller.create_updated_parameter(old_param, value)
                    if new_param is not None:
                        op = ('change', old_param, new_param, function.vtType, function.real_id)
                        param_changes.append(op)
#                        print "Added parameter change for alias=%s, value=%s" % ( k, value  )
                    else:
                        print>>sys.stderr, "CDAT Package: Change parameter %s was not generated"%(k)
                 
        cell_modules = PlotPipelineHelper.find_modules_by_type( pipeline, [ MapCell3D, CloudCell3D ] )
        for module in cell_modules:
            op = DV3DPipelineHelper.get_parameter_change_op( controller, module, 'title', 0, '' )
            if op: param_changes.append(op)
            cell_loc = cell_spec_iter.next()
            op = DV3DPipelineHelper.get_parameter_change_op( controller, module, 'cell_location', 0, cell_loc )
            if op: param_changes.append(op)
            
        action = None
        if len(param_changes) > 0:
            action = core.db.action.create_action(param_changes)
            controller.change_selected_version(parent_version)
            controller.add_new_action(action)
            controller.perform_action(action)
        return action

    @staticmethod    
    def get_parameter_change_op( controller, module, function_name, parameter_index, new_value ):
        op = None
        function = None
        for fn in module.functions:
            if fn.name == function_name:
                function = fn
                break
        if function:
            old_param = function.parameters[ parameter_index ]
            new_param = controller.create_updated_parameter( old_param, new_value )
            if new_param is not None:
                op = ('change', old_param, new_param, function.vtType, function.real_id )
        return op

    
    @staticmethod
    def copy_pipeline_to_other_location(pipeline, controller, sheetName, row, col, 
                                        plot_type, cell):
        #for now this helper will copy the workflow and change the location
        #based on the alias dictionary
        from core.uvcdat.plotmanager import get_plot_manager
        pip_str = core.db.io.serialize(pipeline)
        controller.change_selected_version(cell.current_parent_version)
        modules = controller.paste_modules_and_connections(pip_str, (0.0,0.0))
        cell.current_parent_version = controller.current_version
        pipeline = controller.current_pipeline
        
        plot_obj = get_plot_manager().get_plot_by_vistrail_version(plot_type, 
                                                                   controller.vistrail,
                                                                   controller.current_version)
        plot_obj.current_parent_version = cell.current_parent_version
        plot_obj.current_controller = controller
        cell.plots = [plot_obj]
        
        aliases = {}
        for a in pipeline.aliases:
            aliases[a] = pipeline.get_alias_str_value(a)
        
        if (plot_obj.serializedConfigAlias and 
            plot_obj.serializedConfigAlias in aliases):
            plot_obj.unserializeAliases(aliases)
            
        #FIXME: this will always spread the cells in the same row
        for j in range(plot_obj.cellnum):
            if plot_obj.cells[j].row_name and plot_obj.cells[j].col_name:
                aliases[plot_obj.cells[j].row_name] = str(row+1)
                aliases[plot_obj.cells[j].col_name] = str(col+1+j)
            elif plot_obj.cells[j].address_name:
                aliases[plot_obj.cells[j].address_name] = "%s%s"%(chr(ord('A') + col+j),
                                                                  row+1)
        
        actions = plot_obj.applyChanges(aliases)
        
        #this will update the variables
        for i in range(plot_obj.varnum):
            cell.variables.append(aliases[plot_obj.vars[i]])
            
        #get the most recent action that is not None
        if len(actions) > 0:
            action = actions.pop()
            while action == None and len(actions) > 0:
                action = actions.pop()
            if action is not None:
                cell.current_parent_version = action.id
                return action
        return None
    
    @staticmethod
    def load_pipeline_in_location(pipeline, controller, sheetName, row, col, 
                                        plot_type, cell):
        #for now this helper will change the location in place
        #based on the alias dictionary

        var_modules = DV3DPipelineHelper.find_modules_by_type(pipeline, 
                                                              [CDMSVariable,
                                                               CDMSVariableOperation])
        
        # This assumes that the pipelines will be different except for variable 
        # modules
        controller.change_selected_version(cell.current_parent_version)
        plot_obj = DV3DPipelineHelper.get_plot_by_vistrail_version(plot_type, 
                                                                   controller.vistrail, 
                                                                   controller.current_version)
        if plot_obj is not None:
            plot_obj.current_parent_version = cell.current_parent_version
            plot_obj.current_controller = controller
            cell.plots = [plot_obj]
            #FIXME: this will always spread the cells in the same row
            cell_specs = []
            cell_addresses = []
            for j in range(plot_obj.cellnum):
                ccell = plot_obj.cells[j] 
                location = ccell.address_name if ccell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
                cell_spec = "%s%s" % ( chr(ord('A') + col+j ), row+1)
                cell_specs.append( '%s!%s' % ( location, cell_spec ) )
                cell_addresses.append( cell_spec )

            sheetTabWidget = getSheetTabWidget()
            sheetName = sheetTabWidget.getSheetName()                  
            for cell_address in cell_addresses:
                for mid in pipeline.modules:   
                    DV3DPipelineHelper.moduleMap[mid] = ( sheetName, cell_address )
            
            # Update project controller cell information    
            cell.variables = []
            #FIXME: this doesn't work as expected... DV3D should provide a way 
            #to find the variables connected to a plot module so that only the
            # operation or variable connected is added.
            for var in var_modules:
                cell.variables.append(DV3DPipelineHelper.get_variable_name_from_module(var))
        else:
            print "Error: Could not find DV3D plot type based on the pipeline"
            print "Visualizations can't be loaded."            

    
    @staticmethod
    def build_python_script_from_pipeline(controller, version, plot_objs=[]):
        from api import load_workflow_as_function
        text = "from api import load_workflow_as_function\n"
        if len(plot_objs) > 0:
            text += "proj_file = '%s'\n"%controller.get_locator().name
            text += "vis_id = %s\n"%version
            text += "vis = load_workflow_as_function(proj_file, vis_id)\n"
            vis = load_workflow_as_function(controller.get_locator().name, version)
            doc = vis.__doc__
            lines = doc.split("\n")
            for line in lines:
                text += "# %s\n"%line                 
            return text
            
    @staticmethod
    def are_workflows_compatible(vistrail_a, vistrail_b, version_a, version_b):
        #FIXME:
        # This assumes that the workflows will be different by at most variable
        # modules added to the pipeline. If modules can be deleted from original
        # vistrails, then this function needs to be updated.
        diff_versions = ((vistrail_a, version_a), (vistrail_b, version_b))
        diff = core.db.io.get_workflow_diff(*diff_versions)
        (p1, p2, v1Andv2, heuristicMatch, v1Only, v2Only, paramChanged) = diff
        if len(v1Only) == 0 and len(v2Only)==0:
            return True
        elif len(v2Only) == 0 and len(v1Only) > 0:
            moduletypes =  (CDMSVariable, CDMSVariableOperation)
            invalid = []
            for mid in v1Only:
                module = p1.modules[mid]
                desc = module.module_descriptor
                if not issubclass(desc.module, moduletypes):
                    invalid.append(module)
            if len(invalid) == 0:
                return True
        return False

    @staticmethod
    def getActiveCells():
        sheetTabWidget = getSheetTabWidget()
        selected_cells = sheetTabWidget.getSelectedLocations() 
        return selected_cells

    @staticmethod
    def getActiveIrens():
        from packages.vtDV3D.PersistentModule import PersistentVisualizationModule
        irens = []
        for cell in DV3DPipelineHelper.getActiveCells():
            cell_spec = "%s%s" % ( chr(ord('A') + cell[1] ), cell[0]+1 )
            iren = PersistentVisualizationModule.renderMap.get( cell_spec, None )
            irens.append( iren )
        return irens

    @staticmethod
    def getActiveRenWinIds():
        rwins = []
        for iren in DV3DPipelineHelper.getActiveIrens():
            rw = iren.GetRenderWindow() if iren else None
            if rw: rwins.append( id(rw) )
        return rwins
    
    @staticmethod
    def show_configuration_widget( controller, version, plot_objs=[ None ] ):
        from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper, CDMSPlotWidget
        current_controller = api.get_current_controller()
        pipeline = controller.vt_controller.vistrail.getPipeline(version) 
#        print '-'*50      
#        print 'New Configuration panel: version=%d, current_version=%d, pid=%d, modules=%s' % ( version, current_controller.current_version, pipeline.db_id, [ mid for mid in pipeline.modules ] )    
#        print '-'*50      
        pmods = set()
        DV3DPipelineHelper.reset()
        menu = DV3DPipelineHelper.startNewMenu()
        configFuncs = ConfigurableFunction.getActiveFunctionList( ) # DV3DPipelineHelper.getActiveIrens() )
        active_renwin_ids = DV3DPipelineHelper.getActiveRenWinIds()
        for configFunc in configFuncs:
            if configFunc.isValid():
                action_key = ( str( configFunc.label ), str( configFunc.name ) )
                config_key = configFunc.key 
                pmod = configFunc.module
                if pmod.renderer:
                    isActive = ( id( pmod.renderer.GetRenderWindow() ) in active_renwin_ids ) 
                    DV3DPipelineHelper.addAction( pmod, action_key, config_key, isActive ) 
                    pmods.add(pmod)
                    
#        for module in pipeline.module_list:
#            pmod = ModuleStore.getModule(  module.id ) 
#            if pmod:
#                pmods.add(pmod)
#                configFuncs = pmod.configurableFunctions.values()
#                for configFunc in configFuncs:
#                    action_key = str( configFunc.label )
#                    config_key = configFunc.key               
#                    DV3DPipelineHelper.addAction( pmod, action_key, config_key ) 
                    
        menu1 = DV3DPipelineHelper.startNewMenu() 
        for pmod in pmods:
            DV3DPipelineHelper.addAction( pmod, [ 'Help', 'help' ], 'h' )
            DV3DPipelineHelper.addAction( pmod, [ 'Show Colorbar', 'colorbar' ], 'l' )
            DV3DPipelineHelper.addAction( pmod, [ 'Reset', 'reset' ], 'r' )
        
        DV3DPipelineHelper.config_widget = DV3DConfigControlPanel( menu, menu1, controller, version, plot_objs[0] )
        for pmod in pmods:
            cmdList = pmod.getConfigFunctions( [ 'leveling', 'uvcdat-gui' ] )
            for cmd in cmdList:
                DV3DPipelineHelper.addConfigCommand( pmod, cmd )
            pmod.resetNavigation()
        return DV3DPipelineHelper.config_widget

    @staticmethod
    def getGuiKernel( ):
        return DV3DPipelineHelper.config_widget.configWidget if DV3DPipelineHelper.config_widget else None
    
    @staticmethod
    def isEligibleFunction( configFn ):
        return DV3DPipelineHelper.config_widget.isEligibleCommand( configFn )
         
    @staticmethod
    def get_plot_by_vistrail_version(plot_type, vistrail, version):
        from core.uvcdat.plotmanager import get_plot_manager
        plots = get_plot_manager()._plot_list[plot_type]
        vistrail_a = vistrail
        version_a = version
        if vistrail_a is None or version_a <=0:
            return None
        pipeline = vistrail.getPipeline(version)
        for pl in plots.itervalues():
            vistrail_b = pl.plot_vistrail
            version_b = pl.workflow_version
            if vistrail_b is not None and version_b > 0:
                if (DV3DPipelineHelper.are_workflows_compatible(vistrail_a, vistrail_b, 
                                                                version_a, version_b) and
                    len(pipeline.aliases) == len(pl.workflow.aliases)):
                    return pl
        return None
    
    @staticmethod
    def get_variable_name_from_module(module):
        desc = module.module_descriptor.module
        if issubclass(desc, CDMSVariable):
            result = DV3DPipelineHelper.get_value_from_function(module, "name")
        elif issubclass(desc, CDMSVariableOperation):
            result = DV3DPipelineHelper.get_value_from_function(module, "varname")
        else:
            result = None
        return result
