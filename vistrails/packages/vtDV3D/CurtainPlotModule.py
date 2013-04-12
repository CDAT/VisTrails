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

def displayMessage( msg ):
     msgBox = QMessageBox()
     msgBox.setText(msg)
     msgBox.exec_() 
 
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
        self.n_spline_spans = 10
        self.spline_resolution = 20
        self.addConfigurableLevelingFunction( 'colorScale',    'C', label='Colormap Scale', units='data', setLevel=self.setColorScale, getLevel=self.getColorScale, layerDependent=True, adjustRangeInput=0 )
#        self.addConfigurableLevelingFunction( 'opacity', 'O', label='Curtain Opacity', activeBound='min', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange, layerDependent=True )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setInputZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )
        self.addConfigurableLevelingFunction( 'nHandles', 'H', label='Number Of Handles', setLevel=self.setNumberOfHandles, activeBound='max', getLevel=self.getNumberOfHandles, windowing=False, initRange=[ 3.0, self.n_spline_spans, 1 ] )
#        self.addConfigurableLevelingFunction( 'splineRes', 'T', label='Trajectory Resolution', setLevel=self.setSplineResolution, activeBound='max', getLevel=self.getSplineResolution, windowing=False, initRange=[ 5.0, self.spline_resolution, 1 ] )
        self.addConfigurableMethod('Reset Path', self.resetSpline, 'R' )
        self.addConfigurableMethod('Read Path File', self.readPath, 'E' )
        self.addConfigurableMethod('Save Path', self.savePath, 'S' )
        self.addConfigurableMethod('Toggle Path Edit', self.toggleEditSpline, 'I' )
        self.trajectory = None
        self.editMode = False
        self.firstEdit = True
        self.modifiedPoints = None
        self.nPoints = 100
        self.initNewSpline()
        self.curtainModified = False
        self.activated = False

    def initNewSpline( self, **args ):
        handle_points = args.get( 'handles', None )
        self.spline = vtk.vtkSplineWidget() 
        self.spline.SetProjectionNormalToZAxes() 
        self.spline.SetProjectToPlane(2) 
        if self.iren: self.activateSpline( self.iren ) 
        if handle_points: self.modifyTrajectory( handle_points, **args )   
     
    def setInputZScale( self, zscale_data, **args  ): 
        rv = PersistentVisualizationModule.setInputZScale( self,  zscale_data, **args )      
        curtain = self.createCurtain()                
        self.probeFilter.SetInput( curtain )
        return rv
    
    def getTrajectoryPoints( self, **args ):
        isModification = args.get( "isModification", False )
        if isModification: self.curtainModified = True
        if self.curtainModified: return self.getSplinePoints( isModification )
        if self.trajectory == None: self.trajectory = self.computeInitialTrajectory()         
        return self.trajectory
    
    def resetSpline(self):
        self.curtainModified = False
        self.modifiedPoints = None
        curtain = self.createCurtain(  )                  
        self.probeFilter.SetInput( curtain )
        handle_points = self.getHandlesFromTrajectoryPoints( self.getTrajectoryPoints() )
        if handle_points: self.modifyTrajectory( handle_points )  
        self.render()
               
    def setNumberOfHandles(self, nhandles_data, **args  ):
        if self.editMode:
            ns = int( round( nhandles_data[1] ) )
            if ns <> self.n_spline_spans:
                self.resetHandles(ns)          
        elif self.activated: 
            displayMessage( " Must be in path edit mode to use this feature (click 'Toggle Edit Path'). " )
           
    def setSplineResolution(self, tres_data, **args  ):
        sr = int( round( tres_data[1] ) )
        if sr <> self.spline_resolution:
            self.resetResolution(sr)
            
    def getNumberOfHandles(self):
        return [ 3.0, 50.0, 1.0 ]

    def getSplineResolution(self):
        return [ 2.0, 100.0, 1.0 ]
    
    def savePath(self):
        qFilePath = QFileDialog.getSaveFileName( None, QString("Save path file"), os.path.expanduser('~'), QString("Path Files (*.path)") )
        ftok = str(qFilePath).split('.')
        if ftok[-1] <> 'path': ftok.append( 'path' )
        fname =  '.'.join(ftok)
        f = QFile( QString( fname ) )
        if not f.open( QIODevice.WriteOnly | QIODevice.Text ):
            displayMessage( " Can't open this file. " )
            return
        out = QTextStream (f)
        nh = self.spline.GetNumberOfHandles()
        for iH in range( nh ):
            hpos = self.spline.GetHandlePosition(iH)
            out << "%.2f,%.2f\n" %  ( hpos[0], hpos[1] )
        f.close()

    def readPath(self):
        filename = QFileDialog.getOpenFileName( None, QString("Read path file"), os.path.expanduser('~'), QString("Path Files (*.path)") )
        f = QFile( filename )
        if not f.open( QIODevice.ReadOnly | QIODevice.Text ):
            displayMessage( " Can't open this file. " )
            return
        instream = QTextStream(f)
        handle_points = vtk.vtkPoints()
        handle_points.SetDataTypeToFloat()
        while not instream.atEnd():
            line = str( instream.readLine() )
            coords =line.split(',') 
            handle_points.InsertNextPoint( float(coords[0]), float(coords[1]), 0.0 ) 
            print "Insert Point: %s " % str( [ float(coords[0]), float(coords[1]) ] )
        f.close() 
        self.modifyTrajectory( handle_points, isModification=True )          

    def modifyTrajectory( self, handle_points, **args ):
        self.spline.InitializeHandles( handle_points )
        if not self.editMode: self.spline.SetEnabled( True )
        curtain = self.createCurtain( **args ) 
        self.probeFilter.SetInput( curtain )
        if not self.editMode: self.spline.SetEnabled( False )  
        self.render()
                   
    def toggleEditSpline( self, notify=True ):
        self.editMode = not self.editMode 
        self.spline.SetEnabled( self.editMode )
        self.spline.SetProcessEvents( self.editMode ) 
        if self.editMode and self.firstEdit:
            if notify: displayMessage( " Click on the yellow curved line and then drag the handles (spheres) to modify the trajectory." )
            self.firstEdit = False
           
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
        points = vtk.vtkPoints()
        if pathInput <> None: 
            path = pathInput.name       
            reader = PathFileReader()
            reader.read(path)  
            latData = reader.getData( 'Latitude' )
            lonData = reader.getData( 'Longitude' )
            for iPt in range(len(latData)):
                points.InsertNextPoint( lonData[iPt], latData[iPt], 0.0 ) 
        else:
            nPts = self.nPoints 
            xstep =  (self.roi[1]-self.roi[0]) / nPts
            ysize = ( self.roi[3]-self.roi[2] ) / 2.5
            y0 = ( self.roi[3]+self.roi[2] ) / 2.0
            for iPt in range( nPts + 1 ):
                x = self.roi[0] + xstep*iPt
                y = y0 + ysize * math.sin( (iPt/float(nPts)) * 2.0 * math.pi )
                points.InsertNextPoint( x, y, 0.0 )
        return points
    
    def getSplinePoints( self, isModification ):
        polyData = vtk.vtkPolyData()
        self.spline.GetPolyData( polyData )
        if isModification: self.modifiedPoints = polyData
        return polyData
 
