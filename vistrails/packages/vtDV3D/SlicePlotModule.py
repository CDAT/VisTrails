'''
Created on Jan 14, 2011

@author: tpmaxwel
'''
import vtk, math
#from PyQt4.QtCore import *
#from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from core.modules.vistrails_module import Module, InvalidOutput, ModuleError
from packages.vtDV3D.ColorMapManager import ColorMapManager 
# from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.PersistentModule import * 
from packages.vtDV3D.WorkflowModule import WorkflowModule
from packages.vtDV3D.vtUtilities import *
from packages.pylab.figure_cell import MplFigureCellWidget
from packages.spreadsheet.basic_widgets import SpreadsheetCell 
from matplotlib.pyplot import figure, show, axes, sci
from matplotlib import cm, colors
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, Normalize
from numpy import amin, amax, ravel
from vtk.util.numpy_support import *
from packages.vtDV3D import HyperwallManager
import time
PlotVersion = 0
        
class PM_SlicePlotCell( SpreadsheetCell, PersistentVisualizationModule ):
    """
        This module generates 2D matplotlib plots of slices from a volumetric data set. 
    <h3>  Command Keys </h3>   
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> key </td> <td> Function. </td>
        </table>
    """
           
    def __init__(self, mid, **args):
        SpreadsheetCell.__init__(self)
        PersistentVisualizationModule.__init__(self, mid, ndims = 2, **args)
        self.imageAxes = None
        self.cmaps = ( {}, {} )
        self.currentTime = 0
        self.fill_value_range = None
        self.contour_value_range = None
        self.buttonPressed = False
        self.axisBounds = None
        self.iOrientation = 0
        self.mfm = None
        self.cellWidget = None 
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', setLevel=self.scaleColormap, getLevel=self.getScalarRange, adjustRange=True, units='data' )
        
    def SliceObserver( self, caller, event ):
#        print " SliceObserver: %s " % event
        self.drawImageData()

    def updateHyperwall(self):
        HyperwallManager.getInstance().executeCurrentWorkflow( self.moduleID )

    def formatCoord( self, x, y ):
        numrows, numcols  = self.image_data.shape
        col = int( ( (numcols-1) * (x-self.axisBounds[0]) / (self.axisBounds[1]-self.axisBounds[0]) ) + 0.5 )
        row = int( ( (numrows-1) * (self.axisBounds[3]-y) / (self.axisBounds[3]-self.axisBounds[2]) ) + 0.5 )
        if col>=0 and col<numcols and row>=0 and row<numrows:
            z = self.image_data[row,col]
            if self.iOrientation == 0: return 'lat=%4.1f, lev=%4.1f, value=%f' % ( x, y, z )
            if self.iOrientation == 1: return 'lon=%4.1f, lev=%4.1f, value=%f' % ( x, y, z )
            if self.iOrientation == 2: return 'lon=%4.1f, lat=%4.1f, value=%f' % ( x, y, z )
        else:
            if self.iOrientation == 0: return 'lat=%4.1f, lev=%4.1f' % ( x, y )
            if self.iOrientation == 1: return 'lon=%4.1f, lev=%4.1f' % ( x, y )
            if self.iOrientation == 2: return 'lon=%4.1f, lat=%4.1f' % ( x, y )
           
    def drawImageData( self, initialization=False ):
        iOrientation = self.getAxisBounds() 
        [ fillType, contourType, nlevels, version ] = self.getInputValue( "plotType", [ "image", "none", 5, 0 ] )  
        fill_cmap = self.getPylabColormap(False) 
        contour_cmap = self.getPylabColormap(True) 
        self.image_data = self.getPythonInput()
        self.fill_plot, self.contour_plot, self.colorbar = None, None, None
        aspect = 'auto'
        levels, contour_norm, fill_norm = None, None, None
        if self.contour_value_range: 
            contour_norm = Normalize( self.contour_value_range[0], self.contour_value_range[1] ) 
        else: 
            contour_norm = Normalize() 
            contour_norm.autoscale( self.image_data )
            
        if self.fill_value_range:
            fill_norm = Normalize( self.fill_value_range[0], self.fill_value_range[1] )  
            dr = ( self.fill_value_range[1] - self.fill_value_range[0] ) / ( nlevels )
            levels = [ ( self.fill_value_range[0] + dr*i ) for i in range( 0, ( nlevels + 1 ) ) ] 
        else:
            fill_norm = Normalize() 
            fill_norm.autoscale( self.image_data )
            
