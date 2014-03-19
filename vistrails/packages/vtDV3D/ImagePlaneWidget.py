
import vtk, sys, gc
from vtUtilities import versionAgnosticSetInput

VTK_NEAREST_RESLICE = 0
VTK_LINEAR_RESLICE  = 1
VTK_CUBIC_RESLICE   = 2


class ImagePlaneWidget:  
    
    InteractionStartEvent = 0
    InteractionUpdateEvent = 1
    InteractionEndEvent = 2
    
    NoButtonDown = 0
    RightButtonDown = 1
    LeftButtonDown = 2
   
    Start = 0
    Cursoring = 1
    Pushing = 2
    Moving = 3
    Outside  = 4
    
    def __init__( self, actionHandler, picker, planeIndex, orientation = None, **args ):  
        self.State  = ImagePlaneWidget.Start            
        self.Interaction  = 1
        self.PlaneIndex = planeIndex
        self.Orientation = orientation if ( orientation <> None ) else planeIndex
        self.ActionHandler = actionHandler
        self.Interactor = None
        self.Enabled = False
        self.VisualizationInteractionEnabled = True
        self.CurrentRenderer = None
        self.CurrentButton = self.NoButtonDown
        self.RenderWindow = None
        self.LastPickPosition = None
        self.PlaceFactor = 0.5;
        self.PlaneOrientation   = 0
        self.PlaceFactor  = 1.0
        self.TextureInterpolate = 1
        self.ResliceInterpolate = VTK_LINEAR_RESLICE
        self.UserControlledLookupTable= 0
        self.CurrentCursorPosition = [ 0, 0, 0 ]
        self.CurrentScreenPosition = [ 0, 0 ]
        self.CurrentImageValue   = vtk.VTK_DOUBLE_MAX
        self.CurrentImageValue2 = vtk.VTK_DOUBLE_MAX
        self.NavigationInteractorStyle = None
        self.ConfigurationInteractorStyle = vtk.vtkInteractorStyleUser()
        self.Input2ExtentOffset = [0,0,0]        
        self.Input2OriginOffset = [0,0,0]
        self.ResliceAxes   = vtk.vtkMatrix4x4()   
        self.ResliceAxes2   = vtk.vtkMatrix4x4()   
        self.ContourInputDims = 0;     
        self.InputDims = 0;     
                        
        # Represent the plane's outline
        #
        self.PlaneSource  = vtk.vtkPlaneSource()
        self.PlaneSource.SetXResolution(1)
        self.PlaneSource.SetYResolution(1)
        self.PlaneOutlinePolyData  = vtk.vtkPolyData()
        self.PlaneOutlineActor     = vtk.vtkActor()
            
        # Represent the resliced image plane
        #
        self.ColorMap = vtk.vtkImageMapToColors()
#        self.ContourFilter = vtk.vtkContourFilter
        self.Reslice = vtk.vtkImageReslice()
        self.Reslice.TransformInputSamplingOff()
        self.Reslice2 = None        
        self.Texture = vtk.vtkTexture()
        self.TexturePlaneActor   = vtk.vtkActor()
        self.Transform     = vtk.vtkTransform()
        self.ImageData    = 0
        self.ImageData2   = 0
        self.LookupTable  = 0
        self.InputBounds = None
            
        # Represent the cross hair cursor
        #
        self.CursorPolyData  = vtk.vtkPolyData()
        self.CursorActor     = vtk.vtkActor()
                                    
        self.GeneratePlaneOutline()
            
        # Define some default point coordinates
        #
        bounds = [ -0.5, 0.5, -0.5, 0.5, -0.5, 0.5 ]
            
        # Initial creation of the widget, serves to initialize it
        #
        self.PlaceWidget(bounds)
            
        self.GenerateTexturePlane()
        self.GenerateCursor()
            
        # Manage the picking stuff
        #
        self.PlanePicker = None
        self.SetPicker(picker)
            
        # Set up the initial properties
        #
        self.PlaneProperty   = 0
        self.SelectedPlaneProperty = 0
        self.TexturePlaneProperty  = 0
        self.CursorProperty  = 0
        self.CreateDefaultProperties()                                              
        self.TextureVisibility = 1

    def __del__(self):
        print " **************************************** Deleting ImagePlaneWidget module, id = %d  **************************************** " % id(self)
        sys.stdout.flush()

#----------------------------------------------------------------------------
    def LookupTableObserver( self, caller=None, event = None ):
        table_range = self.LookupTable.GetTableRange()
        print " Image Plane Widget LookupTable Observer: event = %s, caller=%x, range=%s, LookupTable=%x, self=%s" % ( event, id(caller), str( table_range ), id(self.LookupTable), id(self) )        

    def GetCurrentButton(self): 
        return self.CurrentButton
    
    def HasThirdDimension(self):
        return ( self.InputDims == 3 )

    def GetCurrentImageValue(self): 
        return self.CurrentImageValue

    def GetCurrentImageValue2(self): 
        return self.CurrentImageValue2

    def GetCurrentCursorPosition(self): 
        return self.CurrentCursorPosition
        
    def GetCurrentScreenPosition(self): 
        return self.CurrentScreenPosition
        
    def SetResliceInterpolateToNearestNeighbour(self):
        self.SetResliceInterpolate(VTK_NEAREST_RESLICE)
        
    def SetResliceInterpolateToLinear(self):
        self.SetResliceInterpolate(VTK_LINEAR_RESLICE)
        
    def SetResliceInterpolateToCubic(self):
        self.SetResliceInterpolate(VTK_CUBIC_RESLICE)

    def SetColorMap( self, value ):
        self.ColorMap = value

    def SetPlaneProperty( self, value ):
        self.PlaneProperty = value
        
    def GetPlaneProperty(self):
        return self.PlaneProperty

    def SetSelectedPlaneProperty( self, value ):
        self.SelectedPlaneProperty = value

    def SetTexturePlaneProperty( self, value ):
        self.TexturePlaneProperty = value

    def SetCursorProperty( self, value ):
        self.CursorProperty = value

    def SetUserControlledLookupTable( self, value ):
        self.UserControlledLookupTable = value

    def SetTextureInterpolate( self, value ):
        self.TextureInterpolate = value
        
    def SetPlaneOrientationToXAxes(self):
        self.SetPlaneOrientation(0)
        
    def SetPlaneOrientationToYAxes(self):
        self.SetPlaneOrientation(1)
        
    def SetPlaneOrientationToZAxes(self):
        self.SetPlaneOrientation(2)

    def MatchesBounds( self, bnds ):
        if self.InputBounds:
            for index, bval in enumerate(bnds):
                if self.InputBounds[index] <> bval:
                    return False
        return True
    
#----------------------------------------------------------------------------

    def updateInteractor(self): 
        pass
    
