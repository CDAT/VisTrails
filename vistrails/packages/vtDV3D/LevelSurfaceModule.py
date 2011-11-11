'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from packages.vtk.base_module import vtkBaseModule
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from ColorMapManager import ColorMapManager 
from InteractiveConfiguration import QtWindowLeveler 
from vtUtilities import *
from PersistentModule import *
        
class PM_LevelSurface(PersistentVisualizationModule):
    """
        This module generates level surfaces from 3D volumetric (<i>vtkImagedata</i>) data.   The number of levels generated is
    controlled by the <b>nLevels</b> gui function, and the level values are controlled by the <b>levelRangeScale</b> leveling function.  The
    colormap and colorscaling can also be configured by gui and leveling commands respectively.  The <b>opacity</b> of the contours
    is configured using the opacity leveling function. 
    <h3>  Command Keys </h3>   
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> l </td> <td> Toggle show colorbar. </td>
        </table>
    """
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self,  mid, **args)
        self.opacityRange =  [ 0.8, 0.8 ]
        self.imageRange = None
        self.numberOfLevels = 1
        self.addConfigurableLevelingFunction( 'colorScale', 'C', setLevel=self.setColorScale, getLevel=self.getColorScale, layerDependent=True, units=self.units )
        self.addConfigurableLevelingFunction( 'levelRangeScale', 'L', setLevel=self.setLevelRange, getLevel=self.getDataRangeBounds, layerDependent=True, units=self.units )
        self.addConfigurableLevelingFunction( 'opacity', 'O', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange, layerDependent=True )
        self.addConfigurableGuiFunction( 'nLevels', NLevelConfigurationWidget, 'n', setValue=self.setNumberOfLevels, getValue=self.getNumberOfLevels, layerDependent=True )
        pass
    
    def setOpacityRange( self, opacity_range ):
        print "Update Opacity, range = %s" %  str( opacity_range )
        self.opacityRange = opacity_range
        self.colormapManager.setAlphaRange ( opacity_range[0:2] ) 
#        self.levelSetProperty.SetOpacity( opacity_range[1] )
        
    def setColorScale( self, range ):
        self.imageRange = self.getImageValues( range[0:2] ) 
        self.levelSetMapper.SetScalarRange( self.imageRange[0], self.imageRange[1] )
        self.colormapManager.setDisplayRange( range )

    def getColorScale( self ):
        sr = self.getDataRangeBounds()
        return [ sr[0], sr[1], 0 ]

    def getOpacityRange( self ):
        return [ self.opacityRange[0], self.opacityRange[1], 0 ]
         
#    def getLevelRange(self): 
#        level_data_values = self.getDataValues( self.range )
#        print "getLevelRange, data range = %s, image range = %s" % ( str( self.range ),  str( level_data_values ) )
#        level_data_values.append( 0 )
#        return level_data_values
##        return [ self.range[0], self.range[1], 0 ]

    def setNumberOfLevels( self, nLevelsData  ):
        self.numberOfLevels = int( getItem( nLevelsData ) )
        if self.numberOfLevels < 1: self.numberOfLevels = 1
        self.updateLevels()

    def getNumberOfLevels( self ):
        return [ self.numberOfLevels, ]
    
    def setLevelRange( self, range ):
        print "setLevelRange, data range = %s" % str( range ) 
        self.range = self.getImageValues( range )
        self.updateLevels()
    
    def updateLevels(self):
        self.levelSetFilter.SetNumberOfContours( self.numberOfLevels ) 
        nL1 = self.numberOfLevels + 1
        dL = ( self.range[1] - self.range[0] ) / nL1
        for i in range( 1, nL1 ): self.levelSetFilter.SetValue ( i, self.range[0] + dL * i )    
        self.updateColorMapping()
        print "Update %d Level(s), range = [ %f, %f ], levels = %s" %  ( self.numberOfLevels, self.range[0], self.range[1], str(self.getLevelValues()) )  
        
    def updateColorMapping(self):
        if self.colorByMappedScalars: 
            pass
#        else:
#            color = self.lut.
#            self.levelSetProperty.SetColor( color )        
        
    def getLevelValues(self):
        return [ self.levelSetFilter.GetValue( iV ) for iV in range( self.levelSetFilter.GetNumberOfContours() ) ]
 
        
    def finalizeConfiguration( self ):
        PersistentVisualizationModule.finalizeConfiguration( self )
        self.levelSetFilter.ComputeNormalsOn()
        self.render()

    def setInteractionState( self, caller, event ):
        PersistentVisualizationModule.setInteractionState( self, caller, event )
        if self.InteractionState <> None: 
            self.levelSetFilter.ComputeNormalsOff()
            self.levelSetFilter.ComputeGradientsOff()
                           
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        textureModule = self.wmod.forceGetInputFromPort( "texture", None )
        if self.input == None:
            if textureModule <> None:
                self.input = textureModule.getOutput() 
            else:
                print>>sys.stderr, "Error, must provide an input to the LevelSurface module!"