#    def getCurtainGeometryFromSpline( self, **args ):
#        if self.trajectory == None: 
#            self.trajectory = self.computeInitialTrajectory()
#        polyData = vtk.vtkPolyData()
#        self.spline.GetPolyData( polyData )
#        npts = polyData.GetNumberOfPoints()
#        isModification = args.get( "isModification", False )
#        if isModification: self.modifiedPoints = polyData
#        print "----------------------------------------------------"
#        print " ** Get Curtain Geometry From Spline, NP = %d **" % npts
#        print "----------------------------------------------------"
#        sys.stdout.flush()                
#        extent =  self.input().GetExtent() 
#        spacing =  self.input().GetSpacing() 
#        nStrips = extent[5] - extent[4] 
#        zmax = spacing[2] * nStrips
#        z_inc = zmax / nStrips
#        polydata = vtk.vtkPolyData()
#        stripArray = vtk.vtkCellArray()
#        stripData = [ vtk.vtkIdList() for istrip in range( nStrips ) ]
#        points = vtk.vtkPoints() 
#        nH = self.spline.GetNumberOfHandles ()
#        for iPt in range( npts ):  
#            ptcoords = polyData.GetPoint( iPt )
#            z = 0.0
#            for iLevel in range( nStrips ):
#                vtkId = points.InsertNextPoint( ptcoords[0], ptcoords[1], z )
#                sd = stripData[ iLevel ]
#                sd.InsertNextId( vtkId )               
#                sd.InsertNextId( vtkId+1 )
#                z = z + z_inc 
#            points.InsertNextPoint( ptcoords[0], ptcoords[1], z )
#                       
#        for strip in stripData:
#            stripArray.InsertNextCell(strip)
#            
#        polydata.SetPoints( points )
#        polydata.SetStrips( stripArray )
#        self.curtainModified = True
#        return polydata

    def getHandlesFromTrajectoryPoints( self, points ):
        npts = points.GetNumberOfPoints() if points else 0
        handle_points = None
        if npts:
            handle_points = vtk.vtkPoints()
            handle_step = npts / self.n_spline_spans
            for iS in range( self.n_spline_spans ):
                iPt = iS*handle_step
                ptcoords = points.GetPoint( iPt )
                handle_points.InsertNextPoint( ptcoords[0], ptcoords[1], 0.0 )
            ptcoords = points.GetPoint( npts-1 )
            handle_points.InsertNextPoint( ptcoords[0], ptcoords[1], 0.0 ) 
        return handle_points          
    
    def resetHandles( self, nspans ):
        if not self.editMode: self.toggleEditSpline()
        self.n_spline_spans = nspans
        handle_points = self.getHandlesFromTrajectoryPoints( self.modifiedPoints )
        if handle_points:
            self.modifyTrajectory( handle_points )
        else: 
            curtain = self.createCurtain()
            self.probeFilter.SetInput( curtain )


