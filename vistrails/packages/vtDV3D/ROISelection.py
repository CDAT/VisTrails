'''
Created on Mar 30, 2011

@author: tpmaxwel
'''

#!/usr/bin/env python

from __future__ import division
import functools
import random
import sys
import os
import math
#import nvEarthUtils
#from nvAxis import nvAxis
#from nvAxisCollection import nvAxisCollection
#from nvField import nvField
#from nvFieldCollection import nvFieldCollection
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import time
#from netCDF4 import Dataset # from Scientific.IO.NetCDF import NetCDFFile
import numpy.oldnumeric as N
import numpy as np
#import LatLongUTMconversion
#import LevelChangeDlg

packagePath = os.path.dirname( __file__ )  
defaultMapDir = os.path.join( packagePath, 'data' )
defaultMapFile = [ os.path.join( defaultMapDir,  'WorldMap.jpg' ), os.path.join( defaultMapDir,  'WorldMap.jpg' ) ]
WorldMapGridExtent = [ ( 106, 72, 2902, 1470 ), ( 106, 72, 2902, 1470 ) ]

def GetRandomColormap( seed=11325 ):
     random.seed( seed )
     CM = []
     for ic in range(256):
         c = QColor( int(256*random.random()), int(256*random.random()), int(256*random.random()) )
#            print 'C: ( ' + str(c.red()) + ', ' + str(c.green()) + ', ' + str(c.blue()) + ' )' 
         CM.append( c.rgb() )
     return CM

class VariableSelectionDlg(QDialog):
    def __init__(self, varList, parent=None):
        super(VariableSelectionDlg, self).__init__(parent)
 
        chooseVariableLabel = QLabel("Choose Variable: ")
        self.varComboBox = QComboBox() 
        for var in varList:
            self.varComboBox.addItem(var)
            
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Close)

        grid = QGridLayout()
        grid.addWidget(chooseVariableLabel, 0, 0)
        grid.addWidget(self.varComboBox, 0, 1)
        grid.addWidget(buttonBox, 1, 0, 1, 2)
        self.setLayout(grid)

        self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
        self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
        self.setWindowTitle("Choose Variable")      

    def getSelectedVariable(self):
        return self.varComboBox.currentText() 

class GraphicsView(QGraphicsView):

    def __init__(self, imageGraphicsItem, imageContentExtents, pt0, pt1, parent=None):
        super(GraphicsView, self).__init__(parent)
        self.Extent = ( pt0.x(), pt0.y(), pt1.x(), pt1.y() ) 
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self.imageOriginOffset = QPointF(  imageContentExtents[0], imageContentExtents[1] ) if imageContentExtents <> None else QPointF( 0, 0 )
        imageExtentOffset = QPointF(  imageContentExtents[2], imageContentExtents[3] ) if imageContentExtents <> None else QPointF( imageGraphicsItem.pixmap().width(), imageGraphicsItem.pixmap().height() )
        imagePixelDims = imageExtentOffset - self.imageOriginOffset
        self.imageLatLonScale = ( (self.Extent[2] - self.Extent[0]) / imagePixelDims.x(), (self.Extent[3] - self.Extent[1]) / imagePixelDims.y() )
        self.roiCorner0 = None
        self.roiCorner1 = None
        self.imageGraphicsItem = imageGraphicsItem

#        self.setRenderHint(QPainter.Antialiasing)
#        self.setRenderHint(QPainter.TextAntialiasing)

    def wheelEvent(self, event):
        factor = 1.41 ** (-event.delta() / 240.0)
        self.scale(factor, factor)
        
    def loadImage( self, image ):
        p = QPixmap.fromImage(image)
        self.imageGraphicsItem.setPixmap(p)
        self.update()
        
    def GetPointCoords(self):
        imagePtScaled = None
        ptS = None
        point = self.mapFromGlobal(QCursor.pos())
