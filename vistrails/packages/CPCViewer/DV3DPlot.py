'''
Created on Apr 23, 2014

@author: tpmaxwell
'''
from __future__ import with_statement
from __future__ import division

_TRY_PYSIDE = True

try:
    if not _TRY_PYSIDE:
        raise ImportError()
    import PySide.QtCore as _QtCore
    QtCore = _QtCore
    import PySide.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = True
except ImportError:
    import sip
    try: sip.setapi('QString', 2)
    except: pass
    try: sip.setapi('QVariant', 2)
    except: pass
    import PyQt4.QtCore as _QtCore
    QtCore = _QtCore
    import PyQt4.QtGui as _QtGui
    QtGui = _QtGui
    USES_PYSIDE = False
    
import vtk, sys
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
MIN_LINE_LEN = 50
VTK_NOTATION_SIZE = 14
from packages.CPCViewer.ColorMapManager import *

def CheckAbort(obj, event):
    if obj.GetEventPending() != 0:
        obj.SetAbortRender(1)

def getClassName( instance ):
    return instance.__class__.__name__ if ( instance <> None ) else "None" 

class PlotType:
    Planar = 0
    Spherical = 1
    List = 0
    Grid = 1
    LevelAliases = [ 'isobaric', "layers", "interfaces" ]
    
    @classmethod
    def validCoords( cls, lat, lon ):
        return ( id(lat) <> id(None) ) and ( id(lon) <> id(None) )
    
    @classmethod
    def isLevelAxis( cls, pid ):
        lname = pid.lower()
        if ( lname.find('lev')  >= 0 ): return True
        if ( lname.find('bottom') >= 0 ) and ( lname.find('top') >= 0 ): return True
        if pid in cls.LevelAliases: return True
        if lname in cls.LevelAliases: return True
        return False    

    @classmethod
    def getPointsLayout( cls, grid ):
        if grid <> None:
            if (grid.__class__.__name__ in ( "RectGrid", "FileRectGrid") ): 
                return cls.Grid
        return cls.List  


def getBool( val ):
    if isinstance( val, str ):
        if( val.lower()[0] == 't' ): return True
        if( val.lower()[0] == 'f' ): return False
        try:    val = int(val)
        except: pass
    return bool( val )

class QVTKAdaptor( QVTKRenderWindowInteractor ):
    
    def __init__( self, **args ):
        QVTKRenderWindowInteractor.__init__( self, **args )
        print str( dir( self ) )
    
    def keyPressEvent( self, qevent ):
        QVTKRenderWindowInteractor.keyPressEvent( self, qevent )
        self.emit( QtCore.SIGNAL('event'), ( 'KeyEvent', qevent.key(), str( qevent.text() ), qevent.modifiers() ) )
#        print " QVTKAdaptor keyPressEvent: %x [%s] " % ( qevent.key(), str( qevent.text() ) )
#        sys.stdout.flush()

    def closeEvent( self, event ):
        self.emit( QtCore.SIGNAL('Close') )
        QVTKRenderWindowInteractor.closeEvent( self, event )

    def resizeEvent( self, event ):
        self.emit( QtCore.SIGNAL('event'), ( 'ResizeEvent', 0 ) )
        QVTKRenderWindowInteractor.resizeEvent( self, event )
 
class TextDisplayMgr:
    
    def __init__( self, renderer ):
        self.renderer = renderer
    
    def setTextPosition(self, textActor, pos, size=[400,30] ):
#        vpos = [ 2, 2 ] 
        vp = self.renderer.GetSize()
        vpos = [ pos[i]*vp[i] for i in [0,1] ]
        textActor.GetPositionCoordinate().SetValue( vpos[0], vpos[1] )      
        textActor.GetPosition2Coordinate().SetValue( vpos[0] + size[0], vpos[1] + size[1] )      
  
    def getTextActor( self, aid, text, pos, **args ):
        textActor = self.getProp( 'vtkTextActor', aid  )
        if textActor == None:
            textActor = self.createTextActor( aid, **args  )
            self.renderer.AddViewProp( textActor )
        self.setTextPosition( textActor, pos )
        text_lines = text.split('\n')
        linelen = len(text_lines[-1])
        if linelen < MIN_LINE_LEN: text += (' '*(MIN_LINE_LEN-linelen)) 
        text += '.' 
        textActor.SetInput( text )
        textActor.Modified()
        return textActor

    def getProp( self, ptype, pid = None ):
        try:
            props = self.renderer.GetViewProps()
            nitems = props.GetNumberOfItems()
            for iP in range(nitems):
                prop = props.GetItemAsObject(iP)
                if prop.IsA( ptype ):
                    if not pid or (prop.id == pid):
                        return prop
        except: 
            pass
        return None
  
    def createTextActor( self, aid, **args ):
        textActor = vtk.vtkTextActor()  
        textActor.SetTextScaleMode( vtk.vtkTextActor.TEXT_SCALE_MODE_PROP )  
