'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, os, sys, math
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from packages.vtk.base_module import vtkBaseModule
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
# from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.PersistentModule import *

packagePath = os.path.dirname( __file__ )  
defaultDataDir = os.path.join( packagePath, 'data' )
defaultPathFile = os.path.join( defaultDataDir,  'demoPath.csv' )

class PathFileReader:
    
    def __init__( self, **args ):
        self.cols = {}
        self.sep = args.get( 'sep', '\r' )
        self.headers = []
        
    def getData( self, header ):
        return self.cols.get( header, None )
    
    def read( self, fileName ):    
        pathFile = open( fileName, 'r' )
        data = pathFile.read().split( self.sep )
        stage = 0
        for line_data in data:
            line = line_data.split(',')
            if line == ['']:
                if stage == 0: stage = 1 
            else:
                if stage == 1:
                    for item in line:
                       self.headers.append( item ) 
                    stage = 2
                elif stage == 2:
                    headerIter = iter( self.headers )
                    for item in line:
                        try:
                            header = headerIter.next()
                            col = self.cols.setdefault( header, [] ) 
                            if (item == '') or (item == None):
                                col.append( None )
                            else:
                                try:
                                    col.append( float(item) )  
                                except ValueError: 
                                    col.append( item ) 
                        except StopIteration: break                                           
        pathFile.close()


         
class PM_CurtainPlot(PersistentVisualizationModule):
    """
        This module generates curtain plots from 3D volumetric (<i>vtkImagedata</i>) data and a trajectory file.  The
    colormap and colorscaling can also be configured by gui and leveling commands respectively.  The <b>opacity</b> of the curtains
    is configured using the opacity leveling function. 
    <h3>  Command Keys </h3>   
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> l </td> <td> Toggle show colorbar. </td>
        </table>
    """
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, **args)
        self.opacityRange =  [ 0.0, 1.0 ]
        self.addConfigurableLevelingFunction( 'colorScale',    'C', label='Colormap Scale', units='data', setLevel=self.setColorScale, getLevel=self.getColorScale, layerDependent=True, adjustRangeInput=0 )
#        self.addConfigurableLevelingFunction( 'opacity', 'O', label='Curtain Opacity', activeBound='min', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange, layerDependent=True )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setInputZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )
        self.trajectory = None
        self.spline = vtk.vtkSplineWidget()

    def setInputZScale( self, zscale_data, **args  ): 
        rv = PersistentVisualizationModule.setInputZScale( self,  zscale_data, **args )      
        curtain = self.getCurtainGeometry()                   
        self.probeFilter.SetInput( curtain )
        return rv
    
    def setOpacityRange( self, opacity_range, **args  ):
        self.opacityRange = opacity_range
        colormapManager = self.getColormapManager( index=0 )
        colormapManager.setAlphaRange ( [ opacity_range[0], opacity_range[0] ]  ) 
        self.curtainMapper.Modified()
        
    def setColorScale( self, range, cmap_index=0, **args  ):
        ispec = self.getInputSpec( cmap_index )
        if ispec and ispec.input():
            imageRange = self.getImageValues( range[0:2], cmap_index ) 
            colormapManager = self.getColormapManager( index=cmap_index )
            colormapManager.setScale( imageRange, range )
            self.curtainMapper.Modified()

    def getColorScale( self, cmap_index=0 ):
        sr = self.getDataRangeBounds( cmap_index )
        return [ sr[0], sr[1], 0 ]

    def getOpacityRange( self ):
        return [ self.opacityRange[0], self.opacityRange[1], 0 ]
        
    def finalizeConfiguration( self ):
        PersistentVisualizationModule.finalizeConfiguration( self )
        self.render()

    def setInteractionState( self, caller, event ):
        PersistentVisualizationModule.setInteractionState( self, caller, event )
        
    def computeInitialTrajectory(self):
        path = defaultPathFile
        pathInput = self.wmod.forceGetInputFromPort( "path", None ) 
        lonData = []
        latData = []
        if pathInput <> None: 
            path = pathInput.name       
            reader = PathFileReader()
            reader.read(path)  
            latData = reader.getData( 'Latitude' )
            lonData = reader.getData( 'Longitude' )
        else:
            spline_span_length = 10
            n_spline_spans = 10
            nPts = spline_span_length * n_spline_spans 
            xstep =  (self.roi[1]-self.roi[0])/nPts
            ysize = ( self.roi[3]-self.roi[2] ) / 2.5
            y0 = ( self.roi[3]+self.roi[2] ) / 2.0
            self.spline.SetNumberOfHandles( n_spline_spans + 1 )
            self.spline.SetResolution( spline_span_length*50 )
            self.spline.SetProjectionNormalToZAxes() 
            self.spline.SetProjectToPlane(2)       
            for iPt in range(nPts+1):
                x = self.roi[0] + xstep*iPt
                y = y0 + ysize * math.sin( (iPt/float(nPts)) * 2.0 * math.pi )
                lonData.append( x )
                latData.append( y )
                if iPt % spline_span_length == 0:
                    iH = iPt/spline_span_length 
                    self.spline.SetHandlePosition ( iH, x, y, 0.0 )
        return ( lonData, latData )
 
    def getCurtainGeometryFromSpline( self, **args ):
        polyData = vtk.vtkPolyData()
        self.spline.GetPolyData( polyData )
        npts = polyData.GetNumberOfPoints()
        print "Get Curtain Geometry From Spline, NP = ", npts
        sys.stdout.flush()                
        extent =  self.input().GetExtent() 
        spacing =  self.input().GetSpacing() 
        nStrips = extent[5] - extent[4] 
        zmax = spacing[2] * nStrips
        z_inc = zmax / nStrips
        polydata = vtk.vtkPolyData()
        stripArray = vtk.vtkCellArray()
        stripData = [ vtk.vtkIdList() for istrip in range( nStrips ) ]
        points = vtk.vtkPoints()  
        for iPt in range( npts ):  
            ptcoords = polyData.GetPoint( iPt )
            z = 0.0
            for iLevel in range( nStrips ):
                vtkId = points.InsertNextPoint( ptcoords[0], ptcoords[1], z )
                sd = stripData[ iLevel ]
                sd.InsertNextId( vtkId )               
                sd.InsertNextId( vtkId+1 )
                z = z + z_inc 
            points.InsertNextPoint( ptcoords[0], ptcoords[1], z )
                       
        for strip in stripData:
            stripArray.InsertNextCell(strip)
            
        polydata.SetPoints( points )
        polydata.SetStrips( stripArray )
        return polydata
       
    def getCurtainGeometry( self, **args ):
        if self.trajectory == None: self.trajectory = self.computeInitialTrajectory()
        ( lonData, latData ) = self.trajectory
        extent =  self.input().GetExtent() 
        spacing =  self.input().GetSpacing() 
        nStrips = extent[5] - extent[4] 
        zmax = spacing[2] * nStrips
        lonDataIter = iter( lonData )
        z_inc = zmax / nStrips
        polydata = vtk.vtkPolyData()
        stripArray = vtk.vtkCellArray()
        stripData = [ vtk.vtkIdList() for istrip in range( nStrips ) ]
        points = vtk.vtkPoints()     
        for latVal in latData:
            lonVal = lonDataIter.next()
            z = 0.0
            for iLevel in range( nStrips ):
                vtkId = points.InsertNextPoint( lonVal, latVal, z )
                sd = stripData[ iLevel ]
                sd.InsertNextId( vtkId )               
                sd.InsertNextId( vtkId+1 )
                z = z + z_inc 
            points.InsertNextPoint( lonVal, latVal, z )
                       
        for strip in stripData:
            stripArray.InsertNextCell(strip)
            
        polydata.SetPoints( points )
        polydata.SetStrips( stripArray )
        return polydata

    def updateModule(self, **args ):
        textureInput = self.input()
        self.probeFilter.SetSource( textureInput )      
        self.probeFilter.Modified()
        self.set3DOutput()
                
