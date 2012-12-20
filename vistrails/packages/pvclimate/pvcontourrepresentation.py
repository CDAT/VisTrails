
#// Import base class module
from pvrepresentationbase import *
from pvcdmsreader import *

#// Import registry and vistrails app
from core.modules.module_registry import get_module_registry
from core.modules.vistrails_module import ModuleConnector
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper

#// Import paraview
import paraview.simple as pvsp

#// CDAT
import cdms2, cdtime, cdutil, MV2
import core.modules.basic_modules as basic_modules
from packages.uvcdat_cdms.init import CDMSVariable

#// Import pvclimate modules
from pvcontour_widget import *

class PVContourRepresentation(PVRepresentationBase):
    def __init__(self):
        PVRepresentationBase.__init__(self)
        self.contour_var_name = None
        self.contour_var_type = None
        self.contour_values = None

    def compute(self):
        #// @todo:
        pass

    def get_contour_values(self):
        return self.contour_values

    def set_contour_values(self, values):
        self.contour_values = values

    def set_contour_by(self, name, type):
        self.contour_var_name = name
        self.contour_var_type = type

    def execute(self):
        self.cdms_variables = self.forceGetInputListFromPort('cdms_variable')
        for cdms_var in self.cdms_variables:

            #// Get the min and max to draw default contours
            min = cdms_var.var.min()
            max = cdms_var.var.max()

            reader = PVCDMSReader()
            time_values = [None, 1, True]
            image_data = reader.convert(cdms_var, time=time_values)

            #// Make white box filter so we can work at proxy level
            ProgrammableSource1 = pvsp.ProgrammableSource()

            #// Get a hole of the vtk level filter it controls
            ps = ProgrammableSource1.GetClientSideObject()

            #//  Give it some data (ie the imagedata)
            ps.myid = image_data

            ProgrammableSource1.OutputDataSetType = 'vtkImageData'
            ProgrammableSource1.PythonPath = ''

            #// Make the scripts that it runs in pipeline RI and RD passes
            ProgrammableSource1.ScriptRequestInformation = """
executive = self.GetExecutive()
outInfo = executive.GetOutputInformation(0)
extents = self.myid.GetExtent()
spacing = self.myid.GetSpacing()
outInfo.Set(executive.WHOLE_EXTENT(), extents[0], extents[1], extents[2], extents[3], extents[4], extents[5])
outInfo.Set(vtk.vtkDataObject.SPACING(), spacing[0], spacing[1], spacing[2])
dataType = 10 # VTK_FLOAT
numberOfComponents = 1
vtk.vtkDataObject.SetPointDataActiveScalarInfo(outInfo, dataType, numberOfComponents)"""

            ProgrammableSource1.Script = """self.GetOutput().ShallowCopy(self.myid)"""
            ProgrammableSource1.UpdatePipeline()
            pvsp.SetActiveSource(ProgrammableSource1)

            self.contour_var_name = str(cdms_var.varNameInFile)

            #// If the data is three dimensional, then don't draw the background imagery
            #// since it may hide the contours
            if not reader.is_three_dimensional(cdms_var):
                data_rep = pvsp.Show(view=self.view)
                data_rep.LookupTable = pvsp.GetLookupTableForArray(self.contour_var_name, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[min, 0.23, 0.299, 0.754, max, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1)
                data_rep.ColorArrayName = self.contour_var_name

            try:
                contour = pvsp.Contour()
                pvsp.SetActiveSource(contour)
                contour.ContourBy = ['POINTS', self.contour_var_name]

                delta = (max - min) / 10.0

                contours = self.forceGetInputListFromPort("contour_values")
                if(len(contours) and contours):
                    self.contour_values = [float(d) for d in contours[0].split(',')]                    

                # if( (self.contour_values == None) or (len(self.contour_values) == 0) ):
                else:   
                    self.contour_values = [ (x * delta + min) for x in range(10) ]                    
                    functions = []                    
                    functions.append(("contour_values", [str(self.contour_values).strip('[]')]))                    
                    self.update_functions('PVContourRepresentation', functions)

                contour.Isosurfaces = self.contour_values
                contour.ComputeScalars = 1
                contour.ComputeNormals = 0
                contour.UpdatePipeline()

                #// @todo: Remove hard-coded values
                contour_rep = pvsp.Show(view=self.view)
                contour_rep.Representation = 'Surface'
                if reader.is_three_dimensional(cdms_var):
                    contour_rep.LookupTable = pvsp.GetLookupTableForArray(self.contour_var_name, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[min, 0.23, 0.299, 0.754, max, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1)
                    contour_rep.ColorArrayName = self.contour_var_name
                else:
                    contour_rep.DiffuseColor = [0.0, 0.0, 0.0]
                    contour_rep.ColorArrayName = ''


                #// Scalar bar
                ScalarBarWidgetRepresentation1 = pvsp.CreateScalarBar( Title=self.contour_var_name, LabelFontSize=12, Enabled=1, TitleFontSize=12 )
                pvsp.GetRenderView().Representations.append(ScalarBarWidgetRepresentation1)

                if not reader.is_three_dimensional(cdms_var):
                    ScalarBarWidgetRepresentation1.LookupTable = data_rep.LookupTable
                else:
                    ScalarBarWidgetRepresentation1.LookupTable = contour_rep.LookupTable

            except ValueError:
                print "[ERROR] Unable to generate contours. Please check your input values"
            except (RuntimeError, TypeError, NameError):
                print "[ERROR] Unknown error"
                pass        

    @staticmethod
    def name():
        return 'PV Contour Representation'

    @staticmethod
    def configuration_widget(parent, rep_module):
        contour_rep_widget = ContourRepresentationConfigurationWidget(parent, rep_module)
        contour_values_str = contour_rep_widget.function_value('contour_values')
        contour_rep_widget.synchronize(contour_values_str)
        return contour_rep_widget

class ContourRepresentationConfigurationWidget(RepresentationBaseConfigurationWidget):
    def __init__(self, parent, rep_module):
        RepresentationBaseConfigurationWidget.__init__(self, parent, rep_module)
        self.contour_widget = PVContourWidget()

        layout = QVBoxLayout()
        self.setLayout(layout)
        widgetLayout = QHBoxLayout()
        widgetLayout.addWidget(self.contour_widget)
        layout.addLayout(widgetLayout)

        self.connect(self.contour_widget, QtCore.SIGNAL('requestedApplyChagnes()'), self.update_contour_values)

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if necessary) then close the widget
        """
        pass

    def synchronize(self, contour_values_str):
        self.contour_widget.set_contour_values(contour_values_str)

    def update_contour_values(self):
        contour_values = str(self.contour_widget.get_contour_values()).strip('[]')
        functions = []
        functions.append(("contour_values", [contour_values]))
        self.update_vistrails(self.rep_module, functions)

def register_self():
    registry = get_module_registry()
    registry.add_module(PVContourRepresentation)
    registry.add_output_port(PVContourRepresentation, "self", PVContourRepresentation)
    registry.add_input_port(PVContourRepresentation, "contour_values", basic_modules.String)
    registry.add_input_port(PVContourRepresentation, "cdms_variable", CDMSVariable)
