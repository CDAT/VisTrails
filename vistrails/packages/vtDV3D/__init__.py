'''
Created on Dec 7, 2010

@author: tpmaxwel
'''

"""
   This package implements a VisTrails module called vtDV3D

"""
identifier = 'gov.nasa.nccs.vtdv3d'
name = 'vtDV3D'
version = '0.2.0'

#Configuration object
import sys
vtk_pkg_identifier = 'edu.utah.sci.vistrails.vtk'
from core.modules.basic_modules import Integer, Float, String, Boolean, Variant, Color
from core.bundles import py_import
hasMatplotlib = True
try:
    mpl_dict = {'linux-ubuntu': 'python-matplotlib', 'linux-fedora': 'python-matplotlib'}
    matplotlib = py_import('matplotlib', mpl_dict)
    pylab = py_import('pylab', mpl_dict)
    from SlicePlotModule import SlicePlotCell, SlicePlotConfigurationWidget
except Exception, e:
    print>>sys.stderr, "Matplotlib import Exception: %s" % e
    print "Matplotlib dependent features will be disabled."
    hasMatplotlib = False

def package_dependencies():
    return [ vtk_pkg_identifier, 'edu.utah.sci.vistrails.matplotlib' ]

def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('vtk'):
        raise core.requirements.MissingRequirement('vtk')
    if not core.requirements.python_module_exists('PyQt4'):
        raise core.requirements.MissingRequirement('PyQt4')
    import vtk 
    
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from core.modules.module_registry import get_module_registry

typeMapDict = {'int': Integer,
               'long': Integer,
               'float': Float,
               'char*': String,
               'char *': String,
               'string': String,
               'char': String,
               'const char*': String,
               'const char *': String}

def typeMap(name, package=None):
    """ typeMap(name: str) -> Module
    Convert from C/C++ types into VisTrails Module type
    
    """
    if package is None:
        package = vtk_pkg_identifier
    if type(name) == tuple:
        return [typeMap(x, package) for x in name]
    if name in typeMapDict:
        return typeMapDict[name]
    else:
        registry = get_module_registry()
        if not registry.has_descriptor_with_name(package, name):
            return None
        else:
            return registry.get_descriptor_by_name(package, name).module

from CDMSModule import *   
from PersistentModule import *
from vtUtilities import *
from HyperwallManager import HyperwallManager

def initialize(*args, **keywords):
    import core.modules.module_registry
    from VolumeSlicerModule import VolumeSlicer
    from VolumeRenderModule import VolumeRenderer
    from WorldMapModule import WorldFrame
#    from DemoDataModule import DemoData, DemoDataConfigurationWidget
    from DV3DCell import DV3DCell
    from InteractiveConfiguration import LayerConfigurationWidget
    from DV3DCell import DV3DCellConfigurationWidget
    from LevelSurfaceModule import LevelSurface 
    from CurtainPlotModule import CurtainPlot 
    from ResampleModule import Resample 
    from CDATUtilitiesModule import CDMS_CDATUtilities, CDATUtilitiesModuleConfigurationWidget
    from GradientModule import  Gradient
    from WorkflowModule import WorkflowModule
#        from packages.pylab.init import MplFigureManager
    from VectorCutPlaneModule import GlyphArrayCutPlane, StreamlineCutPlane 
    from VectorVolumeModule import VectorVolume 
    from packages.spreadsheet.basic_widgets import CellLocation
    from core.modules.basic_modules import Integer, Float, String, Boolean, Variant, Color
    import api
        
    reg = core.modules.module_registry.get_module_registry()   
    vtkAlgorithmOutputType = typeMap('vtkAlgorithmOutput')
    vtkImageDataType = typeMap('vtkImageData')
    reg.add_module( AlgorithmOutputModule, abstract=True) # hide_descriptor=True )       
    reg.add_module( AlgorithmOutputModule3D, abstract=True) # hide_descriptor=True )   
    reg.add_module( WorkflowModule, abstract=True) # hide_descriptor=True )   
    reg.add_module( CDMSDataset, abstract=True) # hide_descriptor=True )   
     
    reg.add_module( DV3DCell, configureWidgetType=DV3DCellConfigurationWidget, namespace='spreadsheet' ) 
    reg.add_input_port( DV3DCell, "volume", AlgorithmOutputModule3D  )   
    reg.add_input_port( DV3DCell, "cell_location", [ ( String, 'cell_coordinates' ) ], True )
    reg.add_input_port( DV3DCell, "world_cut", Integer, optional=True  )
    reg.add_input_port( DV3DCell, "map_border_size",  [ ( Float, 'border_in_degrees' ) ], optional=True  )
    reg.add_input_port( DV3DCell, "enable_basemap",  [ ( Boolean, 'enable' ) ], optional=True  )    
    reg.add_input_port( DV3DCell, "world_map", [ ( File, 'map_file' ), ( Integer, 'map_cut' ) ], optional=True  ) 
    reg.add_input_port( DV3DCell, "opacity", [ ( Float, 'value' ) ], optional=True  ) 
    reg.add_input_port( DV3DCell, "title", [ ( String, 'value' ) ], optional=True  ) 