#        if self.geometry().contains(point):
        ptS = self.mapToScene(point) - self.imageGraphicsItem.pos()
        mapPt = ptS - self.imageOriginOffset
        imagePtScaled = QPointF( (mapPt.x() * self.imageLatLonScale[0]) + self.Extent[0], self.Extent[3] - (mapPt.y() * self.imageLatLonScale[1] ) ) 
        if imagePtScaled.x() < self.Extent[0]:
            imagePtScaled.setX( self.Extent[0] )      
        if imagePtScaled.x() > self.Extent[2]:
            imagePtScaled.setX( self.Extent[2] )      
        if imagePtScaled.y() < self.Extent[1]:
            imagePtScaled.setY( self.Extent[1] )      
        if imagePtScaled.y() > self.Extent[3]:
            imagePtScaled.setY( self.Extent[3] )      
        return ( imagePtScaled, ptS )
    
    def GetScenePointFromGeoPoint(self, geoPt ):
        if geoPt.x() < self.Extent[0]:
            geoPt.setX( self.Extent[0] )      
        if geoPt.x() > self.Extent[2]:
            geoPt.setX( self.Extent[2] )      
        if geoPt.y() < self.Extent[1]:
            geoPt.setY( self.Extent[1] )      
        if geoPt.y() > self.Extent[3]:
            geoPt.setY( self.Extent[3] ) 
        return QPointF(  ( geoPt.x() - self.Extent[0] ) / self.imageLatLonScale[0] + self.imageOriginOffset.x(), 
                         ( self.Extent[3] - geoPt.y() ) / self.imageLatLonScale[1] + self.imageOriginOffset.y() )

    def mousePressEvent(self, event):
        self.roiCorner0, self.scenePt0  = self.GetPointCoords()
        QGraphicsView.mousePressEvent(self, event)
        
    def orderX(self, pt0, pt1):
        if( pt0.x() > pt1.x() ):
            tmp = pt1.x()
            pt1.setX( pt0.x() )
            pt0.setX( tmp )
            
    def orderY(self, pt0, pt1):
        if( pt0.y() > pt1.y() ):
            tmp = pt1.y()
            pt1.setY( pt0.y() )
            pt0.setY( tmp )
            
    def orderCoords(self, pt0, pt1):
        self.orderX(pt0, pt1)
        self.orderY(pt0, pt1)
      
    def mouseReleaseEvent(self, event):
        ( self.roiCorner1, self.scenePt1 ) = self.GetPointCoords()
        if self.roiCorner0 != None and self.roiCorner1 != None:
            self.orderCoords( self.roiCorner0, self.roiCorner1 )
            self.emit( SIGNAL("ROISelected"), self.roiCorner0, self.roiCorner1, self.scenePt0, self.scenePt1 )
        if self.scenePt1 != None:
            self.emit( SIGNAL("PointSelected"), self.scenePt1, self.roiCorner1 )
        QGraphicsView.mouseReleaseEvent(self, event)
        
        
class ROISelectionDialog(QDialog):

    def __init__(self, parent=None, **args ):
        super(QDialog, self).__init__(parent)
             
        self.scene = QGraphicsScene(self)
        self.lonRangeType = args.get( 'lonRangeType', 1 )
        worldMapFile = QString( defaultMapFile[ self.lonRangeType ] )
        pixmap = QPixmap(worldMapFile) 
        item = QGraphicsPixmapItem( pixmap, None, self.scene )
        item.setFlags(QGraphicsItem.ItemIsMovable)
        item.setAcceptedMouseButtons ( Qt.LeftButton )
        item.setPos( 0, 0 )
        
        ROIcorner0 = QPointF( 0, -90)   if self.lonRangeType == 0 else QPointF(-180,-90 )    
        ROIcorner1 = QPointF(360, 90)   if self.lonRangeType == 0 else QPointF( 180, 90 )  
        worldMapExtent = WorldMapGridExtent[ self.lonRangeType ]      
        self.view = GraphicsView( item, worldMapExtent, ROIcorner0, ROIcorner1, self )
        self.view.setMinimumSize( 500, 500 )
        self.filename = QString()
        self.view.setScene(self.scene)
#        self.scene.addItem(item)
               
        self.roiRect = QGraphicsRectItem( worldMapExtent[0], worldMapExtent[1], (worldMapExtent[2]-worldMapExtent[0]), (worldMapExtent[3]-worldMapExtent[1]), item, self.scene )
        self.roiRect.setBrush( QBrush(Qt.NoBrush) )
        pen = QPen(Qt.green) 
        pen.setWidth(2);
        self.roiRect.setPen( pen )
        self.roiRect.setZValue (1)
#       self.scene.addItem( self.roiRect )
        
        w = QWidget()
        panelLayout = QHBoxLayout()
        w.setLayout( panelLayout )
        
        ROICorner0Label = QLabel("<b><u>ROI Corner0:</u></b>")
        ROICorner1Label = QLabel("<b><u>ROI Corner1:</u></b>")
        self.ROICornerLon0 = QLineEdit( "%.1f" % ROIcorner0.x() )
        self.ROICornerLat0 = QLineEdit( "%.1f" % ROIcorner0.y() )
        self.ROICornerLon1 = QLineEdit( "%.1f" % ROIcorner1.x() )
        self.ROICornerLat1 = QLineEdit( "%.1f" % ROIcorner1.y() )
        self.ROICornerLon0.setValidator( QDoubleValidator(self) )
        self.ROICornerLat0.setValidator( QDoubleValidator(self) )
        self.ROICornerLon1.setValidator( QDoubleValidator(self) )
        self.ROICornerLat1.setValidator( QDoubleValidator(self) )
        
        self.connect( self.ROICornerLon0, SIGNAL("editingFinished()"), self.adjustROIRect )
        self.connect( self.ROICornerLat0, SIGNAL("editingFinished()"), self.adjustROIRect )
        self.connect( self.ROICornerLon1, SIGNAL("editingFinished()"), self.adjustROIRect )
        self.connect( self.ROICornerLat1, SIGNAL("editingFinished()"), self.adjustROIRect )
      
        LatLabel0 = QLabel("Lat: ")
        LonLabel0 = QLabel("Lon: ")            