#    def resetResolution( self, sr ):
#        self.spline_resolution = sr
#        npts = self.modifiedPoints.GetNumberOfPoints() if self.modifiedPoints else 0
#        spline_coords = []
#        if npts:
#            handle_step = npts / self.n_spline_spans
#            for iS in range( self.n_spline_spans ):
#                iPt = iS*handle_step
#                ptcoords = self.modifiedPoints.GetPoint( iPt )
#                spline_coords.append( ptcoords )
#            ptcoords = self.modifiedPoints.GetPoint( npts-1 )
#            spline_coords.append( ptcoords )
#        else:
#            ( lonData, latData ) = self.trajectory
#            npts = len(latData)
#            handle_step = npts / self.n_spline_spans
#            for iPt in range( 0, npts, handle_step ):
#                 latVal = latData[iPt]
#                 lonVal = lonData[iPt]
#                 spline_coords.append( ( lonData[iPt], latData[iPt] ) ) 
#        nHandles = len(spline_coords)          
#        spline_span_length = self.nPoints / self.n_spline_spans 
#        self.spline.SetNumberOfHandles( nHandles )
##        self.spline.SetResolution( spline_span_length * self.spline_resolution )
#        self.spline.SetProjectionNormalToZAxes() 
#        self.spline.SetProjectToPlane(2) 
#        for iS in range( nHandles ):
#            ptcoords = spline_coords[iS]      
#            self.spline.SetHandlePosition ( iS, ptcoords[0], ptcoords[1], 0.0 )
#        curtain = self.getCurtainGeometryFromSpline()
#        self.probeFilter.SetInput( curtain )           
#        npts = curtain.GetNumberOfPoints()
#        print " *** Set Spline Resolution: %d, npts = %d, handles = %s " % ( sr, npts, str(spline_coords) )            
       

