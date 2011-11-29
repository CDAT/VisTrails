from PyQt4 import QtCore
from core.modules.module_registry import get_module_registry
from packages.vtk.vtkcell import QVTKWidget
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_cell import QCellWidget
#from PVBase import PVModule
import paraview.simple as pvsp
import paraview.pvfilters
import vtk

# We are using our own constant (though we are calling it a variable)
import pvvariable

class PVClimateCell(SpreadsheetCell):
    def __init__(self):
        SpreadsheetCell.__init__(self)
        self.cellWidget = None

    def compute(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """
        proxies = self.forceGetInputListFromPort('variable')
        self.cellWidget = self.displayAndWait(QParaViewWidget, (proxies,))

class QParaViewWidget(QVTKWidget):

    def __init__(self, parent=None, f=QtCore.Qt.WindowFlags()):
        QVTKWidget.__init__(self, parent, f)
        self.view = None

    def updateContents(self, inputPorts):

        if self.view==None:
            self.view = pvsp.CreateRenderView()
            renWin = self.view.GetRenderWindow()
            self.SetRenderWindow(renWin)
            iren = renWin.GetInteractor()
            print type(iren)
            iren.SetNonInteractiveRenderDelay(0)
            iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        
        # Fetch variables from the input port
        (pvvariables, ) = inputPorts
        for var in pvvariables:
            reader = var.get_reader()
            variableName = var.get_variable_name()
            variableType = var.get_variable_type()
            #print reader
            #contour = pvsp.Contour(reader)
            #contour.ContourBy = [variableType, variableName]
            #contour.Isosurfaces = [0]
            #rep = pvsp.GetDisplayProperties(contour)
            # Now make a representation and add it to the view
            reader.Stride = [5,5,5]
            
            # Update pipeline
            reader.UpdatePipeline()
            
            # Get bounds
            bounds = reader.GetDataInformation().GetBounds()
            origin = []
            origin.append((bounds[1] + bounds[0]) / 2.0)
            origin.append((bounds[3] + bounds[2]) / 2.0)
            origin.append((bounds[5] + bounds[4]) / 2.0)
            
            print origin
            
            # Create a slice representation
            sliceFilter = pvsp.Slice(reader)
            sliceFilter.SliceType.Normal = [0,0,1]
            sliceFilter.SliceType.Origin = origin
            
            # \TODO: 
            # 1. Fix saturation
            # 2. Add scalar bar
            rep = pvsp.GetDisplayProperties(sliceFilter)
            rep.LookupTable = pvsp.MakeBlueToRedLT(0,30)
            rep.ColorArrayName = 'TEMP'
            
            # Apply scale (squish in Z)
            rep.Scale  = [1,1,0.01]
            
            self.view.Representations = []
            self.view.Representations.append(rep)
            
            # Create a contour representation            
            contour = pvsp.Contour(reader)
            contour.ContourBy = [variableType, variableName]
            contour.Isosurfaces = [8]
            contour.ComputeScalars = 1
            contour.ComputeNormals = 1
            contourRep = pvsp.GetDisplayProperties(contour)
            contourRep.LookupTable = pvsp.MakeBlueToRedLT(0,30)
            contourRep.ColorArrayName = variableName            
            contourRep.Scale  = [1,1,0.01]
            
            self.view.Representations.append(contourRep)

        self.view.ResetCamera()
        self.view.StillRender()

        QCellWidget.updateContents(self, inputPorts)

    def saveToPNG(self, filename):
        """ saveToPNG(filename: str) -> filename or vtkUnsignedCharArray

        Save the current widget contents to an image file. If
        str==None, then it returns the vtkUnsignedCharArray containing
        the PNG image. Otherwise, the filename is returned.

        """
        image = self.view.CaptureWindow(1)
        image.UnRegister(None)

        writer = vtk.vtkPNGWriter()
        writer.SetInput(image)
        if filename!=None:
            writer.SetFileName(filename)
        else:
            writer.WriteToMemoryOn()
        writer.Write()
        if filename:
            return filename
        else:
            return writer.GetResult()

    def deleteLater(self):
        QCellWidget.deleteLater(self)



def registerSelf():
    registry = get_module_registry()
    registry.add_module(PVClimateCell)
    registry.add_input_port(PVClimateCell, "Location", CellLocation)
    registry.add_input_port(PVClimateCell, "variable", pvvariable.PVVariableConstant)
    registry.add_output_port(PVClimateCell, "self", PVClimateCell)
