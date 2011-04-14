'''
Created on Jan 3, 2011

@author: tpmaxwel
'''
'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk, os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter

from core.modules.basic_modules import Integer, Float, String, File, Variant, Color

from ColorMapManager import ColorMapManager 
from InteractiveConfiguration import QtWindowLeveler 
from vtUtilities import *
from PersistentModule import *

packagePath = os.path.dirname( __file__ )  
defaultDataDir = os.path.join( packagePath, 'data' )
defaultPathFile = os.path.join( defaultDataDir,  'demoPath.csv' )
        
class PM_Resample(PersistentVisualizationModule):
    """
        This module enables rescaling, clipping, and decimation (resolution reduction) of 3D volumetric (<i>vtkImagedata</i>). 
    <h3>  Command Keys </h3>   
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> b </td> <td> Show Bounding Box (AOI) widget. </td>
        <tr> <td> d </td> <td> Show Decimation widget. </td>
        </table>
    """
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self, mid, createColormap=False, **args)
        aoi_sig = [ (Float, 'xmin'), (Float, 'xmax'), (Float, 'ymin'), (Float, 'ymax'), (Float, 'zmin'), (Float, 'zmax')  ]
        self.addConfigurableWidgetFunction( 'aoi',     aoi_sig,   BoxWidgetWrapper, 'b', getValue=self.getAoi, setValue=self.setAoi )
        self.addConfigurableGuiFunction( 'decimation', DecimationConfigurationWidget, 'd', setValue=self.setDecimation, getValue=self.getDecimation )
        self.currentExtent = None
        
    def startConfigurationObserver( self, parameter_name, *args ):
        PersistentVisualizationModule.startConfigurationObserver( self, parameter_name, *args )
        self.currentScaledBounds = None

    def getAoi(self):
        unscaledWorldExtent = self.getUnscaledWorldExtent( self.currentExtent )
        print " --- Get AOI: aoi = %s " % ( str(unscaledWorldExtent) )
        return unscaledWorldExtent

    def setAoi( self, unscaledWorldExtent ):
        extent = self.getImageExtent(  unscaledWorldExtent )
        print " --- Set AOI: aoi = %s " % ( str(extent) )
        self.setExtent( extent )
                            
    def startResample(self, object, event):
        self.currentAoi = self.getUnscaledWorldExtent( self.currentExtent )      
                                              
    def getExtent(self):  
        return self.initialExtent if ( self.currentExtent == None ) else  self.currentExtent 

    def setExtent( self, value ):  
        self.currentExtent = self.boundImageExtent( value )
        outputWholeExtent = [ int(round(self.currentExtent[i])) for i in range(6) ]
        self.clip.SetVOI( outputWholeExtent[0], outputWholeExtent[1], outputWholeExtent[2], outputWholeExtent[3], outputWholeExtent[4], outputWholeExtent[5] )
        self.currentAoi = self.getUnscaledWorldExtent( self.currentExtent )
        self.imageInfo.SetOutputOrigin( self.currentAoi[0], self.currentAoi[2], self.currentAoi[4] )
        print " --- Set Extent: extent = %s, aoi = %s " % ( str(outputWholeExtent), str(self.currentAoi) )
                                                                                              
    def getImageCoords( self, unscaledWorldCoords ):
        return [ ( ( ( unscaledWorldCoords[iAxis] - self.initialOrigin[iAxis] ) / self.initialSpacing[ iAxis ] )  ) for iAxis in range(3) ]

    def getUnscaledWorldCoords( self, imageCoords ):
         return [ ( ( imageCoords[ iAxis ] * self.initialSpacing[ iAxis ] ) + self.initialOrigin[iAxis]  ) for iAxis in range(3) ]
                                                
    def getImageExtent( self, unscaledWorldExtent ):
        return [ ( ( ( unscaledWorldExtent[i] - self.initialOrigin[i/2] ) / self.initialSpacing[ i/2 ] )  ) for i in range(6) ]

    def getUnscaledWorldExtent( self, extent=None, spacing = None, origin = None ):
        if extent  == None: extent  = self.getExtent()
        if origin  == None: origin  = self.initialOrigin
        if spacing == None: spacing = self.initialSpacing
        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]
    
    def setDecimation(self, decimation ):
        print " ***** set Decimation: %s " % str( decimation )
        dec = [ 1, 1, 1 ]
        mag = [ 1, 1, 1 ]
        rescale = [ 1.0, 1.0, 1.0 ] 
        for i in range( 3 ):
            if decimation[i] > 0:
                dec[i] =  decimation[i]   
                rescale[i] = float(decimation[i])   
            else:                   
                mag[i] = -decimation[i]
                rescale[i] = 1.0 / mag[i] 
        self.clip.SetSampleRate( decimation ) 
        self.pad.SetMagnificationFactors( mag ) 
        self.imageInfo.SetOutputSpacing( self.initialSpacing[0] * rescale[0], self.initialSpacing[1] * rescale[1], self.initialSpacing[2] * rescale[2] )

    def getDecimation(self ):
        dec = self.clip.GetSampleRate( )  
        mag = self.pad.GetMagnificationFactors() 
        return [ -mag[i] if (mag[i]>1) else dec[i] for i in range(3) ]

    def boundImageCoord( self, iAxis, coordValue ):
        bounds = [ self.initialExtent[2*iAxis], self.initialExtent[2*iAxis+1] ]
        if coordValue < bounds[0]:  coordValue =  bounds[0] 
        if coordValue > bounds[1]:  coordValue =  bounds[1] 
        return coordValue

    def boundImageExtent( self,  extent ):
        return [ self.boundImageCoord( i/2, extent[i] ) for i in range(6) ]
            
    def onResampleEvent(self, caller, event ):
        print " >>>>>>>>> Resample Event: %s " % ( event )
        self.PrintState()
        
    def PrintState(self):
        output = self.clip.GetOutput()