#        print " Slice Plot->drawImageData: plotType=%s, range=[ %.2f, %.2f ], shape = %s, orientation=%d, roi = %s, init = %s " % ( plotType, value_range[0], value_range[1], str( self.image_data.shape ), self.iOrientation, str( self.axisBounds ), str( initialization ) )
        origin = 'upper' if (iOrientation == 2) else 'lower'
        if fillType == "image":
             origin = 'upper'
             if self.fill_value_range:  self.fill_plot = self.imageAxes.imshow( self.image_data, cmap=fill_cmap, aspect=aspect, extent=self.axisBounds, vmin=self.fill_value_range[0], vmax=self.fill_value_range[1] )
             else:                      self.fill_plot = self.imageAxes.imshow( self.image_data, aspect=aspect, cmap=fill_cmap, extent=self.axisBounds )
        elif fillType == "levels":
            if levels:  self.fill_plot = self.imageAxes.contourf( self.image_data, origin=origin, cmap=fill_cmap, extent=self.axisBounds, extend='both', norm=fill_norm, levels=levels )
            else:       self.fill_plot = self.imageAxes.contourf( self.image_data, origin=origin, cmap=fill_cmap, extent=self.axisBounds, extend='both', norm=fill_norm  )
#        self.vector_plot = self.imageAxes.quiver(U, V, **kw)
   
        if contourType <> 'none':
            if levels:  self.contour_plot = self.imageAxes.contour( self.image_data, origin=origin, cmap=contour_cmap, extent=self.axisBounds, extend='both', norm=contour_norm, levels=levels, linewidths=2  )
            else:       self.contour_plot = self.imageAxes.contour( self.image_data, origin=origin, cmap=contour_cmap, extent=self.axisBounds, extend='both', norm=contour_norm, linewidths=2  )
            if contourType == 'labeled': self.imageAxes.clabel( self.contour_plot, fontsize=9, inline=1)

#        print " **** pylab_plot methods: %s " % dir( self.pylab_plot )
        self.imageAxes.format_coord = self.formatCoord
        try:
            if self.fill_plot: 
#                print "Drawing colorbar: levels = %s, crange = %s " % ( str(levels), str(self.fill_value_range) )     
                self.colorbar = self.fig.colorbar( self.fill_plot, self.colorbarAxes, orientation='horizontal', format="%.2g" )
            elif self.contour_plot:
#                print "Drawing colorbar: levels = %s, crange = %s " % ( str(levels), str(self.contour_value_range) )  
                self.colorbar = self.fig.colorbar( self.contour_plot, self.colorbarAxes, orientation='horizontal', format="%.2g" )
            if self.colorbar: self.colorbar.set_label( self.units )
            if not initialization: self.fig.draw_artist( self.colorbarAxes )
        except Exception, err:
            print "Error drawing colorbar: %s " % str(err)
        if not initialization: 
            self.fig.draw_artist( self.imageAxes )
            if self.mfm: self.mfm.figManager.canvas.draw()
    
    def updateImageData( self ):
        self.image_data = self.getPythonInput()
        if self.fill_plot: self.fill_plot.set_array( self.image_data )
        if self.contour_plot: self.contour_plot.set_array( self.image_data )

    def createPlot( self, md ):
        self.fig.clear()
        varName = md['vars'][0]
        varAttributes = md[varName]
        self.dataScaling = varAttributes.get( 'scale', None )  
        self.dataType = md['datatype']  
        self.figtitle = varAttributes.get( 'long_name', varName )
        self.units = varAttributes.get( 'units', '' )
        self.annotation = self.fig.text(0.5, 0.9, '',  horizontalalignment='center',  fontproperties=FontProperties(size=12) )
        self.imageAxes = self.fig.add_axes( [0.1, 0.15, 0.85, 0.8 ] )
        self.imageAxes.set_title( self.figtitle )
#        self.imageAxes.set_aspect( 'auto', 'box' )
#        self.imageAxes.autoscale( False, axis='y' )
        self.colorbarAxes = self.fig.add_axes([0.05, 0.08, 0.85, 0.04], label=self.units )
        
    def getPythonInput( self ):
        self.input.Update()
        image_data = self.imageExport.GetArray()
        if (self.dataScaling <> None) and (self.dataType <> 'Float'):
            image_data = (image_data/self.dataScaling[1])  - self.dataScaling[0]