#    def getCurtainGeometry( self, **args ):
#        if self.trajectory == None: self.trajectory = self.computeInitialTrajectory()
#        ( lonData, latData ) = self.trajectory
#        extent =  self.input().GetExtent() 
#        spacing =  self.input().GetSpacing() 
#        nStrips = extent[5] - extent[4] 
#        zmax = spacing[2] * nStrips
#        lonDataIter = iter( lonData )
#        z_inc = zmax / nStrips
#        polydata = vtk.vtkPolyData()
#        stripArray = vtk.vtkCellArray()
#        stripData = [ vtk.vtkIdList() for istrip in range( nStrips ) ]
#        points = vtk.vtkPoints() 
#        spline_span_length = self.nPoints / self.n_spline_spans 
#        self.spline.SetNumberOfHandles( self.n_spline_spans + 1 )
#        iPt = 0  
#        for latVal in latData:
#            lonVal = lonDataIter.next()
#            z = 0.0
#            for iLevel in range( nStrips ):
#                vtkId = points.InsertNextPoint( lonVal, latVal, z )
#                sd = stripData[ iLevel ]
#                sd.InsertNextId( vtkId )               
#                sd.InsertNextId( vtkId+1 )
#                z = z + z_inc 
#            if iPt % spline_span_length == 0:
#                iH = iPt / spline_span_length 
#                self.spline.SetHandlePosition ( iH, lonVal, latVal, 0.0 )
#            points.InsertNextPoint( lonVal, latVal, z )
#            iPt = iPt+1
#                       
#        for strip in stripData:
#            stripArray.InsertNextCell(strip)
#            
#        polydata.SetPoints( points )
#        polydata.SetStrips( stripArray )
#        return polydata

    def createCurtain( self, **args ):
        trajectory_points = self.getTrajectoryPoints( **args )
        extent =  self.input().GetExtent() 
        spacing =  self.input().GetSpacing() 
        nStrips = extent[5] - extent[4] 
        zmax = spacing[2] * nStrips
        z_inc = zmax / nStrips
        polydata = vtk.vtkPolyData()
        stripArray = vtk.vtkCellArray()
        stripData = [ vtk.vtkIdList() for ix in range(nStrips) ] 
        points = vtk.vtkPoints() 
        for iPt in range( trajectory_points.GetNumberOfPoints() ):
            pt_coords = trajectory_points.GetPoint( iPt )
            z = 0.0
            for iLevel in range( nStrips ):
                vtkId = points.InsertNextPoint( pt_coords[0], pt_coords[1], z )
                sd = stripData[ iLevel ]
                sd.InsertNextId( vtkId )               
                sd.InsertNextId( vtkId+1 )
                z = z + z_inc 
            points.InsertNextPoint( pt_coords[0], pt_coords[1], z )
                       
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
        if iren: self.activateSpline( iren )
           
    def activateSpline( self, iren ):
        self.spline.SetInteractor( iren )       
        self.addObserver( self.spline, 'EndInteractionEvent', self.onTrajectoryModified )
        self.activated = True
        handle_points = self.getHandlesFromTrajectoryPoints( self.getTrajectoryPoints() )
        if handle_points: self.modifyTrajectory( handle_points )  

#        self.addObserver( self.spline, 'AnyEvent', self.onAnyEvent )

#    def onAnyEvent( self, caller, event ):
#        code = self.iren.GetKeyCode()
#        epos = self.iren.GetEventPosition()
#        if ( event == "KeyPressEvent" ) or ( event == "KeyReleaseEvent" ):
#            print "Key Press Position: %s " % str( epos )

    def onTrajectoryModified( self, caller, event ):
        curtain = self.createCurtain( isModification=True ) 
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

 