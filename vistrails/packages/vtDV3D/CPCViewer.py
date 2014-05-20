'''
Created on Oct 29, 2013

@author: tpmaxwel
'''
from packages.vtDV3D.PersistentModule import *
from packages.CPCViewer.PointCloudViewer import CPCPlot
from packages.CPCViewer.ControlPanel import ConfigurationWidget
from packages.vtDV3D.CDMS_VariableReaders import  CDMSReaderConfigurationWidget
from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper            
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def get_vt_decl( val_decl_str ):
    import core.modules.basic_modules as basic_modules
    if val_decl_str == "bool":  return basic_modules.Boolean 
    if val_decl_str == "int":   return basic_modules.Integer 
    if val_decl_str == "float": return basic_modules.Float 
    if val_decl_str == "str":   return basic_modules.String 

class PM_CPCViewer(PersistentVisualizationModule):
    """
        This module wraps the CPCViewer package. 

    """
    PortSpecs = None       
    
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, **args)
        self.primaryInputPorts = [ 'pointCloud' ] 
        self.n_overview_points = 500000
        self.grid_file = None
        self.data_file = None
        self.varname = None
        self.height_varname = None
        self.addConfigurableFunctions()
#         try:
#             self.addConfigurableFunctions()
#         except Exception, err:
#             print str(err)
        self.plotter = None

    def processKeyEvent( self, key, caller=None, event=None ):
        PersistentVisualizationModule.processKeyEvent( self, key, caller, event )
        shift = caller.GetShiftKey()
        alt   = caller.GetAltKey()
        ctrl  = caller.GetControlKey()
        mods = Qt.ShiftModifier if shift else 0
        eventArgs = [ caller.GetKeyCode(), caller.GetKeySym(), mods ]
        self.plotter.onKeyEvent( eventArgs )
#        print "Process Key Event: key = %s, mods = %s" % ( key, str((shift,alt,ctrl)) )

    def initializeInputs( self, **args ):        
        isAnimation = args.get( 'animate', False )
        restarting = args.get( 'restarting', False )
        self.newDataset = False
        inputPorts = self.getPrimaryInputPorts()
        for inputIndex, inputPort in enumerate( inputPorts ):
            ispec = InputSpecs()
            self.inputSpecs[ inputIndex ] = ispec
#            inputList = self.getPrimaryInputList( port=inputPort, **args )
            inMod = self.getPrimaryInput( port=inputPort, **args )
            if inMod: ispec.inputModule = inMod
        
    def execute(self, **args ):
        self.initializeRendering()
        cdms_vars = self.getInputValues( "pointCloud"  ) 
        if cdms_vars and len(cdms_vars):
            cdms_var = cdms_vars.pop(0)
            mdList = extractMetadata( cdms_var.fieldData )
            md = mdList[0]
            self.varname = md[ 'varName' ]
            self.data_file = md[ 'file' ]
            self.set3DOutput( name="pointCloud" )
        
    def activateEvent( self, caller, event ):
        from gui.application import get_vistrails_application
        PersistentVisualizationModule.activateEvent( self, caller, event )
        if self.renwin <> None:
            if self.plotter == None:
                self.plotter = CPCPlot( self.renwin ) 
                op = None 
                self.plotter.init( init_args = ( self.grid_file, self.data_file, self.varname, self.height_varname, op ), n_overview_points=self.n_overview_points ) # , n_subproc_points=100000000 )
                self.getConfigWidget()
                DV3DPipelineHelper.denoteCPCViewer( self.moduleID )
                app = get_vistrails_application()
                app.connect( app, QtCore.SIGNAL("aboutToQuit()"), self.plotter.terminate ) 
                self.render()       

    def closeCPCWidget( self, parmRecList ):
        DV3DPipelineHelper.disconnectCPCWidgets()
        self.change_parameters( parmRecList )
        for parmRec in parmRecList:
            self.setParameter( parmRec[0],  parmRec[1] ) 
        
    def addConfigurableFunctions( self ):
        if PM_CPCViewer.PortSpecs == None:
            config_widget = ConfigurationWidget()
            config_widget.build()
            PM_CPCViewer.PortSpecs = config_widget.getPersistentParameterSpecs()
        for port_spec in PM_CPCViewer.PortSpecs:
            name = port_spec[0]
            values_decl_list = port_spec[1]
            signature = [ get_vt_decl(val_decl_str) for val_decl_str in values_decl_list]
            self.configurableFunctions[name] = ConfigurableFunction( name, signature )
                       
    def getConfigWidget( self ):
        self.config_widget = ConfigurationWidget()
        self.config_widget.build()
        QObject.connect( self.config_widget, QtCore.SIGNAL("ConfigCmd"), self.plotter.processConfigCmd )
        QObject.connect( self.config_widget, QtCore.SIGNAL("Close"), self.closeCPCWidget )
    #    configDialog.connect( g, QtCore.SIGNAL("UpdateGui"), configDialog.externalUpdate )
        for port_spec in PM_CPCViewer.PortSpecs:
            pname = port_spec[0]
            parm_values = self.getInputValue( pname )
            if parm_values <> None:
#                print "*** Initialize Parameter %s: %s " % ( pname, str(parm_values) );
                self.config_widget.initialize( pname, parm_values )
        self.config_widget.activate()
        sys.stdout.flush()
        return self.config_widget
    
    def getPlotter(self):
        return self.plotter
     
from packages.vtDV3D.WorkflowModule import WorkflowModule

class CPCViewer(WorkflowModule):
    
    PersistentModuleClass = PM_CPCViewer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        print " "
                
class CPCViewerConfigurationWidget(StandardModuleConfigurationWidget):

    def __init__(self, module, controller, title, parent=None):
        StandardModuleConfigurationWidget.__init__(self, module, controller, parent)
        self.setWindowTitle( title )
        self.moduleId = module.id
#        self.pmod = module.module_descriptor.module.forceGetPersistentModule( module.id ) # self.module_descriptor.module.forceGetPersistentModule( module.id )
        self.getParameters( module )        
        self.cfg_widget = ConfigurationWidget()    
        self.setLayout( QVBoxLayout() )
#        self.layout().setMargin(0)
#        self.layout().setSpacing(0)

        self.tabbedWidget = QTabWidget()
        self.layout().addWidget( self.cfg_widget ) 
#        self.createButtonLayout() 
        
#        self.cfg_widget.build()
#        self.cfg_widget.activate()

    def getParameters( self, module ):
        pass
