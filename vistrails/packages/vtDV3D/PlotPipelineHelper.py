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
from packages.vtDV3D.DV3DCell import MapCell3D
from packages.vtDV3D import ModuleStore
from packages.uvcdat_cdms.init import CDMSVariableOperation, CDMSVariable 
from packages.vtDV3D.vtUtilities import *
from core.uvcdat.plot_registry import get_plot_registry
from core.modules.module_registry import get_module_registry
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def getFormattedQString( value ):
    val = float( value )
    if val > 99999 or val < 0.001:  sval = "%.2g" % val
    if val > 1:                     sval = "%.2f" % val
    else:                           sval = "%.4f" % val
    return QString( sval )

class ConfigMenuManager( QObject ):
    
    def __init__( self, **args ):
        QObject.__init__( self )
        self.cfg_cmds = {}
        self.callbacks = None
#        self.signals = [ SIGNAL("startConfig(QString,QString)"), SIGNAL("endConfig()") ]
             
    def addAction( self, module, action_key, config_key ):
        actionList = self.actionMap.setdefault( action_key, [] )
        actionList.append( ( module, config_key ) ) 
        if len( actionList ) == 1:
            menuItem = self.menu.addAction( action_key )
            self.connect ( menuItem, SIGNAL("triggered()"), lambda akey=action_key: self.execAction( akey ) )
    
    def getConfigCmd( self, cfg_key ):   
        return self.cfg_cmds.get( cfg_key, None )

    def addConfigCommand( self, pmod, cmd ):
        cmd_list = self.cfg_cmds.setdefault( cmd.key, [] )
        cmd_list.append( ( pmod, cmd ) )
        
    def setCallbacks( self, startConfigCallable, endConfigCallable ):
        self.callbacks = [ startConfigCallable, endConfigCallable ]
#        for iC in range(2): self.connect ( self, self.signals[iC], self.callbacks[iC] ) 

    
    def execAction( self, action_key ): 
        print " execAction: ", action_key
        actionList  =  self.actionMap[ action_key ]
        for ( module, key ) in actionList:
            module.processKeyEvent( key )
        if self.callbacks and (key in self.cfg_cmds):
            self.callbacks[0]( action_key, key )
#        self.emit( SIGNAL('startConfig(QString,QString)'), action_key, key )

    def endInteraction( self ):
        self.callbacks[1]()
#        self.emit( SIGNAL('endConfig()') ) 
                
    def reset(self):
        self.actionMap = {}
        self.cfg_cmds = {}
#        if self.callbacks:
#            for iC in range(2):
#                self.disconnect ( self, self.signals[iC], self.callbacks[iC] ) 
        self.callbacks = None
               
    def startNewMenu(self):
        self.menu = QMenu()
        return self.menu

ConfigCommandMenuManager = ConfigMenuManager()

class DV3DParameterSliderWidget(QWidget):
    
    def __init__( self, label, parent=None):
        QWidget.__init__(self,parent)
        self.range = [ 0.0, 1.0, 1.0 ]
        
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
        
    def setDisplayValue( self, fval ):
        qsval = getFormattedQString( fval ) 
        self.textbox.setText( qsval )
        
    def setRange( self, fmin, fmax ):
        self.range = [ fmin, fmax, (fmax-fmin) ]

    def setValue( self, value ):
        sliderVal = int( 100 * ( value-self.range[0] ) / self.range[2] ) 
        self.slider.setValue( sliderVal )
        qsval = getFormattedQString( value ) 
        self.textbox.setText( qsval  )
                
class DV3DRangeConfigWidget(QFrame):
    MIN_SLIDER = 0
    MAX_SLIDER = 1
    
    def __init__( self, parent=None):
        QWidget.__init__( self, parent )