#----------------------------------------------------------------------------

    def SetRenderer( self, value ):
        self.CurrentRenderer = value
        if self.CurrentRenderer: self.CurrentRenderer.AddObserver( 'ModifiedEvent', self.ActivateEvent )

#----------------------------------------------------------------------------

    def ActivateEvent( self, caller, event ):
        if self.Interactor == None: 
            if self.CurrentRenderer:
                self.RenderWindow = self.CurrentRenderer.GetRenderWindow( )
                if self.RenderWindow <> None:
                    iren = self.RenderWindow.GetInteractor()
                    if iren: self.SetInteractor( iren ) 

#----------------------------------------------------------------------------

    def RemoveAllObservers( self ):
        self.Interactor.RemoveAllObservers()
        self.RenderWindow.RemoveAllObservers()
        
#----------------------------------------------------------------------------
                                
    def SetInteractor( self, iren ):
        if ( iren <> None ):
            if ( iren <> self.Interactor ):
                self.Interactor = iren  
                self.Interactor.AddObserver( 'LeftButtonPressEvent', self.OnLeftButtonDown )
                self.Interactor.AddObserver( 'LeftButtonReleaseEvent', self.OnLeftButtonUp )
                self.Interactor.AddObserver( 'RightButtonReleaseEvent', self.OnRightButtonUp )
                self.Interactor.AddObserver( 'RightButtonPressEvent', self.OnRightButtonDown )
                self.Interactor.AddObserver( 'ModifiedEvent', self.OnUpdateInteraction )
#                self.Interactor.AddObserver( 'MouseMoveEvent', self.OnMouseMove )
                self.Interactor.AddObserver( 'CharEvent', self.OnKeyPress ) 
#                self.Interactor.AddObserver( 'AnyEvent', self.OnAnyEvent )   
                self.SetEnabled()       
         
#----------------------------------------------------------------------------

    def SetTextureVisibility( self, vis ):
        if (self.TextureVisibility == vis): return
        self.TextureVisibility = vis
         
        if ( self.Enabled ): 
            if (self.TextureVisibility):
                self.CurrentRenderer.AddViewProp(self.TexturePlaneActor)
        else:
            self.CurrentRenderer.RemoveViewProp(self.TexturePlaneActor)
        self.Modified()

#----------------------------------------------------------------------------
    def SetEnabled( self ):

        if ( not self.Interactor ):   
            print>>sys.stderr, "The interactor must be set prior to enabling/disabling widget"
            return
    
        if self.Enabled:  return                     
        self.Enabled = True
        if self.CurrentRenderer == None:
            self.RenderWindow = self.Interactor.GetRenderWindow()
    
        self.CurrentRenderer.AddViewProp(self.PlaneOutlineActor)
        self.PlaneOutlineActor.SetProperty(self.PlaneProperty)
    
        #add the TexturePlaneActor
        if (self.TextureVisibility):  
            self.CurrentRenderer.AddViewProp(self.TexturePlaneActor)
    
        self.TexturePlaneActor.SetProperty(self.TexturePlaneProperty)
        
        # Add the cross-hair cursor
        self.CurrentRenderer.AddViewProp(self.CursorActor)
        self.CursorActor.SetProperty(self.CursorProperty)
        
        self.TexturePlaneActor.PickableOn()

        self.Interactor.Render()
        
        # draw the outline map only in the XY plane
#        if self.PlaneIndex==2:
#            _range = self.outlineMap.GetPointData().GetScalars('scalars').GetRange()
            
#              bwLut = vtk.vtkLookupTable()
#              bwLut.SetTableRange (_range[0], _range[1])
#              bwLut.SetSaturationRange (0, 0) # no color saturation
#              bwLut.SetValueRange (0, 1)      # from black to white
#              bwLut.SetAlphaRange(1, 0)
#              bwLut.Build()
#              
#              map2rgb = vtk.vtkImageMapToColors()
#              map2rgb.SetInput(self.outlineMap)
#              map2rgb.SetOutputFormatToRGBA()
#              map2rgb.SetLookupTable(bwLut)
#              map2rgb.Update()
#              
#              atext = vtk.vtkTexture()
#              atext.SetInput(self.outlineMap)
#              atext.SetLookupTable(bwLut)
#             atext.SetBlendingMode(vtk.vtkTexture.VTK_TEXTURE_BLENDING_MODE_ADD)
      
#             planeMapper = vtk.vtkPolyDataMapper()
#             planeMapper.SetInputConnection(self.PlaneSource.GetOutputPort())
#             
#             self.planeActor = vtk.vtkActor()
#             self.planeActor.SetMapper(planeMapper)
# #            self.planeActor.SetTexture(atext)
#             self.planeActor.VisibilityOn()
#             self.CurrentRenderer.AddViewProp(self.planeActor)

        
    def EnablePicking( self ):
        self.TexturePlaneActor.PickableOn()  

    def DisablePicking( self ):
        self.TexturePlaneActor.PickableOff()  

    def EnableInteraction( self ):
        self.VisualizationInteractionEnabled = True 

    def DisableInteraction( self ):
        self.VisualizationInteractionEnabled = False
        
    def GetOrigin(self):
        return self.PlaneSource.GetOrigin()

#----------------------------------------------------------------------------

    def BuildRepresentation(self):    
        self.PlaneSource.Update()
        o = self.PlaneSource.GetOrigin()
        pt1 = self.PlaneSource.GetPoint1()
        pt2 = self.PlaneSource.GetPoint2()
        
        x = [ o[0] + (pt1[0]-o[0]) + (pt2[0]-o[0]), o[1] + (pt1[1]-o[1]) + (pt2[1]-o[1]), o[2] + (pt1[2]-o[2]) + (pt2[2]-o[2]) ]
        
        points = self.PlaneOutlinePolyData.GetPoints()
        points.SetPoint(0,o)
        points.SetPoint(1,pt1)
        points.SetPoint(2,x)
        points.SetPoint(3,pt2)
        points.GetData().Modified()
        self.PlaneOutlinePolyData.Modified()

#----------------------------------------------------------------------------

    def HighlightPlane( self, highlight ):   
        if ( highlight ):       
            self.PlaneOutlineActor.SetProperty(self.SelectedPlaneProperty)
            self.LastPickPosition = self.PlanePicker.GetPickPosition()        
        else:       
            self.PlaneOutlineActor.SetProperty(self.PlaneProperty)
    
#----------------------------------------------------------------------------

    def OnLeftButtonDown(self, caller, event ):
        shift = caller.GetShiftKey()
        if self.VisualizationInteractionEnabled and not shift:
            self.CurrentButton = self.LeftButtonDown
            self.StartCursor()

#----------------------------------------------------------------------------

    def OnLeftButtonUp( self, caller, event ):
#        print " ImagePlaneWidget: LeftButtonRelease "
        if self.VisualizationInteractionEnabled and (self.CurrentButton <> self.NoButtonDown):
            self.StopCursor()
            self.CurrentButton = self.NoButtonDown
        
