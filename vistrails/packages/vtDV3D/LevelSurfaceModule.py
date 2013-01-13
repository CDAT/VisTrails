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
from packages.vtDV3D.ColorMapManager import ColorMapManager 
from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.PersistentModule import *
        
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
    NoButtonDown = 0
    RightButtonDown = 1
    LeftButtonDown = 2

    Start = 0
    Cursoring = 1
    Outside  = 2
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self,  mid, **args)
        self.state  = self.Start
        self.primaryInputPorts = [ 'volume', 'texture' ]
        self.opacityRange =  [ 0.2, 0.99 ]
        self.numberOfLevels = 1
        self.generateTexture = False
        self.surfacePicker = None
        self.levelSetActor = None
        self.cursorActor = None
        self.currentButton = self.NoButtonDown
        self.visualizationInteractionEnabled = True
        self.removeConfigurableFunction( 'colormap' )
#        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', setLevel=self.setColorScale, getLevel=self.getColorScale, layerDependent=True, adjustRangeInput=0, units='data'  )
        self.addConfigurableLevelingFunction( 'levelRangeScale', 'L', label='Isosurface Level Range', setLevel=self.setLevelRange, getLevel=self.getDataRangeBounds, layerDependent=True, units='data', adjustRangeInput=0 )
        self.addConfigurableLevelingFunction( 'isoOpacity', 'p', label='Isosurface Opacity', activeBound='min', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange, layerDependent=True )
        self.addUVCDATConfigGuiFunction( 'nLevels', NLevelConfigurationWidget, 'n', label='# Isosurface Levels', setValue=self.setNumberOfLevels, getValue=self.getNumberOfLevels, layerDependent=True )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setInputZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Texture Colormap Scale', units='data', setLevel=lambda data, **args:self.setColorScale(data,1,**args), getLevel=lambda:self.getDataRangeBounds(1), layerDependent=True, adjustRangeInput=1, isValid=self.hasTexture )
        self.addUVCDATConfigGuiFunction( 'colormap', ColormapConfigurationDialog, 'c', label='Choose Texture Colormap', setValue=lambda data:self.setColormap(data,1) , getValue=lambda: self.getColormap(1), layerDependent=True, isValid=self.hasTexture )

    def createDefaultProperties(self):                       
        if (  not  self.cursorProperty ):           
            self.cursorProperty  = vtk.vtkProperty()
#            self.cursorProperty.SetAmbient(1)
            self.cursorProperty.SetColor(1,0,0)
            self.cursorProperty.SetOpacity(0.6)
#            self.cursorProperty.SetRepresentationToWireframe()
#            self.cursorProperty.SetInterpolationToFlat()
            
    def setCursorProperty( self, value ):
        self.cursorProperty = value

    def enableInteraction( self ):
        self.visualizationInteractionEnabled = True 

    def disableInteraction( self ):
        self.visualizationInteractionEnabled = False

    def hasTexture(self):
        return self.generateTexture

    def onLeftButtonPress( self, caller, event ):
        shift = caller.GetShiftKey()
        if self.visualizationInteractionEnabled and not shift:
            self.currentButton = self.LeftButtonDown
            if self.startCursor(): return      
        PersistentVisualizationModule. onLeftButtonPress( self, caller, event )

    def onLeftButtonRelease( self, caller, event ):
        if self.visualizationInteractionEnabled and (self.currentButton <> self.NoButtonDown):
            self.stopCursor()
            self.currentButton = self.NoButtonDown
        else:
            PersistentVisualizationModule. onLeftButtonRelease( self, caller, event )

    def onModified(self, caller, event ):
    
        if ( self.state == self.Outside or self.state == self.Start ): 
            PersistentVisualizationModule.onModified( self, caller, event ) 
            return
               
        X = self.iren.GetEventPosition()[0]
        Y = self.iren.GetEventPosition()[1]
                
        camera = self.renderer.GetActiveCamera()
        if (  not camera ): return
                                    
        if ( self.state == self.Cursoring ):          
            self.updateCursor(X,Y)         
            self.iren.Render()
        
    def startCursor(self):
        if self.state == self.Cursoring: return
    
        X = self.iren.GetEventPosition()[0]
        Y = self.iren.GetEventPosition()[1]
        
        # Okay, make sure that the pick is in the current renderer
        if ( not self.renderer or  not self.renderer.IsInViewport(X, Y)):        
            self.state  = self.Outside
            return
        
        if self.doPick( X, Y ):      
            self.state  = self.Cursoring
            self.cursorActor.VisibilityOn()
            self.updateCursor(X,Y)
            self.startInteraction()
