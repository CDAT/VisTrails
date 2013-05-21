import sys, os, cdms2
sys.path.append('/Developer/Projects/EclipseWorkspace/vistrails')
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


class PlotType:
    SLICER = 0
    VOLUME_RENDER = 1
    HOV_SLICER = 2
    HOV_VOLUME_RENDER = 3
    ISOSURFACE = 4
    CURTAIN = 4

class UVCDAT_API():
    
    def __init__(self):
        from core.requirements import MissingRequirement, check_all_vistrails_requirements
        disable_lion_restore() 
        self.inputId = 0
        try:
            check_all_vistrails_requirements()
        except MissingRequirement, e:
            msg = ("VisTrails requires %s to properly run.\n" % e.requirement)
            debug.critical("Missing requirement", msg)
            sys.exit(1)
        self.dv3dpkg = 'gov.nasa.nccs.vtdv3d'
        self.start()

    def __del__(self ):
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper            
        DV3DPipelineHelper.clear_input_variables()
        
    def start(self): 
        try:
            v =  gui.application.start_application()
            self.app = gui.application.get_vistrails_application()                
        except SystemExit, e:
            self.app = gui.application.get_vistrails_application()
            if self.app: self.app.finishSession()
            sys.exit(e)
        except Exception, e:
            self.app = gui.application.get_vistrails_application()
            if self.app: self.app.finishSession()
            print "Uncaught exception on initialization: %s" % e
            import traceback
            traceback.print_exc()
            sys.exit(255)

#    def start_application(self, optionsDict=None):
#        from gui.application import VistrailsApplicationSingleton, get_vistrails_application, set_vistrails_application
#        VistrailsApplication = get_vistrails_application()
#        VistrailsApplication = VistrailsApplicationSingleton()
#        set_vistrails_application(VistrailsApplication)
#        x = VistrailsApplication.init(optionsDict)
#        if x == True: return 0
#        else:         return 1
        
    def newModule(self, module_name, **args ):
        registry = get_module_registry()
        controller = self.app.get_controller()
        self.dv3dpkg
        package_name = args.get('package', self.dv3dpkg )
        namespace = args.get('ns', '' )
        descriptor = registry.get_descriptor_by_name( package_name, module_name, namespace )
        return controller.create_module_from_descriptor(descriptor)
    
    def newConnection(self, source, source_port, target, target_port):
        controller = self.app.get_controller()
        c = controller.create_connection(source, source_port, target, target_port)
        return c
    
    def setPortValue(self, module, port_name, value):
        controller = self.app.get_controller()
        function = controller.create_function(module, port_name, [str(value)])
        module.add_function(function)
        return
    
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
        
    def createPlot( self, **args ): 
        from packages.vtDV3D.PlotPipelineHelper import DV3DPipelineHelper            
        type = args.get( 'type', PlotType.SLICER )
        input = args.get( 'input', None ) 
        inputId = self.getNewInputId()
        name = args.get( 'name', "input-%s" % inputId ) 
        DV3DPipelineHelper.add_input_variable( inputId, input )
        
        variableSource = self.newModule('CDMSVariableSource', ns='cdms' )
        self.setPortValue( variableSource, "inputId", inputId )
        self.addToPipeline( [variableSource] )
                     
        variable = self.newModule( 'CDMSTranisentVariable', ns='cdms' )
        self.setPortValue( variable, "name", name )
        source_to_variable = self.newConnection( variableSource, 'self', variable, 'source' )   
        source_to_variable_axes = self.newConnection( variableSource, 'axes', variable, 'axes' )   
        self.layoutAndAdd( variable, [ source_to_variable, source_to_variable_axes ] )

        if ( type == PlotType.HOV_VOLUME_RENDER ) or ( type == PlotType.HOV_SLICER ):
            volumeReader = self.newModule('CDMS_HoffmullerReader', ns='cdms' )
            variable_to_reader = self.newConnection(variable, 'self', volumeReader, 'variable')        
        else:                 
            volumeReader = self.newModule('CDMS_VolumeReader', ns='cdms' )
            variable_to_reader = self.newConnection(variable, 'self', volumeReader, 'variable')   
             
        self.layoutAndAdd( volumeReader, variable_to_reader )
        
        if (type == PlotType.SLICER) or (type == PlotType.HOV_SLICER):
            plotter = self.newModule('VolumeSlicer', ns='vtk' )
            reader_to_plotter = self.newConnection(volumeReader, 'volume', plotter, 'volume')        
        elif type == PlotType.VOLUME_RENDER or (type == PlotType.HOV_VOLUME_RENDER):
            plotter = self.newModule('VolumeRenderer', ns='vtk' )
            reader_to_plotter = self.newConnection(volumeReader, 'volume', plotter, 'volume')        
        elif type == PlotType.ISOSURFACE:
            plotter = self.newModule('LevelSurface', ns='vtk' )
            reader_to_plotter = self.newConnection(volumeReader, 'volume', plotter, 'volume')        
        elif type == PlotType.CURTAIN:
            plotter = self.newModule('CurtainPlot', ns='vtk' )
            reader_to_plotter = self.newConnection(volumeReader, 'volume', plotter, 'volume')        
        else:
            print>>sys.stderr, "Error, unrecognized plot type."
            return

        self.layoutAndAdd( plotter, reader_to_plotter )
        
        cellModule = self.newModule('MapCell3D', ns='spreadsheet' )
        plotter_to_cell = self.newConnection( plotter, 'volume', cellModule, 'volume')
        self.layoutAndAdd( cellModule, plotter_to_cell )

        controller = self.app.get_controller()
        proj_controller = self.app.uvcdatWindow.get_current_project_controller()