#        print " Spacing: %s, Origin: %s, Extent: %s " % ( str2f( self.resample.GetOutputSpacing() ), str2f( self.resample.GetOutputOrigin() ), str2f( self.resample.GetOutputExtent() )  )
        print " Output: Origin: %s, Spacing: %s, Extent: %s " % ( str2f( output.GetOrigin() ), str2f( output.GetSpacing() ), str( output.GetExtent() ) )                     

    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """        
        self.initialOrigin = self.input.GetOrigin()
        self.initialExtent = self.input.GetExtent()
        self.initialSpacing = self.input.GetSpacing()
        self.initialAoi = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing ) 
        self.currentAoi = list( self.initialAoi )
                
        self.clip = vtk.vtkExtractVOI()  
        self.inputModule.inputToAlgorithm( self.clip )
        
        self.pad = vtk.vtkImageMagnify()
        self.pad.InterpolateOn()
        self.pad.SetInputConnection( self.clip.GetOutputPort() ) 
        
        self.imageInfo = vtk.vtkImageChangeInformation()
        self.imageInfo.SetInputConnection( self.pad.GetOutputPort() ) 
        self.imageInfo.SetOutputOrigin( self.initialOrigin[0], self.initialOrigin[1], self.initialOrigin[2] )
        self.imageInfo.SetOutputExtentStart( self.initialExtent[0], self.initialExtent[2], self.initialExtent[4] )
        self.imageInfo.SetOutputSpacing( self.initialSpacing[0], self.initialSpacing[1], self.initialSpacing[2] )
        
        self.setExtent( self.initialExtent )          
        self.set3DOutput( port=self.imageInfo.GetOutputPort() )
        
    def updateModule( self ):
        pass
        
#        self.clip.AddObserver( 'StartEvent', self.onResampleEvent )     
#        self.clip.AddObserver( 'EndEvent', self.onResampleEvent ) 
        
#        position = wmod.forceGetInputFromPort( "position", self.getPosition() ) 
#        self.setPosition( position )                                                                             

#class Resample1(PersistentVisualizationModule):
#    """
#        This module enables rescaling, clipping, and decimation (resolution reduction) of 3D volumetric (<i>vtkImagedata</i>). 
#    <h3>  Command Keys </h3>   
#        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
#        <tr> <th> Command Key </th> <th> Function </th> </tr> 
#        <tr> <td> b </td> <td> Show Bounding Box (AOI) widget. </td>
#        <tr> <td> r </td> <td> Show Resolution (Decimation widget). </td>
#        <tr> <td> s </td> <td> Show Scaling widget. </td>
#        </table>
#    """
#           
#    def __init__(self, **args):
#        PersistentVisualizationModule.__init__(self, createColormap=False, **args)
#        aoi_sig = [ (Float, 'xmin'), (Float, 'xmax'), (Float, 'ymin'), (Float, 'ymax'), (Float, 'zmin'), (Float, 'zmax')  ]
#        scale_sig = [ (Float, 'sx'), (Float, 'sy'), (Float, 'sz') ] 
#        self.addConfigurableWidgetFunction( 'aoi',     aoi_sig,   BoxWidgetWrapper, 'b', configToParameter=self.boundsToAoi, parameterToConfig=self.AoiToBounds, getValue=self.getAoi, setValue=self.setAoi )
##        self.addConfigurableWidgetFunction( 'scaling', scale_sig, BoxWidgetWrapper, 's', configToParameter=self.boundsToScaling, parameterToConfig=self.scalingToBounds, getValue=self.getScaling, setValue=self.setScaling  )
#        self.addConfigurableGuiFunction( 'resolution', DecimationConfigurationWidget, 'r', setValue=self.setSpacing, getValue=self.getSpacing, getAoi=self.getAoi )
#        self.currentOrigin = None
#        self.currentExtent = None
#        self.currentSpacing = None
#        
#    def boundExtent( self, extent, extentBounds ):
#        bounded_extent = []
#        for iAxis in range(3):
#            low = 2*iAxis
#            high = low + 1
#            bounded_extent.append( bound( extent[ low ],   extentBounds[ low ],  extentBounds[ high ] ) )
#            bounded_extent.append( bound( extent[ high ],  extentBounds[ low ],  extentBounds[ high ] ) )
#        return bounded_extent
#                   
#    def boundsToAoi(self, scaledBounds ):
##        scaledInitialAoi = self.scaleWorldExtent( self.initialAoi )
##        boundedScaledBounds = self.boundExtent( scaledBounds, scaledInitialAoi )
#        boundedScaledBounds = scaledBounds
#        if self.currentScaledBounds <> None:
#            spacing = self.getSpacing()
#            newImageExtent = []
#            scaling = self.getFieldData( 'scale' )
#            position = self.getFieldData( 'position' )
#            new_position = []
#            for iAxis in range(3):
#                low = 2*iAxis
#                high = low + 1
#                db0 = ( boundedScaledBounds[ low ] -  self.currentScaledBounds[ low  ] )
#                db1 = ( boundedScaledBounds[ high ] - self.currentScaledBounds[ high ] )
#                scale_factor = ( spacing[iAxis] * scaling[iAxis] )
#                e0 = self.currentExtent[low]   + db0 / scale_factor
#                e1 = self.currentExtent[high]  + db1 / scale_factor
##                e0b = bound( e0,  self.initialExtent[ low ],  self.initialExtent[ high ] )
##                e1b = bound( e1,  self.initialExtent[ low ],  self.initialExtent[ high ] )
#                newImageExtent.append( e0 )
#                newImageExtent.append( e1 )
#                dp = ( e0 - self.currentExtent[ low ] ) * scale_factor
#                new_position.append( position[iAxis] + dp )      
#            self.setExtent( newImageExtent )
#            self.setPosition( new_position )
#            self.render()
#            self.currentAoi = self.getUnscaledWorldExtent( newImageExtent )
#            currentScaledAOI = self.scaleWorldExtent( self.currentAoi )
#            print "-------------- boundsToAoi: \n\t scaledBounds: (%.1f, %.1f), currentAoi: (%.1f, %.1f), currentScaledAOI: (%.1f, %.1f)\n\t newImageExtent: (%.1f, %.1f), scaling: ( %.2f %.2f %.2f ), position: %.2f, dp: %.2f" % \
#                ( scaledBounds[0], scaledBounds[1], self.currentAoi[0], self.currentAoi[1], currentScaledAOI[0], currentScaledAOI[1], newImageExtent[0], newImageExtent[1], scaling[0], scaling[1], scaling[2], new_position[0], (new_position[0] - position[0]) )
#            print " Output: scaling: %s, extent: %s " % ( str(self.getScaling()), str(self.resample.GetOutputExtent() ) )
##            print " boundedScaledBounds: %s, scaledInitialAoi: %s " % ( str2f(boundedScaledBounds[0:2]), str2f(scaledInitialAoi[0:2]) )
#        self.currentScaledBounds = boundedScaledBounds
#        return self.currentAoi
#
#    def startConfigurationObserver( self, parameter_name, *args ):
#        PersistentVisualizationModule.startConfigurationObserver( self, parameter_name, *args )
#        self.currentScaledBounds = None
#
#    def getPosition( self ):
#        return self.getFieldData( 'position' )
#        
#    def setPosition( self, position ):
#        wmod.setResult( 'position', position )
#        self.setFieldData( 'position', position )
#        self.resample.Modified()
#        
#    def AoiToBounds( self, aoi ):
#        bounds = self.scaleWorldExtent( aoi )
#        return bounds
#
#    def getAoi(self):
#        unscaledWorldExtent = self.getUnscaledWorldExtent( self.currentExtent )
#        return unscaledWorldExtent
#
#    def setAoi( self, unscaledWorldExtent ):
#        extent = self.getImageExtent(  unscaledWorldExtent )
#        self.setExtent( extent )
#    
#    def getScaling(self):
#        return self.getFieldData( 'scale' )
#
#    def setScaling( self, scaling ):
#        self.setFieldData( 'scale', scaling )
#        self.resample.Modified()
#                        
#    def startResample(self, object, event):
#        self.currentAoi = self.getUnscaledWorldExtent( self.currentExtent )      
#        
#    def getOrigin(self):  
#        return self.initialOrigin if ( self.currentOrigin == None ) else self.currentOrigin
#
#    def setOrigin( self, value ):  
#        self.currentOrigin = value
#        self.resample.SetOutputOrigin( value )
#                                      
#    def getExtent(self):  
#        return self.initialExtent if ( self.currentExtent == None ) else  self.currentExtent 
#
#    def setExtent( self, value ):  
#        self.currentExtent = value
#        self.resample.SetOutputExtent( [ int(round(value[i])) for i in range(6) ] )
#        self.currentAoi = self.getUnscaledWorldExtent( self.currentExtent )
#                                      
#    def getSpacing(self):  
#        return self.initialSpacing if ( self.currentSpacing == None ) else  self.currentSpacing 
#
#    def setSpacing( self, value, **args ):  
#        self.currentSpacing = value
#        self.resample.SetOutputSpacing( value )
#        adjustExtent = args.get( 'adjustExtent', True )
#        if adjustExtent:
#            self.currentExtent = [ ( ( self.currentAoi[i] - self.currentOrigin[i/2] ) / self.currentSpacing[i/2] ) for i in range(6) ]
#            self.resample.SetOutputExtent( [ int( round( self.currentExtent[i] ) ) for i in range(6) ] )
#                                                        
#    def getImageCoords( self, unscaledWorldCoords ):
#        return [ ( ( ( unscaledWorldCoords[iAxis] - self.initialOrigin[iAxis] ) / self.currentSpacing[ iAxis ] )  ) for iAxis in range(3) ]
#
#    def getUnscaledWorldCoords( self, imageCoords ):
#         return [ ( ( imageCoords[ iAxis ] * self.currentSpacing[ iAxis ] ) + self.initialOrigin[iAxis]  ) for iAxis in range(3) ]
#
##    def unscaleWorldExtent( self, scaledWorldExtent ):
##        scaling = self.getFieldData( 'scale' )
##        position = self.getFieldData( 'position' )
##        return [ ( scaledWorldExtent[i] - position[i/2] ) / scaling[i/2] for i in range(6) ]
#
#    def scaleWorldExtent( self, unscaledWorldExtent ):
#        scaling = self.getFieldData( 'scale' )
#        position = self.getFieldData( 'position' )
#        scaledWorldExtent = []
#        for i in range(3):
#            low = 2*i
#            high = low + 1
#            scaledWorldExtent.append( position[i] )
#            scaledWorldExtent.append( position[i] + ( unscaledWorldExtent[high] - unscaledWorldExtent[low] ) * scaling[i] )
#        return scaledWorldExtent
#                                                
#    def getImageExtent( self, unscaledWorldExtent ):
#        return [ ( ( ( unscaledWorldExtent[i] - self.initialOrigin[i/2] ) / self.currentSpacing[ i/2 ] )  ) for i in range(6) ]
#
#    def getUnscaledWorldExtent( self, extent=None, spacing = None, origin = None ):
#        if extent  == None: extent  = self.getExtent()
#        if origin  == None: origin  = self.getOrigin()
#        if spacing == None: spacing = self.getSpacing()
#        return [ ( ( extent[ i ] * spacing[ i/2 ] ) + origin[i/2]  ) for i in range(6) ]
#
#    def boundImageCoord( self, iAxis, coordValue ):
#        bounds = [ self.initialExtent[2*iAxis], self.initialExtent[2*iAxis+1] ]
#        if coordValue < bounds[0]:  coordValue =  bounds[0] 
#        if coordValue > bounds[1]:  coordValue =  bounds[1] 
#        return coordValue
#
#    def boundImageExtent( self,  extent ):
#        for i in range(6): extent[i] = self.boundImageCoord( i/2, extent[i] )
#        
#    def getModuleParameters( self ):
#        return [ 'position' ]
#
#    def boundsToScaling( self, scaledBounds ):
#        scaling = self.getFieldData( 'scale' )
#        if self.currentScaledBounds <> None:
#            for i in range(3):
#                low = 2*i
#                high = low + 1
#                expansion_factor = ( scaledBounds[high] - scaledBounds[low] ) / ( self.currentScaledBounds[high] - self.currentScaledBounds[low] )
#                scaling[i] = scaling[i] * expansion_factor
#            self.setScaling( scaling )
#            self.setPosition( scaledBounds[0:5:2] )
#        self.currentScaledBounds = scaledBounds
#        return scaling
# 
#    def scalingToBounds( self, scaling ):
#        unscaledWorldExtent = self.getUnscaledWorldExtent( self.currentExtent )
#        position = self.getFieldData( 'position' )
#        bounds = self.scaleWorldExtent( unscaledWorldExtent )
#        print "-------------- scalingToBounds: \n\t unscaledWorldExtent: (%.1f, %.1f), bounds: (%.1f, %.1f)\n\t currentExtent: (%.1f, %.1f), position: %.2f, scaling: %.2f" % \
#            ( unscaledWorldExtent[0], unscaledWorldExtent[1], bounds[0], bounds[1], self.currentExtent[0], self.currentExtent[1], position[0], scaling[0] )
#        return bounds
#    
#    def onResampleEvent(self, caller, event ):
#        print " >>>>>>>>> Resample Event: %s " % ( event )
#        self.PrintState()
#        
#    def PrintState(self):
#        output = self.resample.GetOutput()
#        print " Spacing: %s, Origin: %s, Extent: %s " % ( str2f( self.resample.GetOutputSpacing() ), str2f( self.resample.GetOutputOrigin() ), str2f( self.resample.GetOutputExtent() )  )
#        print " Output: Origin: %s, Spacing: %s, Extent: %s " % ( str2f( output.GetOrigin() ), str2f( output.GetSpacing() ), str( output.GetExtent() ) )                     
#
#    def execute(self):
#        """ execute() -> None
#        Dispatch the vtkRenderer to the actual rendering widget
#        """        
#        self.initialOrigin = self.input.GetOrigin()
#        self.initialExtent = self.input.GetExtent()
#        self.initialSpacing = self.input.GetSpacing()
#        self.initialAoi = self.currentAoi = self.getUnscaledWorldExtent( self.initialExtent, self.initialSpacing ) 
#                
#        self.resample = vtk.vtkImageReslice()
#        self.inputModule.inputToAlgorithm( self.resample )
#        
#        self.setOrigin( self.initialOrigin )
#        self.setSpacing( self.initialSpacing, adjustExtent=False )
#        self.setExtent( self.initialExtent )
#          
#        self.set3DOutput( port=self.resample.GetOutputPort() )
#        self.resample.AddObserver( 'StartEvent', self.onResampleEvent )     
#        self.resample.AddObserver( 'EndEvent', self.onResampleEvent )     
#        
#        position = wmod.forceGetInputFromPort( "position", self.getPosition() ) 
#        self.setPosition( position )                                                                             