#        self.setStyleSheet("QWidget#RangeConfigWidget { border-style: outset; border-width: 2px; border-color: blue; }" )
        self.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        self.setLineWidth(2)
        self.setObjectName('RangeConfigWidget') 
        self.initialRange = [ 0, 0, 0 ]
        self.initialize()
        
        main_layout = QVBoxLayout()         
        self.cfg_action_label = QLabel("Configuration:")
        self.cfg_action_label.setFont( QFont( "Arial", 14, QFont.Bold ) )
        main_layout.addWidget( self.cfg_action_label )
        
        self.rangeMinEditor = DV3DParameterSliderWidget( 'Range Min:', self )
        self.rangeMaxEditor = DV3DParameterSliderWidget( 'Range Max:', self )
        self.sliders = [ self.rangeMinEditor, self.rangeMaxEditor ]
        self.connect( self.rangeMinEditor.slider, SIGNAL("sliderMoved(int)"), lambda ival: self.sliderValueChanged(self.MIN_SLIDER,ival) ) 
        self.connect( self.rangeMaxEditor.slider, SIGNAL("sliderMoved(int)"), lambda ival: self.sliderValueChanged(self.MAX_SLIDER,ival) ) 
        self.connect( self.rangeMinEditor.textbox, SIGNAL("returnPressed()"),  lambda: self.processTextValueEntry(self.MIN_SLIDER) ) 
        self.connect( self.rangeMaxEditor.textbox, SIGNAL("returnPressed()"),  lambda: self.processTextValueEntry(self.MAX_SLIDER) ) 
               
        main_layout.addWidget( self.rangeMinEditor )
        main_layout.addWidget( self.rangeMaxEditor )
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
        
        main_layout.addLayout( button_layout )
        main_layout.addStretch()             
        self.setLayout(main_layout)
        self.disable()
        
    def initialize(self):
        self.active_cfg_cmd = None
        self.active_module = None
        
    def processTextValueEntry( self, iSlider ):
        if self.active_cfg_cmd:
            textbox = self.sliders[iSlider].textbox
            fval = float( textbox.text() )
            slider = self.sliders[iSlider]
            slider.setValue( fval ) 
            parm_range = list( self.active_cfg_cmd.range ) 
            parm_range[ iSlider ] = fval
            self.active_cfg_cmd.broadcastLevelingData( parm_range )             
            if self.active_module: self.active_module.render()
        
    def setTitle(self, title ):
        self.cfg_action_label.setText( title )
        
    def sliderValueChanged( self, iSlider, iValue = None ):
        if self.active_cfg_cmd:
            rbnds = self.active_cfg_cmd.range_bounds
            parm_range = list( self.active_cfg_cmd.range )
            fval = rbnds[0] + (rbnds[1]-rbnds[0]) * ( iValue / 100.0 )
            parm_range[ iSlider ] = fval
            self.sliders[iSlider].setDisplayValue( fval )
            self.active_cfg_cmd.broadcastLevelingData( parm_range )             
            if self.active_module: self.active_module.render()
             
    def updateSliderValues( self, initialize=False ): 
        if self.active_cfg_cmd:
            rbnds = self.active_cfg_cmd.range_bounds
            parm_range = list( self.active_cfg_cmd.range )
#            print " Update Slider Values-> range: %s, bounds: %s " % ( str(parm_range), str(rbnds) )
            for iSlider in range(2):
                slider = self.sliders[iSlider]
                fval = parm_range[ iSlider ]
                slider.setDisplayValue( fval )   
                slider.setRange( rbnds[0], rbnds[1] )       
                slider.setValue( fval ) 
                if initialize: self.initialRange[iSlider] = fval
                
    def updateRange(self, min, max ): 
        pass     
     
    def enable(self): 
        self.setVisible(True)

    def disable(self): 
        self.setVisible(False)
          
    def startConfig(self, qs_action_key, qs_cfg_key ):
        self.enable()
        cfg_key = str(qs_cfg_key)
        action_key = str(qs_action_key)
        self.setTitle( action_key )
        try:
            cmd_list = ConfigCommandMenuManager.getConfigCmd ( cfg_key )
            if cmd_list:
                for cmd_entry in cmd_list:
                    self.active_module = cmd_entry[0] 
                    self.active_cfg_cmd = cmd_entry[1] 
                    break
                self.updateSliderValues(True)
                self.connect( self.active_cfg_cmd, SIGNAL('updateLeveling()'), lambda: self.updateSliderValues() )
        except RuntimeError:
            print "RuntimeError"
            
    def endConfig(self):
        self.disable()
        
    def finalizeConfig(self):
        if self.active_module:
            interactionState = self.active_cfg_cmd.name
            self.active_module.finalizeConfigurationObserver( interactionState ) 
            self.active_cfg_cmd.updateWindow()   
        self.endConfig()

    def revertConfig(self):
        if self.active_module:
            self.initialRange[2] = self.active_cfg_cmd.range[2]
            self.active_cfg_cmd.broadcastLevelingData( self.initialRange )  
            interactionState = self.active_cfg_cmd.name
            self.active_module.finalizeConfigurationObserver( interactionState ) 
            self.active_cfg_cmd.updateWindow()   
        self.endConfig()
        