#----------------------------------------------------------------------------

    def OnRightButtonUp( self, caller, event ):
        if self.VisualizationInteractionEnabled and (self.CurrentButton <> self.NoButtonDown):
            self.StopSliceMotion()
            self.CurrentButton = self.NoButtonDown

#----------------------------------------------------------------------------

    def OnRightButtonDown(self, caller, event ):
        shift = caller.GetShiftKey()
        if self.VisualizationInteractionEnabled and not shift:
            self.CurrentButton = self.RightButtonDown
            self.StartSliceMotion()
        
#----------------------------------------------------------------------------

    def StartCursor(self):
        if self.State == ImagePlaneWidget.Cursoring: return
    
        X = self.Interactor.GetEventPosition()[0]
        Y = self.Interactor.GetEventPosition()[1]
        self.CurrentScreenPosition = [ X, Y ]

        # Okay, make sure that the pick is in the current renderer
        if ( not self.CurrentRenderer or  not self.CurrentRenderer.IsInViewport(X, Y)):        
            self.State  = ImagePlaneWidget.Outside
            return
        
        if self.DoPick( X, Y ):      
            self.State  = ImagePlaneWidget.Cursoring
            self.HighlightPlane(1)
            self.ActivateCursor(1)
            self.UpdateCursor(X,Y)
            self.StartInteraction()
            self.ProcessEvent( self.InteractionStartEvent )
            self.Interactor.Render()       
        else:
            self.State  = ImagePlaneWidget.Outside
            self.HighlightPlane(0)
            self.ActivateCursor(0)

#----------------------------------------------------------------------------

    def ProcessEvent( self, event, **args ):
        self.ActionHandler.ProcessIPWAction( self, event, **args )
        
#----------------------------------------------------------------------------

    def HaltNavigationInteraction(self):
        if self.NavigationInteractorStyle == None:
            self.NavigationInteractorStyle = self.Interactor.GetInteractorStyle()       
        self.Interactor.SetInteractorStyle( self.ConfigurationInteractorStyle )  
#        print " ~~~~~~~~~SS SetInteractorStyle: configurationInteractorStyle: %s %x " % ( self.Interactor.GetInteractorStyle().__class__.__name__, id(self.Interactor) )        

    def ResetNavigationInteraction(self):
        if self.NavigationInteractorStyle <> None:    
            self.Interactor.SetInteractorStyle( self.NavigationInteractorStyle )  
#        print " ~~~~~~~~~ES SetInteractorStyle: navigationInteractorStyle: %s %x " % ( self.Interactor.GetInteractorStyle().__class__.__name__, id(self.Interactor) )         

#----------------------------------------------------------------------------

    def StartInteraction(self): 
        from PersistentModule import PersistentVisualizationModule
        update_rate = self.Interactor.GetDesiredUpdateRate()
        self.Interactor.GetRenderWindow().SetDesiredUpdateRate( update_rate )
        self.updateInteractor()
        self.HaltNavigationInteraction()
              
#----------------------------------------------------------------------------

    def EndInteraction(self): 
        from PersistentModule import PersistentVisualizationModule
        update_rate = self.Interactor.GetStillUpdateRate()
        self.Interactor.GetRenderWindow().SetDesiredUpdateRate( update_rate )
        self.ResetNavigationInteraction()

#----------------------------------------------------------------------------

    def ComputeWorldToDisplay( self, x, y, z ):  
        if self.CurrentRenderer == None: return None  
        self.CurrentRenderer.SetWorldPoint( x, y, z, 1.0 )
        self.CurrentRenderer.WorldToDisplay()
        return self.CurrentRenderer.GetDisplayPoint()

#----------------------------------------------------------------------------

    def ComputeDisplayToWorld( self, x, y, z ): 
        if self.CurrentRenderer == None: return None  
        self.CurrentRenderer.SetDisplayPoint(x, y, z);
        self.CurrentRenderer.DisplayToWorld();
        worldPt = list( self.CurrentRenderer.GetWorldPoint() )
        if worldPt[3]:
            worldPt[0] /= worldPt[3];
            worldPt[1] /= worldPt[3];
            worldPt[2] /= worldPt[3];
            worldPt[3] = 1.0;
        return worldPt

#----------------------------------------------------------------------------

    def StopCursor(self): 
        if ( self.State == ImagePlaneWidget.Outside or self.State == ImagePlaneWidget.Start ):   return                  
        self.ProcessEvent( self.InteractionEndEvent )
        self.State  = ImagePlaneWidget.Start
        self.HighlightPlane(0)
        if not self.ActionHandler.showInteractiveLens: self.ActivateCursor(0)
        self.EndInteraction()
        self.Interactor.Render()

#----------------------------------------------------------------------------

    def StartSliceMotion(self):
        if self.State == ImagePlaneWidget.Pushing: return
    
        X = self.Interactor.GetEventPosition()[0]
        Y = self.Interactor.GetEventPosition()[1]
        
        # Okay, make sure that the pick is in the current renderer
        if ( not self.CurrentRenderer or  not self.CurrentRenderer.IsInViewport(X, Y)):    
            self.State  = ImagePlaneWidget.Outside
            return
          
        if self.DoPick( X, Y ):      
            self.State  = ImagePlaneWidget.Pushing
            self.HighlightPlane(1) 
            self.ActivateCursor(0)                
            self.StartInteraction()
            self.ProcessEvent( self.InteractionStartEvent )
            self.Interactor.Render() 
        else:
#            print "No image plane found: %s " % str( (X,Y) )
            self.State  = ImagePlaneWidget.Outside
            self.HighlightPlane(0)                 
    
#----------------------------------------------------------------------------
    def StopSliceMotion(self):     
        if ( self.State == ImagePlaneWidget.Outside or self.State == ImagePlaneWidget.Start ): return
            
        self.ProcessEvent( self.InteractionEndEvent )
        self.State  = ImagePlaneWidget.Start
        self.HighlightPlane(0)
        
        self.EndInteraction()
        self.Interactor.Render()

#----------------------------------------------------------------------------

    def OnKeyPress(self, caller, event ):
        pass
    
#----------------------------------------------------------------------------
    
    def OnAnyEvent( self, caller, event ):
        print " ************* ImagePlaneWidget Event: ", str( event )
    