#        mod, d = self.getRegisteredDescriptor()
        testTexture = True
         
        xMin, xMax, yMin, yMax, zMin, zMax = self.input.GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = self.input.GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input.GetOrigin()
        ox, oy, oz = origin
        dataType = self.input.GetScalarTypeAsString()
        self.setMaxScalarValue( self.input.GetScalarType() )
        self.colorByMappedScalars = False
        print "Data Type = %s, range = (%f,%f), max_scalar = %s" % ( dataType, self.rangeBounds[0], self.rangeBounds[1], self._max_scalar_value )

        dr = self.rangeBounds[1] - self.rangeBounds[0]
        range_offset = .2*dr
        self.range = [ self.rangeBounds[0] + range_offset, self.rangeBounds[1] - range_offset ]

        self.probeFilter = None
        textureRange = self.range
        if textureModule <> None:
            self.probeFilter = vtk.vtkProbeFilter()
            textureInput = textureModule.getOutput() 
            textureRange = textureInput.GetScalarRange()
            self.probeFilter.SetSource( textureInput )
        elif testTexture:
            self.probeFilter = vtk.vtkProbeFilter()
            textureGenerator = vtk.vtkImageSinusoidSource()
            textureGenerator.SetWholeExtent ( xMin, xMax, yMin, yMax, zMin, zMax )
            textureGenerator.SetDirection( 0.0, 0.0, 1.0 )
            textureGenerator.SetPeriod( xMax-xMin )
            textureGenerator.SetAmplitude( 125.0 )
            textureGenerator.Update()
                        
            imageInfo = vtk.vtkImageChangeInformation()
            imageInfo.SetInputConnection( textureGenerator.GetOutputPort() ) 
            imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
            imageInfo.SetOutputExtentStart( xMin, yMin, zMin )
            imageInfo.SetOutputSpacing( spacing[0], spacing[1], spacing[2] )
        
            result = imageInfo.GetOutput() 
            textureRange = result.GetScalarRange()           
            self.probeFilter.SetSource( result )
            
        if  textureRange <> None: print " Texture Range = %s " % str( textureRange )
        
#        vtkImageResample
#        shrinkFactor = 4
#        shrink = vtk.vtkImageShrink3D()
#        shrink.SetShrinkFactors(shrinkFactor, shrinkFactor, 1)
#        shrink.SetInputConnection(demModel.GetOutputPort())
#        shrink.AveragingOn()

#        self.levelSetFilter = vtk.vtkImageMarchingCubes()
        
        self.levelSetFilter = vtk.vtkContourFilter()
        self.inputModule.inputToAlgorithm( self.levelSetFilter )
        self.levelSetMapper = vtk.vtkPolyDataMapper()
        if ( self.probeFilter == None ):
            self.levelSetMapper.SetInputConnection( self.levelSetFilter.GetOutputPort() ) 
            self.levelSetMapper.SetScalarRange( self.range )
        else: 
            self.probeFilter.SetInputConnection( self.levelSetFilter.GetOutputPort() )
            self.levelSetMapper.SetInputConnection( self.probeFilter.GetOutputPort() ) 
            self.levelSetMapper.SetScalarRange( textureRange )
        self.levelSetMapper.SetLookupTable( self.lut ) 
              
        self.colormapManager.setAlphaRange ( self.opacityRange ) 
        self.updateLevels()
          
#        levelSetMapper.SetColorModeToMapScalars()  
#        levelSetActor = vtk.vtkLODActor() 
        levelSetActor = vtk.vtkActor() 
#            levelSetMapper.ScalarVisibilityOff() 
#            levelSetActor.SetProperty( self.levelSetProperty )              
        levelSetActor.SetMapper( self.levelSetMapper )
        
#        pointData = self.levelSetFilter.GetOutput().GetPointData()
#        pointData.SetScalars( colorLevelData )
        
#        if pd <> None:
#            na = pd.GetNumberOfArrays()
#            print " ** Dataset has %d arrays. ** " % ( pd.GetNumberOfArrays() )
#            for i in range( na ): print "   ---  Array %d: %s " % ( i,  str( pd.GetArrayName(i) ) )
#        else: print " ** No point data. "
           
        self.renderer.AddActor( levelSetActor )
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
        nLevel = int( getItem( value ) )
        if nLevel > 0: self.nLevelCombo.setCurrentIndex( nLevel-1 )
        else: print>>sys.stderr, " Illegal number of levels: %s " % nLevel
        
    def createContent(self):
        nLevelTab = QWidget() 
        self.tabbedWidget.addTab( nLevelTab, 'Levels' )                                                     
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

class LevelSurface(WorkflowModule):
    
    PersistentModuleClass = PM_LevelSurface
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
               
if __name__ == '__main__':
    executeVistrail( 'LevelSurfaceDemo' )
 