#    reg.add_module( WorldFrame )
#    reg.add_input_port( WorldFrame, "world_cut", Integer, optional=True  )
#    reg.add_input_port( WorldFrame, "map_border_size",  [ ( Float, 'border_in_degrees' ) ], optional=True  )
#    reg.add_input_port( WorldFrame, "world_map", [ ( File, 'map_file' ), ( Integer, 'map_cut' ) ], optional=True  ) 
#    reg.add_input_port( WorldFrame, "opacity", [ ( Float, 'value' ) ], optional=True  ) 
#    reg.add_input_port( WorldFrame, "zscale", [ ( Float, 'value' ) ], optional=True  ) 
#    reg.add_input_port( WorldFrame, "volume", AlgorithmOutputModule3D  )
#    reg.add_output_port( WorldFrame, "volume", AlgorithmOutputModule3D ) 
#    WorldFrame.registerConfigurableFunctions( reg )

#    reg.add_module( CDMS_VCDATInterfaceSpecs, configureWidgetType=VCDATInterfaceWidget, namespace='cdms', hide_descriptor=True )
#    reg.add_input_port( CDMS_VCDATInterfaceSpecs, "zscale", [ ( Float, 'value' ) ], optional=True  ) 

#    reg.add_module( CDMS_VCDATInterface, namespace='cdms' )
#    reg.add_input_port( CDMS_VCDATInterface, "vcdatInputSpecs",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "vcdatCellSpecs",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port(  CDMS_VCDATInterface, "FileName",    [ ( String, 'FileName' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "VariableName",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "VariableName1",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "VariableName2",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "VariableName3",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Axes",    [ ( String, 'Axes' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Row",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Column",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Row1",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Column1",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Row2",    [ ( String, 'Value' ) ], True ) 
#    reg.add_input_port( CDMS_VCDATInterface, "Column2",    [ ( String, 'Value' ) ], True ) 
#    reg.add_output_port( CDMS_VCDATInterface, "executionSpecs", [ CDMS_VCDATInterfaceSpecs ] ) 
#    reg.add_output_port( CDMS_VCDATInterface, "cellLocation", [ ( String, 'cellLocation' ) ] ) 
#    reg.add_output_port( CDMS_VCDATInterface, "cellLocation1", [ ( String, 'cellLocation' ) ] ) 
#    reg.add_output_port( CDMS_VCDATInterface, "cellLocation2", [ ( String, 'cellLocation' ) ] ) 

    reg.add_module( CDMS_FileReader, configureWidgetType=CDMSDatasetConfigurationWidget, namespace='cdms' )
    reg.add_input_port(  CDMS_FileReader, "executionSpecs",    [ ( String, 'serializedConfiguration' ),  ], True ) 
    reg.add_input_port( CDMS_FileReader, "datasets",    [ ( String, 'serializedDatasetMap' ) ], True ) 
    reg.add_input_port( CDMS_FileReader, "datasetId",    [ ( String, 'currentDatasetId' ), ( Integer, 'version' ) ], True ) 
    reg.add_input_port( CDMS_FileReader, "timeRange",    [ ( Integer, 'startTimeIndex' ), ( Integer, 'endTimeIndex' ), ( Float, 'relativeStartTime' ), ( Float, 'relativeTimeStep' )], True )    
    reg.add_input_port( CDMS_FileReader, "roi",    [ ( Float, 'lon0' ), ( Float, 'lat0' ), ( Float, 'lon1' ), ( Float, 'lat1' ) ], True )    
    reg.add_input_port( CDMS_FileReader, "grid", [ ( String, 'selectedGrid' ) ], optional=True  ) 
    reg.add_input_port( CDMS_FileReader, "decimation", [ ( Integer, 'clientDecimation' ),  ( Integer, 'serverDecimation' ) ], optional=True  ) 
    reg.add_input_port( CDMS_FileReader, "zscale", [ ( Float, 'value' ) ], optional=True  ) 
    reg.add_output_port( CDMS_FileReader, "dataset", CDMSDataset ) 
    CDMS_FileReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_HoffmullerReader, configureWidgetType=CDMS_HoffmullerReaderConfigurationWidget, namespace='cdms' )
    reg.add_input_port( CDMS_HoffmullerReader, "dataset", CDMSDataset )      
    reg.add_input_port( CDMS_HoffmullerReader, "portData",   [ ( String, 'serializedPortData' ), ( Integer, 'version' ) ], True   ) 
    reg.add_output_port( CDMS_HoffmullerReader, "volume", AlgorithmOutputModule3D ) 
    CDMS_HoffmullerReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_VolumeReader, configureWidgetType=CDMS_VolumeReaderConfigurationWidget, namespace='cdms' )
    reg.add_input_port( CDMS_VolumeReader, "dataset", CDMSDataset )      
    reg.add_input_port( CDMS_VolumeReader, "portData",   [ ( String, 'serializedPortData' ), ( Integer, 'version' ) ], True   ) 
    reg.add_output_port( CDMS_VolumeReader, "volume", AlgorithmOutputModule3D ) 
    CDMS_VolumeReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_SliceReader, configureWidgetType=CDMS_SliceReaderConfigurationWidget, namespace='cdms' )
    reg.add_input_port( CDMS_SliceReader, "dataset", CDMSDataset )        
    reg.add_input_port( CDMS_SliceReader, "portData",   [ ( String, 'serializedPortData' ), ( Integer, 'version' ) ], True   ) 
    reg.add_output_port( CDMS_SliceReader, "slice", AlgorithmOutputModule ) 
    CDMS_SliceReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_VectorReader, configureWidgetType=CDMS_VectorReaderConfigurationWidget, namespace='cdms' )
    reg.add_input_port( CDMS_VectorReader, "dataset", CDMSDataset )        
    reg.add_input_port( CDMS_VectorReader, "portData",   [ ( String, 'serializedPortData' ), ( Integer, 'version' ) ], True   ) 
    reg.add_output_port( CDMS_VectorReader, "volume", AlgorithmOutputModule3D ) 
    CDMS_SliceReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_CDATUtilities, configureWidgetType=CDATUtilitiesModuleConfigurationWidget, namespace='cdms' )
    reg.add_input_port( CDMS_CDATUtilities, "dataset", CDMSDataset )   
    reg.add_input_port( CDMS_CDATUtilities, "task",  [ ( String, 'taskData' ) ], True   ) # [ ( String, 'taskName' ), ( String, 'inputVars' ), ( String, 'outputVars' ) ], True   ) 
    reg.add_output_port( CDMS_CDATUtilities, "dataset", CDMSDataset ) 

    reg.add_module( VolumeSlicer, namespace='vtk' )
    reg.add_output_port( VolumeSlicer, "slice",  AlgorithmOutputModule  )
    reg.add_input_port( VolumeSlicer, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( VolumeSlicer, "volume", AlgorithmOutputModule3D ) 
    VolumeSlicer.registerConfigurableFunctions( reg )

    reg.add_module( Gradient, namespace='vtk|experimental'  ) 
    reg.add_input_port( Gradient, "computeVorticity", Integer  )   
    reg.add_input_port( Gradient, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( Gradient, "volume", AlgorithmOutputModule3D ) 
    
    reg.add_module( GlyphArrayCutPlane, namespace='vtk'  )
    reg.add_input_port( GlyphArrayCutPlane, "colors", AlgorithmOutputModule3D  )
    reg.add_output_port( GlyphArrayCutPlane, "slice", AlgorithmOutputModule ) 
    reg.add_input_port( GlyphArrayCutPlane, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( GlyphArrayCutPlane, "volume", AlgorithmOutputModule3D ) 
    GlyphArrayCutPlane.registerConfigurableFunctions(  reg )

    reg.add_module( StreamlineCutPlane, namespace='vtk'  )
    reg.add_input_port( StreamlineCutPlane, "colors", AlgorithmOutputModule3D  )
    reg.add_input_port( StreamlineCutPlane, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( StreamlineCutPlane, "volume", AlgorithmOutputModule3D ) 
    StreamlineCutPlane.registerConfigurableFunctions(  reg )

    reg.add_module( VectorVolume, namespace='vtk'  )
    reg.add_input_port( VectorVolume, "colors", AlgorithmOutputModule3D  )
    reg.add_input_port( VectorVolume, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( VectorVolume, "volume", AlgorithmOutputModule3D ) 
    VectorVolume.registerConfigurableFunctions(  reg )
#    reg.add_module( Resample )
#    reg.add_input_port( Resample, "position", [ ( Float, 'x' ), ( Float, 'y' ), ( Float, 'z' ) ], True   )    
#    reg.add_output_port( Resample, "position",  [ ( Float, 'x' ), ( Float, 'y' ), ( Float, 'z' ) ], True  )
#    reg.add_input_port( Resample, "volume", AlgorithmOutputModule3D  )
#    reg.add_output_port( Resample, "volume", AlgorithmOutputModule3D ) 
#    Resample.registerConfigurableFunctions( reg )

    reg.add_module( CurtainPlot, namespace='vtk|experimental'  )
    reg.add_input_port( CurtainPlot, "path", ( File, 'path_file' )  ) 
    reg.add_input_port( CurtainPlot, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( CurtainPlot, "volume", AlgorithmOutputModule3D ) 
    CurtainPlot.registerConfigurableFunctions( reg )
       
#    reg.add_module( DemoData, configureWidgetType=DemoDataConfigurationWidget )
#    reg.add_input_port( DemoData, "dataset",    [ ( String, 'name' ), ] ) 
#    reg.add_input_port( DemoData, "maxNTimeSteps",   [ ( Integer, 'nts' ) ]   ) 
#    reg.add_output_port( DemoData, "volume", AlgorithmOutputModule3D ) 
#    DemoData.registerConfigurableFunctions( reg )
       
    reg.add_module( VolumeRenderer, namespace='vtk'  ) # , configureWidgetType=LayerConfigurationWidget  )
    reg.add_input_port( VolumeRenderer, "volume", AlgorithmOutputModule3D  )
#    reg.add_input_port( VolumeRenderer, "layer",   [ ( String, 'layer' ), ]   ) 
    reg.add_output_port( VolumeRenderer, "volume", AlgorithmOutputModule3D ) 
    VolumeRenderer.registerConfigurableFunctions( reg )

    reg.add_module( LevelSurface, namespace='vtk'   )
    reg.add_input_port( LevelSurface, "texture", AlgorithmOutputModule3D  )
    reg.add_input_port( LevelSurface, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( LevelSurface, "volume", AlgorithmOutputModule3D ) 
    reg.add_input_port( LevelSurface, "layer",   [ ( String, 'activeLayerName' ) ]   ) 
    LevelSurface.registerConfigurableFunctions( reg )

    if hasMatplotlib:
        reg.add_module( SlicePlotCell, namespace='spreadsheet', configureWidgetType=SlicePlotConfigurationWidget  )
        reg.add_input_port(  SlicePlotCell, "Location", CellLocation)
        reg.add_input_port(  SlicePlotCell, "slice", AlgorithmOutputModule  )
        reg.add_input_port(  SlicePlotCell, "plotType", [ ( String, 'fillType' ), ( String, 'contourType' ), ( Integer, 'numContours' ), ( Integer, 'version' ) ], True   )
        reg.add_output_port( SlicePlotCell, 'File', File)
        SlicePlotCell.registerConfigurableFunctions( reg )
    
    HyperwallManager.initialize()

def executeVistrail( *args, **kwargs ):
    import core.requirements, os
    core.requirements.check_pyqt4()
    from core.db.locator import FileLocator

    from PyQt4 import QtGui
    import gui.application
     
    try:
        optionsDict = kwargs.get( 'options', None )
        v = gui.application.start_application( optionsDict )
        if v != 0:
            if gui.application.VistrailsApplication:
                gui.application.VistrailsApplication.finishSession()
            sys.exit(v)
        app = gui.application.VistrailsApplication()
        resource_path = app.resource_path if hasattr( app, "resource_path" ) else None
        for vistrail_name in args:
            workflow_dir =  resource_path if resource_path else os.path.join( packagePath, "workflows" )
            vistrail_filename = os.path.join( workflow_dir, vistrail_name + '.vt' )
            print " Reading vistrail: ", vistrail_filename
            f = FileLocator(vistrail_filename)
            app.builderWindow.open_vistrail(f) 
    except SystemExit, e:
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        print "Uncaught exception on initialization: %s" % e
        sys.exit(e)
    except Exception, e:
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
    if (app.temp_configuration.interactiveMode and
        not app.temp_configuration.check('spreadsheetDumpCells')): 
        v = app.exec_()
     
    HyperwallManager.shutdown()   
    gui.application.stop_application()
    sys.exit(v)
   
