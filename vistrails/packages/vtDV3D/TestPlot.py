import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def execAction1( index ):
    print " execAction: ", index

class TestObject( QObject ):
    
    def __init__( self, **args ):
        pass

    def __del__(self):
        print "Deleting TestObject"


class TestConfigPopupManager( QObject ):
    
    def __init__( self, **args ):
        self.menu = QMenu()
        self.actionMap = {}

#        self.connect( self.menu, SIGNAL("triggered(QAction)"), self.execAction ) 
            
    def show( self ):
#        self.signalMapper = QSignalMapper()
#        self.connect( self.signalMapper, SIGNAL('mapped(int)'), lambda who="mode1": self.changeMode(who) )
        
        for action_index in range(5):
            menuItem = self.menu.addAction( str( action_index ) )           
#            self.signalMapper.setMapping( menuItem, action_index )
            self.connect ( menuItem, SIGNAL("triggered()"), lambda aindex=str(action_index): self.execAction(aindex) ) #  self.signalMapper, SLOT('map()') )

#            receiver = lambda: self.execAction( menuItem )
#            self.connect( menuItem, SIGNAL("triggered()"), receiver ) 
        if self.menu.isHidden():    
            self.menu.popup( QCursor.pos() )
    
    def execAction( self, action ):
#        origin = sender() 
        print " execAction: ", action
        self.menu.clear()

class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        QMainWindow.__init__(self)
        self.setFixedSize( 300, 300 )
        tobj = TestObject()
#        self.test_obj = tobj
        del tobj
        self.testConfigPopupManager = TestConfigPopupManager()
        
    def mousePressEvent ( self, event ): 
        self.testConfigPopupManager.show()  
        
app = QApplication(sys.argv)
main = MainWindow()
main.show()
app.exec_()

    
    





#import vtk, os, time
#
#packagePath = os.path.dirname( __file__ )  
#defaultMapDir = os.path.join( packagePath, 'data' )
#defaultLogoFile = os.path.join( defaultMapDir,  'uvcdat.jpg' )
#
#reader = vtk.vtkJPEGReader()
#renderer = vtk.vtkRenderer()
#reader.SetFileName( defaultLogoFile )
#logoMapper = vtk.vtkImageMapper()
#input = reader.GetOutput()
#logoMapper.SetInput( input )
#
#imageActor = vtk.vtkActor2D()
#properties = imageActor.GetProperty()  
#properties.SetOpacity(1.0) 
#properties.SetDisplayLocationToForeground()
#
#imageActor.SetMapper( logoMapper )
##            imageActor.SetWidth( 0.25 )      
##            imageActor.SetHeight( 0.1 ) 
#coord = imageActor.GetPositionCoordinate()  
#coord.SetCoordinateSystemToNormalizedViewport()
#coord.SetValue( 0.0, 0.0 )        
#renderer.AddActor2D( imageActor )
#
#renderWindow = vtk.vtkRenderWindow()
#renderWindow.AddRenderer(renderer)
#
#iren = vtk.vtkRenderWindowInteractor()
#iren.SetRenderWindow(renderWindow)
#
#def CheckAbort(obj, event):  
#    if obj.GetEventPending() != 0:
#        obj.SetAbortRender(1)
# 
#renderWindow.AddObserver("AbortCheckEvent", CheckAbort)
#
#input.Update()
#range = input.GetScalarRange()
#logoMapper.SetColorWindow( range[1] - range[0] )
#logoMapper.SetColorLevel( 0.5 * (range[1] + range[0]) )
#
#print "Leveling: ", str( logoMapper.GetColorLevel() ), str( logoMapper.GetColorWindow() )
##logoMapper.SetColorLevel(0.5) 
##logoMapper.SetColorWindow(0.5) 
#
#iren.Initialize()
#renderWindow.Render()
#iren.Start()
#
### Example of how to use Parallel Coordinates View to plot and compare
###     data set attributes.
### Use the "u" character to toggle between "inspect modes" on the parallel coordinates
###    view (i.e. between selecting data and manipulating axes).
### Lines which are commented out show alternative options.
## 
##
## 
### Generate an example image data set with multiple attribute arrays to probe and view
### This is where you would put your reader instead of this rt->elev pipeline...
##rt = vtk.vtkRTAnalyticSource()
##rt.SetWholeExtent(-3,3,-3,3,-3,3)
##grad = vtk.vtkImageGradient()
##grad.SetDimensionality(3)
##grad.SetInputConnection(rt.GetOutputPort())
##brown = vtk.vtkBrownianPoints()
##brown.SetMinimumSpeed(0.5)
##brown.SetMaximumSpeed(1.0)
##brown.SetInputConnection(grad.GetOutputPort())
##elev = vtk.vtkElevationFilter()
##elev.SetLowPoint(-3,-3,-3)
##elev.SetHighPoint(3,3,3)
##elev.SetInputConnection(brown.GetOutputPort())
## 
### Set up the parallel coordinates Representation to be used in the View
##rep = vtk.vtkParallelCoordinatesRepresentation()
##
##output = elev.GetOutput()
##output.Update()
##ptData = output.GetPointData()
##na = ptData.GetNumberOfArrays()
## 
### Plug your reader in here for your own data
##rep.SetInputConnection(elev.GetOutputPort())
## 
### List all of the attribute arrays you want plotted in parallel coordinates
##rep.SetInputArrayToProcess(0,0,0,0,'RTDataGradient')
##rep.SetInputArrayToProcess(1,0,0,0,'RTData')
##rep.SetInputArrayToProcess(2,0,0,0,'Elevation')
##rep.SetInputArrayToProcess(3,0,0,0,'BrownianVectors')
## 
##rep.SetUseCurves(0)        # set to 1 to use smooth curves
##rep.SetLineOpacity(0.5)
## 
### Set up the Parallel Coordinates View and hook in the Representation
##view = vtk.vtkParallelCoordinatesView()
##view.SetRepresentation(rep)
## 
### Inspect Mode determines whether your interactions manipulate the axes or select data
### view.SetInspectMode(0)    # VTK_INSPECT_MANIPULATE_AXES = 0, 
##view.SetInspectMode(1)        # VTK_INSPECT_SELECT_DATA = 1 
## 
### Brush Mode determines the type of interaction you perform to select data
###view.SetBrushModeToLasso()
###view.SetBrushModeToAngle()
##view.SetBrushModeToFunction()
### view.SetBrushModeToAxisThreshold()    # not implemented yet (as of 21 Feb 2010)
## 
### Brush Operator determines how each new selection interaction changes selected lines
### view.SetBrushOperatorToAdd()
### view.SetBrushOperatorToSubtract()
### view.SetBrushOperatorToIntersect()
##view.SetBrushOperatorToReplace()
## 
### Define the callback routine which toggles between "Inspect Modes"
##def ToggleInspectors(obj,event):
##    if (view.GetInspectMode() == 0):
##        view.SetInspectMode(1)
##    else:
##        view.SetInspectMode(0)
## 
### Hook up the callback to toggle between inspect modes (manip axes & select data)
##view.GetInteractor().AddObserver("UserEvent", ToggleInspectors)
## 
### Set up render window
##view.GetRenderWindow().SetSize(600,300)
##view.ResetCamera()
##view.Render()
## 
### Start interaction event loop
##view.GetInteractor().Start()