#            self.processEvent( self.InteractionStartEvent )
            self.iren.Render()  
            return 1     
        else:
            self.state  = self.Outside
            self.cursorActor.VisibilityOff()
            return 0            

    def stopCursor(self): 
        if ( self.state == self.Outside or self.state == self.Start ):   return                  
#        self.ProcessEvent( self.InteractionEndEvent )
        self.state  = self.Start
        self.cursorActor.VisibilityOff()      
        self.endInteraction()
        self.iren.Render()
        
    def updateCursor( self, X, Y ):
        if self.surfacePicker:        
            self.surfacePicker.Pick( X, Y, 0.0, self.renderer )            
            if self.doPick( X, Y ):    
                self.cursorActor.VisibilityOn()
            else:
                self.cursorActor.VisibilityOff()
                return 
                                         
#            pos = self.surfacePicker.GetPickPosition()    
#            if( pos == None ):        
#                self.cursorActor.VisibilityOff()
#                return
#            self.cursor.SetCenter ( pos[0], pos[1], pos[2] )
            self.displayPickData()
            
    def displayPickData( self ):
        pointId =  self.surfacePicker.GetPointId() 
        if pointId < 0:
            self.cursorActor.VisibilityOff()
        else:
            level_ispec = self.getInputSpec() 
            if level_ispec and level_ispec.input: 
                pdata = self.levelSetFilter.GetOutput()
                point_data = pdata.GetPointData()
                pos = pdata.GetPoint( pointId )
                self.cursor.SetCenter ( pos[0], pos[1], pos[2] )
                scalarsArray = point_data.GetScalars()
                image_data_value = scalarsArray.GetTuple1( pointId )
                data_value = level_ispec.getDataValue( image_data_value )
                textDisplay = " Position: (%.2f, %.2f, %.2f), Level Value: %.3G %s" % ( pos[0], pos[1], pos[2], data_value, level_ispec.units )  
                texture_ispec = self.getInputSpec(  1 )                
                if texture_ispec and texture_ispec.input:
                    tex_pdata = self.probeFilter.GetOutput()
                    tex_point_data = tex_pdata.GetPointData()
                    tex_scalarsArray = tex_point_data.GetScalars()
                    tex_image_data_value = tex_scalarsArray.GetTuple1( pointId )
                    tex_data_value = texture_ispec.getDataValue( tex_image_data_value )
                    textDisplay += ", Texture value: %.3G %s" % ( tex_data_value, texture_ispec.units )
                self.updateTextDisplay( textDisplay )                        

    def startInteraction(self): 
        update_rate = self.iren.GetDesiredUpdateRate()
        self.iren.GetRenderWindow().SetDesiredUpdateRate( update_rate )
        self.updateInteractor()
        self.haltNavigationInteraction()
              
#----------------------------------------------------------------------------

    def endInteraction(self): 
        update_rate = self.iren.GetStillUpdateRate()
        self.iren.GetRenderWindow().SetDesiredUpdateRate( update_rate )
        self.resetNavigation()
     
#            o = self.PlaneSource.GetOrigin()
#            
#            # q relative to the plane origin
#            #
#            qro = [ q[0] - o[0], q[1] - o[1], q[2] - o[2] ]
#            
#            p1o = self.GetVector1()
#            p2o = self.GetVector2()        
#            Lp1  = vtk.vtkMath.Dot(qro,p1o)/vtk.vtkMath.Dot(p1o,p1o)
#            Lp2  = vtk.vtkMath.Dot(qro,p2o)/vtk.vtkMath.Dot(p2o,p2o)
#            
#            p1 = self.PlaneSource.GetPoint1()
#            p2 = self.PlaneSource.GetPoint2()
#                   
#            a = [ o[i]  + Lp2*p2o[i]  for i in range(3) ]
#            b = [ p1[i] + Lp2*p2o[i]  for i in range(3) ] #  right
#            c = [ o[i]  + Lp1*p1o[i]  for i in range(3) ] # bottom
#            d = [ p2[i] + Lp1*p1o[i]  for i in range(3) ]  # top
#                    
#            cursorPts = self.CursorPolyData.GetPoints()        
#            cursorPts.SetPoint(0,a)
#            cursorPts.SetPoint(1,b)
#            cursorPts.SetPoint(2,c)
#            cursorPts.SetPoint(3,d)
#            
#            self.CursorPolyData.Modified()
#            self.ProcessEvent( self.InteractionUpdateEvent )
        
    def doPick( self, X, Y ):  
        found = 0
        if self.surfacePicker:
            self.surfacePicker.Pick( X, Y, 0.0, self.renderer )
            path = self.surfacePicker.GetPath()        
            if path:
                path.InitTraversal()
                for _ in range( path.GetNumberOfItems() ):
                    node = path.GetNextNode()
                    if node and ( node.GetViewProp() == self.levelSetActor ):
                        found = 1
                        break
        return found

    def setInputZScale( self, zscale_data, **args  ):       
        texture_ispec = self.getInputSpec(  1 )                
        if texture_ispec and texture_ispec.input:
            textureInput = texture_ispec.input 
            ix, iy, iz = textureInput.GetSpacing()
            sz = zscale_data[1]
            textureInput.SetSpacing( ix, iy, sz )  
            textureInput.Modified() 
        return PersistentVisualizationModule.setInputZScale(self,  zscale_data, **args )
        
    def setOpacityRange( self, opacity_range, **args  ):
