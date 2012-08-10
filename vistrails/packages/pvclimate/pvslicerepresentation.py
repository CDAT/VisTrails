
# Import base class module
from pvrepresentationbase import *

# Import registry
from core.modules.module_registry import get_module_registry
import core.modules.basic_modules as basic_modules

# Import paraview
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
        for var in self.variables:
            reader = var.get_reader()
            self.sliceByVarName = var.get_variable_name()
            self.sliceByVarType = var.get_variable_type()

            # Update pipeline
            reader.UpdatePipeline()

            bounds = reader.GetDataInformation().GetBounds()
            origin = []
            origin.append((bounds[1] + bounds[0]) / 2.0)
            origin.append((bounds[3] + bounds[2]) / 2.0)
            origin.append((bounds[5] + bounds[4]) / 2.0)

            # Create a slice representation
            sliceFilter = pvsp.Slice(reader)
            sliceFilter.SliceType.Normal = self.sliceNormal
            sliceFilter.SliceType.Origin = origin

            sliceFilter.SliceOffsetValues =  self.forceGetInputListFromPort("sliceOffset")

            sliceRep = pvsp.Show(view=self.view)

            # FIXME: Hard coded for now
            sliceRep.LookupTable =  pvsp.GetLookupTableForArray( self.sliceByVarName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[0.0, 0.23, 0.299, 0.754, 30.0, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1 )
            sliceRep.ColorArrayName = self.sliceByVarName
            # Apply scale (squish in Z)
            sliceRep.Scale  = [1,1,0.01]
            sliceRep.Representation = 'Surface'

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
        print self.rep_module
        action = self.update_vistrails(self.rep_module, functions)
        print self.rep_module

        print 'okTriggered'

        if action is not None:
            self.emit(SIGNAL('doneConfigure()'))
            self.emit(SIGNAL('plotDoneConfigure'), action)



def registerSelf():
    registry = get_module_registry()
    registry.add_module(PVSliceRepresentation)
    registry.add_output_port(PVSliceRepresentation, "self", PVSliceRepresentation)
    registry.add_input_port(PVSliceRepresentation, "sliceOffset", basic_modules.Float)
