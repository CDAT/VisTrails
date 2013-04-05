'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, os, math
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
        self.opacityRange =  [ 0.8, 0.8 ]
        self.numberOfLevels = 2
        self.addConfigurableLevelingFunction( 'colorScale',    'C', label='Colormap Scale', units='data', setLevel=self.setColorScale, getLevel=self.getColorScale, layerDependent=True, adjustRangeInput=0 )
        self.addConfigurableLevelingFunction( 'opacity', 'O', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange )
#        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setInputZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )
    
    def setOpacityRange( self, opacity_range, **args  ):
#        print "Update Opacity, range = %s" %  str( opacity_range )
        self.opacityRange = opacity_range
        colormapManager = self.getColormapManager( index=0 )
        colormapManager.setAlphaRange ( [ opacity_range[0], opacity_range[0] ]  ) 
#        self.levelSetProperty.SetOpacity( opacity_range[1] )
        
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
        
    def getCurtainGeometry( self, **args ):
        path = defaultPathFile
        pathInput = self.wmod.forceGetInputFromPort( "path", None ) 
        extent =  self.input().GetExtent() 
        nStrips = extent[5] - extent[4]  
        lonData = []
        latData = []
        if pathInput <> None: 
            path = pathInput.name       
            reader = PathFileReader()
            reader.read(path)  
            latData = reader.getData( 'Latitude' )
            lonData = reader.getData( 'Longitude' )
        else:
            nPts = 100
            xstep =  (self.roi[1]-self.roi[0])/nPts
            ysize = ( self.roi[3]-self.roi[2] ) / 2.5
            y0 = ( self.roi[3]+self.roi[2] ) / 2.0
            for iPt in range(nPts):
                lonData.append( self.roi[0] + xstep*iPt )
                latData.append( y0 + ysize * math.sin( (iPt/float(nPts)) * 2.0 * math.pi ) )
        lonDataIter = iter( lonData )
#        z_inc = ( self.roi[5] - self.roi[4] ) / nStrips
        z_inc = 1.0 / nStrips
        polydata = vtk.vtkPolyData()
        stripArray = vtk.vtkCellArray()
        stripData = [ vtk.vtkIdList() for istrip in range( nStrips ) ]
        points = vtk.vtkPoints()     
        for latVal in latData:
            lonVal = lonDataIter.next()
            if ( latVal <> None ) and  ( lonVal <> None ) :
#                z = self.roi[4]
                z = 0.0
                for iLevel in range( nStrips ):
                    z = z + z_inc 
                    vtkId = points.InsertNextPoint( lonVal, latVal, z )
                    sd = stripData[ iLevel ]
                    sd.InsertNextId( vtkId )               
                    sd.InsertNextId( vtkId+1 )
                        
        for strip in stripData:
            stripArray.InsertNextCell(strip)
            
        polydata.SetPoints( points )
        polydata.SetStrips( stripArray )
        return polydata

    def updateModule(self, **args ):
        probeOutput = self.probeFilter.GetOutput()
        probeOutput.Update() 
        pts = []
        for ipt in range( 100, 200 ):
            ptd = probeOutput.GetPoint( ipt ) 
            pts.append( "(%.2f,%.2f,%.2f)" % ( ptd[0], ptd[1], ptd[2] ) ) 
            if ipt % 10 == 0: pts.append( "\n" )
        print "Sample Points:", ' '.join(pts)
           
                                   
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        self.probeFilter = vtk.vtkProbeFilter()
        textureInput = self.input()
        lut = self.getLut()                     

