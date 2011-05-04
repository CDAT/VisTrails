'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from packages.vtk.base_module import vtkBaseModule
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from InteractiveConfiguration import QtWindowLeveler 
from vtUtilities import *
from PersistentModule import *

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
        self.addConfigurableLevelingFunction( 'colorScale', 'C', setLevel=self.setColorScale, getLevel=self.getColorScale, getInitLevel=self.getScalarRange )
        self.addConfigurableLevelingFunction( 'opacity', 'O', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange )
        pass
    
    def setOpacityRange( self, opacity_range ):
        print "Update Opacity, range = %s" %  str( opacity_range )
        self.opacityRange = opacity_range
        self.colormapManager.setAlphaRange ( opacity_range[0:2] ) 
        self.render()
        
    def setColorScale( self, range ):
        self.curtainMapper.SetScalarRange( range[0], range[1] )
        self.render()

    def getColorScale( self ):
        sr = self.curtainMapper.GetScalarRange()
        return [ sr[0], sr[1], 0 ]

    def getOpacityRange( self ):
        return [ self.opacityRange[0], self.opacityRange[1], 0 ]
         
    def getLevelRange(self): 
        return [ self.range[0], self.range[1], 0 ]
 
        
    def finalizeConfiguration( self ):
        PersistentVisualizationModule.finalizeConfiguration( self )
        self.render()

    def setInteractionState( self, caller, event ):
        PersistentVisualizationModule.setInteractionState( self, caller, event )
        
    def getCurtainGeometry( self, nLevels, vertRange, **args ):
        path = defaultPathFile
        wmod = args.get( 'wmod', self.getWorkflowModule()  )  
        pathInput = wmod.forceGetInputFromPort( "path", None ) 
        if pathInput <> None: path = pathInput.name       
        reader = PathFileReader()
        reader.read(path)  
        points = vtk.vtkPoints()     
        latData = reader.getData( 'Latitude' )
        lonData = reader.getData( 'Longitude' )
        lonDataIter = iter( lonData )
        z_inc = ( vertRange[1] - vertRange[0] ) / ( nLevels - 1 )
        polydata = vtk.vtkPolyData()
        stripArray = vtk.vtkCellArray()
        nstrips = nLevels - 1
        stripData = [ vtk.vtkIdList() for istrip in range( nstrips) ]
        for latVal in latData:
            lonVal = lonDataIter.next()
            if ( latVal <> None ) and  ( lonVal <> None ) :
                z = vertRange[0]
                for iLevel in range( nLevels ):
                    z = z + z_inc 
                    if iLevel < nstrips:
                        vtkId = points.InsertNextPoint( lonVal, latVal, z )
                        sd = stripData[ iLevel ]
                        sd.InsertNextId( vtkId )               
                        sd.InsertNextId( vtkId+1 )
                        
        for strip in stripData:
            stripArray.InsertNextCell(strip)
            
        polydata.SetPoints( points )
        polydata.SetStrips( stripArray )

                           
    def execute(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        testTexture = True
        textureInput = None
        xMin = 0 
        xMax = 360 
        yMin = 0 
        yMax = 180 
        zMin = 0 
        zMax = 20
        spacing = ( 1.0, 1.0, 2.0 )
        origin = ( 0, -90, 0 )
                     
        self.probeFilter = None
        if self.input <> None:
            self.probeFilter = vtk.vtkProbeFilter()
            textureInput = self.input.GetOutput() 
        elif testTexture:
            self.probeFilter = vtk.vtkProbeFilter()
            textureGenerator = vtk.vtkImageSinusoidSource()
            textureGenerator.SetWholeExtent ( xMin, xMax, yMin, yMax, zMin, zMax )
            textureGenerator.SetDirection( 1.0, 1.0, 1.0 )
            textureGenerator.SetPeriod( xMax-xMin )
            textureGenerator.SetAmplitude( 125.0 )
            textureGenerator.Update()
            textureInput = textureGenerator.GetOutput() 
            textureInput.SetSpacing( spacing )
            textureInput.SetOrigin( origin )
            
        textureRange = textureInput.GetScalarRange()
        self.probeFilter.SetSource( textureInput )
         
        nLevels = zMax - zMin
        vertRange = [ zMin*spacing[2], zMax*spacing[2] ]  
        curtain = self.getCurtainGeometry( nLevels, vertRange )
                    
        self.probeFilter.SetInput( curtain )
        self.curtainMapper = vtk.vtkPolyDataMapper()
        self.curtainMapper.SetInputConnection( self.probeFilter.GetOutputPort() ) 
        self.curtainMapper.SetScalarRange( textureRange )
        self.curtainMapper.SetLookupTable( self.lut ) 
              
        self.colormapManager.setAlphaRange ( self.opacityRange )           
#        curtainMapper.SetColorModeToMapScalars()  
#        levelSetActor = vtk.vtkLODActor() 
        curtainActor = vtk.vtkActor() 
#            curtainMapper.ScalarVisibilityOff() 
#            levelSetActor.SetProperty( self.levelSetProperty )              
        curtainActor.SetMapper( self.curtainMapper )
           
        self.renderer.AddActor( curtainActor )
        self.renderer.SetBackground( 0.1, 0.1, 0.2 )                                             
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



from WorkflowModule import WorkflowModule

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
            if gui.application.VistrailsApplication:
                gui.application.VistrailsApplication.finishSession()
            sys.exit(v)
        app = gui.application.VistrailsApplication()
        f = FileLocator(vistrail_filename)
        app.builderWindow.viewManager.open_vistrail(f) 
        app.builderWindow.viewModeChanged(0)   
    except SystemExit, e:
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        sys.exit(e)
    except Exception, e:
        if gui.application.VistrailsApplication:
            gui.application.VistrailsApplication.finishSession()
        print "Uncaught exception on initialization: %s" % e
        import traceback
        traceback.print_exc()
        sys.exit(255)
    if (app.temp_configuration.interactiveMode and
        not app.temp_configuration.check('spreadsheetDumpCells')): 
        v = app.exec_()
    
    gui.application.stop_application()
    sys.exit(v)    
 