class DV3DConfigControlPanel(QWidget):
    MIN_SLIDER = 0
    MAX_SLIDER = 1

    def __init__( self, configMenu, optionsMenu, parent=None):
        QWidget.__init__(self,parent)
        self.active_cfg_cmd = None
        self.active_module = None
           
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
        
        self.rangeConfigWidget = DV3DRangeConfigWidget(self)
        main_layout.addWidget( self.rangeConfigWidget ) 
        print "DV3DConfigControlPanel: %x %x " % ( id(self), id( self.rangeConfigWidget) )
            
        main_layout.addStretch()                       
        self.setLayout(main_layout)

                           
    def startConfig(self, qs_action_key, qs_cfg_key ):
        if self.rangeConfigWidget:
            self.rangeConfigWidget.startConfig( qs_action_key, qs_cfg_key )
            
    def endConfig(self):
        if self.rangeConfigWidget:
            self.rangeConfigWidget.endConfig()
        
class DV3DPipelineHelper( PlotPipelineHelper, QObject ):
    '''
    This will take care of pipeline manipulation for plots.
    '''

    config_widget = None

    def __init__(self):
        QObject.__init__( self )
        PlotPipelineHelper.__init__( self )
        '''
        Constructor
        '''

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
    def build_plot_pipeline_action(controller, version, var_modules, plot_objs, row, col, templates=[]):
#        from packages.uvcdat_cdms.init import CDMSVariableOperation 
        controller.change_selected_version(version)
#        print "build_plot_pipeline_action[%d,%d], version=%d, controller.current_version=%d" % ( row, col, version, controller.current_version )
#        print " --> plot_modules = ",  str( controller.current_pipeline.modules.keys() )
#        print " --> var_modules = ",  str( [ var.id for var in var_modules ] )
        #Considering that plot_objs has a single plot_obj
        plot_obj = plot_objs[0]
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
                filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'filename')
                if filename is None:
                    filename = PlotPipelineHelper.get_value_from_function( var_modules[i], 'file')
                if isinstance( filename, core.modules.basic_modules.File ):
                    filename = filename.name
                url = PlotPipelineHelper.get_value_from_function( var_modules[i], 'url')            
                varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'name')
                file_varname = PlotPipelineHelper.get_value_from_function( var_modules[i], 'varNameInFile')
                axes = PlotPipelineHelper.get_value_from_function( var_modules[i], 'axes')
                aliases[plot_obj.files[i]] = filename
                aliases[ ".".join( [plot_obj.files[i],"url"] )  ] = url if url else ""
                aliases[plot_obj.vars[i]] = varname
                aliases[ "%s.file" % plot_obj.vars[i] ] = file_varname if file_varname else ""
                if len(plot_obj.axes) > i:
                    aliases[plot_obj.axes[i]] = axes

        #FIXME: this will always spread the cells in the same row
        cell_specs = []
        for j in range(plot_obj.cellnum):
            cell = plot_obj.cells[j] 
            location = cell.address_name if cell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
            cell_spec = "%s%s" % ( chr(ord('A') + col+j ), row+1)
#            aliases[ location ] = cell_spec
            cell_specs.append( '%s!%s' % ( location, cell_spec ) )