#        curtain = self.getCurtainGeometry()                   
#        self.probeFilter.SetInput( curtain )
#        probeOutput = self.probeFilter.GetOutput()
#        probeOutput.Update() 
#        self.render()
#        pts = []
#        for ipt in range( 400, 500 ):
#            ptd = probeOutput.GetPoint( ipt ) 
#            pts.append( "(%.2f,%.2f,%.2f)" % ( ptd[0], ptd[1], ptd[2] ) ) 
#            if ipt % 10 == 0: pts.append( "\n" )
#        print "Sample Points:", ' '.join(pts)
           
    def activateWidgets( self, iren ):
        self.spline.SetInteractor( iren )       
        self.addObserver( self.spline, 'EndInteractionEvent', self.onTrajectoryModified )

    def onTrajectoryModified( self, caller, event ):
#        print " onTrajectoryModified: %s " % ( str(event) )
        curtain = self.getCurtainGeometryFromSpline()
        self.probeFilter.SetInput( curtain )
        return 0
                                   
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        self.probeFilter = vtk.vtkProbeFilter()
        textureInput = self.input()            
        textureRange = textureInput.GetScalarRange()
        self.probeFilter.SetSource( textureInput )             
        self.curtainMapper = vtk.vtkPolyDataMapper()
        self.curtainMapper.SetInputConnection( self.probeFilter.GetOutputPort() ) 
        self.curtainMapper.SetScalarRange( textureRange )
                
        colormapManager = self.getColormapManager( index=0 )     
        colormapManager.setAlphaRange ( [ 1.0, 1.0 ]  )
        self.curtainMapper.SetLookupTable( colormapManager.lut ) 
        self.curtainMapper.UseLookupTableScalarRangeOn()
              
        curtainActor = vtk.vtkActor() 
        curtainActor.SetMapper( self.curtainMapper )           
        self.renderer.AddActor( curtainActor )
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )                                            
        self.set3DOutput()                                              
                                                
from packages.vtDV3D.WorkflowModule import WorkflowModule

class CurtainPlot(WorkflowModule):
    
    PersistentModuleClass = PM_CurtainPlot
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 

 