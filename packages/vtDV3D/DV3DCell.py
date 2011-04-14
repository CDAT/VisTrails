'''
Created on Feb 14, 2011

@author: tpmaxwel
'''

from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.vtk.vtkcell import QVTKWidget
from PersistentModule import AlgorithmOutputModule3D, PersistentVisualizationModule
from WorkflowModule import WorkflowModule
from vtUtilities import *
        
class PM_DV3DCell( SpreadsheetCell, PersistentVisualizationModule ):
    """
    VTKCell is a VisTrails Module that can display vtkRenderWindow inside a cell
    
    """

    def __init__( self, mid, **args ):
        SpreadsheetCell.__init__(self)
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, **args )
        self.allowMultipleInputs = True
        self.renderers = []
        self.cellWidget = None
#        print " DV3DCell __init__, id = %s " % str( id(self) ) 
        
    def isBuilt(self):
        return ( self.cellWidget <> None )
   
    def buildPipeline(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
#        print " DV3DCell compute, id = %s, cachable: %s " % ( str( id(self) ), str( self.is_cacheable() ) )
        self.renderers = []
        for inputModule in self.inputModuleList:
            if inputModule <> None:
                renderer = inputModule.getRenderer() 
                if  renderer <> None: 
                    self.renderers.append( wrapVTKModule( 'vtkRenderer', renderer ) )
#                        renderer.SetNearClippingPlaneTolerance(0.0001)
#                        print "NearClippingPlaneTolerance: %f" % renderer.GetNearClippingPlaneTolerance()
                            
        if self.cellWidget == None:
            if len( self.renderers ) > 0:
                renderViews = []
                renderView = None
                iHandlers = []
                iStyle = None
                picker = None
                
                self.cellWidget = self.displayAndWait(QVTKWidget, (self.renderers, renderView, iHandlers, iStyle, picker))
                
            else:
                
                print>>sys.stderr, "Error, no renderers supplied to DV3DCell"
                
    def updateModule(self):
        self.buildPipeline()
        if self.cellWidget:
            renWin = self.cellWidget.GetRenderWindow()
            renderers = renWin.GetRenderers()
            r0 = renderers.GetFirstRenderer()
#            r0 = addr( self.renderers[0] )  if self.renderers else '0'
#            r1 = addr(  )
#            print " updateModule: current renderer: %s, new renderer: %s " % ( r0, r1 )
            renWin.Render()

class DV3DCell(WorkflowModule):
    
    PersistentModuleClass = PM_DV3DCell
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