class NumberEntryBox( QTextEdit ):
    text_entry_signal = SIGNAL('text_entry')
    
    def __init__(self, name, parent = None, **args ):
        QTextEdit.__init__( self, parent )
        self.setReadOnly(False) 
        self.setMaximumHeight( 20 ) 
        self.isFloat = args.get( 'isFloat', True )
        self.name = name

    def keyPressEvent ( self, e ):
        key = str( e.text() )
        isDigit = key.isdigit()
        if isDigit or ( self.isFloat and ( key == "." ) ) or ( key == '\b' ) or e.matches( QKeySequence.Delete ):    
            QTextEdit.keyPressEvent( self, e )
#        elif ( key == '\r' ) or ( key == '\n' ): 
            if isDigit: self.emit( NumberEntryBox.text_entry_signal, self.name, self.getValue()  )
            
    def setValue( self, value ):
        self.setText( str( value ) )
        
    def getValue( self ):
        textVal = str(self.toPlainText())
        value = float( textVal )  if  self.isFloat else int( textVal  )                                  
        return value
          
class DecimationConfigurationWidget( IVModuleConfigurationDialog ):
    """
    DecimationWidget ...   
    """    
    def __init__(self, name, **args):
        self.axisNames = args.get( 'axes', [ 'X', 'Y', 'Z' ] )
        self.decimationValues = [ -5, -4, -3, -2, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 40, 50, 70, 100 ]
        self.decimationValueMap = {}
        for iVal in range( len( self.decimationValues ) ):
           self.decimationValueMap[ self.decimationValues[iVal] ] = iVal
        IVModuleConfigurationDialog.__init__( self, name, **args )
       
    @staticmethod   
    def getSignature():
        return [ (Integer, 'dx'), (Integer, 'dy'), (Integer, 'dz') ]
            
    def getValue( self ):
        value = []
        for combo in self.combos:
            index = combo.currentIndex()
            value.append( self.decimationValues[index] )
        return value

    def setValue( self, value ):
        for ival in range(3):
            self.combos[ ival ].setCurrentIndex( self.decimationValueMap[ value[ival] ] )
    
    def updateDecimation(self, val ):        
        self.updateParameter()
        
    def createContent( self ):
        resTab = QWidget()  
        self.tabbedWidget.addTab( resTab, 'Decimation' )                                                                
        layout = QGridLayout()
        resTab.setLayout( layout ) 
        layout.setMargin(10)
        layout.setSpacing(20)
        self.combos = []
       
        for iAxis in range(3):
            name = self.axisNames[iAxis]
            res_label = QLabel( "%s Decimation:" % name )
            layout.addWidget( res_label, iAxis, 0 )
            decimationCombo =  QComboBox ( self )
            res_label.setBuddy( decimationCombo )
            decimationCombo.setMaximumHeight( 30 )
            layout.addWidget( decimationCombo, iAxis, 1 )
            for iVal in self.decimationValues: decimationCombo.addItem( str(iVal) )  
            self.combos.append( decimationCombo ) 
            self.connect( decimationCombo, SIGNAL("currentIndexChanged(QString)"), self.updateDecimation ) 
            decimationCombo.setCurrentIndex( self.decimationValueMap[ 1 ] )
        