#        print "Update Opacity, range = %s" %  str( opacity_range )
        self.opacityRange = opacity_range
        cmap_index = 1 if self.generateTexture else 0
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setAlphaRange ( [ opacity_range[0], opacity_range[0] ]  ) 
#        self.levelSetProperty.SetOpacity( opacity_range[1] )
        
    def setColorScale( self, range, cmap_index=0, **args  ):
        ispec = self.getInputSpec( cmap_index )
        if ispec and ispec.input:
            imageRange = self.getImageValues( range[0:2], cmap_index ) 
            colormapManager = self.getColormapManager( index=cmap_index )
            colormapManager.setScale( imageRange, range )
            self.levelSetMapper.Modified()

    def getColorScale( self, cmap_index=0 ):
        sr = self.getDataRangeBounds( cmap_index )
        return [ sr[0], sr[1], 0 ]

    def getOpacityRange( self ):
        return [ self.opacityRange[0], self.opacityRange[1], 0 ]
         
#    def getLevelRange(self): 
#        level_data_values = self.getDataValues( self.range )
#        print "getLevelRange, data range = %s, image range = %s" % ( str( self.range ),  str( level_data_values ) )
#        level_data_values.append( 0 )
#        return level_data_values
##        return [ self.range[0], self.range[1], 0 ]

    def setNumberOfLevels( self, nLevelsData, **args   ):
        self.numberOfLevels = int( getItem( nLevelsData ) )
        if self.numberOfLevels < 1: self.numberOfLevels = 1
        self.updateLevels()

    def getNumberOfLevels( self ):
        return [ self.numberOfLevels, ]
    
    def setLevelRange( self, range, **args ):
#        print "  ---> setLevelRange, data range = %s" % str( range ) 
        self.range = self.getImageValues( range )
        self.updateLevels()
    
    def updateLevels(self):
        self.levelSetFilter.SetNumberOfContours( self.numberOfLevels ) 
        nL1 = self.numberOfLevels + 1
        dL = ( self.range[1] - self.range[0] ) / nL1
        for i in range( 1, nL1 ): self.levelSetFilter.SetValue ( i, self.range[0] + dL * i )    
#        self.updateColorMapping()
#        print "Update %d Level(s), range = [ %f, %f ], levels = %s" %  ( self.numberOfLevels, self.range[0], self.range[1], str(self.getLevelValues()) )  
        