#            print " Rescale image data: %s " % str( self.dataScaling )
        plotshape = self.getPlotShape( self.input )
#        print "Reshape input from %s to %s" % ( str(image_data.shape), str(plotshape) )
#        print " Central image data value: %s " % ( str( image_data[ 0, plotshape[0]/2, plotshape[1]/2 ] ) )
        image_data = np.reshape( image_data, plotshape )
        return image_data
    
    def updateTextDisplay( self, text = None ):
        if text <> None: self.annotation.set_text( text )
        
    def getPlotShape( self, dataset ):
        new_dim = []  
        extent = dataset.GetWholeExtent()
        dim = ( extent[5]-extent[4]+1, extent[3]-extent[2]+1, extent[1]-extent[0]+1)
        for x in dim: 
            if x > 1: new_dim.append( x )
        return new_dim
    
    def onKeyPress( self, keyPressEvent ):
        self.processKeyEvent( keyPressEvent.key )

    def onMotion( self, event ):
        if self.buttonPressed:
            w, h = self.mfm.figManager.canvas.get_width_height()
            self.updateLeveling( event.x, event.y, [ w, h ] ) 

    def onButtonPress( self, event ):
        if event.button == 1:
            self.startLeveling( event.x, event.y )
            self.buttonPressed = True

    def onButtonRelease( self, buttonReleaseEvent ):
        if self.buttonPressed:
            self.buttonPressed = False
            self.finalizeLeveling()

    def setColormap( self, data ):
        self.colormapName = str(data[0])
        self.invertColormap = data[1]
        self.buildColormap()

    def buildColormap(self):
        fill_cmap = self.getPylabColormap(False) 
        contour_cmap = self.getPylabColormap(True) 
#        print " ---- buildColormap, valueRange: %s " % ( str( range ), )
        if ( fill_cmap <> None ) and self.fill_plot: self.fill_plot.set_cmap( fill_cmap ) 
        if ( contour_cmap <> None ) and self.contour_plot: self.contour_plot.set_cmap( contour_cmap ) 
             
        if ( self.fill_value_range <> None) and self.fill_plot: self.fill_plot.set_clim( self.fill_value_range[0], self.fill_value_range[1] ) 
        if ( self.contour_value_range <> None) and self.contour_plot: self.contour_plot.set_clim( self.contour_value_range[0], self.contour_value_range[1] ) 
                 
        self.mfm.figManager.canvas.draw()
        return False
 
    def scaleColormap( self, ctf_data ):
        value_range = [ bound( ctf_data[i], self.scalarRange ) for i in [0,1] ]
        if self.contour_plot:
            self.contour_value_range = [ value_range[0], value_range[1] ] 
            self.contour_plot.set_clim( value_range[0], value_range[1] )            
        self.mfm.figManager.canvas.draw()

    def getAxisBounds( self ):    
        md = self.getMetadata()
        iOrientation = md.get( 'orientation', 0 )
        if (iOrientation <> self.iOrientation) or not self.axisBounds:
            if iOrientation == 0: self.axisBounds = [ self.roi[2], self.roi[3], self.roi[4], self.roi[5] ]
            if iOrientation == 1: self.axisBounds = [ self.roi[0], self.roi[1], self.roi[4], self.roi[5] ]
            if iOrientation == 2: self.axisBounds = [ self.roi[0], self.roi[1], self.roi[2], self.roi[3] ]
#        if iOrientation <> self.iOrientation:
        self.iOrientation = iOrientation
        self.createPlot( md )
        return iOrientation
       
    def getPylabColormap( self, internal = True ):
        cmap_data, value_range = None, None
        if internal:
            cmap_data = self.getColormap()
            if not self.contour_value_range: self.contour_value_range = self.scalarRange
        else:    
            md = self.getMetadata()
            cmap_data = md.get('colormap','Spectral,0')
            if type(cmap_data) == type(""): cmap_data = cmap_data.split(',')
            if ( len( cmap_data ) < 4 ):
                value_range = self.fill_value_range if self.fill_value_range else self.scalarRange
            else:
                value_range = self.getDataValues( ( float( cmap_data[2] ), float( cmap_data[3] ) ) )
            self.fill_value_range = value_range