#            res_label.setBuddy( res_edit )
#            layout.addWidget( res_edit, iAxis, 1 )
#            self.connect( res_edit, NumberEntryBox.text_entry_signal, self.updateResEdit ) 
#            self.resEdit[ name ] = res_edit
#            size_label = QLabel( "Size:"  )
#            layout.addWidget( size_label, iAxis, 2 )
#            size_edit = NumberEntryBox( name, self, isFloat = False )
#            size_label.setBuddy( size_edit )
#            layout.addWidget( size_edit, iAxis, 3 )
#            self.connect( size_edit, NumberEntryBox.text_entry_signal, self.updateSizeEdit ) 
#            self.sizeEdit[ name ] = size_edit

#    def getResolution( self, iAxis ):
#        return self.resEdit[ self.axisNames[iAxis] ].getValue()
#
#    def setResolution( self, iAxis, value ):
#        self.resEdit[ self.axisNames[iAxis] ].setValue( value )
# 
#    def setAxisResolution( self, axisName, value ):
#        self.resEdit[ axisName ].setValue( value )
#
#    def getSize( self, iAxis ):
#        return self.sizeEdit[ self.axisNames[iAxis] ].getValue()
#
#    def setSize( self, iAxis, value ):
#        self.sizeEdit[ self.axisNames[iAxis] ].setValue( value )
#
#    def setAxisSize( self, axisName, value ):
#        self.sizeEdit[ axisName ].setValue( value )

