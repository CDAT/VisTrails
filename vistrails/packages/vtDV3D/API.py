import sys, os, cdms2
#path_root = os.path.dirname( os.path.dirname( os.path.dirname(os.path.abspath(__file__))))
#sys.path.append( path_root )
from PyQt4 import QtGui, QtCore
import gui.application
from core.modules.module_registry import get_module_registry

def disable_lion_restore():
    """ Prevent Mac OS 10.7 to restore windows state since it would
    make Qt 4.7.3 unstable due to its lack of handling Cocoa's Main
    Window. """
    import platform
    if platform.system()!='Darwin': return
    release = platform.mac_ver()[0].split('.')
    if len(release)<2: return
    major = int(release[0])
    minor = int(release[1])
    if major*100+minor<107: return
    import os
    ssPath = os.path.expanduser('~/Library/Saved Application State/org.vistrails.savedState')
    if os.path.exists(ssPath):
        os.system('rm -rf "%s"' % ssPath)
    os.system('defaults write org.vistrails NSQuitAlwaysKeepsWindows -bool false')

def startup_app(): 
    from core.requirements import MissingRequirement, check_all_vistrails_requirements
    disable_lion_restore() 
    try:
        check_all_vistrails_requirements()
    except MissingRequirement, e:
        msg = ("VisTrails requires %s to properly run.\n" % e.requirement)
        debug.critical("Missing requirement", msg)
        sys.exit(1)
    try:
        v =  gui.application.start_application()
    except SystemExit, e:
        app = gui.application.get_vistrails_application()
        if app: app.finishSession()
        sys.exit(e)
    except Exception, e:
        app = gui.application.get_vistrails_application()
        if app: app.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)

class PlotType:
    SLICER = 0
    VOLUME_RENDER = 1
    HOV_SLICER = 2
    HOV_VOLUME_RENDER = 3
    ISOSURFACE = 4
    CURTAIN = 5

