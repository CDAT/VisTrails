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
from ColorMapManager import ColorMapManager 
from InteractiveConfiguration import QtWindowLeveler 
from PersistentModule import * 
from vtUtilities import *

from matplotlib.pyplot import figure, show, axes, sci
from matplotlib import cm, colors
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import pylab
from numpy import amin, amax, ravel
from vtk.util.numpy_support import *
import time
        
class PM_SlicePlot( PersistentVisualizationModule ):
    """
        This module generates 2D matplotlib plots of slices from a volumetric data set. 
    <h3>  Command Keys </h3>   
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> key </td> <td> Function. </td>
        </table>
    """
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, ndims = 2 )
        self.imageAxes = None
        self.cmaps = ( {}, {} )
        self.currentTime = 0
        self.buttonPressed = False
        self.addConfigurableLevelingFunction( 'colorScale', 'C', setLevel=self.scaleColormap, getLevel=self.getScalarRange )

    def SliceObserver( self, caller, event ):
#        print " SliceObserver: %s " % event
        self.drawImageData()

    def formatCoord( self, x, y ):
        numrows, numcols  = self.image_data.shape
        col = int( ( (numcols-1) * (x-self.roi[0]) / (self.roi[1]-self.roi[0]) ) + 0.5 )
        row = int( ( (numrows-1) * (self.roi[3]-y) / (self.roi[3]-self.roi[2]) ) + 0.5 )
        if col>=0 and col<numcols and row>=0 and row<numrows:
            z = self.image_data[row,col]
            return 'x=%4.1f, y=%4.1f, z=%f' % (x, y, z )
        else:
            return 'x=%4.1f, y=%4.1f' % (x, y)
           
    def drawImageData( self, initialization=False ):
        cmap, range = self.getPylabColormap()     
        self.image_data = self.getPythonInput()
#        print " MPlotLib: Scale Colormap: [ %.2f, %.2f ], shape = %s, roi = %s " % ( range[0], range[1], str( self.image_data.shape ), str( self.roi[0:4] ) )
        self.pylab_image = self.imageAxes.imshow( self.image_data, cmap=cmap, extent=self.roi[0:4] ) if (range == None) else self.imageAxes.imshow( self.image_data, cmap=cmap, extent=self.roi[0:4], vmin=range[0], vmax=range[1] )
        self.imageAxes.format_coord = self.formatCoord
        self.colorbar = self.fig.colorbar( self.pylab_image, self.colorbarAxes, orientation='horizontal' )
        self.colorbar.set_label( self.units )
        if not initialization: 
            self.fig.draw_artist( self.imageAxes )
            self.fig.draw_artist( self.colorbarAxes )
    
    def updateImageData( self ):
        self.image_data = self.getPythonInput()
        self.pylab_image.set_array( self.image_data )

    def createPlot( self, md ):
        varName = md['vars'][0]
        varAttributes = md[varName]
        self.dataScaling = varAttributes.get( 'scale', None )  
        self.dataType = md['datatype']  
        figtitle = varAttributes['long_name']
        self.units = 'units' # varAttributes['units']
        self.annotation = self.fig.text(0.5, 0.9, '',  horizontalalignment='center',  fontproperties=FontProperties(size=12) )
        self.imageAxes = self.fig.add_axes( [0.1, 0.15, 0.85, 0.8 ] )
        self.imageAxes.set_title( figtitle )
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

    def buildColormap(self):
        cmap, range = self.getPylabColormap() 
        if ( cmap <> None ): 
            self.pylab_image.set_cmap( cmap ) 
        if (range <> None): 
            self.pylab_image.set_clim( range[0], range[1] )
        self.mfm.figManager.canvas.draw()
        return False
 
    def scaleColormap( self, ctf_data ):
        self.pylab_image.set_clim( ctf_data[0], ctf_data[1] ) 
        print " Slice Plot: Scale Colormap: [ %.2f, %.2f ] " % ( ctf_data[0], ctf_data[1] )
        self.mfm.figManager.canvas.draw()
       
    def getPylabColormap( self ):
        md = self.getMetadata()
        cmap_data = md.get('colormap','Spectral,0')
        if type(cmap_data) == type(""): cmap_data = cmap_data.split(',')
        cmap_name = cmap_data[0]
        reverse_cmap  = int( cmap_data[1] ) 
        value_range = self.scalarRange if ( len( cmap_data ) < 4 ) else ( float( cmap_data[2] ), float( cmap_data[3] ) ) 
