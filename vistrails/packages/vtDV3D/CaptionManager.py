'''
Created on Aug 25, 2012

@author: tpmaxwell
'''

from PyQt4 import QtCore, QtGui
from vtUtilities import *
import vtk

class CaptionEditor(QtGui.QDialog):
    
    def __init__(self, caption, parent=None):
        super(CaptionEditor, self).__init__(parent)
        self.caption = caption
        actor = self.getActor()
        c = actor.GetProperty().GetColor()
        a = actor.GetProperty().GetOpacity()
        rgba = [ int(round(c[0]*255)), int(round(c[1]*255)), int(round(c[2]*255)), int(round(a*255)) ]
        self.color = QtGui.QColor( rgba[0], rgba[1], rgba[2], rgba[3] )
 
        captionLabel = QtGui.QLabel("Caption Text: ")
        self.captionTextBox = QtGui.QLineEdit( actor.GetCaption(), self )

        self.chooseColorButton = QtGui.QPushButton( 'Choose Color', self )
        self.chooseColorButton.setAutoFillBackground(True) 
        self.connect(self.chooseColorButton, QtCore.SIGNAL('clicked(bool)'), self.chooseColor )
                    
        buttonBox = QtGui.QDialogButtonBox( QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close )

        grid = QtGui.QGridLayout()
        grid.addWidget(captionLabel, 0, 0)
        grid.addWidget(self.captionTextBox, 0, 1)
        grid.addWidget(self.chooseColorButton, 1, 0, 1, 2)
        grid.addWidget(buttonBox, 2, 0, 1, 2)
        self.setLayout(grid)

        self.connect( buttonBox, QtCore.SIGNAL("accepted()"), self.accept )
        self.connect( buttonBox, QtCore.SIGNAL("rejected()"), self.reject )
        self.setWindowTitle("Caption Editor")
        self.updateButtonColor()  
        
    def getActor(self):
        return self.caption.GetRepresentation().GetCaptionActor2D() 
    
    def updateButtonColor(self):
        pal =  QtGui.QPalette( self.color )
#        self.chooseColorButton.setAutoFillBackground(True)
        self.chooseColorButton.setPalette(pal)
#        self.chooseColorButton.palette().setColor( QtGui.QPalette.ButtonText, self.color )
           
    def chooseColor(self):
        self.color = QtGui.QColorDialog.getColor ( self.color, self, "Choose Caption Color", QtGui.QColorDialog.ShowAlphaChannel ) 
        self.updateButtonColor()
                
    def accept( self ):
        actor = self.getActor()
        actor.SetCaption( str( self.captionTextBox.text() ) )
        actor.GetProperty().SetColor ( self.color.redF(), self.color.greenF(), self.color.blueF() )
        actor.GetProperty().SetOpacity ( self.color.alphaF() )
        super(CaptionEditor, self).accept()   

    def reject( self ):
        super(CaptionEditor, self).reject()   

class CaptionManager( QtCore.QObject ):
    
    persist_captions_signal = QtCore.SIGNAL("persist_captions_signal")
    config_name = "addCaption"

    def __init__( self, cellWidget, iren, **args ):
        QtCore.QObject.__init__( self )
        caption_data = args.get('data', None )
        self.captionKey = 0
        self.captions = {}
        self.cellWidget = cellWidget
        self.iren = iren
        if caption_data: 
            self.deserializeCaptions( caption_data )

    def addCaption( self, **args ):
        self.captionKey += 1
        existing_caption = self.captions.get( self.captionKey, None )
        if not existing_caption:
            text = args.get('text', "Right-click to edit" )            
            color= args.get( 'color',  [ 0, 0, 1 ] )
