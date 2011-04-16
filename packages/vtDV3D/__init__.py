'''
Created on Dec 7, 2010

@author: tpmaxwel
'''

"""
   This package implements a VisTrails module called vtDV3D

"""
identifier = 'gov.nasa.nccs.vtdv3d'
name = 'vtDV3D'
version = '0.1.0'

#Configuration object
from vtDV3DConfiguration import configuration

vtk_pkg_identifier = 'edu.utah.sci.vistrails.vtk'
from core.modules.basic_modules import Integer, Float, String, Boolean, Variant, Color
from core.bundles import py_import
try:
    mpl_dict = {'linux-ubuntu': 'python-matplotlib', 'linux-fedora': 'python-matplotlib'}
    matplotlib = py_import('matplotlib', mpl_dict)
    pylab = py_import('pylab', mpl_dict)
except Exception, e:
    print>>sys.stderr, "Matplotlib import Exception: %s" % e

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

def initialize(*args, **keywords):
    import core.modules.module_registry
    from VolumeSlicerModule import VolumeSlicer
    from VolumeRenderModule import VolumeRenderer
    from WorldMapModule import WorldFrame
#    from DemoDataModule import DemoData, DemoDataConfigurationWidget
    from DV3DCell import DV3DCell
    from InteractiveConfiguration import LayerConfigurationWidget
    from LevelSurfaceModule import LevelSurface 
    from CurtainPlotModule import CurtainPlot 
    from ResampleModule import Resample 
    from CDATUtilitiesModule import CDMS_CDATUtilities, CDATUtilitiesModuleConfigurationWidget
    from GradientModule import  Gradient
    from WorkflowModule import WorkflowModule
    from SlicePlotModule import SlicePlot
    from TestModule import AddTest
    from VectorCutPlaneModule import VectorCutPlane 
    from packages.pylab.init import MplFigureManager
    from core.modules.basic_modules import Integer, Float, String, Boolean, Variant, Color
    import api
        
    reg = core.modules.module_registry.get_module_registry() 
    vtkAlgorithmOutputType = typeMap('vtkAlgorithmOutput')
    vtkImageDataType = typeMap('vtkImageData')
    reg.add_module( AlgorithmOutputModule, abstract=True) # hide_descriptor=True )       
    reg.add_module( AlgorithmOutputModule3D, abstract=True) # hide_descriptor=True )   
    reg.add_module( WorkflowModule, abstract=True) # hide_descriptor=True )   
    reg.add_module( CDMSDataset, abstract=True) # hide_descriptor=True )   
 
    reg.add_module( AddTest ) 
    reg.add_input_port( AddTest, "parm", Integer  )   
    reg.add_input_port( AddTest, "arg",  Integer  )   
    reg.add_input_port( AddTest, "layer",  Integer  )   
    reg.add_output_port( AddTest, "out", Integer ) 
    
    reg.add_module( DV3DCell ) 
    reg.add_input_port( DV3DCell, "volume", AlgorithmOutputModule3D  )   

    reg.add_module( WorldFrame )
    reg.add_input_port( WorldFrame, "world_cut", Integer, optional=True  )
    reg.add_input_port( WorldFrame, "map_border_size",  [ ( Float, 'border_in_degrees' ) ], optional=True  )
    reg.add_input_port( WorldFrame, "world_map", [ ( File, 'map_file' ), ( Integer, 'map_cut' ) ], optional=True  ) 
    reg.add_input_port( WorldFrame, "opacity", [ ( Float, 'value' ) ], optional=True  ) 
    reg.add_input_port( WorldFrame, "zscale", [ ( Float, 'value' ) ], optional=True  ) 
    reg.add_input_port( WorldFrame, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( WorldFrame, "volume", AlgorithmOutputModule3D ) 
    WorldFrame.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_FileReader, configureWidgetType=CDMSDatasetConfigurationWidget )
    reg.add_input_port( CDMS_FileReader, "datasets",    [ ( String, 'serializedDatasetMap' ) ], True ) 
    reg.add_input_port( CDMS_FileReader, "datasetId",    [ ( String, 'currentDatasetId' ), ( Integer, 'version' ) ], True ) 
    reg.add_input_port( CDMS_FileReader, "timeRange",    [ ( Integer, 'startTimeIndex' ), ( Integer, 'endTimeIndex' ) ], True )    
    reg.add_input_port( CDMS_FileReader, "roi",    [ ( Float, 'lon0' ), ( Float, 'lat0' ), ( Float, 'lon1' ), ( Float, 'lat1' ) ], True )    
    reg.add_output_port( CDMS_FileReader, "dataset", CDMSDataset ) 
    CDMS_FileReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_VolumeReader, configureWidgetType=CDMS_VolumeReaderConfigurationWidget )
    reg.add_input_port( CDMS_VolumeReader, "dataset", CDMSDataset )    
    reg.add_input_port( CDMS_VolumeReader, "portData",   [ ( String, 'serializedPortData' ), ( Integer, 'version' ) ], True   ) 
    reg.add_output_port( CDMS_VolumeReader, "volume", AlgorithmOutputModule3D ) 
    CDMS_VolumeReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_SliceReader, configureWidgetType=CDMS_SliceReaderConfigurationWidget )
    reg.add_input_port( CDMS_SliceReader, "dataset", CDMSDataset )        
    reg.add_input_port( CDMS_SliceReader, "portData",   [ ( String, 'serializedPortData' ), ( Integer, 'version' ) ], True   ) 
    reg.add_output_port( CDMS_SliceReader, "slice", AlgorithmOutputModule ) 
    CDMS_SliceReader.registerConfigurableFunctions( reg )

    reg.add_module( CDMS_CDATUtilities, configureWidgetType=CDATUtilitiesModuleConfigurationWidget )
    reg.add_input_port( CDMS_CDATUtilities, "dataset", CDMSDataset )   
    reg.add_input_port( CDMS_CDATUtilities, "task",  [ ( String, 'taskData' ) ], True   ) # [ ( String, 'taskName' ), ( String, 'inputVars' ), ( String, 'outputVars' ) ], True   ) 
    reg.add_output_port( CDMS_CDATUtilities, "dataset", CDMSDataset ) 

    reg.add_module( VolumeSlicer, configureWidgetType=LayerConfigurationWidget )
    reg.add_output_port( VolumeSlicer, "slice",  AlgorithmOutputModule  )
    reg.add_input_port( VolumeSlicer, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( VolumeSlicer, "volume", AlgorithmOutputModule3D ) 
    VolumeSlicer.registerConfigurableFunctions( reg )

    reg.add_module( Gradient ) 
    reg.add_input_port( Gradient, "computeVorticity", Integer  )   
    reg.add_input_port( Gradient, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( Gradient, "volume", AlgorithmOutputModule3D ) 
    
    reg.add_module( VectorCutPlane )
    reg.add_input_port( VectorCutPlane, "colors", AlgorithmOutputModule3D  )
    reg.add_output_port( VectorCutPlane, "slice", AlgorithmOutputModule ) 
    reg.add_input_port( VectorCutPlane, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( VectorCutPlane, "volume", AlgorithmOutputModule3D ) 
    VectorCutPlane.registerConfigurableFunctions(  reg )

    reg.add_module( Resample )
#    reg.add_input_port( Resample, "position", [ ( Float, 'x' ), ( Float, 'y' ), ( Float, 'z' ) ], True   )    
#    reg.add_output_port( Resample, "position",  [ ( Float, 'x' ), ( Float, 'y' ), ( Float, 'z' ) ], True  )
    reg.add_input_port( Resample, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( Resample, "volume", AlgorithmOutputModule3D ) 
    Resample.registerConfigurableFunctions( reg )

    reg.add_module( CurtainPlot )
    reg.add_input_port( CurtainPlot, "path", ( File, 'path_file' )  ) 
    reg.add_input_port( CurtainPlot, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( CurtainPlot, "volume", AlgorithmOutputModule3D ) 
    CurtainPlot.registerConfigurableFunctions( reg )
       
#    reg.add_module( DemoData, configureWidgetType=DemoDataConfigurationWidget )
#    reg.add_input_port( DemoData, "dataset",    [ ( String, 'name' ), ] ) 
#    reg.add_input_port( DemoData, "maxNTimeSteps",   [ ( Integer, 'nts' ) ]   ) 
#    reg.add_output_port( DemoData, "volume", AlgorithmOutputModule3D ) 
#    DemoData.registerConfigurableFunctions( reg )
       
    reg.add_module( VolumeRenderer ) # , configureWidgetType=LayerConfigurationWidget  )
    reg.add_input_port( VolumeRenderer, "volume", AlgorithmOutputModule3D  )
#    reg.add_input_port( VolumeRenderer, "layer",   [ ( String, 'layer' ), ]   ) 
    reg.add_output_port( VolumeRenderer, "volume", AlgorithmOutputModule3D ) 
    VolumeRenderer.registerConfigurableFunctions( reg )

    reg.add_module( LevelSurface, configureWidgetType=LayerConfigurationWidget  )
    reg.add_input_port( LevelSurface, "texture", AlgorithmOutputModule3D  )
    reg.add_input_port( LevelSurface, "volume", AlgorithmOutputModule3D  )
    reg.add_output_port( LevelSurface, "volume", AlgorithmOutputModule3D ) 
    reg.add_input_port( LevelSurface, "layer",   [ ( String, 'activeLayerName' ) ]   ) 
    LevelSurface.registerConfigurableFunctions( reg )

    reg.add_module( SlicePlot )
    reg.add_input_port( SlicePlot, "slice", AlgorithmOutputModule  )
    reg.add_output_port(SlicePlot, 'FigureManager', MplFigureManager)
    reg.add_output_port(SlicePlot, 'File', File)
    SlicePlot.registerConfigurableFunctions( reg )

    