#----------------------------------------------------------------------------
   
    def OnMouseMove(self, caller, event ):
        pass

    def OnUpdateInteraction(self, caller, event ):
    
        if ( self.State == ImagePlaneWidget.Outside or self.State == ImagePlaneWidget.Start ): return        
        X = self.Interactor.GetEventPosition()[0]
        Y = self.Interactor.GetEventPosition()[1]
        self.CurrentScreenPosition = [ X, Y ]

        camera = self.CurrentRenderer.GetActiveCamera()
        if (  not camera ): return
                          
        if ( self.State == ImagePlaneWidget.Pushing ):
            # Compute the two points defining the motion vector
            #
            focalPoint = self.ComputeWorldToDisplay( self.LastPickPosition[0],  self.LastPickPosition[1],  self.LastPickPosition[2] )
            z = focalPoint[2]
            
            prevPickPoint = self.ComputeDisplayToWorld( float(self.Interactor.GetLastEventPosition()[0]), float(self.Interactor.GetLastEventPosition()[1]), z )        
            pickPoint = self.ComputeDisplayToWorld( float(X), float(Y), z )
          
            self.Push( prevPickPoint, pickPoint )
            self.UpdatePlane()
            self.BuildRepresentation()
          
        elif ( self.State == ImagePlaneWidget.Cursoring ):          
            self.UpdateCursor(X,Y)
          
        self.Interactor.Render()

#----------------------------------------------------------------------------

    def DoPick1( self, X, Y ):  
        self.PlanePicker.Pick( X, Y, 0.0, self.CurrentRenderer )
        path = self.PlanePicker.GetPath()        
        if path:
            path.InitTraversal()
            nitems =  path.GetNumberOfItems()
            for _ in range( nitems ):
                node = path.GetNextNode()
                if node: 
                    found = ( node.GetViewProp() == self.TexturePlaneActor ) 
                    return found                   
        return 0

    def DoPick( self, X, Y ):  
        self.PlanePicker.Pick( X, Y, 0.0, self.CurrentRenderer )
        path = self.PlanePicker.GetPath()        
        found = 0;
        if path:
            path.InitTraversal()
            for _ in range( path.GetNumberOfItems() ):
                node = path.GetNextNode()
                if node and (node.GetViewProp() == self.TexturePlaneActor):
                    found = 1
                    break
        return found
    
#----------------------------------------------------------------------------

    def GetCursorData(self):
        if ( self.State <> ImagePlaneWidget.Cursoring  or  self.CurrentImageValue == vtk.VTK_DOUBLE_MAX ): return None                  
        return [ self.CurrentCursorPosition[0], self.CurrentCursorPosition[1], self.CurrentCursorPosition[2], self.CurrentImageValue, self.CurrentImageValue2 ]        

#----------------------------------------------------------------------------
    def GetCursorDataStatus(self):
        if ( self.State <> ImagePlaneWidget.Cursoring  or  self.CurrentImageValue == vtk.VTK_DOUBLE_MAX ): return 0
        return 1
    
#----------------------------------------------------------------------------

    def Push( self, p1, p2 ):
        v = [  p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2] ]
        distance = vtk.vtkMath.Dot( v, self.PlaneSource.GetNormal() )
        self.PlaneSource.Push( distance )
#        print "Push Plane by distance %.3f " % distance
        self.ProcessEvent( self.InteractionUpdateEvent )

#----------------------------------------------------------------------------

    def CreateDefaultProperties(self):

        if (  not  self.PlaneProperty ):          
            self.PlaneProperty  = vtk.vtkProperty()
            self.PlaneProperty.SetAmbient(1)
            self.PlaneProperty.SetColor(1,1,1)
            self.PlaneProperty.SetRepresentationToWireframe()
            self.PlaneProperty.SetInterpolationToFlat()
                        
        if (  not  self.SelectedPlaneProperty ):           
            self.SelectedPlaneProperty  = vtk.vtkProperty()
            self.SelectedPlaneProperty.SetAmbient(1)
            self.SelectedPlaneProperty.SetColor(0,1,0)
            self.SelectedPlaneProperty.SetRepresentationToWireframe()
            self.SelectedPlaneProperty.SetInterpolationToFlat()
                       
        if (  not  self.CursorProperty ):           
            self.CursorProperty  = vtk.vtkProperty()
            self.CursorProperty.SetAmbient(1)
            self.CursorProperty.SetColor(1,0,0)
            self.CursorProperty.SetRepresentationToWireframe()
            self.CursorProperty.SetInterpolationToFlat()
                       
        if (  not  self.TexturePlaneProperty ):            
            self.TexturePlaneProperty  = vtk.vtkProperty()
            self.TexturePlaneProperty.SetAmbient(1)
            self.TexturePlaneProperty.SetInterpolationToFlat()
    
#----------------------------------------------------------------------------
    def PlaceWidget( self, bnds ):
        
        self.InputBounds = bnds
        placeFactor = self.PlaceFactor
        center = [ (bnds[0] + bnds[1])/2.0, (bnds[2] + bnds[3])/2.0,  (bnds[4] + bnds[5])/2.0 ] 
        bounds = []
        bounds.append(  center[0] + placeFactor*(bnds[0]-center[0]) )
        bounds.append(  center[0] + placeFactor*(bnds[1]-center[0]) )
        bounds.append(  center[1] + placeFactor*(bnds[2]-center[1]) )
        bounds.append(  center[1] + placeFactor*(bnds[3]-center[1]) )
        bounds.append(  center[2] + placeFactor*(bnds[4]-center[2]) )
        bounds.append(  center[2] + placeFactor*(bnds[5]-center[2]) )
        for ib in range(3): 
            if ( bounds[2*ib] == bounds[2*ib+1] ): bounds[2*ib+1] = bounds[2*ib] + 0.001
        
        if ( self.PlaneOrientation == 1 ):
#            pt1 = self.PlaneSource.GetPoint1()
            y0 = center[1] # pt1[1] # center[1]       
            self.PlaneSource.SetOrigin(bounds[0],y0,bounds[4])
            self.PlaneSource.SetPoint1(bounds[1],y0,bounds[4])
            self.PlaneSource.SetPoint2(bounds[0],y0,bounds[5])
            
        elif ( self.PlaneOrientation == 2 ):
            
            self.PlaneSource.SetOrigin(bounds[0],bounds[2],center[2])
            self.PlaneSource.SetPoint1(bounds[1],bounds[2],center[2])
            self.PlaneSource.SetPoint2(bounds[0],bounds[3],center[2])
            
        else: #default or x-normal
#            pt1 = self.PlaneSource.GetPoint1()
            x0 = center[0] # pt1[0] # center[0]
            self.PlaneSource.SetOrigin(x0,bounds[2],bounds[4])
            self.PlaneSource.SetPoint1(x0,bounds[3],bounds[4])
            self.PlaneSource.SetPoint2(x0,bounds[2],bounds[5])
                   
        self.UpdatePlane()
        self.BuildRepresentation()

#----------------------------------------------------------------------------

    def GetPlaneOrientation( self ):
        return self.PlaneOrientation   
    