#            self.probeFilter = vtk.vtkProbeFilter()
#            textureGenerator = vtk.vtkImageSinusoidSource()
#            textureGenerator.SetWholeExtent ( xMin, xMax, yMin, yMax, zMin, zMax )
#            textureGenerator.SetDirection( 1.0, 1.0, 1.0 )
#            textureGenerator.SetPeriod( xMax-xMin )
#            textureGenerator.SetAmplitude( 125.0 )
#            textureGenerator.Update()
#            textureInput = textureGenerator.GetOutput() 
#            textureInput.SetSpacing( spacing )
#            textureInput.SetOrigin( origin )
            
        textureRange = textureInput.GetScalarRange()
        self.probeFilter.SetSource( textureInput )             
        curtain = self.getCurtainGeometry()
                    
        self.probeFilter.SetInput( curtain )
        self.curtainMapper = vtk.vtkPolyDataMapper()
        self.curtainMapper.SetInputConnection( self.probeFilter.GetOutputPort() ) 
        self.curtainMapper.SetScalarRange( textureRange )
                
        colormapManager = self.getColormapManager( index=0 )     
        colormapManager.setAlphaRange ( self.opacityRange ) 
        self.curtainMapper.SetLookupTable( colormapManager.lut ) 
        self.curtainMapper.UseLookupTableScalarRangeOn()
              
#        self.colormapManager.setAlphaRange ( self.opacityRange )           
#        curtainMapper.SetColorModeToMapScalars()  
#        levelSetActor = vtk.vtkLODActor() 
        curtainActor = vtk.vtkActor() 
#            curtainMapper.ScalarVisibilityOff() 
#            levelSetActor.SetProperty( self.levelSetProperty )              
        curtainActor.SetMapper( self.curtainMapper )
           
        self.renderer.AddActor( curtainActor )
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] )                                             
        self.set3DOutput()                                              
                                                

class NLevelConfigurationWidget( IVModuleConfigurationDialog ):
    """
    NLevelConfigurationWidget ...   
    """    
    def __init__(self, name, **args):
        IVModuleConfigurationDialog.__init__( self, name, **args )
        
    @staticmethod   
    def getSignature():
        return [ (Integer, 'nlevels'), ]
        
    def getValue(self):
        return int( self.nLevelCombo.currentText() )

    def setValue( self, value ):
        nLevelStr = str( value )
        itemIndex = self.nLevelCombo.findText( nLevelStr, Qt.MatchFixedString )
        if itemIndex >= 0: self.nLevelCombo.setCurrentIndex( itemIndex )
        else: print>>sys.stderr, " Illegal number of levels: %s " % nLevelStr
        
    def createContent( self ):
        nLevelTab = QWidget()        
        self.layout().addTab( nLevelTab )                 
        layout = QGridLayout()
        nLevelTab.setLayout( layout ) 
        layout.setMargin(10)
        layout.setSpacing(20)
       
        nLevel_label = QLabel( "Number of Levels:"  )
        layout.addWidget( nLevel_label, 0, 0 ) 

        self.nLevelCombo =  QComboBox ( self.parent() )
        nLevel_label.setBuddy( self.nLevelCombo )
        self.nLevelCombo.setMaximumHeight( 30 )
        layout.addWidget( self.nLevelCombo, 0,1 )
        for iLevel in range(1,6): self.nLevelCombo.addItem( str(iLevel) )   
        self.connect( self.nLevelCombo, SIGNAL("currentIndexChanged(QString)"), self.updateParameter )  



from packages.vtDV3D.WorkflowModule import WorkflowModule

class CurtainPlot(WorkflowModule):
    
    PersistentModuleClass = PM_CurtainPlot
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 

         
                
if __name__ == '__main__':
    import core.requirements, os
    from core.db.locator import FileLocator
    core.requirements.check_pyqt4()
    vistrail_filename = os.path.join( os.path.dirname( __file__ ), 'CurtainPlotDemo.vt' )

    from PyQt4 import QtGui
    import gui.application
    import sys
    import os

    try:
        v = gui.application.start_application()
        if v != 0:
            app = gui.application.get_vistrails_application()
            if app:
                app.finishSession()
            sys.exit(v)
        app = gui.application.get_vistrails_application()
        f = FileLocator(vistrail_filename)
        app.builderWindow.open_vistrail(f) 
#        app.builderWindow.viewModeChanged(0)   
    except SystemExit, e:
        app = gui.application.get_vistrails_application()
        if app:
            app.finishSession()
        sys.exit(e)
    except Exception, e:
        app = gui.application.get_vistrails_application()
        if app:
            app.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
    if (app.temp_configuration.interactiveMode and
        not app.temp_configuration.check('spreadsheetDumpCells')): 
        v = app.exec_()
    
    gui.application.stop_application()
    sys.exit(v)    
 
