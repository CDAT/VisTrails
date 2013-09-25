'''
Created on Sep 25, 2013

@author: tpmaxwel
'''


import vtk, sys

VTK_NEAREST_RESLICE = 0
VTK_LINEAR_RESLICE  = 1
VTK_CUBIC_RESLICE   = 2

class cpcPlaneWidget:  
    
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
    
    def __init__( self, actionHandler, picker, planeIndex, **args ):  
        self.State  = cpcPlaneWidget.Start            
        self.Interaction  = 1
        self.PlaneIndex = planeIndex
        self.ActionHandler = actionHandler
        self.Interactor = None
        self.Enabled = False
        self.VisualizationInteractionEnabled = True
        self.CurrentRenderer = None
        self.CurrentButton = self.NoButtonDown
        self.CurrentScreenPosition = None
        self.RenderWindow = None
        self.PlaceFactor = 0.5;
        self.PlaneOrientation   = 0
        self.PlaceFactor  = 1.0
        self.NavigationInteractorStyle = None
        self.ConfigurationInteractorStyle = vtk.vtkInteractorStyleUser()
                         
        # Represent the plane's outline
        #
        self.PlaneSource  = vtk.vtkPlaneSource()
        self.PlaneSource.SetXResolution(1)
        self.PlaneSource.SetYResolution(1)
        self.PlaneOutlinePolyData  = vtk.vtkPolyData()
        self.PlaneOutlineActor     = vtk.vtkActor()
                                                
        self.GeneratePlaneOutline()
            
        # Define some default point coordinates
        #
        bounds = [ -0.5, 0.5, -0.5, 0.5, -0.5, 0.5 ]
            
        # Initial creation of the widget, serves to initialize it
        #
        self.PlaceWidget(bounds)
                                    
        # Set up the initial properties
        #
        self.PlaneProperty   = 0
        self.SelectedPlaneProperty = 0
        self.CreateDefaultProperties()

    def __del__(self):
        print " **************************************** Deleting cpcPlaneWidget module, id = %d  **************************************** " % id(self)
        sys.stdout.flush()


    def GetCurrentButton(self): 
        return self.CurrentButton
            
    def SetPlaneProperty( self, value ):
        self.PlaneProperty = value
        
    def GetPlaneProperty(self):
        return self.PlaneProperty

    def SetSelectedPlaneProperty( self, value ):
        self.SelectedPlaneProperty = value
        
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
    
        self.Interactor.Render()
        
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
#        print " cpcPlaneWidget: LeftButtonRelease "
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
        update_rate = self.Interactor.GetDesiredUpdateRate()
        self.Interactor.GetRenderWindow().SetDesiredUpdateRate( update_rate )
        self.updateInteractor()
        self.HaltNavigationInteraction()
              
#----------------------------------------------------------------------------

    def EndInteraction(self): 
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

    def StartSliceMotion(self):
        if self.State == cpcPlaneWidget.Pushing: return
    
        X = self.Interactor.GetEventPosition()[0]
        Y = self.Interactor.GetEventPosition()[1]
        
        # Okay, make sure that the pick is in the current renderer
        if ( not self.CurrentRenderer or  not self.CurrentRenderer.IsInViewport(X, Y)):    
            self.State  = cpcPlaneWidget.Outside
            return
          
        if self.DoPick( X, Y ):      
            self.State  = cpcPlaneWidget.Pushing
            self.HighlightPlane(1)               
            self.StartInteraction()
            self.ProcessEvent( self.InteractionStartEvent )
            self.Interactor.Render() 
        else:
#            print "No image plane found: %s " % str( (X,Y) )
            self.State  = cpcPlaneWidget.Outside
            self.HighlightPlane(0)                 
    
#----------------------------------------------------------------------------
    def StopSliceMotion(self):     
        if ( self.State == cpcPlaneWidget.Outside or self.State == cpcPlaneWidget.Start ): return
            
        self.ProcessEvent( self.InteractionEndEvent )
        self.State  = cpcPlaneWidget.Start
        self.HighlightPlane(0)
        
        self.EndInteraction()
        self.Interactor.Render()

#----------------------------------------------------------------------------

    def OnKeyPress(self, caller, event ):
        pass
    
#----------------------------------------------------------------------------
    
    def OnAnyEvent( self, caller, event ):
        print " ************* cpcPlaneWidget Event: ", str( event )
    
#----------------------------------------------------------------------------
   
    def OnMouseMove(self, caller, event ):
        pass

    def OnUpdateInteraction(self, caller, event ):
    
        if ( self.State == cpcPlaneWidget.Outside or self.State == cpcPlaneWidget.Start ): return        
        X = self.Interactor.GetEventPosition()[0]
        Y = self.Interactor.GetEventPosition()[1]
        self.CurrentScreenPosition = [ X, Y ]

        camera = self.CurrentRenderer.GetActiveCamera()
        if (  not camera ): return
                          
        if ( self.State == cpcPlaneWidget.Pushing ):
            # Compute the two points defining the motion vector
            #
            focalPoint = self.ComputeWorldToDisplay( self.LastPickPosition[0],  self.LastPickPosition[1],  self.LastPickPosition[2] )
            z = focalPoint[2]
            
            prevPickPoint = self.ComputeDisplayToWorld( float(self.Interactor.GetLastEventPosition()[0]), float(self.Interactor.GetLastEventPosition()[1]), z )        
            pickPoint = self.ComputeDisplayToWorld( float(X), float(Y), z )
          
            self.Push( prevPickPoint, pickPoint )
            self.UpdatePlane()
            self.BuildRepresentation()
                    
        self.Interactor.Render()
       
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
               
        self.ImageData.UpdateInformation()
        extent = self.ImageData.GetWholeExtent()
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

    def UpdatePlane(self):
        
        self.ImageData  =self.Reslice.GetInput()
        if (  not self.Reslice or not self.ImageData ): return
           
        # Calculate appropriate pixel spacing for the reslicing
        #
        self.ImageData.UpdateInformation()
        spacing = self.ImageData.GetSpacing()
        origin = self.ImageData.GetOrigin()
        extent = self.ImageData.GetWholeExtent()        
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
                
#        print " >+++++++++> cpcPlaneWidget[%d].SetSlice: Push=%.2f " % ( self.PlaneIndex, amount )
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

    def Modified(self):
        pass
#----------------------------------------------------------------------------

    def SetOrigin( self,  x,  y,  z ):
        self.PlaneSource.SetOrigin(x,y,z)
        self.Modified()    
 
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
        planeOutlineMapper.SetInput( self.PlaneOutlinePolyData )
        planeOutlineMapper.SetResolveCoincidentTopologyToPolygonOffset()
        self.PlaneOutlineActor.SetMapper(planeOutlineMapper)
        self.PlaneOutlineActor.PickableOff()    

        
if __name__ == '__main__': 
    ipw =   cpcPlaneWidget()     