#----------------------------------------------------------------------------

    def SetPlaneOrientation( self, i ):

        # Generate a XY plane if i = 2, z-normal
        # or a YZ plane if i = 0, x-normal
        # or a ZX plane if i = 1, y-normal
        #
        self.PlaneOrientation = i
        
        # This method must be called _after_ SetInput
        #
        self.ImageData  = self.Reslice.GetInput()
        if ( not self.ImageData ):        
            print>>sys.stderr, "SetInput() before setting plane orientation."
            return
               
        extent = self.ImageData.GetExtent()
        origin = self.ImageData.GetOrigin()
        spacing = self.ImageData.GetSpacing()
        
        # Prevent obscuring voxels by offsetting the plane geometry
        #
        xbounds = [ origin[0] + spacing[0] * (extent[0] - 0.5), origin[0] + spacing[0] * (extent[1] + 0.5) ]
        ybounds = [ origin[1] + spacing[1] * (extent[2] - 0.5), origin[1] + spacing[1] * (extent[3] + 0.5) ]
        zbounds = [ origin[2] + spacing[2] * (extent[4] - 0.5), origin[2] + spacing[2] * (extent[5] + 0.5) ]
        
        if ( spacing[0] < 0.0 ):
            
            t = xbounds[0]
            xbounds[0] = xbounds[1]
            xbounds[1] = t
            
        if ( spacing[1] < 0.0 ):
            
            t = ybounds[0]
            ybounds[0] = ybounds[1]
            ybounds[1] = t
            
        if ( spacing[2] < 0.0 ):
            
            t = zbounds[0]
            zbounds[0] = zbounds[1]
            zbounds[1] = t
            
            
        if ( i == 2 ): #XY, z-normal
            
            self.PlaneSource.SetOrigin(xbounds[0],ybounds[0],zbounds[0])
            self.PlaneSource.SetPoint1(xbounds[1],ybounds[0],zbounds[0])
            self.PlaneSource.SetPoint2(xbounds[0],ybounds[1],zbounds[0])
            
        elif ( i == 0 ): #YZ, x-normal
            
            self.PlaneSource.SetOrigin(xbounds[0],ybounds[0],zbounds[0])
            self.PlaneSource.SetPoint1(xbounds[0],ybounds[1],zbounds[0])
            self.PlaneSource.SetPoint2(xbounds[0],ybounds[0],zbounds[1])
            
        else:  #ZX, y-normal
            
            self.PlaneSource.SetOrigin(xbounds[0],ybounds[0],zbounds[0])
            self.PlaneSource.SetPoint1(xbounds[0],ybounds[0],zbounds[1])
            self.PlaneSource.SetPoint2(xbounds[1],ybounds[0],zbounds[0])
        
        
        self.UpdatePlane()
        self.BuildRepresentation()
        self.Modified()


#----------------------------------------------------------------------------

    def SetInput(self, inputData, inputData2=None ):
    
        self.ImageData = inputData
        self.ImageData2 = inputData2
        
        if(  not self.ImageData ):       
            # If None is passed, remove any reference that Reslice had
            # on the old ImageData
            versionAgnosticSetInput( self.Reslice, None )
            return
                   
        scalar_range = self.ImageData.GetScalarRange()
        
        if (  not self.UserControlledLookupTable ):       
            self.LookupTable.SetTableRange( scalar_range[0], scalar_range[1] )
            self.LookupTable.Build()
            
        versionAgnosticSetInput( self.Reslice, self.ImageData )
        self.Reslice.Modified()
        dims = self.ImageData.GetDimensions()
        self.InputDims = 3 if ( ( len(dims) > 2 ) and ( dims[2] > 1 ) ) else 2
             
        interpolate = self.ResliceInterpolate
        self.ResliceInterpolate = -1 # Force change
        self.SetResliceInterpolate(interpolate)
                
        self.ColorMap.SetInputConnection( self.Reslice.GetOutputPort() )   
        
        self.Texture.SetInputConnection( self.ColorMap.GetOutputPort() )   
        self.Texture.SetInterpolate(self.TextureInterpolate)
        
#        self.SetPlaneOrientation(self.PlaneOrientation)
        
#----------------------------------------------------------------------------

    def UpdatePlane(self):
        
        self.ImageData  =self.Reslice.GetInput()
        if (  not self.Reslice or not self.ImageData ): return
           
        # Calculate appropriate pixel spacing for the reslicing
        #
#        self.ImageData.UpdateInformation()
        spacing = self.ImageData.GetSpacing()
        origin = self.ImageData.GetOrigin()
        extent = self.ImageData.GetExtent()        
        bounds = [ origin[0] + spacing[0]*extent[0], origin[0] + spacing[0]*extent[1],  origin[1] + spacing[1]*extent[2],  origin[1] + spacing[1]*extent[3],  origin[2] + spacing[2]*extent[4],  origin[2] + spacing[2]*extent[5] ]    
        
        for j in range( 3 ): 
            i = 2*j   
            if ( bounds[i] > bounds[i+1] ):
                t = bounds[i+1]
                bounds[i+1] = bounds[i]
                bounds[i] = t
           
        abs_normal = list( self.PlaneSource.GetNormal() )
        planeCenter = list( self.PlaneSource.GetCenter() )
        nmax = 0.0
        k = 0
        for i in range( 3 ):    
            abs_normal[i] = abs(abs_normal[i])
            if ( abs_normal[i]>nmax ):       
                nmax = abs_normal[i]
                k = i
            
        # Force the plane to lie within the true image bounds along its normal
        #
        if ( planeCenter[k] > bounds[2*k+1] ):    
            planeCenter[k] = bounds[2*k+1]   
        elif ( planeCenter[k] < bounds[2*k] ):   
            planeCenter[k] = bounds[2*k]
               
        self.PlaneSource.SetCenter(planeCenter)
            
        planeAxis1 = self.GetVector1()
        planeAxis2 = self.GetVector2()
        
        # The x,y dimensions of the plane
        #
        planeSizeX  = vtk.vtkMath.Normalize(planeAxis1)
        planeSizeY  = vtk.vtkMath.Normalize(planeAxis2)
        normal = list( self.PlaneSource.GetNormal() )
        
        # Generate the slicing matrix
        #
        self.ResliceAxes.Identity()
        for i in range( 3 ):       
            self.ResliceAxes.SetElement(0,i,planeAxis1[i])
            self.ResliceAxes.SetElement(1,i,planeAxis2[i])
            self.ResliceAxes.SetElement(2,i,normal[i])
           
        srcPlaneOrigin = self.PlaneSource.GetOrigin()         
        planeOrigin = [ srcPlaneOrigin[0], srcPlaneOrigin[1], srcPlaneOrigin[2], 1.0 ]
        originXYZW = self.ResliceAxes.MultiplyPoint(planeOrigin)    
        self.ResliceAxes.Transpose()
        neworiginXYZW = self.ResliceAxes.MultiplyPoint(originXYZW) 
        
        self.ResliceAxes.SetElement(0,3,neworiginXYZW[0])
        self.ResliceAxes.SetElement(1,3,neworiginXYZW[1])
        self.ResliceAxes.SetElement(2,3,neworiginXYZW[2])        
        self.Reslice.SetResliceAxes(self.ResliceAxes)
        
        spacingX = abs(planeAxis1[0]*spacing[0]) + abs(planeAxis1[1]*spacing[1]) + abs(planeAxis1[2]*spacing[2])   
        spacingY = abs(planeAxis2[0]*spacing[0]) + abs(planeAxis2[1]*spacing[1]) + abs(planeAxis2[2]*spacing[2])
        
        # make sure we're working with valid values
        realExtentX = vtk.VTK_INT_MAX if ( spacingX == 0 ) else planeSizeX / spacingX       
        # make sure extentY doesn't wrap during padding
        realExtentY = vtk.VTK_INT_MAX if ( spacingY == 0 ) else planeSizeY / spacingY

        extentX = 1
        while (extentX < realExtentX): extentX = extentX << 1
        extentY = 1
        while (extentY < realExtentY): extentY = extentY << 1
            
        outputSpacingX = 1.0 if (planeSizeX == 0) else planeSizeX/extentX
        outputSpacingY = 1.0 if (planeSizeY == 0) else planeSizeY/extentY
        self.Reslice.SetOutputSpacing(outputSpacingX, outputSpacingY, 1)
        self.Reslice.SetOutputOrigin(0.5*outputSpacingX, 0.5*outputSpacingY, 0)
        self.Reslice.SetOutputExtent(0, extentX-1, 0, extentY-1, 0, 0)

        if self.ImageData2 and not self.Reslice2:
            dims2 = self.ImageData2.GetDimensions()
            self.ContourInputDims = 3 if ( ( len(dims2) > 2 ) and ( dims2[2] > 1 ) ) else 2
            self.Reslice2 = vtk.vtkImageReslice()
            self.Reslice2.TransformInputSamplingOff()
            versionAgnosticSetInput( self.Reslice2, self.ImageData2 )
            self.Reslice2.Modified()
        
        if self.Reslice2:
            self.Reslice2.SetResliceAxes(self.ResliceAxes)
            if self.ContourInputDims == 2: 
                self.ResliceAxes2.DeepCopy( self.ResliceAxes )
                self.ResliceAxes2.SetElement( 2, 3, 0.0 ) 
                self.Reslice2.SetResliceAxes(self.ResliceAxes2) 
            else: 
                self.Reslice2.SetResliceAxes(self.ResliceAxes)
            