#        textActor.SetMaximumLineHeight( 0.4 )       
        textprop = textActor.GetTextProperty()
        textprop.SetColor( *args.get( 'color', ( VTK_FOREGROUND_COLOR[0], VTK_FOREGROUND_COLOR[1], VTK_FOREGROUND_COLOR[2] ) ) )
        textprop.SetOpacity ( args.get( 'opacity', 1.0 ) )
        textprop.SetFontSize( args.get( 'size', 10 ) )
        if args.get( 'bold', False ): textprop.BoldOn()
        else: textprop.BoldOff()
        textprop.ItalicOff()
        textprop.ShadowOff()
        textprop.SetJustificationToLeft()
        textprop.SetVerticalJustificationToBottom()        
        textActor.GetPositionCoordinate().SetCoordinateSystemToDisplay()
        textActor.GetPosition2Coordinate().SetCoordinateSystemToDisplay() 
        textActor.VisibilityOff()
        textActor.id = aid
        return textActor 
       
class DV3DPlot(QtCore.QObject):  

    sliceAxes = [ 'x', 'y', 'z' ]  

    def __init__( self,  **args ):
        QtCore.QObject.__init__( self )
        self.useGui = args.get( 'gui', True )
        self.xcenter = 100.0
        self.xwidth = 300.0
        self.ycenter = 0.0
        self.ywidth = 180.0

        self.widget = None
        self.textDisplayMgr = None
        self.enableClip = False
        self.variables = {}

        self.isValid = True
        self.cameraOrientation = {}
        self.labelBuff = ""
        self.configDialog = None
        self.colormapManagers= {}
        self.stereoEnabled = 0
        self.maxStageHeight = 100.0
        self.observerTargets = set()

        self.renderWindow = args.get( 'renwin', self.createRenderWindow() )
        self.renderWindowInteractor = self.renderWindow.GetInteractor()
        style = args.get( 'istyle', vtk.vtkInteractorStyleTrackballCamera() )  
        self.renderWindowInteractor.SetInteractorStyle( style )
        self.configurationInteractorStyle = vtk.vtkInteractorStyleUser()
        self.activated = False

    def clearReferrents(self):
        self.removeObservers()
        self.renderer = None
        self.renderWindowInteractor = None

    def removeObservers( self ): 
        for target in self.observerTargets:
            target.RemoveAllObservers()
        self.observerTargets.clear()

    def createRenderWindow(self):
        if self.useGui:
            self.widget = QVTKAdaptor()
            self.widget.Initialize()
            self.widget.Start()        
            self.connect( self.widget, QtCore.SIGNAL('event'), self.processEvent )  
            self.connect( self.widget, QtCore.SIGNAL("Close"), self.closeConfigDialog  ) 
            renwin = self.widget.GetRenderWindow()
        else:
            renwin = vtk.vtkRenderWindow()
            self.renderWindowInteractor = vtk.vtkGenericRenderWindowInteractor()
            self.renderWindowInteractor.SetRenderWindow( renwin )
            
        return renwin
    
    def closeConfigDialog(self):
        pass
    
    def enableRender(self, **args ):
        return True

    def render( self, **args ):
        if self.enableRender( **args ):
            self.renderWindow.Render()

    def processEvent(self, eventArgs ):
        if eventArgs[0] == "KeyEvent":
            self.onKeyEvent( eventArgs[1:])
        if eventArgs[0] == "ResizeEvent":
            self.onResizeEvent()           
            
    def onKeyEvent(self, eventArgs ):
        pass

    def getLUT( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut

    def toggleColormapVisibility(self):
        for colormapManager in self.colormapManagers.values():
            colormapManager.toggleColormapVisibility()
        self.render()
    
    def getColormapManager( self, **args ):
        cmap_index = args.get('index',0)
        name = args.get('name',None)
        invert = args.get('invert',None)
        smooth = args.get('smooth',None)
        cmap_mgr = self.colormapManagers.get( cmap_index, None )
        if cmap_mgr == None:
            lut = vtk.vtkLookupTable()
            cmap_mgr = ColorMapManager( lut ) 
            self.colormapManagers[cmap_index] = cmap_mgr
        if (invert <> None): cmap_mgr.invertColormap = invert
        if (smooth <> None): cmap_mgr.smoothColormap = smooth
        if name:   cmap_mgr.load_lut( name )
        return cmap_mgr
        
    def setColormap( self, data, **args ):
        colormapName = str(data[0])
        invertColormap = getBool( data[1] ) 
        enableStereo = getBool( data[2] )
        show_colorBar = getBool( data[3] ) if ( len( data ) > 3 ) else 0 
        cmap_index = args.get( 'index', 0 )
        metadata = self.getMetadata()
        var_name = metadata.get( 'var_name', '')
        var_units = metadata.get( 'var_units', '')
        self.updateStereo( enableStereo )
        colormapManager = self.getColormapManager( name=colormapName, invert=invertColormap, index=cmap_index, units=var_units )
        if( colormapManager.colorBarActor == None ): 
            cm_title = str.replace( "%s (%s)" % ( var_name, var_units ), " ", "\n" )
            cmap_pos = [ 0.9, 0.2 ] if (cmap_index==0) else [ 0.02, 0.2 ]
            self.renderer.AddActor( colormapManager.createActor( pos=cmap_pos, title=cm_title ) )
        colormapManager.setColorbarVisibility( show_colorBar )
        self.render() 
        return True
        return False 
    
    def getUnits(self, var_index ):
        return ""
    
    def getMetadata(self):
        return {}
    

    def updateStereo( self, enableStereo ):   
        if enableStereo:
            self.renderWindow.StereoRenderOn()
            self.stereoEnabled = 1
        else:
            self.renderWindow.StereoRenderOff()
            self.stereoEnabled = 0

            
    def getColormap(self, cmap_index = 0 ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return [ colormapManager.colormapName, colormapManager.invertColormap, self.stereoEnabled ]

    def start(self):
        self.renderWindowInteractor.Start() 
         
    def invalidate(self):
        self.isValid = False

    def getLabelActor(self):
        return self.textDisplayMgr.getTextActor( 'label', self.labelBuff, (.01, .90), size = VTK_NOTATION_SIZE, bold = True  ) if self.textDisplayMgr else None

    def onResizeEvent(self):
        self.updateTextDisplay( None, True )
        
    def updateTextDisplay( self, text, render=False ):
        if text <> None:
            metadata = self.getMetadata()
            var_name = metadata.get( 'var_name', '')
            var_units = metadata.get( 'var_units', '')
            self.labelBuff = "%s (%s)\n%s" % ( var_name, var_units, str(text) )
        label_actor = self.getLabelActor()
        if label_actor: label_actor.VisibilityOn() 
        if render: self.render()     

    def getLut( self, cmap_index=0  ):
        colormapManager = self.getColormapManager( index=cmap_index )
        return colormapManager.lut
        
    def updatingColormap( self, cmap_index, colormapManager ):
        pass

    def addObserver( self, target, event, observer ):
        self.observerTargets.add( target ) 
        target.AddObserver( event, observer ) 

    def createRenderer(self, **args ):
        background_color = args.get( 'background_color', VTK_BACKGROUND_COLOR )
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*background_color)

        self.renderWindow.AddRenderer( self.renderer )    
        self.renderWindowInteractor.AddObserver( 'RightButtonPressEvent', self.onRightButtonPress )  
        self.textDisplayMgr = TextDisplayMgr( self.renderer )             
        self.pointPicker = vtk.vtkPointPicker()
        self.pointPicker.PickFromListOn()   
        try:        self.pointPicker.SetUseCells(True)  
        except:     print>>sys.stderr,  "Warning, vtkPointPicker patch not installed, picking will not work properly."
        self.pointPicker.InitializePickList()             
        self.renderWindowInteractor.SetPicker(self.pointPicker) 
        self.addObserver( self.renderer, 'ModifiedEvent', self.activateEvent )
        if self.enableClip:
            self.clipper = vtk.vtkBoxWidget()
            self.clipper.RotationEnabledOff()
            self.clipper.SetPlaceFactor( 1.0 ) 
            self.clipper.KeyPressActivationOff()
            self.clipper.SetInteractor( self.renderWindowInteractor )    
            self.clipper.SetHandleSize( 0.005 )
            self.clipper.SetEnabled( True )
            self.clipper.InsideOutOn()  
           
#        self.clipper.AddObserver( 'StartInteractionEvent', self.startClip )
#        self.clipper.AddObserver( 'EndInteractionEvent', self.endClip )
#        self.clipper.AddObserver( 'InteractionEvent', self.executeClip )
            self.clipOff() 

    def isConfigStyle( self, iren ):
        if not iren: return False
        return getClassName( iren.GetInteractorStyle() ) == getClassName( self.configurationInteractorStyle )

    def setInteractionState(self, caller, event):
        print "Caught key press event"
        return 0
    
    def onAnyEvent(self, caller, event):
        return 0

    def updateLevelingEvent(self, caller, event):
        return 0
    
    def onKeyPress(self, caller, event):
        print "Caught key press event"
        return 0
    
    def onKeyRelease(self, caller, event):
        return 0
    
    def onLeftButtonPress(self, caller, event):
        return 0
    
    def onModified(self, caller, event):
        return 0
    
    def onRender(self, caller, event):
        return 0

    def onLeftButtonRelease(self, caller, event):
        return 0

    def onRightButtonRelease(self, caller, event):
        return 0

    def onRightButtonPress(self, caller, event):
        return 0
    
    def updateInteractor(self): 
        return 0    
    
    def activateEvent( self, caller, event ):
        if not self.activated:
#            self.addObserver( self.renwin,"AbortCheckEvent", CheckAbort)
#            self.activateWidgets( self.renderWindowInteractor )                                  
            self.addObserver( self.renderWindowInteractor, 'CharEvent', self.setInteractionState )                   
            self.addObserver( self.renderWindowInteractor, 'MouseMoveEvent', self.updateLevelingEvent )
#                        self.addObserver( 'LeftButtonReleaseEvent', self.finalizeLevelingEvent )
            self.addObserver( self.renderWindowInteractor, 'AnyEvent', self.onAnyEvent )  
#                        self.addObserver( 'MouseWheelForwardEvent', self.refineLevelingEvent )     
#                        self.addObserver( 'MouseWheelBackwardEvent', self.refineLevelingEvent )     
#            self.addObserver( self.renderWindowInteractor, 'CharEvent', self.onKeyPress )
            self.addObserver( self.renderWindowInteractor, 'KeyReleaseEvent', self.onKeyRelease )
            self.addObserver( self.renderWindowInteractor, 'LeftButtonPressEvent', self.onLeftButtonPress )
            self.addObserver( self.renderWindowInteractor, 'ModifiedEvent', self.onModified )
            self.addObserver( self.renderWindowInteractor, 'RenderEvent', self.onRender )                   
            self.addObserver( self.renderWindowInteractor, 'LeftButtonReleaseEvent', self.onLeftButtonRelease )
            self.addObserver( self.renderWindowInteractor, 'RightButtonReleaseEvent', self.onRightButtonRelease )
            self.addObserver( self.renderWindowInteractor, 'RightButtonPressEvent', self.onRightButtonPress )
#             for configurableFunction in self.configurableFunctions.values():
#                 configurableFunction.activateWidget( self.renderWindowInteractor  )
            self.updateInteractor() 
            self.activated = True 
            
    def toggleClipping(self):
        if self.clipper.GetEnabled():   self.clipOff()
        else:                           self.clipOn()
        
    def clipOn(self):
        if self.enableClip:
            self.clipper.On()
            self.executeClip()

    def clipOff(self):
        if self.enableClip:
            self.clipper.Off()      
        
        
    def startEventLoop(self):
        self.renderWindowInteractor.Start()

    def recordCamera( self ):
        c = self.renderer.GetActiveCamera()
        self.cameraOrientation[ self.topo ] = ( c.GetPosition(), c.GetFocalPoint(), c.GetViewUp() )

    def resetCamera( self, pts = None ):
        cdata = self.cameraOrientation.get( self.topo, None )
        if cdata:
            self.renderer.GetActiveCamera().SetPosition( *cdata[0] )
            self.renderer.GetActiveCamera().SetFocalPoint( *cdata[1] )
            self.renderer.GetActiveCamera().SetViewUp( *cdata[2] )       
        elif pts:
            self.renderer.ResetCamera( pts.GetBounds() )
        else:
            self.renderer.ResetCamera( self.getBounds() )
            
    def initCamera(self):
        self.renderer.GetActiveCamera().SetPosition( self.xcenter, self.ycenter, 400.0 )
        self.renderer.GetActiveCamera().SetFocalPoint( self.xcenter, self.ycenter, 0.0 )
        self.renderer.GetActiveCamera().SetViewUp( 0, 1, 0 )  
        self.renderer.ResetCameraClippingRange()     
            
    def getCamera(self):
        return self.renderer.GetActiveCamera()
    
    def setFocalPoint( self, fp ):
        self.renderer.GetActiveCamera().SetFocalPoint( *fp )
        
    def printCameraPos( self, label = "" ):
        cam = self.getCamera()
        cpos = cam.GetPosition()
        cfol = cam.GetFocalPoint()
        cup = cam.GetViewUp()
        camera_pos = (cpos,cfol,cup)
        print "%s: Camera => %s " % ( label, str(camera_pos) )

    def update(self):
        pass