#        grid0 = QGridLayout()
#        grid0.addWidget( ROICorner0Label, 0, 0, 1, 2 )
#        grid0.addWidget( LonLabel0, 1, 0 )
#        grid0.addWidget( self.ROICornerLon0, 1, 1 )
#        grid0.addWidget( LatLabel0, 2, 0 )
#        grid0.addWidget( self.ROICornerLat0, 2, 1 )
        grid0 = QHBoxLayout()
        grid0.addWidget( LonLabel0 )
        grid0.addWidget( self.ROICornerLon0 )
        grid0.addWidget( LatLabel0 )
        grid0.addWidget( self.ROICornerLat0 )

        w0 = QGroupBox("ROI Corner0:")  
#        w0.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
        w0.setLayout( grid0 )
        panelLayout.addWidget( w0 )

        LatLabel1 = QLabel("Lat: ")
        LonLabel1 = QLabel("Lon: ")            
#        grid1 = QGridLayout()
#        grid1.addWidget( ROICorner1Label, 0, 0, 1, 2 )
#        grid1.addWidget( LonLabel1, 1, 0 )
#        grid1.addWidget( self.ROICornerLon1, 1, 1 )
#        grid1.addWidget( LatLabel1, 2, 0 )
#        grid1.addWidget( self.ROICornerLat1, 2, 1 )
        grid1 = QHBoxLayout()
        grid1.addWidget( LonLabel1 )
        grid1.addWidget( self.ROICornerLon1 )
        grid1.addWidget( LatLabel1 )
        grid1.addWidget( self.ROICornerLat1 )
        
        w1 = QGroupBox("ROI Corner1:")  
#        w1.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
        w1.setLayout( grid1 )
        panelLayout.addWidget( w1 )
        
#        FileLabel = QLabel("Current Data File: ")
#        FieldLabel = QLabel("Current Field: ")            
#        self.FileNameLabel = QLabel("None")
#        self.FileNameLabel.setFrameStyle(QFrame.StyledPanel|QFrame.Sunken)
#        self.FieldNameLabel = QLabel("None") 
#        self.FieldNameLabel.setFrameStyle(QFrame.StyledPanel|QFrame.Sunken)
#        self.newFileButton = QPushButton("New")           
#        self.newFieldButton = QPushButton("Choose")           
#        grid2 = QGridLayout()
#        grid2.addWidget( FileLabel, 0, 0 )
#        grid2.addWidget( self.FileNameLabel, 0, 1 )
#        grid2.addWidget( self.newFileButton, 0, 2 )
#        grid2.addWidget( FieldLabel, 1, 0 )
#        grid2.addWidget( self.FieldNameLabel, 1, 1 )
#        grid2.addWidget( self.newFieldButton, 1, 2 )
#        w2 = QFrame()
#        w2.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
#        w2.setLayout( grid2 )
#        panelLayout.addWidget( w2 )
#        self.connect( self.newFileButton, SIGNAL("clicked()"), self.open )
#        self.connect( self.newFieldButton, SIGNAL("clicked()"), self.chooseField )
#        self.newFieldButton.setEnabled(False)
         
        panelLayout.addStretch(1)

        self.connect(self.view, SIGNAL("ROISelected"), self.UpdateROICoords )
        
        self.okButton = QPushButton('&OK', self)
        self.okButton.setFixedWidth(100)
        panelLayout.addWidget(self.okButton)
        self.cancelButton = QPushButton('&Cancel', self)
        self.cancelButton.setShortcut('Esc')
        self.cancelButton.setFixedWidth(100)
        panelLayout.addWidget(self.cancelButton)
        self.connect(self.okButton, SIGNAL('clicked(bool)'), self.okTriggered)
        self.connect(self.cancelButton, SIGNAL('clicked(bool)'), self.close )
        self.view.scale( 0.4, 0.4 )


#        self.renderROIButton = QPushButton("Render ROI")
#        self.connect(self.renderROIButton, SIGNAL("clicked()"), self.renderROI )
#        self.renderROIButton.setEnabled(False)
#        panelLayout.addWidget(self.renderROIButton)
                 
#        self.editROIButton = QPushButton("Edit ROI")
#        self.connect(self.editROIButton, SIGNAL("clicked()"), self.editROI )
#        self.editROIButton.setEnabled(False)
#        panelLayout.addWidget(self.editROIButton)
        
#        button = QPushButton("&Quit")
#        self.connect(button, SIGNAL("clicked()"), self.accept )
#        panelLayout.addWidget(button)
        