#            pos = QtCore.QPointF( self.cellWidget.current_pos )

            captionRep =  vtk.vtkCaptionRepresentation() 
            captionWidget = vtk.vtkCaptionWidget()
            captionWidget.SetInteractor(self. iren )
            captionWidget.SetRepresentation(captionRep)
            captionWidget.SelectableOn() 
            captionWidget.ResizableOn() 
            captionWidget.AddObserver( 'AnyEvent', self.captionObserver )
            pos0 = args.get( 'pos0',  [ 0.8, 0.8 ] )
            pos1 = args.get( 'pos1',  [ 0.2, 0.05 ] )
            apos = args.get( 'apos',  [ 20.0, 20.0, 0.0 ] )
            captionRep.SetPosition( pos0[0], pos0[1]  )
            captionRep.SetPosition2( pos1[0], pos1[1]  )
            captionRep.SetAnchorPosition( apos )
            captionActor = captionRep.GetCaptionActor2D() 
            captionWidget.GetEventTranslator().SetTranslation( vtk.vtkCommand.RightButtonPressEvent, vtk.vtkWidgetEvent.Select )
            captionWidget.GetEventTranslator().SetTranslation( vtk.vtkCommand.RightButtonReleaseEvent, vtk.vtkWidgetEvent.EndSelect )
            
            captionActor.SetCaption( text )
            captionActor.BorderOn()
#            captionActor.SetAttachmentPoint(  pos.x(), pos.y(), 0.0  ) 
            captionActor.GetCaptionTextProperty().BoldOff()
            captionActor.GetCaptionTextProperty().ItalicOff()
            captionActor.GetCaptionTextProperty().ShadowOff()
            captionActor.GetCaptionTextProperty().SetFontFamilyToArial()
            captionActor.GetCaptionTextProperty().SetJustificationToCentered()
            captionActor.ThreeDimensionalLeaderOff()
            captionActor.LeaderOn()
            captionActor.SetLeaderGlyphSize( 10.0 )
            captionActor.GetProperty().SetColor ( color[0], color[1], color[2] )
            captionActor.SetMaximumLeaderGlyphSize( 10.0 )
            self.captions[ self.captionKey ] = captionWidget
            captionWidget.On()
            return captionWidget
        
    def serializeCaptions(self):
        serialized_captions = []
        for caption in self.captions.values():
            captionRep = caption.GetRepresentation()
            pos = captionRep.GetPosition ()
            pos2 = captionRep.GetPosition2 ()
            captionActor = captionRep.GetCaptionActor2D() 
            color = captionActor.GetProperty().GetColor()
            text = captionActor.GetCaption ()
            arrow_pos = captionActor.GetAttachmentPoint()
            serialized_caption = "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%s" % ( pos[0], pos[1], pos2[0], pos2[1],arrow_pos[0],arrow_pos[1],arrow_pos[2],color[0],color[1],color[2],text)
            serialized_captions.append( serialized_caption )
        result = ';'.join( serialized_captions )
        self.emit(self.persist_captions_signal, result )
        
    def deserializeCaptions( self, captionData ):
        captionReps = getItem( captionData ).split(';')
        for captionRep in captionReps:
            cf = captionRep.split(',')
            pos0 = [ float(cf[0]), float(cf[1]) ]
            pos1 = [ float(cf[2]), float(cf[3]) ]
            apos = [ float(cf[4]), float(cf[5]), float(cf[6]) ]
            color = [ float(cf[7]), float(cf[8]), float(cf[9]) ]
            text = cf[10]
            self.addCaption( text=text, pos0=pos0, pos1=pos1, apos=apos, color=color )
        
    def deleteCaption( self, caption ):
        caption.Off()
#        for item in self.captions.items():
#            if item[1] == caption:
#                self.captions[ item[0] ] = None
        
    def editCaption( self, caption=None ):
        if caption == None:
            caption = self.captions[ self.captionKey ]
        editor = CaptionEditor( caption )
        editor.exec_()
        self.serializeCaptions()    

    def captionObserver (self, caller, event ):
        if self.cellWidget:           
            if ( str(event) == "ModifiedEvent" ) or ( str(event) == "EndInteractionEvent" ):
                self.serializeCaptions()    
            elif str(event) == "StartInteractionEvent":
                if self.cellWidget.current_button == QtCore.Qt.RightButton:
                    caller.GetRepresentation().MovingOff() 
                    captionActionMenu = QtGui.QMenu()
                    captionActionMenu.addAction("Edit")
                    captionActionMenu.addAction("Delete")
                    selectedItem = captionActionMenu.exec_( self.cellWidget.current_pos )
                    if selectedItem:
                        if   selectedItem.text() == "Edit":    self.editCaption( caller )           
                        elif selectedItem.text() == "Delete":  self.deleteCaption( caller )           
#            print " Caption Observer: event = %s, button = %s " % ( str( event ), str( self.cellWidget.current_button ) )