#        cell.current_parent_version = controller.current_version
        proj_controller.execute_plot( controller.current_version )
#        proj_controller.update_plot_configure(sheetName, row, column)
        
    def run(self):
        v = self.app.exec_()
        gui.application.stop_application()        
        
if __name__ == '__main__':
    file_url = "/Developer/Data/AConaty/comp-ECMWF/ecmwf.xml"
    varname = "Temperature"
    cdmsfile = cdms2.open( file_url )
    input_var = cdmsfile( varname )
    uvcdat_api = UVCDAT_API()
    uvcdat_api.createPlot( input=input_var )
    uvcdat_api.run()
   

##============================ start script =====================================
#
##start with http file module
#httpFA = newModule(httppkg, 'HTTPFile')
#url = 'http://www.vistrails.org/download/download.php?type=DATA&id=gktbhFA.vtk'
#setPortValue(httpFA, 'url', url)
#
##add to pipeline
#addToPipeline([httpFA])
#
##create data set reader module for the gktbhFA.vtk file
#dataFA = newModule(vtkpkg, 'vtkDataSetReader')
#
##connect modules
#http_dataFA = newConnection(httpFA, 'file', dataFA, 'SetFile')
#
##layout new modules before adding
#layoutAndAdd(dataFA, http_dataFA)
#
##add contour filter
#contour = newModule(vtkpkg, 'vtkContourFilter')
#setPortValue(contour, 'SetValue', (0,0.6))
#dataFA_contour = newConnection(dataFA, 'GetOutputPort0',
#                               contour, 'SetInputConnection0')
#layoutAndAdd(contour, dataFA_contour)
#
##add normals, stripper, and probe filter
#normals = newModule(vtkpkg, 'vtkPolyDataNormals') #GetOutputPort0
#setPortValue(normals, 'SetFeatureAngle', 60.0)
#contour_normals = newConnection(contour, 'GetOutputPort0', 
#                                normals, 'SetInputConnection0')
#layoutAndAdd(normals, contour_normals)
#
#stripper = newModule(vtkpkg, 'vtkStripper') #GetOutputPort0
#normals_stripper = newConnection(normals, 'GetOutputPort0',
#                                 stripper, 'SetInputConnection0')
#layoutAndAdd(stripper, normals_stripper)
#
#probe = newModule(vtkpkg, 'vtkProbeFilter') #same
#stripper_probe = newConnection(stripper, 'GetOutputPort0',
#                               probe, 'SetInputConnection0')
#layoutAndAdd(probe, stripper_probe)
#
##build other branch in reverse
#colors = newModule(vtkpkg, 'vtkImageMapToColors')
#setPortValue(colors, 'SetOutputFormatToRGBA', True)
#colors_probe = newConnection(colors, 'GetOutputPort0',
#                             probe, 'SetInputConnection1')
#layoutAndAdd(colors, colors_probe)
#
#lookup = newModule(vtkpkg, 'vtkLookupTable')
#setPortValue(lookup, 'SetHueRange', (0.0,0.8))
#setPortValue(lookup, 'SetSaturationRange', (0.3,0.7))
#setPortValue(lookup, 'SetValueRange', (1.0,1.0))
#lookup_colors = newConnection(lookup, 'self',
#                              colors, 'SetLookupTable')
#layoutAndAdd(lookup, lookup_colors)
#
#dataL123 = newModule(vtkpkg, 'vtkDataSetReader')
#dataL123_colors = newConnection(dataL123, 'GetOutputPort0',
#                                colors, 'SetInputConnection0')
#layoutAndAdd(dataL123, dataL123_colors)
#
#httpL123 = newModule(httppkg, 'HTTPFile')
#url = 'http://www.vistrails.org/download/download.php?type=DATA&id=gktbhL123.vtk'
#setPortValue(httpL123, 'url', url)
#httpL123_dataL123 = newConnection(httpL123, 'file',
#                                  dataL123, 'SetFile')
#layoutAndAdd(httpL123, httpL123_dataL123)
#
##finish bottom section
#mapper = newModule(vtkpkg, 'vtkPolyDataMapper')
#setPortValue(mapper, 'ScalarVisibilityOn', True)
#probe_mapper = newConnection(probe, 'GetOutputPort0',
#                             mapper, 'SetInputConnection0')
#layoutAndAdd(mapper, probe_mapper)
#
#actor = newModule(vtkpkg, 'vtkActor')
#mapper_actor = newConnection(mapper, 'self',
#                             actor, 'SetMapper')
#layoutAndAdd(actor, mapper_actor)
#
#prop = newModule(vtkpkg, 'vtkProperty')
#setPortValue(prop, 'SetDiffuseColor', (1.0,0.49,0.25))
#setPortValue(prop, 'SetOpacity', 0.7)
#setPortValue(prop, 'SetSpecular', 0.3)
#setPortValue(prop, 'SetSpecularPower', 2.0)
#prop_actor = newConnection(prop, 'self',
#                           actor, 'SetProperty')
#layoutAndAdd(prop, prop_actor)
#
#renderer = newModule(vtkpkg, 'vtkRenderer')
#setPortValue(renderer, 'SetBackgroundWidget', 'white')
#actor_renderer = newConnection(actor, 'self',
#                               renderer, 'AddActor')
#layoutAndAdd(renderer, actor_renderer)
#
#camera = newModule(vtkpkg, 'vtkCamera')
#setPortValue(camera, 'SetFocalPoint', (15.666,40.421,39.991))
#setPortValue(camera, 'SetPosition', (207.961,34.197,129.680))
#setPortValue(camera, 'SetViewUp', (0.029, 1.0, 0.008))
#camera_renderer = newConnection(camera, 'self',
#                                renderer, 'SetActiveCamera')
#layoutAndAdd(camera, camera_renderer)
#
##this is missing when running from script??
## cell = newModule(vtkpkg, 'VTKCell')
## cell = newModule(vtkpkg, 'vtkCell')
## renderer_cell = newConnection(renderer, 'self',
##                               cell, 'AddRenderer')
## layoutAndAdd(cell, renderer_cell)
#
##write to file
#locator = vistrails.core.db.locator.FileLocator('brain_no_gaps_preserve_order.vt')
#controller.write_vistrail(locator)