#            cell_specs.append( cell_spec )
#            cell_specs.append( 'location%d!%s' % ( j, cell_spec ) )
#            
#        for a,w in plot_obj.alias_widgets.iteritems():
#            try:    aliases[a] = w.contents()
#            except Exception, err: print>>sys.stderr, "Error updating alias %s:" % str( a ), str(err)

        if plot_obj.serializedConfigAlias and var_modules: aliases[ plot_obj.serializedConfigAlias ] = ';;;' + ( '|'.join( cell_specs ) )
        pip_str = core.db.io.serialize(plot_obj.workflow)
        controller.paste_modules_and_connections(pip_str, (0.0,0.0))

#        Disable File Reader, get Variable from UVCDAT
#        plot_obj.addMergedAliases( aliases, controller.current_pipeline )
        action = DV3DPipelineHelper.addParameterChangesAction( controller.current_pipeline,  controller,  controller.vistrail, controller.current_version, aliases, iter(cell_specs) )        
        if action: controller.change_selected_version( action.id )   
        
        reader_1v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VolumeReader, CDMS_HoffmullerReader, CDMS_SliceReader ] )
        reader_2v_modules = PlotPipelineHelper.find_modules_by_type( controller.current_pipeline, [ CDMS_VectorReader ] )
        reader_modules = reader_1v_modules + reader_2v_modules
        iVarModule = 0
        ops = []           
        for module in reader_modules:
            nInputs = 1 if module in reader_1v_modules else 2
            for iInput in range( nInputs ):
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
                    print>>sys.stderr, "Exception adding CDMSVaraible input:", str( err)
                    break
                                   
        try:
            action = core.db.action.create_action(ops)
            controller.add_new_action(action)
            controller.perform_action(action)
        except Exception, err:
            print " Error connecting CDMSVariable to workflow: ", str(err)
            traceback.print_exc()
        return action

    @staticmethod
    def addParameterChangesAction( pipeline, controller, vistrail, parent_version, aliases, cell_spec_iter ):
        param_changes = []
        newid = parent_version
        print "addParameterChangesAction()"
        print "Aliases: %s " % str( aliases )
        print "Pipeline Aliases: %s " % str( pipeline.aliases )
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
                 
        cell_modules = PlotPipelineHelper.find_modules_by_type( pipeline, [ MapCell3D ] )
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
            for j in range(plot_obj.cellnum):
                ccell = plot_obj.cells[j] 
                location = ccell.address_name if ccell.address_name else 'location%d' % (j+1)   # address_name defined using 'address_alias=...' in cell section of plot cfg file.
                cell_spec = "%s%s" % ( chr(ord('A') + col+j ), row+1)
                cell_specs.append( '%s!%s' % ( location, cell_spec ) )
            
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
    def show_configuration_widget( controller, version, plot_objs=[] ):
        from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper, CDMSPlotWidget
        pipeline = controller.vt_controller.vistrail.getPipeline(version)
        print " ------------ show_configuration_widget ----------------------------------"
        
        pmods = set()
        ConfigCommandMenuManager.reset()
        menu = ConfigCommandMenuManager.startNewMenu()
        for module in pipeline.module_list:
            pmod = ModuleStore.getModule(  module.id ) 
            if pmod:
                pmods.add(pmod)
                configFuncs = pmod.configurableFunctions.values()
                for configFunc in configFuncs:
                    action_key = str( configFunc.label )
                    config_key = configFunc.key               
                    ConfigCommandMenuManager.addAction( pmod, action_key, config_key ) 
                    
        menu1 = ConfigCommandMenuManager.startNewMenu() 
        for pmod in pmods:
            ConfigCommandMenuManager.addAction( pmod, 'Help', 'h' )
            ConfigCommandMenuManager.addAction( pmod, 'Colorbar', 'l' )
            ConfigCommandMenuManager.addAction( pmod, 'Reset', 'r' )
        
        config_widget = DV3DConfigControlPanel( menu, menu1 )
        ConfigCommandMenuManager.setCallbacks( config_widget.startConfig, config_widget.endConfig )
        for pmod in pmods:
            cmdList = pmod.getConfigFunctions( [ 'leveling' ] )
            for cmd in cmdList:
                ConfigCommandMenuManager.addConfigCommand( pmod, cmd )
        return config_widget

               
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