class UVCDAT_API():
    
    def __init__(self):
        self.inputId = 0
        self.plotIndex = -1
        self.sheetName = None
        self.row = 0
        self.col = 0
        self.cell_address = "%s%s" % ( chr(ord('A') + self.col ), self.row+1)
        self.dv3dpkg = 'gov.nasa.nccs.vtdv3d'
        self.app = gui.application.get_vistrails_application()                

    def __del__(self ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper            
        DV3DPipelineHelper.clear_input_variables()
                
    def newModule(self, module_name, **args ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper 
        registry = get_module_registry()
        controller = self.app.get_controller()
        package_name = args.get('package', self.dv3dpkg )
        namespace = args.get('ns', '' )
        descriptor = registry.get_descriptor_by_name( package_name, module_name, namespace )
        module = controller.create_module_from_descriptor(descriptor)
        DV3DPipelineHelper.add_module( module.id, self.sheetName, self.cell_address )
        ports = args.get( 'ports', {} )
        for portItem in ports.items():
            self.setPortValue( module, portItem[0], portItem[1] )      
        return module
    
    def newConnection(self, source, source_port, target, target_port):
        controller = self.app.get_controller()
        c = controller.create_connection(source, source_port, target, target_port)
        return c
    
    def setPortValue(self, module, port_name, value_list):
        controller = self.app.get_controller()
        str_value_list = [ str(val) for val in value_list ]
        function = controller.create_function( module, port_name, str_value_list )
        module.add_function(function)  
        op = controller.update_function_ops( module, port_name, str_value_list )      
        self.port_ops.extend( op )
    
    def addToPipeline(self, items, ops=[]):
        import core.db.action
        controller = self.app.get_controller()
        item_ops = [('add',item) for item in items]
        action = core.db.action.create_action(item_ops + ops)
        controller.add_new_action(action)
        version = controller.perform_action(action)
        controller.change_selected_version(version)
    
    def layoutAndAdd(self, module, connections):
        controller = self.app.get_controller()
        if not isinstance(connections, list): connections = [connections]
        ops = controller.layout_modules_ops( preserve_order=True, no_gaps=True, new_modules=[module], new_connections=connections )
        self.addToPipeline([module] + connections, ops)

    def loadVistrail( self, vistrail_name, **kwargs ):
        resource_path = kwargs.get( 'dir', None )
        version = kwargs.get( 'version', None )
        if not resource_path:
            resource_path = self.app.resource_path if hasattr( app, "resource_path" ) else None
        for vistrail_name in args:
            workflow_dir =  resource_path if resource_path else os.path.join( packagePath, "workflows" )
            vistrail_filename = os.path.join( workflow_dir, vistrail_name + '.vt' )
            self.loadVistrailFile( vistrail_filename, version )
            
    def loadVistrailFile( self, vistrail_filename, version=None ):
        from core.db.locator import FileLocator
        print " Reading vistrail: ", vistrail_filename
        f = FileLocator(vistrail_filename)
        self.app.builderWindow.open_vistrail_without_prompt( f, version, True ) 
        
    def getNewInputId(self):
        self.inputId = self.inputId + 1
        return str( self.inputId )
    
    def getPlotName( self, type ):
        if   type == PlotType.SLICER:               return "Slicer"
        elif type == PlotType.VOLUME_RENDER:        return "Volume Render"
        elif type == PlotType.HOV_SLICER:           return "Hovmoller Slicer"
        elif type == PlotType.HOV_VOLUME_RENDER:    return "Hovmoller Volume"
        elif type == PlotType.ISOSURFACE:           return "IsoSurface"
        elif type == PlotType.CURTAIN:              return "Curtain Plot"
        return ""
    
    def initPlot(self):
        proj_controller = self.app.uvcdatWindow.get_current_project_controller()
        self.plotIndex = self.plotIndex + 1
        self.inputId = 0
        self.variables = []
        self.port_ops = []
        self.sheetName = proj_controller.current_sheetName
        self.row = self.plotIndex % 2
        self.col = self.plotIndex / 2
        self.cell_address = "%s%s" % ( chr(ord('A') + self.col ), self.row+1)

    def initVariables(self):
        proj_controller = self.app.uvcdatWindow.get_current_project_controller()
        self.plotIndex = self.plotIndex + 1
        self.inputId = 0
        self.variables = []
        self.port_ops = []
        
    def initInput( self, inputVariable ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper 
        inputId = self.getNewInputId()
        DV3DPipelineHelper.add_input_variable( inputId, inputVariable )
        return inputVariable.id, inputId

    def finalizePlot( self, plot_name ):
        from packages.vtDV3D.CDMS_VariableReaders import CDMSTransientVariable
        from core.db.action import create_action
        proj_controller = self.app.uvcdatWindow.get_current_project_controller()
        controller = self.app.get_controller()
        plot = proj_controller.plot_registry.add_plot( plot_name, 'DV3D', None, None )
        action = create_action( self.port_ops ) 
        controller.add_new_action(action)
        controller.perform_action(action)
        controller.select_latest_version()
        current_version = controller.current_version
        proj_controller.plot_was_dropped( (plot, self.sheetName, self.row, self.col) )
        proj_controller.execute_plot( current_version )
        controller.change_selected_version( current_version )
        proj_controller.update_plot_configure( self.sheetName, self.row, self.col )
        cell = proj_controller.sheet_map[ self.sheetName ][ ( self.row, self.col ) ]
        cell.current_parent_version = current_version  
        
        for ( name, var ) in self.variables:
            dvar = CDMSTransientVariable.from_module( var )
            proj_controller.defined_variables[ name ] = dvar
        proj_controller.emit( QtCore.SIGNAL("update_cell"), self.sheetName, self.row, self.col, None, None, 'DV3D', current_version )

    def finalizeVariables( self ):
        from packages.vtDV3D.CDMS_VariableReaders import CDMSTransientVariable
        from core.db.action import create_action
        proj_controller = self.app.uvcdatWindow.get_current_project_controller()
        controller = self.app.get_controller()
        action = create_action( self.port_ops ) 
        controller.add_new_action(action)
        controller.perform_action(action)
        controller.select_latest_version()
        current_version = controller.current_version        
        for ( name, var ) in self.variables:
            dvar = CDMSTransientVariable.from_module( var )
            proj_controller.defined_variables[ name ] = dvar
        
    def newVariableModule( self, cdmsVariable ):
        name, inputId = self.initInput( cdmsVariable )                     
        variable = self.newModule( 'CDMSTransientVariable', ns='cdms' )
        self.setPortValue( variable, "name", [ name ] )
        self.setPortValue( variable, "inputId", [ inputId ] )
        self.addToPipeline( [ variable ] )
        self.app.uvcdatWindow.dockVariable.widget().addVariable( cdmsVariable )
        self.variables.append( ( name, variable ) )
        return variable
        
    def createPlot( self, **args ): 
        type = args.get( 'type', PlotType.SLICER )
        viz_parms = args.get( 'viz_parms', {} )
        self.initPlot()
        
        if ( type == PlotType.HOV_VOLUME_RENDER ) or ( type == PlotType.HOV_SLICER ):
            volumeReader = self.newModule('CDMS_HoffmullerReader', ns='cdms' )
        else:                 
            volumeReader = self.newModule('CDMS_VolumeReader', ns='cdms' )
        
        input_list = args.get( 'inputs', [] ) 
        variable_to_reader_con_list = []
        for cdmsVariable in input_list:
            variable = self.newVariableModule( cdmsVariable )           
            variable_to_reader = self.newConnection(variable, 'self', volumeReader, 'variable') 
            variable_to_reader_con_list.append( variable_to_reader )       
            
        self.layoutAndAdd( volumeReader, variable_to_reader_con_list )
        
        reader_to_plotter_cons = []
        if (type == PlotType.SLICER) or (type == PlotType.HOV_SLICER):
            plotter = self.newModule('VolumeSlicer', ns='vtk', ports=viz_parms )
            reader_to_plotter_cons.append( self.newConnection(volumeReader, 'volume', plotter, 'volume') )  
            if len( input_list ) > 1: 
                reader_to_plotter_cons.append( self.newConnection(volumeReader, 'volume', plotter, 'contours') )      
        elif type == PlotType.VOLUME_RENDER or (type == PlotType.HOV_VOLUME_RENDER):
            plotter = self.newModule('VolumeRenderer', ns='vtk', ports=viz_parms )
            reader_to_plotter_cons.append( self.newConnection(volumeReader, 'volume', plotter, 'volume') )       
        elif type == PlotType.ISOSURFACE:
            plotter = self.newModule('LevelSurface', ns='vtk', ports=viz_parms )
            reader_to_plotter_cons.append( self.newConnection(volumeReader, 'volume', plotter, 'volume') )       
            if len( input_list ) > 1: 
                reader_to_plotter_cons.append( self.newConnection(volumeReader, 'volume', plotter, 'texture') )      
        elif type == PlotType.CURTAIN:
            plotter = self.newModule('CurtainPlot', ns='vtk', ports=viz_parms )
            reader_to_plotter_cons.append( self.newConnection(volumeReader, 'volume', plotter, 'volume') )       
        else:
            print>>sys.stderr, "Error, unrecognized plot type."
            return

        self.layoutAndAdd( plotter, reader_to_plotter_cons )
        
        cellModule = self.newModule('MapCell3D', ns='spreadsheet' )
        plotter_to_cell = self.newConnection( plotter, 'volume', cellModule, 'volume')
        self.layoutAndAdd( cellModule, plotter_to_cell )
        
        self.finalizePlot( self.getPlotName(type) )

    def inputVariables( self, input_list ):
        self.initVariables() 
        for cdmsVariable in input_list:
            variable = self.newVariableModule( cdmsVariable )  
        self.finalizeVariables()          
        
    def run(self):
        v = self.app.exec_()
        gui.application.stop_application()        
        
if __name__ == '__main__':
    cdmsfile = cdms2.open('~/data/AConaty/comp-ECMWF/ecmwf.xml')
#    cdmsfile = cdms2.open('/Developer/Data/AConaty/comp-ECMWF/ecmwf.xml')
    Temperature = cdmsfile('Temperature')
    Temperature = Temperature(lat=(90.0, -90.0),isobaric=(1000.0, 10.0),lon=(0.0, 359.0),time=('2011-5-1 0:0:0.0', '2011-5-1 18:0:0.0'),)
    axesOperations = eval("{'lat': 'def', 'isobaric': 'def', 'lon': 'def', 'time': 'def'}")
    for axis in list(axesOperations):
        if axesOperations[axis] == 'sum':
            Temperature = cdutil.averager(Temperature, axis='(%s)'%axis, weight='equal', action='sum')
        elif axesOperations[axis] == 'avg':
            Temperature = cdutil.averager(Temperature, axis='(%s)'%axis, weight='equal')
        elif axesOperations[axis] == 'wgt':
            Temperature = cdutil.averager(Temperature, axis='(%s)'%axis)
        elif axesOperations[axis] == 'gtm':
            Temperature = genutil.statistics.geometricmean(Temperature, axis='(%s)'%axis)
        elif axesOperations[axis] == 'std':
            Temperature = genutil.statistics.std(Temperature, axis='(%s)'%axis)
    port_map = {'zScale': [2.0, 4.0, 1, 0.0, 1.0], 'colormap': ['jet', 0, 0, 1], 'colorScale': [208.39464294433594, 304.16563934326172, 1, 0.0, 1.0]}

    startup_app()
    uvcdat_api = UVCDAT_API()
#    uvcdat_api.createPlot( inputs=[Temperature], type=PlotType.SLICER, viz_parms=port_map )  # This will create a plot for you
    uvcdat_api.inputVariables( [Temperature] )    # This will import the variable into uvcdat without creating a plot for you
    uvcdat_api.run()
