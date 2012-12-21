
#// Import base class module
from pvrepresentationbase import *
from pvcdmsreader import *

#// Import registry
from core.modules.module_registry import get_module_registry
import core.modules.basic_modules as basic_modules

#// Import pvclimate modules
from pvslice_widget import *

#// Import paraview
import paraview.simple as pvsp

#// CDAT
import cdms2, cdtime, cdutil, MV2
import core.modules.basic_modules as basic_modules
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper
from packages.uvcdat_cdms.init import CDMSVariable

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class PVSliceRepresentation(PVRepresentationBase):
    def __init__(self):
        PVRepresentationBase.__init__(self)
        self.slice_by_var_name = None
        self.slice_by_var_type = None
        self.slice_normal = []
        self.slice_origin = []
        self.slice_offset_values = []

    def compute(self):
        # TODO:
        pass

    def set_slice_offset_values(self, offset_values):
        self.slice_offset_values = offset_values

    def get_slice_offset_values(self):
        return self.slice_offset_values

    def set_slice_origin(self, origin):
        self.slice_origin = origin

    def get_slice_origin(self):
        return self.slice_origin

    def set_slice_normal(self, normal):
        self.slice_normal = normal

    def get_slice_normal(self):
        return self.slice_normal

    def execute(self):
        self.cdms_variables = self.forceGetInputListFromPort('cdms_variable')
        for cdms_var in self.cdms_variables:
            
            #// @todo: hardcoded for now
            time_values = [None, 1, True]
            
            #// Get the min and max to draw default contours
            min = cdms_var.var.min()
            max = cdms_var.var.max()

            reader = PVCDMSReader()
            image_data = reader.convert(cdms_var, time=time_values)

            #// Make white box filter so we can work at proxy level
            programmable_source = pvsp.ProgrammableSource()

            #// Get a hole of the vtk level filter it controls
            ps = programmable_source.GetClientSideObject()

            #//  Give it some data (ie the imagedata)
            ps.myid = image_data

            programmable_source.OutputDataSetType = 'vtkImageData'
            programmable_source.PythonPath = ''

            #// Make the scripts that it runs in pipeline RI and RD passes
            programmable_source.ScriptRequestInformation = """
executive = self.GetExecutive()
outInfo = executive.GetOutputInformation(0)
extents = self.myid.GetExtent()
spacing = self.myid.GetSpacing()
outInfo.Set(executive.WHOLE_EXTENT(), extents[0], extents[1], extents[2], extents[3], extents[4], extents[5])
outInfo.Set(vtk.vtkDataObject.SPACING(), spacing[0], spacing[1], spacing[2])
dataType = 10 # VTK_FLOAT
numberOfComponents = 1
vtk.vtkDataObject.SetPointDataActiveScalarInfo(outInfo, dataType, numberOfComponents)"""

            programmable_source.Script = """self.GetOutput().ShallowCopy(self.myid)"""
            programmable_source.UpdatePipeline()
            pvsp.SetActiveSource(programmable_source)

            self.slice_by_var_name = cdms_var.varNameInFile
            self.slice_by_var_type = 'POINTS'

            if not reader.is_three_dimensional(cdms_var):
              data_rep = pvsp.Show(view=self.view)
              data_rep.LookupTable = pvsp.GetLookupTableForArray(self.slice_by_var_name, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[min, 0.23, 0.299, 0.754, max, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1)
              data_rep.ColorArrayName = self.slice_by_var_name
              continue

            functions = []
            try:
                slice_origin = self.forceGetInputListFromPort("slice_origin")                
                if (slice_origin == None) or len(slice_origin) == 0:                    
                    bounds = image_data.GetBounds()                    
                    self.slice_origin = []
                    self.slice_origin.append((bounds[1] + bounds[0]) / 2.0)
                    self.slice_origin.append((bounds[3] + bounds[2]) / 2.0)
                    self.slice_origin.append((bounds[5] + bounds[4]) / 2.0)                    
                    functions.append(('slice_origin', [str(self.slice_origin).strip('[]')]))
                else:
                    self.slice_origin = [float(d) for d in slice_origin[0].split(',')]                    

                slice_normal = self.forceGetInputListFromPort("slice_normal")
                if slice_normal == None or len(slice_normal) == 0:
                    self.slice_normal = [0.0, 0.0, 1.0] 
                    functions.append(('slice_normal', [str(self.slice_normal).strip('[]')]))                                        
                else:
                    self.slice_normal = [float(d) for d in slice_normal[0].split(',')]                    

                slice_offset_values = self.forceGetInputListFromPort("slice_offset_values")
                if(len(slice_offset_values) and slice_offset_values):
                    self.slice_offset_values = [float(d) for d in slice_offset_values[0].split(',')]                    
                else:
                    self.slice_offset_values = [0.0]
                    functions.append(('slice_offset_values', [str(self.slice_offset_values).strip('[]')]))                    
                  
                if len(functions) > 0:                      
                    self.update_functions('PVSliceRepresentation', functions)

                #// Create a slice representation
                plane_slice = pvsp.Slice( SliceType="Plane" )
                pvsp.SetActiveSource(plane_slice)

                plane_slice.SliceType.Normal = self.slice_normal
                plane_slice.SliceType.Origin = self.slice_origin
                plane_slice.SliceOffsetValues = self.slice_offset_values

                slice_rep = pvsp.Show(view=self.view)

                slice_rep.LookupTable =  pvsp.GetLookupTableForArray( self.slice_by_var_name, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[min, 0.23, 0.299, 0.754, max, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1 )
                slice_rep.ColorArrayName = self.slice_by_var_name
                slice_rep.Representation = 'Surface'

                #// Scalar bar
                ScalarBarWidgetRepresentation1 = pvsp.CreateScalarBar( Title=self.slice_by_var_name, LabelFontSize=12, Enabled=1, TitleFontSize=12 )
                self.view.Representations.append(ScalarBarWidgetRepresentation1)

                if not reader.is_three_dimensional(cdms_var):
                    ScalarBarWidgetRepresentation1.LookupTable = data_rep.LookupTable
                else:
                    ScalarBarWidgetRepresentation1.LookupTable = slice_rep.LookupTable

            except ValueError:
                print "[ERROR] Unable to generate slice. Please check your input values"
            except (RuntimeError, TypeError, NameError):
                print "[ERROR] Unknown error"

    @staticmethod
    def name():
        return 'PV Slice Representation'

    @staticmethod
    def configuration_widget(parent, rep_module):
        return PVSliceRepresentationConfigurationWidget(parent, rep_module)

class PVSliceRepresentationConfigurationWidget(RepresentationBaseConfigurationWidget):
    def __init__(self, parent, rep_module):
        RepresentationBaseConfigurationWidget.__init__(self, parent, rep_module)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.slice_rep_widget = PVSliceWidget()

        slice_widge_layout = QHBoxLayout()
        slice_widge_layout.addWidget(self.slice_rep_widget)
        layout.addLayout(slice_widge_layout)

        slice_offset_values_str = self.function_value('slice_offset_values')
        slice_origin_str = self.function_value('slice_origin')
        slice_normal_str = self.function_value('slice_normal')

        self.slice_rep_widget.set_slice_offset_values(slice_offset_values_str)
        self.slice_rep_widget.set_slice_origin(slice_origin_str)
        self.slice_rep_widget.set_slice_normal(slice_normal_str)

        self.connect(self.slice_rep_widget, QtCore.SIGNAL('requestedApplyChagnes()'), self.update_slice)

    def update_slice(self):
        slice_offset_values = str(self.slice_rep_widget.get_slice_offset_values()).strip('[]')
        slice_origin = str(self.slice_rep_widget.get_slice_origin()).strip('[]')
        slice_normal = str(self.slice_rep_widget.get_slice_normal()).strip('[]')

        functions = []
        functions.append(("slice_offset_values", [slice_offset_values]))
        functions.append(("slice_origin", [slice_origin]))
        functions.append(("slice_normal", [slice_normal]))

        self.update_vistrails(self.rep_module, functions)

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if necessary) then close the widget

        """
        pass

def register_self():
    registry = get_module_registry()
    registry.add_module(PVSliceRepresentation)
    registry.add_output_port(PVSliceRepresentation, "self", PVSliceRepresentation)
    registry.add_input_port(PVSliceRepresentation, "slice_offset_values", basic_modules.String)
    registry.add_input_port(PVSliceRepresentation, "slice_origin", basic_modules.String)
    registry.add_input_port(PVSliceRepresentation, "slice_normal", basic_modules.String)
    registry.add_input_port(PVSliceRepresentation, "cdms_variable", CDMSVariable)