#        self.editROIButton.setDefault(False)
#        self.editROIButton.setAutoDefault(False)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(w)
        self.setLayout(layout)
        
    def initScaling(self):
        self.view.scale( 0.4, 0.4 )
        
#        autoLoad = nvSettings.data['autoLoad Default Field']
#        if autoLoad:
#           dataFile = QString( nvSettings.data['Data directory'] + nvSettings.data['Default File'] ) 
#           self.open( dataFile )
#           fieldName = QString( nvSettings.data['Default Field Name'] ) 
#           self.chooseField( fieldName )

    def setROI( self, roi ):
        geoPt0 = QPointF( roi[0], roi[1] )
        geoPt1 = QPointF( roi[2], roi[3] )
        scenePt0 = self.view.GetScenePointFromGeoPoint( geoPt0 )
        scenePt1 = self.view.GetScenePointFromGeoPoint( geoPt1 )
        self.UpdateROICoords( geoPt0, geoPt1, scenePt0, scenePt1 )
                
    def UpdateROICoords(self, geoPt0, geoPt1, scenePt0, scenePt1 ):
        self.ROICornerLon0.setText ( "%.1f" % geoPt0.x() )
        self.ROICornerLat0.setText ( "%.1f" % geoPt0.y() )
        self.ROICornerLon1.setText ( "%.1f" % geoPt1.x() )
        self.ROICornerLat1.setText ( "%.1f" % geoPt1.y() )
        self.UpdateROIRect( scenePt0, scenePt1 )
        
    def UpdateROIRect(self, scenePt0, scenePt1 ):
        self.roiRect.setRect ( scenePt0.x(), scenePt0.y(), scenePt1.x()-scenePt0.x(), scenePt1.y()-scenePt0.y() )
        self.view.update()
        
    def okTriggered(self):
        self.emit(SIGNAL('doneConfigure()'))
        self.close()

    def getROI(self):
         return [ float(self.ROICornerLon0.text()), float(self.ROICornerLat0.text()), float(self.ROICornerLon1.text()), float(self.ROICornerLat1.text())   ]      
     
    def adjustROIRect(self): 
        geoPt0 = QPointF( float(self.ROICornerLon0.text()), float(self.ROICornerLat0.text()) ) 
        geoPt1 = QPointF( float(self.ROICornerLon1.text()), float(self.ROICornerLat1.text()) )   
        if( geoPt1.x() < geoPt0.x() ):
            geoPt1.setX( geoPt0.x() )
        if( geoPt1.y() < geoPt0.y() ):
            geoPt1.setY( geoPt0.y() )           
        scenePt0 = self.view.GetScenePointFromGeoPoint( geoPt0 )
        scenePt1 = self.view.GetScenePointFromGeoPoint( geoPt1 )
        self.UpdateROIRect( scenePt0, scenePt1 )
       
#    def reject(self):
#        self.accept()
#        
#    def close(self):
#        pass
#            
#    def accept(self):
#        self.close()
        
#    def chooseField( self, fieldName=None ):  
#        varnames = self.ncfile.variables.keys()  
#        if fieldName == None or fieldName.isEmpty():
#            varSelDlg = VariableSelectionDlg(varnames,self)
#            var = varnames[0]
#            if varSelDlg.exec_():
#                var = varSelDlg.getSelectedVariable()
#            self.fieldName = str(var)
#        else:
#            self.fieldName = str(fieldName)
#        self.ncvar = self.ncfile.variables[self.fieldName]
#        self.FieldNameLabel.setText( self.fieldName )
#        self.fields = nvFieldCollection( self.ncfile, self.axes, self.fieldName )
#        self.field = self.fields.GetField( self.fieldName )
#        self.editROIButton.setEnabled(True)
#        self.renderROIButton.setEnabled(True)   
                 
#    def open(self, fileName=None):
#        doChooseField = False
#        if fileName == None or fileName.isEmpty():
#            path = QFileInfo(self.filename).path() if not len(self.filename) == 0 else nvSettings.data['Data directory']
#            fileName = QFileDialog.getOpenFileName(self, "Array Editor - Open", path, "NetCDF Files (*.nc *.nc4)")
#            doChooseField = True
#            if fileName.isEmpty():
#                return 
#        self.close()     
#        self.filename = str( fileName ) 
#        print "Reading file: " +  self.filename  
#        self.ncfile = NetCDFFile(self.filename, 'r+')
#        self.axes = nvAxisCollection( self.ncfile ) 
#        self.FileNameLabel.setText( os.path.split( self.filename )[1] ) 
#        self.newFieldButton.setEnabled(True)
#        if doChooseField:
#            self.chooseField()
 