#    def initWidgetFields(self, spacing ):
#        aoi = self.getAoi()
#        for i in range(3):
#            low  = 2*i
#            high = low + 1
#            res = spacing[i]
#            extent = aoi[high] - aoi[low] 
#            size = int( round( extent / res ) ) if (res > 0) else 0
#            self.setSize( i, size )      
#            self.setResolution( i, res )      
#        self.updateParameter()
#                      
#    def updateSizeValue(self):
#        aoi = self.getAoi()
#        for i in range(3):
#            low  = 2*i
#            high = low + 1
#            res = self.getResolution( i )
#            extent = aoi[high] - aoi[low] 
#            size = int( round( extent / res ) ) if (res > 0) else 0
#            self.setSize( i, size )      
#
#    def updateResValue(self):
#        aoi = self.getAoi()
#        for i in range(3):
#            low  = 2*i
#            high = low + 1
#            size = self.getSize( i )   
#            extent = aoi[high] - aoi[low] 
#            res = extent / size if (size > 0) else 0
#            self.setResolution( i, res )     
               
#    def updateResEdit(self, axis_name, value ):
#        print ' %s updateResEdit: %f ' % ( axis_name, value )
#        self.setAxisResolution( axis_name, value )
#        self.updateSizeValue()
#        self.updateParameter()
#
##    def updateSizeEdit(self, axis_name, value ):
#        print ' %s updateSizeEdit: %d ' % ( axis_name, value )
#        self.setAxisSize( axis_name, value )
#        self.updateResValue()
#        self.updateParameter()
            
 ################################################################################

