
#// Import base class module
from pvrepresentationbase import *
from pvcdmsreader import *

#// Import registry
from core.modules.module_registry import get_module_registry
import core.modules.basic_modules as basic_modules

#// Import paraview
import paraview.simple as pvsp

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class PVSliceRepresentation(PVRepresentationBase):
    def __init__(self):
        PVRepresentationBase.__init__(self)
        self.sliceByVarName = None
        self.sliceByVarType = None
        self.sliceNormal = [0.0, 0.0, 1.0]
        self.sliceOffsets = []

    def compute(self):
        # TODO:
        pass

    def setView(self, view):
        self.view = view

    def setSliceOffsets(self, offsets):
        self.sliceOffsets = offsets

    def setSliceBy(self, varName, varType):
        self.contourByVarName = varName
        self.contourByVarType = varType

    def execute(self):
        for cdms_var in self.cdms_variables:
            #// Get the min and max to draw default contours
            min = cdms_var.var.min()
            max = cdms_var.var.max()

            reader = PVCDMSReader()
            time_values = [None, 1, True]
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

            self.sliceByVarName = cdms_var.varNameInFile
            self.sliceByVarType = 'POINTS'

            if not reader.is_three_dimensional(cdms_var):
              data_rep = pvsp.Show(view=self.view)
              data_rep.LookupTable = pvsp.GetLookupTableForArray(self.sliceByVarName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[min, 0.23, 0.299, 0.754, max, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1)
              data_rep.ColorArrayName = self.sliceByVarName

              print 'data has three dimensions'
              continue

            bounds = image_data.GetBounds()
            origin = []
            origin.append((bounds[1] + bounds[0]) / 2.0)
            origin.append((bounds[3] + bounds[2]) / 2.0)
            origin.append((bounds[5] + bounds[4]) / 2.0)

            # Create a slice representation
            plane_slice = pvsp.Slice( SliceType="Plane" )#
            pvsp.SetActiveSource(plane_slice)

            plane_slice.SliceType.Normal = self.sliceNormal
            plane_slice.SliceType.Origin = origin
            plane_slice.SliceOffsetValues = self.forceGetInputListFromPort("sliceOffset")

            slice_rep = pvsp.Show(view=self.view)

            # FIXME: Hard coded for now
            slice_rep.LookupTable =  pvsp.GetLookupTableForArray( self.sliceByVarName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[min, 0.23, 0.299, 0.754, max, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1 )
            slice_rep.ColorArrayName = self.sliceByVarName

            # Apply scale (Make it flat)
            slice_rep.Scale  = [1,1,0.01]
            slice_rep.Representation = 'Surface'

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

        sliceOffset = self.function_value('sliceOffset')

        sliceOffsetLayout = QHBoxLayout()
        sliceOffsetLabel = QLabel("Slice Offset:")
        self.slice_offset_value =  QLineEdit (parent)

        if sliceOffset != None:
            self.slice_offset_value.setText(sliceOffset)

        sliceOffsetLayout.addWidget( sliceOffsetLabel )
        sliceOffsetLayout.addWidget( self.slice_offset_value )
        layout.addLayout(sliceOffsetLayout)
        parent.connect(self.slice_offset_value, SIGNAL("textEdited(const QString&)"), parent.stateChanged)

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if necessary) then close the widget

        """
        slice_offset = str(self.slice_offset_value.text().toLocal8Bit().data())
        functions = []
        functions.append(("sliceOffset", [slice_offset]))
        action = self.update_vistrails(self.rep_module, functions)
        if action is not None:
            self.emit(SIGNAL('doneConfigure()'))
            self.emit(SIGNAL('plotDoneConfigure'), action)


def register_self():
    registry = get_module_registry()
    registry.add_module(PVSliceRepresentation)
    registry.add_output_port(PVSliceRepresentation, "self", PVSliceRepresentation)
    registry.add_input_port(PVSliceRepresentation, "sliceOffset", basic_modules.Float)
