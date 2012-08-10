
# Import base class module
from pvrepresentationbase import *

# Import registry
from core.modules.module_registry import get_module_registry

# Import paraview
import paraview.simple as pvsp

class PVContourRepresentation(PVRepresentationBase):
    def __init__(self):
        PVRepresentationBase.__init__(self)
        self.contourByVarName = None
        self.contourByVarType = None
        self.contourValues = []        
            
    def compute(self):
        # TODO:
        pass
        
    def setView(self, view):
        self.view = view
        
    def setContourValues(self, values):
        self.contourValues = values
        
    def setControuBy(self, varName, varType):
        self.contourByVarName = varName
        self.contourByVarType = varType        
    
    def execute(self):        
        for var in self.variables:
            reader = var.get_reader()
            self.contourByVarName = var.get_variable_name()
            self.contourByVarType = var.get_variable_type()

            print 'reader is ', reader
            print 'variableName is ', self.contourByVarName
            print 'variableType is ', self.contourByVarType

            # Update pipeline
            reader.UpdatePipeline()

            # Create a contour representation
            contour = pvsp.Contour(self.reader)
            contour.ContourBy = [self.contourByVarType, self.contourByVarName]        
            contour.Isosurfaces = self.contourValues
            
            # FIXME:
            # Hard coded for now
            contour.ComputeScalars = 1
            contour.ComputeNormals = 0
            contourRep = pvsp.Show(view=self.view)
            
            # FIXME:
            # Hard coded for now        
            contourRep.LookupTable = pvsp.GetLookupTableForArray(self.contourByVarName, 1, NanColor=[0.25, 0.0, 0.0], RGBPoints=[0.0, 0.23, 0.299, 0.754, 30.0, 0.706, 0.016, 0.15], VectorMode='Magnitude', ColorSpace='Diverging', LockScalarRange=1)
            
            # FIXME:
            # Hard coded for now
            contourRep.Scale = [1, 1, 0.01]
        
            # FIXME:
            # Hard coded for now
            contourRep.Representation = 'Surface'        
            contourRep.ColorArrayName = self.contourByVarName

    @staticmethod
    def name():
        return 'PV Contour Representation'

    @staticmethod
    def configuration_widget(parent, rep_module):
        return ContourRepresentationConfigurationWidget(parent, rep_module)

class ContourRepresentationConfigurationWidget(RepresentationBaseConfigurationWidget):
    def __init__(self, parent, rep_module):
        RepresentationBaseConfigurationWidget.__init__(self, parent, rep_module)
        self.representation_module = parent
        layout = QVBoxLayout()
        self.setLayout(layout)

        sliceOffsetLayout = QHBoxLayout()
        sliceOffsetLabel = QLabel("Some property:")
        self.slice_offset_value =  QLineEdit (parent)
        sliceOffsetLayout.addWidget( sliceOffsetLabel )
        sliceOffsetLayout.addWidget( self.slice_offset_value )
        layout.addLayout(sliceOffsetLayout)
        parent.connect(self.slice_offset_value, SIGNAL("editingFinished()"), parent.stateChanged)

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if necessary) then close the widget

        """

def registerSelf():    
    registry = get_module_registry()    
    registry.add_module(PVContourRepresentation)
    registry.add_output_port(PVContourRepresentation, "self", PVContourRepresentation)