class BoxWidgetWrapper( IVModuleWidgetWrapper ):
    """
    BoxWidgetWrapper ...   
    """    
    def __init__(self, name, module, **args):        
        IVModuleWidgetWrapper.__init__( self, name, module, **args )
        
    def getBounds( self ):
        self.boxWidget.GetPlanes(self.planes)
        bounds = []
        points = self.planes.GetPoints()
        for i in range( 6 ):
            iAxis = i/2
            pt = points.GetPoint(i)
            bounds.append( pt[iAxis] )
        return bounds
    
    def setBounds( self, value ):
        print " Place BoxWidget: %s " % str( value )
        self.boxWidget.PlaceWidget( value[0], value[1], value[2], value[3], value[4], value[5]  )
        
    def setWidgetConfiguration(self, value ):
        self.setBounds( value ) 

    def getWidgetConfiguration(self ):
        return self.getBounds(  ) 
    
    def startConfiguration(self, object, event):
        if self.boxWidget.GetEnabled():
#            print " %% BoxWidget: start Configuration"
            self.startParameter()
                  
    def updateConfiguration(self, object, event):
        if self.boxWidget.GetEnabled():
#            print " %% BoxWidget: update Configuration"
            self.updateParameter()

    def endConfiguration(self, object, event):
        if self.boxWidget.GetEnabled():
