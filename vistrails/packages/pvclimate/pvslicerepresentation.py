
# Import base class module
from pvrepresentationbase import *

# Import registry
from core.modules.module_registry import get_module_registry

# Import paraview
import paraview.simple as pvsp

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
        for var in self.variables:
            reader = var.get_reader()
            self.sliceByVarName = var.get_variable_name()
            self.sliceByVarType = var.get_variable_type()

            # Update pipeline
            reader.UpdatePipeline()
            pvsp.SetActiveSource(reader)

            bounds = reader.GetDataInformation().GetBounds()
            origin = []
            origin.append((bounds[1] + bounds[0]) / 2.0)
            origin.append((bounds[3] + bounds[2]) / 2.0)
            origin.append((bounds[5] + bounds[4]) / 2.0)

            # Unroll a sphere
            # FIXME: Currently hard coded
            if reader.__class__.__name__ == 'UnstructuredNetCDFPOPreader':
                trans_filter = self.get_project_sphere_filter()
                trans_filter.UpdatePipeline()
                bounds = trans_filter.GetDataInformation().GetBounds()
                origin [:] = []
                origin.append((bounds[1] + bounds[0]) / 2.0)
                origin.append((bounds[3] + bounds[2]) / 2.0)
                origin.append((bounds[5] + bounds[4]) / 2.0)

                pvsp.SetActiveSource(trans_filter)

            # Create a slice representation
            slice = pvsp.Slice( SliceType="Plane" )#
            pvsp.SetActiveSource(slice)

            slice.SliceType.Normal = self.sliceNormal
            slice.SliceType.Origin = origin
            slice.SliceOffsetValues = self.sliceOffsets

            slice_rep = pvsp.Show(view=self.view)

            # FIXME: Hard coded for now
            slice_rep.LookupTable =  pvsp.GetLookupTableForArray( self.sliceByVarName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[0.0, 0.23, 0.299, 0.754, 30.0, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1 )
            slice_rep.ColorArrayName = self.sliceByVarName

            # Apply scale (Make it flat)
            slice_rep.Scale  = [1,1,0.01]
            slice_rep.Representation = 'Surface'

def register_self():
    registry = get_module_registry()
    registry.add_module(PVSliceRepresentation)
    registry.add_output_port(PVSliceRepresentation, "self", PVSliceRepresentation)