#        print " ---- getColormap:  %s, valueRange: %s " % ( str( cmap_data ), str( self.value_range ) )
        cmap_name = cmap_data[0]
        reverse_cmap  = int( cmap_data[1] ) 
        if cmap_name in self.cmaps[reverse_cmap]:
            return self.cmaps[reverse_cmap][ cmap_name ]
        else:
            lut = vtk.vtkLookupTable()
            colormapManager = ColorMapManager( lut )
            colormapManager.reverse_lut = reverse_cmap
            colormapManager.load_lut( cmap_name )
            ncolors = lut.GetNumberOfTableValues()
            colors, color = [], None
            end_colors = [ lut.GetTableValue(0)[0:3], lut.GetTableValue(ncolors-1)[0:3] ]
            for id in range( 1, ncolors-1 ):
                color = lut.GetTableValue(id)[0:3]
                colors.append( color )
#                print " ---- %d : %s " % ( id, str(color) )
            cmap = ListedColormap( colors, name=cmap_name )
            cmap.set_under( end_colors[0] )
            cmap.set_over( end_colors[1] )
            self.cmaps[reverse_cmap][ cmap_name ] = cmap
            return cmap
       
    def buildPipeline(self):
        """ compute() -> None        
        Either passing the figure manager to a SpreadsheetCell or save
        the image to file
        """      
        self.input.AddObserver( "RenderEvent", self.SliceObserver )
        self.imageExport = vtkImageExportToArray()
        self.imageExport.SetInput( self.input )
        input_dims = self.input.GetDimensions()
        md = extractMetadata( self.input.GetFieldData() )
              
        self.fig = figure()      
        self.createPlot( md )       
        self.drawImageData(True)
        
        noOutput = not self.mfm
        if noOutput:
            from packages.pylab.init import MplFigureManager
            self.mfm = MplFigureManager()
            self.mfm.figManager = pylab.get_current_fig_manager()
            self.mfm.figManager.canvas.mpl_connect( 'key_press_event', self.onKeyPress )
            self.mfm.figManager.canvas.mpl_connect( 'motion_notify_event', self.onMotion )
            self.mfm.figManager.canvas.mpl_connect( 'button_press_event', self.onButtonPress )
            self.mfm.figManager.canvas.mpl_connect( 'button_release_event', self.onButtonRelease )
            self.buildWidget()
            noOutput = False
#            print "FigManager(%s) canvas(%s) methods: %s" % ( self.mfm.figManager.__class__.__name__ , self.mfm.figManager.canvas.__class__.__name__ ,dir( self.mfm.figManager.canvas ) )
        wmod.setResult('File', InvalidOutput)
        if 'File' in self.wmod.outputPorts:
            f = self.wmod.interpreter.filePool.create_file(suffix='.png')
            pylab.savefig(f.name)
            self.wmod.setResult('File', f)
            noOutput = False
        if noOutput:
            pylab.show()


    def buildWidget(self):                        
        if not self.cellWidget:
            self.cellWidget = self.displayAndWait( MplFigureCellWidget, (self.mfm.figManager, ) )

    def updateModule(self, **args ):
#        printTime( 'Start Animation Step' )
        self.updateImageData()
        if self.wmod: self.wmod.setResult('FigureManager', self.mfm) 
        self.mfm.figManager.canvas.draw()
#        printTime( 'Finish Animation Step' )

    def initializeConfiguration(self):
        PersistentModule.initializeConfiguration(self)
        self.drawImageData()

class SlicePlotCell(WorkflowModule):
    
    PersistentModuleClass = PM_SlicePlotCell
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
                
if __name__ == '__main__':
    from packages.spreadsheet.spreadsheet_config import configuration
    configuration.rowCount=1
    configuration.columnCount=2
    executeVistrail( 'VolumeSlicePlotDemo' )
    
    