#    def editROI(self):
#        pt0 = QPointF( float(self.ROICornerLon0.text()),  float(self.ROICornerLat0.text())) 
#        pt1 = QPointF( float(self.ROICornerLon1.text()),  float(self.ROICornerLat1.text()))       
#        print "ImageROI: { Pt0 = " + str(pt0) + ", Pt1 = " + str(pt1) + " }, Field = " + self.fieldName
#       
#        roi = QRectF()
#        self.field.loadDataSlice( pt0, pt1, 4 )       
#               
#        data = self.field.data.astype('uint8')
#        AE = ArrayEditor( data, pt0, pt1, self )
#        rect = QApplication.desktop().availableGeometry()
#        AE.resize(int(rect.width() * 0.6), int(rect.height() * 0.9))
##        self.connect( AE, SIGNAL("SaveArray"), self.saveArray )
#        AE.show() 
        
#    def constructHeightFromPressure( self ):
#        dPVarName = nvSettings.data['dPVarName']
#        pField = self.fields.GetField( dPVarName )
#        if pField == None:
#            print "Can't find dP var: " + dPVarName
#            return
#        dPData = pField.getZCol()
#        print "DP data:"
#        pressure = 100.0  # PA
#        P0 = 100000 # PA
#        height = None
#        max_height = None
#        nLevels = len(dPData)
#        for i in range( nLevels ):
#            height = -7.0 * math.log( pressure / P0 )
#            if max_height == None:
#                max_height = height
#            print ' -- %d   P = %.1f PA,  dP = %.1f PA,  H= %.1f km'  % ( i, pressure, dPData[i], height )
#            pressure += dPData[i]
#        zscale = ( max_height - height ) / ( nLevels - 1 )
#        return zscale
    
#    def getVolumeSpacing( self, pt0, pt1 ):
#        zspacing = self.constructHeightFromPressure()
#        
#        dLatVarName = nvSettings.data['Lat Var Name']
#        pLatField = self.fields.GetField( dLatVarName )
#        if pLatField == None:
#            print "Can't find Lat var: " + dLatVarName
#            return
#        dLonVarName = nvSettings.data['Lon Var Name']
#        pLonField = self.fields.GetField( dLonVarName )
#        if pLonField == None:
#            print "Can't find Lon var: " + dLonVarName
#            return
#        
#        gridCenterPoint = ( int(( self.field.xstart + self.field.xend ) / 2), int(( self.field.ystart + self.field.yend ) / 2 ) )
#        
#        lon0 = pLonField.Get1DDataValue( gridCenterPoint[0] )
#        lon1 = pLonField.Get1DDataValue( gridCenterPoint[0] + 1 )
#        lat0 = pLatField.Get1DDataValue( gridCenterPoint[1] )
#        lat1 = pLatField.Get1DDataValue( gridCenterPoint[1] + 1 )
#       
#        ( zone0, e0, n0 ) = self.getUTM( QPointF(lon0,lat0) )
#        ( zone1, e1, n1 ) = self.getUTM( QPointF(lon1,lat0) )
#        ( zone2, e2, n2 ) = self.getUTM( QPointF(lon0,lat1) )
#        iz0 = int(zone0[:-1])
#        iz1 = int(zone1[:-1])
#        iz2 = int(zone2[:-1])
#        assert iz0 == iz1, 'Crossed UTM Zone boundary in VolumeSpacing calculation'
#        assert iz0 == iz2, 'Crossed UTM Zone boundary in VolumeSpacing calculation'
#        spacing = ( abs((e1-e0)/1000), abs((n2-n0)/1000), zspacing)
#        return spacing
           
#    def getUTM(self, pt): # return (UTMZone, UTMEasting, UTMNorthing)
#        lat = pt.y()
#        lon = pt.x() if pt.x() < 180 else pt.x() - 360.0
#        return LatLongUTMconversion.LLtoUTM( 23, lat, lon )
#        
#    def renderROI(self):
#        from VolumeRenderer import *
#        
#        pt0 = QPointF( float(self.ROICornerLon0.text()),  float(self.ROICornerLat0.text())) 
#        pt1 = QPointF( float(self.ROICornerLon1.text()),  float(self.ROICornerLat1.text())) 
#        zStretchFactor = 50      
#        print "ImageROI: { Pt0 = " + str(pt0) + ", Pt1 = " + str(pt1) + " }, Field = " + self.fieldName
#       
#        roi = QRectF()
#        self.field.loadDataSlice( pt0, pt1, 2 ) 
#        physicalSpacing = self.getVolumeSpacing( pt0, pt1 )
#        volSpacing = ( physicalSpacing[0], physicalSpacing[1], physicalSpacing[2]*zStretchFactor )
#        minDataValue = nvSettings.data['MinFieldDataValue']
#         
#        volRenderer = VolumeRenderer( self.field.data, 5.0e-9, volSpacing, VolumeRayCastFunctionType.Isosurface, self ) 
#        volRenderer.Display()     
#        
#    def saveArray( self, data ):
#        self.field.saveDataSlice( data )
#        self.ncfile.sync()
                 