#        print " ---- getColormap:  %s, valueRange: %s " % ( str( cmap_data ), str( value_range ) )
        if cmap_name in self.cmaps[reverse_cmap]:
            return self.cmaps[reverse_cmap][ cmap_name ], value_range
        else:
            lut = vtk.vtkLookupTable()
            colormapManager = ColorMapManager( lut )
            colormapManager.reverse_lut = reverse_cmap
            colormapManager.load_lut( cmap_name )
            ncolors = lut.GetNumberOfTableValues()
            colors = []
            for id in range( 0, ncolors ):
                color = lut.GetTableValue(id)[0:3]
                colors.append( color )
#                print " ---- %d : %s " % ( id, str(color) )
            cmap = ListedColormap( colors, name=cmap_name )
            self.cmaps[reverse_cmap][ cmap_name ] = cmap
            return cmap, value_range
       
    def buildPipeline(self):
        """ compute() -> None        
        Either passing the figure manager to a SpreadsheetCell or save
        the image to file
        """  
        wmod = self.getWorkflowModule()     
        self.input.AddObserver( "RenderEvent", self.SliceObserver )
        self.imageExport = vtkImageExportToArray()
        self.imageExport.SetInput( self.input )
        input_dims = self.input.GetDimensions()
        md = extractMetadata( self.input.GetFieldData() )
              
        self.fig = figure()      
        self.createPlot( md )       
        self.drawImageData(True)
        
        noOutput = True
        if wmod.outputPorts.has_key('FigureManager'):
            from packages.pylab.init import MplFigureManager
            self.mfm = MplFigureManager()
            self.mfm.figManager = pylab.get_current_fig_manager()
            self.mfm.figManager.canvas.mpl_connect( 'key_press_event', self.onKeyPress )
            self.mfm.figManager.canvas.mpl_connect( 'motion_notify_event', self.onMotion )
            self.mfm.figManager.canvas.mpl_connect( 'button_press_event', self.onButtonPress )
            self.mfm.figManager.canvas.mpl_connect( 'button_release_event', self.onButtonRelease )
            wmod.setResult('FigureManager', self.mfm)
            noOutput = False
#            print "FigManager(%s) canvas(%s) methods: %s" % ( self.mfm.figManager.__class__.__name__ , self.mfm.figManager.canvas.__class__.__name__ ,dir( self.mfm.figManager.canvas ) )
        wmod.setResult('File', InvalidOutput)
        if 'File' in wmod.outputPorts:
            f = wmod.interpreter.filePool.create_file(suffix='.png')
            pylab.savefig(f.name)
            wmod.setResult('File', f)
            noOutput = False
        if noOutput:
            pylab.show()

    def updateModule(self):
#        printTime( 'Start Animation Step' )
        self.updateImageData()
        wmod = self.getWorkflowModule() 
        if wmod: wmod.setResult('FigureManager', self.mfm) 
        self.mfm.figManager.canvas.draw()
#        printTime( 'Finish Animation Step' )


from WorkflowModule import WorkflowModule

class SlicePlot(WorkflowModule):
    
    PersistentModuleClass = PM_SlicePlot
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
        
        
if __name__ == '__main__':
    from packages.spreadsheet.spreadsheet_config import configuration
    configuration.rowCount=1
    configuration.columnCount=2
    executeVistrail( 'VolumeSlicePlotDemo' )
