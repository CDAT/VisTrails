'''
Created on Aug 15, 2012

@author: tpmaxwell
'''
import vtk

class CaptionActorManager:

    def __init__( self, mid, **args ):
      self.LeaderGlyph = None
      self.CaptionTextProperty = None
      self.CaptionActor = vtk.vtkActor2D()
      self.AttachmentPointCoordinate = vtk.vtkCoordinate()
      self.AttachmentPointCoordinate.SetCoordinateSystemToWorld()
      self.AttachmentPointCoordinate.SetValue(0.0,0.0,0.0)
    
      self.PositionCoordinate.SetCoordinateSystemToDisplay()
      self.PositionCoordinate.SetReferenceCoordinate( self.AttachmentPointCoordinate )
      self.PositionCoordinate.SetValue(static_cast<double>(10), static_cast<double>(10))
    
      # This sets up the Position2Coordinate
      self.vtkActor2D::SetWidth(0.25)
      self.vtkActor2D::SetHeight(0.10)
    
      self.Border = 1
      self.Leader = 1
      self.AttachEdgeOnly = 0
      self.ThreeDimensionalLeader = 1
      self.LeaderGlyphSize = 0.025
      self.MaximumLeaderGlyphSize = 20
      self.LeaderGlyph = NULL
    
      # Control font properties
      self.Padding = 3
    
      self.CaptionTextProperty = vtk.vtkTextProperty()
      self.CaptionTextProperty.SetBold(1)
      self.CaptionTextProperty.SetItalic(1)
      self.CaptionTextProperty.SetShadow(1)
      self.CaptionTextProperty.SetFontFamily(VTK_ARIAL)
      self.CaptionTextProperty.SetJustification(VTK_TEXT_LEFT)
      self.CaptionTextProperty.SetVerticalJustification(VTK_TEXT_BOTTOM)
    
      # What is actually drawn
      self.TextActor = vtk.vtkTextActor()
      self.TextActor.GetPositionCoordinate().SetCoordinateSystemToDisplay()
      self.TextActor.GetPositionCoordinate().SetReferenceCoordinate(NULL)
      self.TextActor.GetPosition2Coordinate().SetCoordinateSystemToDisplay()
      self.TextActor.GetPosition2Coordinate().SetReferenceCoordinate(NULL)
      self.TextActor.SetTextScaleModeToProp()
      self.TextActor.SetTextProperty(self.CaptionTextProperty)
    
      self.BorderPolyData = vtk.vtkPolyData()
      vtk.vtkPoints *pts = vtk.vtkPoints()
      pts.SetNumberOfPoints(4)
      self.BorderPolyData.SetPoints(pts)
      pts.Delete()
      vtk.vtkCellArray *border = vtk.vtkCellArray()
      border.InsertNextCell(5)
      border.InsertCellPoint(0)
      border.InsertCellPoint(1)
      border.InsertCellPoint(2)
      border.InsertCellPoint(3)
      border.InsertCellPoint(0)
      self.BorderPolyData.SetLines(border)
      border.Delete()
    
      self.BorderMapper = vtk.vtkPolyDataMapper2D()
      self.BorderMapper.SetInput(self.BorderPolyData)
      self.BorderActor = vtk.vtkActor2D()
      self.BorderActor.SetMapper(self.BorderMapper)
    
      # Set border mapper coordinate system to Display.
      vtk.vtkCoordinate *coord = vtk.vtkCoordinate()
      coord.SetCoordinateSystemToDisplay()
      self.BorderMapper.SetTransformCoordinate(coord)
      coord.Delete()
    
      # This is for glyphing the head of the leader
      # A single point with a vector for glyph orientation
      self.HeadPolyData = vtk.vtkPolyData()
      pts = vtk.vtkPoints()
      pts.SetNumberOfPoints(1)
      self.HeadPolyData.SetPoints(pts)
      pts.Delete()
      vtk.vtkDoubleArray *vecs = vtk.vtkDoubleArray()
      vecs.SetNumberOfComponents(3)
      vecs.SetNumberOfTuples(1)
      self.HeadPolyData.GetPointData().SetVectors(vecs)
      vecs.Delete()
    
      # This is the leader (line) from the attachment point to the caption
      self.LeaderPolyData = vtk.vtkPolyData()
      pts = vtk.vtkPoints()
      pts.SetNumberOfPoints(2)
      self.LeaderPolyData.SetPoints(pts)
      pts.Delete()
      vtk.vtkCellArray *leader = vtk.vtkCellArray()
      leader.InsertNextCell(2)
      leader.InsertCellPoint(0)
      leader.InsertCellPoint(1) #at the attachment point
      self.LeaderPolyData.SetLines(leader)
      leader.Delete()
    
      # Used to generate the glyph on the leader head
      self.HeadGlyph = vtk.vtkGlyph3D()
      self.HeadGlyph.SetInput(self.HeadPolyData)
      self.HeadGlyph.SetScaleModeToDataScalingOff()
      self.HeadGlyph.SetScaleFactor(0.1)
    
      # Appends the leader and the glyph head
      self.AppendLeader = vtk.vtkAppendPolyData()
      self.AppendLeader.UserManagedInputsOn()
      self.AppendLeader.SetNumberOfInputs(2)
      self.AppendLeader.SetInputByNumber(0,self.LeaderPolyData)
      self.AppendLeader.SetInputByNumber(1,self.HeadGlyph.GetOutput())
    
      # Used to transform from world to other coordinate systems
      self.MapperCoordinate2D = vtk.vtkCoordinate()
      self.MapperCoordinate2D.SetCoordinateSystemToWorld()
    
      # If 2D leader is used, then use this mapper/actor combination
      self.LeaderMapper2D = vtk.vtkPolyDataMapper2D()
      self.LeaderMapper2D.SetTransformCoordinate(self.MapperCoordinate2D)
      self.LeaderActor2D = vtk.vtkActor2D()
      self.LeaderActor2D.SetMapper(self.LeaderMapper2D)
    
      # If 3D leader is used, then use this mapper/actor combination
      self.LeaderMapper3D = vtk.vtkPolyDataMapper()
      self.LeaderActor3D = vtk.vtkActor()
      self.LeaderActor3D.SetMapper(self.LeaderMapper3D)
        
    def SetLeaderGlyph(self, glyph ):
        self.LeaderGlyph = glyph
        
    def SetCaptionTextProperty(self, glyph ):
        self.CaptionTextProperty = glyph
        
    def GetCaptionActor(self):
        return self.CaptionActor