#            print " Set contour extent = %s, spacing = %s " % ( str( (extentX,extentY) ), str( (outputSpacingX,outputSpacingY) ) )
            self.Reslice2.SetOutputSpacing(outputSpacingX, outputSpacingY, 1)
            self.Reslice2.SetOutputOrigin(0.5*outputSpacingX, 0.5*outputSpacingY, 0)
            self.Reslice2.SetOutputExtent(0, extentX-1, 0, extentY-1, 0, 0)

              
#----------------------------------------------------------------------------

    def GetResliceOutput(self):             
        return self.Reslice.GetOutput()

    def GetReslice2Output(self):      
        return self.Reslice2.GetOutput() if self.Reslice2 else None      

#----------------------------------------------------------------------------
    def SetResliceInterpolate( self, i ):
        
        if ( self.ResliceInterpolate == i ):  return
          
        self.ResliceInterpolate = i
        self.Modified()
        
        if (  not self.Reslice ): return
                  
        if ( i == VTK_NEAREST_RESLICE ):    
            self.Reslice.SetInterpolationModeToNearestNeighbor()          
        elif ( i == VTK_LINEAR_RESLICE): 
            self.Reslice.SetInterpolationModeToLinear()          
        else:                               
            self.Reslice.SetInterpolationModeToCubic()
          
        self.Texture.SetInterpolate(self.TextureInterpolate)

#----------------------------------------------------------------------------

    def SetPicker( self, picker):
        
# we have to have a picker for slice motion, window level and cursor to work
        if (self.PlanePicker <> picker):
        
            self.PlanePicker = picker            
                
            if (self.PlanePicker == None):           
                self.PlanePicker  = vtk.vtkCellPicker()
                self.PlanePicker.SetTolerance(0.005)
            
            self.PlanePicker.AddPickList(self.TexturePlaneActor)
            self.PlanePicker.PickFromListOn()

#----------------------------------------------------------------------------

    def CreateDefaultLookupTable(self):    
        lut  = vtk.vtkLookupTable()
        lut.SetNumberOfColors( 256)
        lut.SetHueRange( 0, 0)
        lut.SetSaturationRange( 0, 0)
        lut.SetValueRange( 0 ,1)
        lut.SetAlphaRange( 1, 1)
        lut.Build()
        return lut

#----------------------------------------------------------------------------

    def SetLookupTable( self, table ):
        
        if (self.LookupTable <> table):
            self.LookupTable = table       
            if (self.LookupTable == None): self.LookupTable = self.CreateDefaultLookupTable()
#            self.LookupTable.AddObserver( 'AnyEvent', self.LookupTableObserver )
#            print " Image Plane Widget %x: SetLookupTable: %x " % ( id(self), id( self.LookupTable ) )
               
        self.ColorMap.SetLookupTable(self.LookupTable)
        self.Texture.SetLookupTable(self.LookupTable)
        
        if( self.ImageData and  not self.UserControlledLookupTable):       
            scalar_range = self.ImageData.GetScalarRange()            
            self.LookupTable.SetTableRange(scalar_range[0],scalar_range[1])
            self.LookupTable.Build()
                
#----------------------------------------------------------------------------

    def SetSlicePosition( self, position ):
    
        amount = 0.0
        planeOrigin = self.PlaneSource.GetOrigin()
        
        if ( self.PlaneOrientation == 2 ): # z axis        
            amount = position - planeOrigin[2]       
        elif ( self.PlaneOrientation == 0 ): # x axis        
            amount = position - planeOrigin[0]        
        elif ( self.PlaneOrientation == 1 ):  #y axis       
            amount = position - planeOrigin[1]
                
#        print " >+++++++++> ImagePlaneWidget[%d].SetSlice: Push=%.2f " % ( self.PlaneIndex, amount )
        self.PlaneSource.Push( amount )
        self.UpdatePlane()
        self.BuildRepresentation()
        self.Modified()

#----------------------------------------------------------------------------
    def GetSlicePosition(self):
        
        planeOrigin = self.PlaneSource.GetOrigin( )
        
        if ( self.PlaneOrientation == 2 ):
        
            return planeOrigin[2]
        
        elif ( self.PlaneOrientation == 1 ):
         
            return planeOrigin[1]
        
        elif ( self.PlaneOrientation == 0 ):
          
            return planeOrigin[0]        
        
        return 0.0

#----------------------------------------------------------------------------

    def SetSliceIndex(self, index):
        
        if (  not self.Reslice ): return
        
        self.ImageData  = self.Reslice.GetInput()
        if (  not self.ImageData ): return
         