#    def updateColorMapping(self):
#        if self.colorByMappedScalars: 
#            pass
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

    def updateModule(self, **args ):
        primaryInput = self.input()
        self.levelSetFilter.SetInput( primaryInput )
        self.levelSetFilter.Modified()
        self.set3DOutput()
        print "Update Level Surface Module with %d Level(s), range = [ %f, %f ], levels = %s" %  ( self.numberOfLevels, self.range[0], self.range[1], str(self.getLevelValues()) )  
                           
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        
        primaryInput = self.input()
        texture_ispec = self.getInputSpec(  1 )                
        xMin, xMax, yMin, yMax, zMin, zMax = primaryInput.GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = primaryInput.GetSpacing()
        sx, sy, sz = spacing       
        origin = primaryInput.GetOrigin()
        ox, oy, oz = origin
        dataType = primaryInput.GetScalarTypeAsString()
        self.setMaxScalarValue( primaryInput.GetScalarType() )
        self.colorByMappedScalars = False
        rangeBounds = self.getRangeBounds()

        dr = rangeBounds[1] - rangeBounds[0]
        range_offset = .2*dr
        self.range = [ rangeBounds[0] + range_offset, rangeBounds[1] - range_offset ]
        print "Data Type = %s, range = (%f,%f), range bounds = (%f,%f), max_scalar = %s" % ( dataType, self.range[0], self.range[1], rangeBounds[0], rangeBounds[1], self._max_scalar_value )
        self.probeFilter = None
        textureRange = self.range
        if texture_ispec and texture_ispec.input:
            self.probeFilter = vtk.vtkProbeFilter()
            textureRange = texture_ispec.input.GetScalarRange()
            self.probeFilter.SetSource( texture_ispec.input )
            self.generateTexture = True

        if (self.surfacePicker == None):           
            self.surfacePicker  = vtk.vtkPointPicker()
                    
        self.levelSetFilter = vtk.vtkContourFilter()
        self.levelSetFilter.SetInout()
        self.levelSetMapper = vtk.vtkPolyDataMapper()
        self.levelSetMapper.SetColorModeToMapScalars()
        if ( self.probeFilter == None ):
            imageRange = self.getImageValues( self.range ) 
            self.levelSetMapper.SetInputConnection( self.levelSetFilter.GetOutputPort() ) 
            self.levelSetMapper.SetScalarRange( imageRange[0], imageRange[1] )
        else: 
            self.probeFilter.SetInputConnection( self.levelSetFilter.GetOutputPort() )
            self.levelSetMapper.SetInputConnection( self.probeFilter.GetOutputPort() ) 
            self.levelSetMapper.SetScalarRange( textureRange )
            
        if texture_ispec and texture_ispec.input:
            colormapManager = self.getColormapManager( index=1 )     
            colormapManager.setAlphaRange ( self.opacityRange ) 
            self.levelSetMapper.SetLookupTable( colormapManager.lut ) 
            self.levelSetMapper.UseLookupTableScalarRangeOn()
        else:
            colormapManager = self.getColormapManager()     
            colormapManager.setAlphaRange ( self.opacityRange ) 
            self.levelSetMapper.SetLookupTable( colormapManager.lut ) 
            self.levelSetMapper.UseLookupTableScalarRangeOn()
        
        self.updateLevels()
          
#        levelSetMapper.SetColorModeToMapScalars()  
#        levelSetActor = vtk.vtkLODActor() 
        self.levelSetActor = vtk.vtkActor() 
#            levelSetMapper.ScalarVisibilityOff() 
#            levelSetActor.SetProperty( self.levelSetProperty )              
        self.levelSetActor.SetMapper( self.levelSetMapper )

        self.cursorActor     = vtk.vtkActor()
        self.cursorProperty  = None 
        self.cursor = vtk.vtkSphereSource()
        self.cursor.SetRadius(2.0)
        self.cursor.SetThetaResolution(8)
        self.cursor.SetPhiResolution(8)
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInput(self.cursor.GetOutput())
        self.cursorActor.SetMapper(mapper)        
        self.createDefaultProperties() 
                                                            
#        pointData = self.levelSetFilter.GetOutput().GetPointData()
#        pointData.SetScalars( colorLevelData )
        
#        if pd <> None:
#            na = pd.GetNumberOfArrays()
#            print " ** Dataset has %d arrays. ** " % ( pd.GetNumberOfArrays() )
#            for i in range( na ): print "   ---  Array %d: %s " % ( i,  str( pd.GetArrayName(i) ) )
#        else: print " ** No point data. "
           
        self.renderer.AddActor( self.levelSetActor )
        self.surfacePicker.AddPickList( self.levelSetActor )
        self.surfacePicker.PickFromListOn()
        self.renderer.AddViewProp(self.cursorActor)
        self.cursorActor.SetProperty(self.cursorProperty)
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
        nLevel = int( getItem( value ) )
        if nLevel > 0: self.nLevelCombo.setCurrentIndex( nLevel-1 )
        else: print>>sys.stderr, " Illegal number of levels: %s " % nLevel
        
    def createContent(self):
        nLevelTab = QWidget() 
        self.tabbedWidget.addTab( nLevelTab, 'Levels' )                                                     
        self.tabbedWidget.setCurrentWidget(nLevelTab)
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

class LevelSurface(WorkflowModule):
    
    PersistentModuleClass = PM_LevelSurface
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
               
if __name__ == '__main__':
    executeVistrail( 'LevelSurfaceDemo' )
 