#----------------------------------------------------------------------------
    def SetCaption(self, caption):
        self.TextActor.SetInput(caption)

#----------------------------------------------------------------------------
    def GetCaption(self):
        return self.TextActor.GetInput()


#----------------------------------------------------------------------------
     def RenderOpaqueGeometry(vtkViewport *viewport)
{
  # Build the caption (almost always needed so we don't check mtime)
  vtkDebugMacro(<<"Rebuilding caption")

  # compute coordinates and set point values
  #
  double *w1, *w2
  int *x1, *x2, *x3
  double p1[4], p2[4], p3[4]
  x1 = self.AttachmentPointCoordinate.GetComputedDisplayValue(viewport)
  x2 = self.PositionCoordinate.GetComputedDisplayValue(viewport)
  x3 = self.Position2Coordinate.GetComputedDisplayValue(viewport)
  p1[0] = (double)x1[0] p1[1] = (double)x1[1] p1[2] = 0.0
  p2[0] = (double)x2[0] p2[1] = (double)x2[1] p2[2] = p1[2]
  p3[0] = (double)x3[0] p3[1] = (double)x3[1] p3[2] = p1[2]

  # Set up the scaled text - take into account the padding
  self.TextActor.SetTextProperty(self.CaptionTextProperty)
  self.TextActor.GetPositionCoordinate().SetValue(
    p2[0]+self.Padding,p2[1]+self.Padding,0.0)
  self.TextActor.GetPosition2Coordinate().SetValue(
    p3[0]-self.Padding,p3[1]-self.Padding,0.0)

  # Define the border
  vtkPoints *pts = self.BorderPolyData.GetPoints()
  pts.SetPoint(0, p2)
  pts.SetPoint(1, p3[0],p2[1],p1[2])
  pts.SetPoint(2, p3[0],p3[1],p1[2])
  pts.SetPoint(3, p2[0],p3[1],p1[2])

  # Define the leader. Have to find the closest point from the
  # border to the attachment point. We look at the four vertices
  # and four edge centers.
  double d2, minD2, pt[3], minPt[3]
  minD2 = VTK_DOUBLE_MAX

  minPt[0] = p2[0]
  minPt[1] = p2[1]

  pt[0] = p2[0] pt[1] = p2[1] pt[2] = minPt[2] = 0.0
  if ( !self.AttachEdgeOnly &&
    (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[0] = (p2[0]+p3[0])/2.0
  if ( (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[0] = p3[0]
  if ( !self.AttachEdgeOnly &&
    (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[1] = (p2[1]+p3[1])/2.0
  if ( (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[1] = p3[1]
  if ( !self.AttachEdgeOnly &&
    (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[0] = (p2[0]+p3[0])/2.0
  if ( (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[0] = p2[0]
  if ( !self.AttachEdgeOnly &&
    (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  pt[1] = (p2[1]+p3[1])/2.0
  if ( (d2 = vtkMath::Distance2BetweenPoints(p1,pt)) < minD2 )
    {
    minD2 = d2
    minPt[0] = pt[0] minPt[1] = pt[1]
    }

  # Set the leader coordinates in appropriate coordinate system
  # The pipeline is connected differently depending on the dimension
  # and availability of a leader head.
  if ( self.Leader )
    {
    pts = self.LeaderPolyData.GetPoints()

    w1 = self.AttachmentPointCoordinate.GetComputedWorldValue(viewport)
    viewport.SetWorldPoint(w1[0],w1[1],w1[2],1.0)
    viewport.WorldToView()
    viewport.GetViewPoint(p1)

    # minPt is in display coordinates and it is OK
    double val[3]
    val[0] = minPt[0]
    val[1] = minPt[1]
    val[2] = 0
    # convert to view
    viewport.DisplayToNormalizedDisplay(val[0],val[1])
    viewport.NormalizedDisplayToViewport(val[0],val[1])
    viewport.ViewportToNormalizedViewport(val[0],val[1])
    viewport.NormalizedViewportToView(val[0],val[1],val[2])

    # use the zvalue from the attach point
    val[2] = p1[2]
    viewport.SetViewPoint(val)
    viewport.ViewToWorld()
    double w3[4]
    viewport.GetWorldPoint(w3)
    if ( w3[3] != 0.0 )
      {
      w3[0] /= w3[3] w3[1] /= w3[3] w3[2] /= w3[3]
      }
    w2 = w3

    pts.SetPoint(0, w1)
    pts.SetPoint(1, w2)
    self.HeadPolyData.GetPoints().SetPoint(0,w1)
    self.HeadPolyData.GetPointData().
      GetVectors().SetTuple3(0,w1[0]-w2[0],w1[1]-w2[1],w1[2]-w2[2])

    pts.Modified()
    self.HeadPolyData.Modified()
    }

  if ( self.LeaderGlyph )
    {
    # compute the scale
    self.LeaderGlyph.Update()
    double length = self.LeaderGlyph.GetLength()
    int *sze = viewport.GetSize()
    int   numPixels = static_cast<int> (self.LeaderGlyphSize *
      sqrt(static_cast<double>(sze[0]*sze[0] + sze[1]*sze[1])))
    numPixels = (numPixels > self.MaximumLeaderGlyphSize ?
                 self.MaximumLeaderGlyphSize : numPixels )

    # determine the number of units length per pixel
    viewport.SetDisplayPoint(sze[0]/2,sze[1]/2,0)
    viewport.DisplayToWorld()
    viewport.GetWorldPoint(p1)
    if ( p1[3] != 0.0 ) {p1[0] /= p1[3] p1[1] /= p1[3] p1[2] /= p1[3]}

    viewport.SetDisplayPoint(sze[0]/2+1,sze[1]/2+1,0)
    viewport.DisplayToWorld()
    viewport.GetWorldPoint(p2)
    if ( p2[3] != 0.0 ) {p2[0] /= p2[3] p2[1] /= p2[3] p2[2] /= p2[3]}

    # Arbitrary 1.5 factor makes up for the use of "diagonals" in length
    # calculations otherwise the scale factor tends to be too small
    double sf = 1.5 * numPixels *
      sqrt(vtkMath::Distance2BetweenPoints(p1,p2)) / length

    vtkDebugMacro(<<"Scale factor: " << sf)

    self.HeadGlyph.SetSource(self.LeaderGlyph)
    self.HeadGlyph.SetScaleFactor(sf)

    self.LeaderMapper2D.SetInput(self.AppendLeader.GetOutput())
    self.LeaderMapper3D.SetInput(self.AppendLeader.GetOutput())
    self.AppendLeader.Update()
    }
  else
    {
    self.LeaderMapper2D.SetInput(self.LeaderPolyData)
    self.LeaderMapper3D.SetInput(self.LeaderPolyData)
    self.LeaderPolyData.Update()
    }

  # assign properties
  #
  self.TextActor.SetProperty(self.GetProperty())
  self.BorderActor.SetProperty(self.GetProperty())
  self.LeaderActor2D.SetProperty(self.GetProperty())
  self.LeaderActor3D.GetProperty().SetColor(
    self.GetProperty().GetColor())

  # Okay we are ready to render something
  int renderedSomething = 0
  renderedSomething += self.TextActor.RenderOpaqueGeometry(viewport)
  if ( self.Border )
    {
    renderedSomething += self.BorderActor.RenderOpaqueGeometry(viewport)
    }

  if ( self.Leader )
    {
    if ( self.ThreeDimensionalLeader )
      {
      renderedSomething += self.LeaderActor3D.RenderOpaqueGeometry(viewport)
      }
    else
      {
      renderedSomething += self.LeaderActor2D.RenderOpaqueGeometry(viewport)
      }
    }

  return renderedSomething
}