class ArrayEditor(QDialog):
 
    def __init__(self, data, ROICorner0, ROICorner1, parent=None):
        super(ArrayEditor, self).__init__(parent)
        
        config = ConfigParser.SafeConfigParser( nvSettings.data )
        self.Dirty = False
 
        print "Editing array: data[ " + str(data.shape[0]) + " ][ " + str(data.shape[1]) + " ]  " 
        self.colorTable = GetRandomColormap(19999)
        self.data = data
        data1D = data.ravel()
        self.image = QImage( data1D, data.shape[1], data.shape[0], QImage.Format_Indexed8 ).mirrored(False,True)
        self.image.setColorTable( self.colorTable )
        self.ROICorner0 = ROICorner0
        self.ROICorner1 = ROICorner1
    
        pixmap = QPixmap(self.image) 
        self.graphicsImageItem = QGraphicsPixmapItem(pixmap)
        self.graphicsImageItem.setFlags( QGraphicsItem.ItemIsMovable )
        self.graphicsImageItem.setAcceptedMouseButtons ( Qt.LeftButton )
        self.graphicsImageItem.setPos( 0, 0 )
               
        self.view = GraphicsView( self.graphicsImageItem, None, ROICorner0, ROICorner1, self )
        self.scene = QGraphicsScene(self)
        self.filename = QString()
        self.view.setScene(self.scene)
        self.scene.addItem(self.graphicsImageItem)
        
        bMap = BoundaryMap( self.view, self.graphicsImageItem )
        bMap.ReadMap( ROICorner0, ROICorner1 )
        
        w = QWidget()
        panelLayout = QHBoxLayout()
        w.setLayout( panelLayout )
        
        SelectedPointLabel = QLabel("<b><u>Selected point:</u></b>")
        self.CurrentPointLon = QLineEdit()
        self.CurrentPointLat = QLineEdit()
        
        LatLabel = QLabel("Lat: ")
        LonLabel = QLabel("Lon: ")            
        grid0 = QGridLayout()
        grid0.addWidget( SelectedPointLabel, 0, 0, 1, 2 )
        grid0.addWidget( LonLabel, 1, 0 )
        grid0.addWidget( self.CurrentPointLon, 1, 1 )
        grid0.addWidget( LatLabel, 2, 0 )
        grid0.addWidget( self.CurrentPointLat, 2, 1 )
        w0 = QFrame()
        w0.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
        w0.setLayout( grid0 )
        panelLayout.addWidget( w0 )
 
        penWidth = 1       
        SelectedPointValueLabel = QLabel( "Selected Point Value: " )
        self.SelectedPointValueDisplay = QLabel("None")
        self.SelectedPointValueDisplay.setFrameStyle(QFrame.StyledPanel|QFrame.Sunken)
        NewValueLabel = QLabel("New Value: ") 
        self.NewValueEdit = QLineEdit()  
        self.SetNewValueButton = QPushButton("Set") 
        self.AutoSetCheckBox = QCheckBox("Set With Click")
        self.AutoSetCheckBox.setChecked(False)
        self.PenSizeLabel = QLabel("Pen Width: ") 
        self.PenSizeSpinBox = QSpinBox()
        self.PenSizeSpinBox.setRange (1,9)
        self.PenSizeSpinBox.setSingleStep (2)
        self.PenSizeSpinBox.setValue(penWidth)
        
        grid1 = QGridLayout()
        grid1.addWidget( SelectedPointValueLabel, 0, 0 )
        grid1.addWidget( self.SelectedPointValueDisplay, 0, 1, 1, 2 )
        grid1.addWidget( NewValueLabel, 1, 0 )
        grid1.addWidget( self.NewValueEdit, 1, 1 )
        grid1.addWidget( self.SetNewValueButton, 1, 2 )
        grid1.addWidget( self.PenSizeLabel, 2, 0 )
        grid1.addWidget( self.PenSizeSpinBox, 2, 1 )
        grid1.addWidget( self.AutoSetCheckBox, 2, 2 )

        self.connect(self.SetNewValueButton, SIGNAL("clicked()"), self.setNewValue)
        w1 = QFrame()
        w1.setFrameStyle( QFrame.StyledPanel|QFrame.Raised )
        w1.setLayout( grid1 )
        panelLayout.addWidget( w1 )       
        panelLayout.addStretch(1)

        self.connect(self.view, SIGNAL("PointSelected"), self.UpdatePointCoords )
        button = QPushButton("&Save")
        panelLayout.addWidget(button)
        self.connect(button, SIGNAL("clicked()"), self.save)
        button = QPushButton("&Quit")
        panelLayout.addWidget(button)
        self.connect(button, SIGNAL("clicked()"), self.accept )          

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(w)
        self.setLayout(layout)

        self.setWindowTitle("Array Editor")
                
    def UpdatePointCoords( self, scenePt, latLonPt ):
        if latLonPt.x() > self.ROICorner0.x() and latLonPt.x() < self.ROICorner1.x() and latLonPt.y() > self.ROICorner0.y() and latLonPt.y() < self.ROICorner1.y():
            self.CurrentPointLon.setText ( "%.2f" % latLonPt.x() )
            self.CurrentPointLat.setText ( "%.2f" % latLonPt.y() )
            self.scenePoint = QPoint( int(scenePt.x()), int(scenePt.y()) )
            self.datPoint = QPoint( int(self.data.shape[0] - scenePt.y()), int(scenePt.x()) )
            try:
                ival = self.data[ self.datPoint.x(), self.datPoint.y() ]
        #        print " ---- Scene Pt: ( " + str(self.scenePoint.x()) + " " + str(self.scenePoint.y()) + " ) -> data Pt: ( " + str(self.datPoint.x()) + " " + str(self.datPoint.y()) + " ) -> " + str(ival)
                self.SelectedPointValueDisplay.setText( str(ival) )
                if self.AutoSetCheckBox.isChecked():
                    self.setNewValue()
            except IndexError, e:
                print "ArrayEditor.UpdatePointCoords Error: %s" % e
        
    def setNewValue(self):
        ival = int( self.NewValueEdit.text() )
        penWidth = self.PenSizeSpinBox.value()
        if penWidth == 1:
            self.data[ self.datPoint.x(), self.datPoint.y() ] = ival
            self.image.setPixel ( self.scenePoint, ival )
        else:
            iPenExt = int(penWidth/2)
            rect = ( self.datPoint.x()-iPenExt,self.datPoint.x()+iPenExt+1, self.datPoint.y()-iPenExt,self.datPoint.y()+iPenExt+1)
            self.data[ rect[0]:rect[1], rect[2]:rect[3] ] = ival
            sRect = ( self.scenePoint.x()-iPenExt,self.scenePoint.x()+iPenExt+1, self.scenePoint.y()-iPenExt,self.scenePoint.y()+iPenExt+1)
            for i0 in range( sRect[0], sRect[1] ):
                for i1 in range( sRect[2], sRect[3] ):
                    self.image.setPixel ( i0, i1, ival )
            
        self.view.loadImage( self.image )
        self.Dirty = True
        
    def save(self):
        self.emit( SIGNAL("SaveArray"), self.data )
        self.Dirty = False
 
    def accept(self):
        self.offerSave()
        QDialog.accept(self)
        
    def offerSave(self):
        if self.Dirty and QMessageBox.question(self, "Array Editor - Unsaved Changes", "Save unsaved changes?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.save()

class GraphicsPolylineItem(QAbstractGraphicsShapeItem):
    
    def __init__(self, polygon, parent = None, scene = None ):
        super(GraphicsPolylineItem, self).__init__( parent, scene )
        self.polygon = polygon
        
    def paint( self, painter, options,  widget):
        painter.setPen( self.pen() )
        painter.setBrush( self.brush() );
        painter.drawPolyline( self.polygon )

    def boundingRect( self ):
        return self.polygon.boundingRect()
    
    def shape( self ):
        pp = QPainterPath()
        pp.addPolygon(self.polygon)
        return pp
     
class BoundaryMap:
 
    def __init__(self, view, parentGraphItem =None):
        self.view = view
        self.parentGraphItem = parentGraphItem
        config = ConfigParser.SafeConfigParser( nvSettings.data )
        self.boundaryMapFile = str( nvSettings.data['RootDir'] + '/' + nvSettings.data['WorldBoundaryMap'] )
        self.boundaryMapLayer = str( nvSettings.data['WorldBoundaryMapLayer'] )
        self.checkStride = nvSettings.data['checkStride']
        self.drawStride = nvSettings.data['drawStride']
 
    def ReadMap( self, roiPt0, roiPt1 ):
        start = time.time()
        if not os.path.exists(self.boundaryMapFile):
            print >>sys.stderr, "ERROR: Boundary Map NetCDF file doesn't exist -- %s" % self.boundaryMapFile
            return       
        nc = NetCDFFile( self.boundaryMapFile )   
        segvar = nc.variables[ '%s_seg' % self.boundaryMapLayer ]
        lonvar = nc.variables[ '%s_lon' % self.boundaryMapLayer ]
        latvar = nc.variables[ '%s_lat' % self.boundaryMapLayer ]                        
        ptIndexOffset = 0
        nseg = len(segvar)       
        pen = QPen(Qt.black) 
        pen.setWidth(1)
        useGraphicsPolylineItem = True
        print 'ReadMap- Extent: ( x0:%.1f' % roiPt0.x() +' x1:%.1f' % roiPt1.x() +' y0:%.1f' % roiPt0.y() +' y1:%.1f' % roiPt1.y() +' ), stride =  %d' % self.checkStride
        for i in range(nseg):
            npts = segvar[i]
            startIndex = -1
            for j in range( 0, npts, self.checkStride ):
                k = ptIndexOffset + j
                x = lonvar[k]
                y = latvar[k]
                if x > 180.0:
                    x -= 360.0
                if x > roiPt0.x() and x < roiPt1.x() and y > roiPt0.y() and y < roiPt1.y() :
#                    print 'R['+"%d" % i+':'+"%d" % npts+']-- Pt['+"%d" % k+']: ( ' + "%.1f" % x + ' ' + "%.1f" % y +' ) ' 
                    startIndex = j - self.checkStride if j > 0 else 0
                    break           
            if startIndex >= 0:
                if useGraphicsPolylineItem :
                    polygon = QPolygonF()
                    for j in range( startIndex, npts, self.drawStride ):
                        k = ptIndexOffset+j
                        x = lonvar[k]
                        y = latvar[k]
                        if x > 180.0:
                            x -= 360.0
                        if x > roiPt0.x() and x < roiPt1.x() and y > roiPt0.y() and y < roiPt1.y():
                            geoPt = QPointF(x,y)
                            sPt = self.view.GetScenePointFromGeoPoint( geoPt )
                            polygon.append( sPt )
                            
                    polyItem = GraphicsPolylineItem( polygon, self.parentGraphItem, self.view.scene() )
                    polyItem.setPen( pen )
                    polyItem.setZValue(1)
                                         
                else :
                    sPt0 = None
                    sPt1 = None
                    lines = []
                    for j in range( startIndex, npts, self.drawStride ):
                        k = ptIndexOffset+j
                        x = lonvar[k]
                        y = latvar[k]
                        if x > 180.0:
                            x -= 360.0
                        if x > roiPt0.x() and x < roiPt1.x() and y > roiPt0.y() and y < roiPt1.y():
                            geoPt = QPointF(x,y)
                            sPt0 = self.view.GetScenePointFromGeoPoint( geoPt )
                            if sPt1 <> None:
                                QGraphicsLineItem( sPt0.x(), sPt0.y(), sPt1.x(), sPt1.y(), self.parentGraphItem, self.view.scene() )
    #                            pgi.setPen( pen )
    #                            pgi.setZValue (1)
                            sPt1 = sPt0
            ptIndexOffset += npts              
        nc.close()             
        elapsed = time.time() - start
        print "Boundary Load time: %f " % elapsed

class MainForm(QDialog):
 
    def __init__(self, parent=None):
        super(MainForm, self).__init__(parent)
        self.lonRangeType = 1
        self.fullRoi = [ [ 0.0, -90.0, 360.0, 90.0 ], [ -180.0, -90.0, 180.0, 90.0 ] ]
        self.roi = self.fullRoi[ self.lonRangeType ]

        layout = QVBoxLayout()
        
        self.roiLabel = QLabel( "ROI: %s" % str( self.roi )  )
        layout.addWidget(self.roiLabel)
        
        roiButton_layout = QHBoxLayout()
        layout.addLayout(roiButton_layout )
                 
        self.selectRoiButton = QPushButton('Select ROI', self)
        roiButton_layout.addWidget( self.selectRoiButton )
        self.connect( self.selectRoiButton, SIGNAL('clicked(bool)'), self.selectRoi )

        self.resetRoiButton = QPushButton('Reset ROI', self)
        roiButton_layout.addWidget( self.resetRoiButton )
        self.connect( self.resetRoiButton, SIGNAL('clicked(bool)'), self.resetRoi )
        
        self.roiSelector = ROISelectionDialog( self.parent() )
        if self.roi: self.roiSelector.setROI( self.roi )
        self.connect(self.roiSelector, SIGNAL('doneConfigure()'), self.setRoi )
        
        self.setLayout(layout)
        self.setWindowTitle("ROI Selector")

    def selectRoi( self ): 
        if self.roi: self.roiSelector.setROI( self.roi )
        self.roiSelector.show()

    def resetRoi( self ): 
        roi0 = self.fullRoi[ self.lonRangeType ]
        self.roiSelector.setROI( roi0 )        
        self.roiLabel.setText( "ROI: %s" % str( roi0 )  ) 
        for i in range( len( self.roi ) ): self.roi[i] = roi0[i] 

    def setRoi(self):
        self.roi = self.roiSelector.getROI()
        self.roiLabel.setText( "ROI: %s" % str( self.roi )  ) 
        
#    def show(self):
#        self.roiSelector.initScaling()
#        QDialog.show( self )
         
        
if __name__ == '__main__':                                                
    app = QApplication(sys.argv)
    form = MainForm()

    rect = QApplication.desktop().availableGeometry()
    form.resize( 300, 150 )
    form.show()
    app.exec_()