class SlicePlotConfigurationWidget(DV3DConfigurationWidget):
    """
    SlicePlotConfigurationWidget ...
    
    """

    def __init__(self, module, controller, parent=None):
        """ SlicePlotConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> SlicePlotConfigurationWidget
        Setup the dialog ...
        
        """
        self.datasetId = None
        self.fillTypeList = [ 'image', 'levels', 'none' ]
        self.contourTypeList = [ 'unlabeled', 'labeled', 'none' ]
        self.fillType = self.fillTypeList[0]
        self.contourType = self.contourTypeList[0]
        self.nContours = 5
        DV3DConfigurationWidget.__init__(self, module, controller, 'CDMS Data Reader Configuration', parent)
     
    def getParameters( self, module ):
        global PlotVersion
        plotTypeData = getFunctionParmStrValues( module, "plotType" )
        if plotTypeData: 
             self.fillType = plotTypeData[0]
             self.contourType = plotTypeData[1]
             self.nContours = int( plotTypeData[2] )
             PlotVersion = int( plotTypeData[3] )
                                                  
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        
        """        
        plotTypeTab = QWidget()        
        self.tabbedWidget.addTab( plotTypeTab, 'plot' ) 
        self.tabbedWidget.setCurrentWidget(plotTypeTab)
        plotTypeLayout = QVBoxLayout()                
        plotTypeTab.setLayout( plotTypeLayout )

        
        fill_selection_layout = QHBoxLayout()
        fill_selection_label = QLabel( "Fill Type:" )
        fill_selection_layout.addWidget( fill_selection_label ) 

        self.fillTypeCombo =  QComboBox ( self.parent() )
        fill_selection_label.setBuddy( self.fillTypeCombo )
        self.fillTypeCombo.setMaximumHeight( 30 )
        fill_selection_layout.addWidget( self.fillTypeCombo  ) 
        for fill_type in self.fillTypeList: 
            self.fillTypeCombo.addItem( fill_type )            
        selIndex = self.fillTypeCombo.findText( self.fillType ) 
        if selIndex >= 0: self.fillTypeCombo.setCurrentIndex( selIndex )
        else: self.fillTypeCombo.setCurrentIndex( 0 )
        self.connect( self.fillTypeCombo, SIGNAL("currentIndexChanged(QString)"), self.updateFillType ) 
        plotTypeLayout.addLayout(fill_selection_layout)


        contour_selection_layout = QHBoxLayout()
        contour_selection_label = QLabel( "Contour Type:" )
        contour_selection_layout.addWidget( contour_selection_label ) 

        self.contourTypeCombo =  QComboBox ( self.parent() )
        contour_selection_label.setBuddy( self.contourTypeCombo )
        self.contourTypeCombo.setMaximumHeight( 30 )
        contour_selection_layout.addWidget( self.contourTypeCombo  ) 
        for contour_type in self.contourTypeList: 
            self.contourTypeCombo.addItem( contour_type )            
        selIndex = self.contourTypeCombo.findText( self.contourType ) 
        if selIndex >= 0: self.contourTypeCombo.setCurrentIndex( selIndex )
        else: self.contourTypeCombo.setCurrentIndex( 0 )
        self.connect( self.contourTypeCombo, SIGNAL("currentIndexChanged(QString)"), self.updateContourType ) 
        plotTypeLayout.addLayout(contour_selection_layout)

                
        nContours_selection_layout = QHBoxLayout()
        nContours_selection_label = QLabel( "Number of Contours:" )
        nContours_selection_layout.addWidget( nContours_selection_label ) 

        self.nContoursCombo =  QComboBox ( self.parent() )
        nContours_selection_label.setBuddy( self.nContoursCombo )
        self.nContoursCombo.setMaximumHeight( 30 )
        nContours_selection_layout.addWidget( self.nContoursCombo  ) 
        for index in range(1,16): 
            self.nContoursCombo.addItem( str(index) )            
        selIndex = self.nContoursCombo.findText( str(self.nContours) ) 
        if selIndex >= 0: self.nContoursCombo.setCurrentIndex( selIndex )
        self.connect( self.nContoursCombo, SIGNAL("currentIndexChanged(QString)"), self.updateNContours ) 
        plotTypeLayout.addLayout(nContours_selection_layout)

    def updateContourType( self, contour_type ):
        ctype = str(contour_type)
        if ctype <> self.contourType: 
            self.contourType = ctype
            self.stateChanged(True)
        
    def updateNContours( self, num_contours ):
        nc = int( str(num_contours) )
        if nc <> self.nContours: 
            self.nContours = nc
            self.stateChanged(True)
        
    def updateFillType( self, fill_type ):
        ptype = str(fill_type)
        if ptype <> self.fillType: 
            self.fillType = ptype
            self.stateChanged(True)
        
    def updateController(self, controller):
        if self.state_changed:
            global PlotVersion
            self.persistParameterList( [ ('plotType', [ self.fillType, self.contourType, self.nContours, PlotVersion ] ) ] )
            print " Slice Plot: Persist Parameters: %s " % str( [ self.fillType, self.contourType, self.nContours  ] )
            PlotVersion = PlotVersion + 1 
            self.stateChanged(False)

          
    def okTriggered(self, checked = False):
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
                                       
        
if __name__ == '__main__':

    executeVistrail( 'workflows/DemoWorkflow4' )

 