#            print " %% BoxWidget: finalize Configuration"
            self.finalizeParameter()
               
    def open( self, startValue   ):
        self.boxWidget.SetEnabled(1)
        self.setValue( startValue if ( startValue <> None ) else self.initial_value )
        faceProperty = self.boxWidget.GetFaceProperty() 
        faceProperty.SetOpacity(0.0)
        faceProperty.SetRepresentationToPoints() 
        self.module.render()
 
    def close( self ):
        self.boxWidget.SetEnabled(0)
                         
    def createContent( self ):
        input =  self.module.inputModule.getOutput()  
        self.boxWidget = vtk.vtkBoxWidget()
        self.boxWidget.SetRotationEnabled(0)
        self.boxWidget.SetPlaceFactor(1.0)
        self.boxWidget.SetInput( input )
        self.planes = vtk.vtkPlanes()
        self.boxWidget.AddObserver("StartInteractionEvent", self.startConfiguration )
        self.boxWidget.AddObserver("InteractionEvent",      self.updateConfiguration )
        self.boxWidget.AddObserver("EndInteractionEvent",   self.endConfiguration ) 

    def activateWidget( self, iren ):
        self.boxWidget.SetInteractor( iren )

# ################################################################################
#
#class AOIWidgetWrapper( BoxWidgetWrapper ):
#    """
#    AOIWidgetWrapper ...   
#    """  
#    @staticmethod   
#    def getSignature():
#        return [ (Float, 'xmin'), (Float, 'xmax'), (Float, 'ymin'), (Float, 'ymax'), (Float, 'zmin'), (Float, 'zmax')  ]
#   
#    def getValue( self ):
#        scaledBounds = self.getBounds() 
#        unscaledBounds = self.module.unscaleWorldExtent( scaledBounds )
#        return unscaledBounds
#
#    def setValue( self, unscaledBounds ):
#        scaledBounds = self.module.scaleWorldExtent( unscaledBounds )
#        self.boxWidget.PlaceWidget( scaledBounds  )
#        return scaledBounds
#
# ###############################################################################
#
#class ScalingWidgetWrapper( BoxWidgetWrapper ):
#    """
#    ScalingWidgetWrapper ...   
#    """  
#    @staticmethod   
#    def getSignature():
#        return [ (Float, 'sx'), (Float, 'sy'), (Float, 'sz') ]
#  
#    def getValue( self ):
#        scaledBounds = self.getBounds() 
#        scaling = self.module.computeScalingFromScaledBounds( scaledBounds )
#        return scaling
#
#    def setValue( self, scaling ):
#        scaledBounds = self.module.computeScaledBoundsFromScaling( scaling )
#        self.boxWidget.PlaceWidget( bounds  )
#        return scaledBounds

 ###############################################################################


from WorkflowModule import WorkflowModule

class Resample(WorkflowModule):
    
    PersistentModuleClass = PM_Resample
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
         
       
if __name__ == '__main__':
    executeVistrail( 'ResampleDemo' )
 
