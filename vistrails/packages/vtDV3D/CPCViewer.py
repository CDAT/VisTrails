'''
Created on Oct 29, 2013

@author: tpmaxwel
'''
from packages.vtDV3D.PersistentModule import *
from packages.CPCViewer.PointCloudViewer import CPCPlot, kill_all_zombies
from  packages.vtDV3D.CDMS_VariableReaders import  CDMSReaderConfigurationWidget

class PM_CPCViewer(PersistentVisualizationModule):
    """
        This module wraps the CPCViewer package. 

    """       
    
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, **args)
        self.primaryInputPorts = [ 'pointCloud' ] 
        self.n_overview_points = 500000
        self.grid_file = None
        self.data_file = None
        self.varname = None
        self.height_varname = None
        self.plotter = None

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
            self.data_file = md[ 'dsid' ]
            self.set3DOutput( name="pointCloud" )
        
    def activateEvent( self, caller, event ):
        PersistentVisualizationModule.activateEvent( self, caller, event )
        if self.renwin <> None:
            if self.plotter == None:
                self.plotter = CPCPlot( self.renwin )  
                self.plotter.init( init_args = ( self.grid_file, self.data_file, self.varname, self.height_varname ), n_overview_points=self.n_overview_points ) # , n_subproc_points=100000000 )
                self.render()
        
from packages.vtDV3D.WorkflowModule import WorkflowModule

class CPCViewer(WorkflowModule):
    
    PersistentModuleClass = PM_CPCViewer
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
        
class CPCViewerConfigurationWidget(DV3DConfigurationWidget):

    def __init__(self, module, controller, parent=None):
        DV3DConfigurationWidget.__init__(self, module, controller, CDMSDataType.Hoffmuller, parent)

    def getParameters( self, module ):
        CDMSReaderConfigurationWidget.getParameters( self, module ) 

kill_all_zombies()