#        self.ImageData.UpdateInformation()
        origin = self.ImageData.GetOrigin()
        spacing = self.ImageData.GetSpacing()
        planeOrigin = list( self.PlaneSource.GetOrigin() )
        pt1 = list( self.PlaneSource.GetPoint1() )
        pt2 = list( self.PlaneSource.GetPoint2() )
        
        if ( self.PlaneOrientation == 2 ):
        
            planeOrigin[2] = origin[2] + index*spacing[2]
            pt1[2] = planeOrigin[2]
            pt2[2] = planeOrigin[2]
        
        elif ( self.PlaneOrientation == 1 ):
        
            planeOrigin[1] = origin[1] + index*spacing[1] 
            pt1[1] = planeOrigin[1]
            pt2[1] = planeOrigin[1]
        
        elif ( self.PlaneOrientation == 0 ):
        
            planeOrigin[0] = origin[0] + index*spacing[0] 
            pt1[0] = planeOrigin[0]
            pt2[0] = planeOrigin[0]
        
        
#        if self.PlaneIndex == 0: 
#            print " >+++++++++> ImagePlaneWidget[%d].SetSlice: Index=%d, pos=%.2f " % ( self.PlaneIndex, index, pt1[0] )
        self.PlaneSource.SetOrigin(planeOrigin)
        self.PlaneSource.SetPoint1(pt1)
        self.PlaneSource.SetPoint2(pt2)
        self.UpdatePlane()
        self.BuildRepresentation()
        self.Modified()


    def getSliceExtent(self):
        print " Get Slice Extent: PlaneIndex = %d, Orientation = %d " % ( self.PlaneIndex, self.Orientation )
        extent = self.ImageData.GetExtent()
        return ( extent[ 2*self.Orientation ], extent[ 2*self.Orientation + 1 ] )
#----------------------------------------------------------------------------

    def GetSliceIndex(self):
        
        if (  not  self.Reslice ): return 0
        
        self.ImageData  = self.Reslice.GetInput()
        if (  not  self.ImageData ): return 0
         
#        self.ImageData.UpdateInformation()
        origin = self.ImageData.GetOrigin()
        spacing = self.ImageData.GetSpacing()
        planeOrigin = self.PlaneSource.GetOrigin()
        
        if ( self.PlaneOrientation == 2 ):        
            return vtk.vtkMath.Round((planeOrigin[2]-origin[2])/spacing[2])
        
        elif ( self.PlaneOrientation == 1 ):        
            return vtk.vtkMath.Round((planeOrigin[1]-origin[1])/spacing[1])
        
        elif ( self.PlaneOrientation == 0 ):        
            return vtk.vtkMath.Round((planeOrigin[0]-origin[0])/spacing[0])
        return 0


#----------------------------------------------------------------------------
    def ActivateCursor(self, i):        
        if(  not self.CurrentRenderer ):  return        
        if( i == 0 ):   
            self.CursorActor.VisibilityOff()        
        else:           
            self.CursorActor.VisibilityOn()

#----------------------------------------------------------------------------

    def UpdateCursor( self, X, Y ):
        
        self.Reslice.Update()
        self.ImageData  = self.Reslice.GetInput()
        if (  not self.ImageData ): return
        
        # We're going to be extracting values with GetScalarComponentAsDouble(),
        # we might as well make sure that the data is there.  If the data is
        # up to date already, this call doesn't cost very much.  If we don't make
        # this call and the data is not up to date, the GetScalar... call will
        # cause a segfault.
        
        self.PlanePicker.Pick(X,Y,0.0,self.CurrentRenderer)
        self.CurrentImageValue = vtk.VTK_DOUBLE_MAX
        self.CurrentImageValue2 = vtk.VTK_DOUBLE_MAX
        
        if self.DoPick( X, Y ):    
            self.CursorActor.VisibilityOn()
        else:
            self.CursorActor.VisibilityOff()
            return
              
        q = self.PlanePicker.GetPickPosition()    
        q = self.UpdateDiscreteCursor(q)    
 
        if( q == None ):        
            self.CursorActor.VisibilityOff()
            return
 
        o = self.PlaneSource.GetOrigin()
        
        # q relative to the plane origin
        #
        qro = [ q[0] - o[0], q[1] - o[1], q[2] - o[2] ]
        
        p1o = self.GetVector1()
        p2o = self.GetVector2()        
        Lp1  = vtk.vtkMath.Dot(qro,p1o)/vtk.vtkMath.Dot(p1o,p1o)
        Lp2  = vtk.vtkMath.Dot(qro,p2o)/vtk.vtkMath.Dot(p2o,p2o)
        
        p1 = self.PlaneSource.GetPoint1()
        p2 = self.PlaneSource.GetPoint2()
               
        a = [ o[i]  + Lp2*p2o[i]  for i in range(3) ]
        b = [ p1[i] + Lp2*p2o[i]  for i in range(3) ] #  right
        c = [ o[i]  + Lp1*p1o[i]  for i in range(3) ] # bottom
        d = [ p2[i] + Lp1*p1o[i]  for i in range(3) ]  # top
                
        cursorPts = self.CursorPolyData.GetPoints()        
        cursorPts.SetPoint(0,a)
        cursorPts.SetPoint(1,b)
        cursorPts.SetPoint(2,c)
        cursorPts.SetPoint(3,d)
        
        self.CursorPolyData.Modified()
        self.ProcessEvent( self.InteractionUpdateEvent )

#----------------------------------------------------------------------------

    def UpdateDiscreteCursor( self, q ):   
        # vtkImageData will find the nearest implicit point to q
        ptId = self.ImageData.FindPoint(q)        
        if ( ptId == -1 ): return None
         
        closestPt = self.ImageData.GetPoint(ptId,)       
        origin = self.ImageData.GetOrigin()
        spacing = self.ImageData.GetSpacing()
        extent = self.ImageData.GetExtent()
        rq = []       
        for i in range(3):         
            # compute world to image coords
            iqtemp  = vtk.vtkMath.Round((closestPt[i]-origin[i])/spacing[i])           
            # we have a valid pick already, just enforce bounds check
            iq = extent[2*i] if( iqtemp < extent[2*i] ) else ( extent[2*i+1] if (iqtemp > extent[2*i+1]) else iqtemp )            
            # compute image to world coords
            rq.append( iq*spacing[i] + origin[i] )            
            self.CurrentCursorPosition[i] = int(iq)
                  
        self.CurrentImageValue = self.ImageData.GetScalarComponentAsDouble( self.CurrentCursorPosition[0], self.CurrentCursorPosition[1], self.CurrentCursorPosition[2], 0 )
        if self.ImageData2:
            extent = self.ImageData2.GetExtent() 
            pos2 = [ (self.CurrentCursorPosition[i] - self.Input2ExtentOffset[i]) for i in range(3) ] 
            self.CurrentImageValue2 = None
            if self.ContourInputDims == 3:
                if ( (pos2[0] >= extent[0]) and (pos2[0] <= extent[1]) and (pos2[1] >= extent[2]) and (pos2[1] <= extent[3]) and (pos2[2] >= extent[4]) and (pos2[2] <= extent[5]) ):
                    self.CurrentImageValue2 = self.ImageData2.GetScalarComponentAsDouble( pos2[0], pos2[1], pos2[2], 0 )
            else: 
                if ( (pos2[0] >= extent[0]) and (pos2[0] <= extent[1]) and (pos2[1] >= extent[2]) and (pos2[1] <= extent[3]) ):
                    self.CurrentImageValue2 = self.ImageData2.GetScalarComponentAsDouble( pos2[0], pos2[1], 0.0, 0 )
        return rq

#----------------------------------------------------------------------------

    def Modified(self):
        pass
#----------------------------------------------------------------------------

    def SetOrigin( self,  x,  y,  z ):
        self.PlaneSource.SetOrigin(x,y,z)
        self.Modified()


#----------------------------------------------------------------------------
    
    def GetOrigin( self ):
        return self.PlaneSource.GetOrigin()

    def GetOrigin2( self ):
        origin = self.PlaneSource.GetOrigin()
        origin2 = [ origin[i] - self.Input2Offset[i] for i in range(3) ] 
        return origin2 

#----------------------------------------------------------------------------

    def SetPoint1( self, x, y, z):
        self.PlaneSource.SetPoint1(x,y,z)
        self.Modified()

#----------------------------------------------------------------------------

    def GetPoint1(self):
        return self.PlaneSource.GetPoint1()

#----------------------------------------------------------------------------

    def SetPoint2( self, x, y, z):
        self.PlaneSource.SetPoint2(x,y,z)
        self.Modified()

#----------------------------------------------------------------------------

    def GetPoint2(self):
        return self.PlaneSource.GetPoint2()


#----------------------------------------------------------------------------

    def GetCenter(self): 
        return self.PlaneSource.GetCenter()

#----------------------------------------------------------------------------
    def GetNormal(self): 
        return self.PlaneSource.GetNormal()

#----------------------------------------------------------------------------
    def GetPolyData(self, pd):
        pd.ShallowCopy(self.PlaneSource.GetOutput())


#----------------------------------------------------------------------------
    def GetPolyDataAlgorithm(self):
        return self.PlaneSource

#----------------------------------------------------------------------------
    def UpdatePlacement(self):
        self.UpdatePlane()
        self.BuildRepresentation()

#----------------------------------------------------------------------------
    def GetTexture(self):
        return self.Texture

#----------------------------------------------------------------------------

    def GetVector1(self):
        p1 = self.PlaneSource.GetPoint1()
        o =  self.PlaneSource.GetOrigin()
        v1 = [  p1[0] - o[0], p1[1] - o[1], p1[2] - o[2] ]
        return v1

#----------------------------------------------------------------------------

    def GetVector2(self):
        p2 = self.PlaneSource.GetPoint2()
        o =  self.PlaneSource.GetOrigin()
        v2 = [  p2[0] - o[0], p2[1] - o[1], p2[2] - o[2] ]
        return v2

#----------------------------------------------------------------------------
    
    def GetResliceOutputPort(self):       
        return self.Reslice.GetOutputPort()
    
#----------------------------------------------------------------------------

    def GeneratePlaneOutline(self):
        points = vtk.vtkPoints()
        points.SetNumberOfPoints(4)
        for i in range(4): points.SetPoint(i,0.0,0.0,0.0)
                 
        cells  = vtk.vtkCellArray()
        ids = vtk.vtkIdList()
        cells.Allocate(cells.EstimateSize(4,2))
        ids.Reset()
        ids.InsertNextId(3)
        ids.InsertNextId(2)
        cells.InsertNextCell(ids)
        ids.Reset()
        ids.InsertNextId(0)
        ids.InsertNextId(1)
        cells.InsertNextCell(ids)
        ids.Reset()
        ids.InsertNextId(0)
        ids.InsertNextId(3)
        cells.InsertNextCell(ids)
        ids.Reset()
        ids.InsertNextId(1)
        ids.InsertNextId(2)
        cells.InsertNextCell(ids)
        
        self.PlaneOutlinePolyData.SetPoints(points)
        self.PlaneOutlinePolyData.SetLines(cells)
        
        planeOutlineMapper  = vtk.vtkPolyDataMapper()
        versionAgnosticSetInput( planeOutlineMapper, self.PlaneOutlinePolyData )
        planeOutlineMapper.SetResolveCoincidentTopologyToPolygonOffset()
        self.PlaneOutlineActor.SetMapper(planeOutlineMapper)
        self.PlaneOutlineActor.PickableOff()    

#----------------------------------------------------------------------------

    def GenerateTexturePlane(self):

        self.SetResliceInterpolate(self.ResliceInterpolate)       
        self.LookupTable = self.CreateDefaultLookupTable()
        
        self.ColorMap.SetLookupTable(self.LookupTable)
        self.ColorMap.SetOutputFormatToRGBA()
        self.ColorMap.PassAlphaToOutputOn()
        
        texturePlaneMapper  = vtk.vtkPolyDataMapper()
        texturePlaneMapper.SetInputConnection( self.PlaneSource.GetOutputPort() )   
        
        self.Texture.SetQualityTo32Bit()
        self.Texture.MapColorScalarsThroughLookupTableOff()
        self.Texture.SetInterpolate(self.TextureInterpolate)
        self.Texture.RepeatOff()
        self.Texture.SetLookupTable(self.LookupTable)
        
        self.TexturePlaneActor.SetMapper(texturePlaneMapper)
        self.TexturePlaneActor.SetTexture(self.Texture)
        self.TexturePlaneActor.PickableOn()

#----------------------------------------------------------------------------

    def GenerateCursor(self):
        # Construct initial points
        points  = vtk.vtkPoints()
        points.SetNumberOfPoints(4)
        for i in range(4): points.SetPoint(i,0.0,0.0,0.0)       
        cells  = vtk.vtkCellArray()
        cells.Allocate(cells.EstimateSize(2,2))
        
        ids = vtk.vtkIdList()
        ids.Reset()
        ids.InsertNextId(0)
        ids.InsertNextId(1)
        cells.InsertNextCell(ids)
        ids.Reset()
        ids.InsertNextId(2)
        ids.InsertNextId(3)
        cells.InsertNextCell(ids)
        
        self.CursorPolyData.SetPoints(points)
        self.CursorPolyData.SetLines(cells)        
        cursorMapper  = vtk.vtkPolyDataMapper()
        versionAgnosticSetInput( cursorMapper, self.CursorPolyData )
        cursorMapper.SetResolveCoincidentTopologyToPolygonOffset()
        self.CursorActor.SetMapper(cursorMapper)
        self.CursorActor.PickableOff()
        self.CursorActor.VisibilityOff()
        
if __name__ == '__main__': 
    ipw =   ImagePlaneWidget()     
