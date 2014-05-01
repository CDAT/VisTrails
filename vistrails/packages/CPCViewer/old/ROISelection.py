import functools
import random
import sys
import os
import math
import time
import numpy.oldnumeric as N
import numpy as np
from ControlPanel import ConfigControl
from PyQt4 import QtCore
from PyQt4 import QtGui

packagePath = os.path.dirname( __file__ )
defaultMapDir = os.path.join( packagePath, 'data' )
#defaultMapFile = [ os.path.join( defaultMapDir,  'WorldMap.jpg' ), os.path.join( defaultMapDir,  'WorldMap.jpg' ) ]
#WorldMapGridExtent = [ ( 106, 72, 2902, 1470 ), ( 106, 72, 2902, 1470 ) ]

class QtROISelectorMapFrame:
    
     def __init__( self, name, map_dir, map_file, grid_extent, latlon_bounds, map_scale ):
         self.name = name
         self.map_dir = map_dir
         self.map_file = map_file
         self.grid_extent = grid_extent
         self.latlon_bounds = latlon_bounds
         self.mapScale = map_scale
         self.view = None
         
     def getMapGridExtent(self):
        return self.grid_extent
         
     def getMapFilePath(self):
         return os.path.join( self.map_dir, self.map_file )
     
     def getPixmap(self):
         worldMapFile =  self.getMapFilePath()
         return QtGui.QPixmap(worldMapFile) 
     
     def getCornerPoint( self, index ):
         return QtCore.QPointF( self.latlon_bounds[ 2*index ], self.latlon_bounds[ 2*index + 1 ] )

     def createView( self, parent ):      
        self.scene = QtGui.QGraphicsScene(parent)
        self.item = QtGui.QGraphicsPixmapItem( self.getPixmap(), None, self.scene )
        self.item.setFlags( QtGui.QGraphicsItem.ItemIsMovable )
        self.item.setAcceptedMouseButtons ( QtCore.Qt.LeftButton )
        self.item.setPos( 0, 0 )         
        self.view = MapGraphicsView( self.item, self.grid_extent, self.getCornerPoint( 0 ), self.getCornerPoint( 1 ), parent )
        self.view.setScene( self.scene )
        self.view.scale( self.mapScale[0], self.mapScale[1] )
        self.roiRect = QtGui.QGraphicsRectItem( self.grid_extent[0], self.grid_extent[1], (self.grid_extent[2]-self.grid_extent[0]), (self.grid_extent[3]-self.grid_extent[1]), self.item, self.scene )
        self.roiRect.setBrush( QtGui.QBrush( QtCore.Qt.NoBrush ) )
        pen = QtGui.QPen( QtCore.Qt.green ) 
        pen.setWidth( 2 );
        self.roiRect.setPen( pen )
        self.roiRect.setZValue(1)
    
     def getView( self, parent ):
         if not self.view: self.createView( parent )
         return self.view

     def setRect( self, x0, y0, dx, dy ):
         self.roiRect.setRect ( x0, y0, dx, dy )
         self.view.update()
         
MapFrames = [  QtROISelectorMapFrame( 'Double Map', defaultMapDir, 'WorldMap2.jpg', ( 0, 0, 2048, 512 ), ( -180, -90 , 540.0, 90.0), (1.2,1.2) ),
               QtROISelectorMapFrame( 'Gridded Map', defaultMapDir, 'WorldMap.jpg', ( 106, 72, 2902, 1470 ), ( -180, -90 , 180.0, 90.0), (0.4,0.4) ) ]
 
class MapGraphicsView(QtGui.QGraphicsView):

    def __init__(self, imageGraphicsItem, imageContentExtents, pt0, pt1, parent=None):
        super(MapGraphicsView, self).__init__(parent)
        self.Extent = ( pt0.x(), pt0.y(), pt1.x(), pt1.y() ) 
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)

        self.imageOriginOffset = QtCore.QPointF(  imageContentExtents[0], imageContentExtents[1] ) if imageContentExtents <> None else QtCore.QPointF( 0, 0 )
        imageExtentOffset = QtCore.QPointF(  imageContentExtents[2], imageContentExtents[3] ) if imageContentExtents <> None else QtCore.QPointF( imageGraphicsItem.pixmap().width(), imageGraphicsItem.pixmap().height() )
        imagePixelDims = imageExtentOffset - self.imageOriginOffset
        self.imageLatLonScale = ( (self.Extent[2] - self.Extent[0]) / imagePixelDims.x(), (self.Extent[3] - self.Extent[1]) / imagePixelDims.y() )
        self.roiCorner0 = None
        self.roiCorner1 = None
        self.imageGraphicsItem = imageGraphicsItem

#        self.setRenderHint(QtGui.QPainter.Antialiasing)
#        self.setRenderHint(QtGui.QPainter.TextAntialiasing)

    def wheelEvent(self, event):
        factor = 1.41 ** (-event.delta() / 240.0)
        self.scale(factor, factor)
        
    def loadImage( self, image ):
        p = QtGui.QPixmap.fromImage(image)
        self.imageGraphicsItem.setPixmap(p)
        self.update()
        
    def GetPointCoords(self):
        imagePtScaled = None
        ptS = None
        cursor_pos = QtGui.QCursor.pos()
        point = self.mapFromGlobal( cursor_pos )
        pos0 = self.imageGraphicsItem.pos()
        pos1 = self.mapToScene(point)
#        if self.geometry().contains(point):
        ptS = pos1 - pos0 
        mapPt = ptS - self.imageOriginOffset
        imagePtScaled = QtCore.QPointF( (mapPt.x() * self.imageLatLonScale[0]) + self.Extent[0], self.Extent[3] - (mapPt.y() * self.imageLatLonScale[1] ) ) 
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
        return QtCore.QPointF(  ( geoPt.x() - self.Extent[0] ) / self.imageLatLonScale[0] + self.imageOriginOffset.x(), 
                         ( self.Extent[3] - geoPt.y() ) / self.imageLatLonScale[1] + self.imageOriginOffset.y() )

    def mousePressEvent(self, event):
        self.roiCorner0, self.scenePt0  = self.GetPointCoords()
        QtGui.QGraphicsView.mousePressEvent(self, event)
        
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
        if event.button() == QtCore.Qt.RightButton:
            ( self.roiCorner1, self.scenePt1 ) = self.GetPointCoords()
            if self.roiCorner0 != None and self.roiCorner1 != None:
                self.emit( QtCore.SIGNAL("PointSelected"), self.roiCorner1 )
                self.orderCoords( self.roiCorner0, self.roiCorner1 )
                self.emit( QtCore.SIGNAL("ROISelected"), self.roiCorner0, self.roiCorner1, self.scenePt0, self.scenePt1 )
        QtGui.QGraphicsView.mouseReleaseEvent(self, event)

class ROIControl( ConfigControl ):
    
    def __init__(self, cparm, **args ):
        super(ROIControl, self).__init__( cparm, **args )
        self.init_frame_index = args.get("mapFrameIndex",0)

    def addCustomLayout(self):
        self.PointLon = QtGui.QLineEdit( ) 
        self.PointLat = QtGui.QLineEdit( )
        self.PointLon.setValidator( QtGui.QDoubleValidator(self) )
        self.PointLat.setValidator( QtGui.QDoubleValidator(self) )
        
        self.ROICornerLon0 = QtGui.QLineEdit( ) 
        self.ROICornerLat0 = QtGui.QLineEdit( )
        self.ROICornerLon1 = QtGui.QLineEdit( )
        self.ROICornerLat1 = QtGui.QLineEdit( )
        self.ROICornerLon0.setValidator( QtGui.QDoubleValidator(self) )
        self.ROICornerLat0.setValidator( QtGui.QDoubleValidator(self) )
        self.ROICornerLon1.setValidator( QtGui.QDoubleValidator(self) )
        self.ROICornerLat1.setValidator( QtGui.QDoubleValidator(self) )
        
        for mapFrame in MapFrames: 
            view = mapFrame.getView( self )            
            self.connect( view, QtCore.SIGNAL("ROISelected"), self.UpdateGeoCoords )
            self.connect( view, QtCore.SIGNAL("PointSelected"), self.UpdateGeoCoord )
            tab_index, tab_layout = self.addTab( mapFrame.name )
            tab_layout.addWidget( view ) 
            
        w = QtGui.QWidget()
        panelLayout = QtGui.QHBoxLayout()
        w.setLayout( panelLayout )
                
        self.connect( self.ROICornerLon0, QtCore.SIGNAL("editingFinished()"), self.adjustROIRect )
        self.connect( self.ROICornerLat0, QtCore.SIGNAL("editingFinished()"), self.adjustROIRect )
        self.connect( self.ROICornerLon1, QtCore.SIGNAL("editingFinished()"), self.adjustROIRect )
        self.connect( self.ROICornerLat1, QtCore.SIGNAL("editingFinished()"), self.adjustROIRect )

        LatLabelp = QtGui.QLabel( "Lat: ")
        LonLabelp = QtGui.QLabel( "Lon: ")            
        gridp = QtGui.QHBoxLayout()
        gridp.addWidget( LonLabelp )
        gridp.addWidget( self.PointLon )
        gridp.addWidget( LatLabelp )
        gridp.addWidget( self.PointLat )

        wp = QtGui.QGroupBox("Point Coords:")  
        wp.setLayout( gridp )
        panelLayout.addWidget( wp )
      
        LatLabel0 = QtGui.QLabel( "Lat: ")
        LonLabel0 = QtGui.QLabel( "Lon: ")            
        grid0 = QtGui.QHBoxLayout()
        grid0.addWidget( LonLabel0 )
        grid0.addWidget( self.ROICornerLon0 )
        grid0.addWidget( LatLabel0 )
        grid0.addWidget( self.ROICornerLat0 )

        LatLabel1 = QtGui.QLabel("Lat: ")
        LonLabel1 = QtGui.QLabel("Lon: ")            
        grid1 = QtGui.QHBoxLayout()
        grid1.addWidget( LonLabel1 )
        grid1.addWidget( self.ROICornerLon1 )
        grid1.addWidget( LatLabel1 )
        grid1.addWidget( self.ROICornerLat1 )

        w0 = QtGui.QGroupBox("ROI Corner0:")  
        w0.setLayout( grid0 )
        panelLayout.addWidget( w0 )

        LatLabel1 = QtGui.QLabel("Lat: ")
        LonLabel1 = QtGui.QLabel("Lon: ")            
        grid1 = QtGui.QHBoxLayout()
        grid1.addWidget( LonLabel1 )
        grid1.addWidget( self.ROICornerLon1 )
        grid1.addWidget( LatLabel1 )
        grid1.addWidget( self.ROICornerLat1 )
        
        w1 = QtGui.QGroupBox("ROI Corner1:")  
        w1.setLayout( grid1 )
        panelLayout.addWidget( w1 )
                 
        panelLayout.addStretch(1)        
        self.layout().addWidget(w)
        self.initROIBounds( self.init_frame_index )
        self.setCurrentMapFrame( self.init_frame_index )

    def addButtons(self):
        self.addButton( 'Submit Selection', self.submitSelection )
        self.addButton( 'Reset', self.reset )
        
    def reset(self):
        pass
        
    def submitSelection(self):
        return # Currently disabled.  
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( self.getName(), "Submit", self.getROI() ) )

    def updateTabPanel(self, current_tab_index=-1 ):
        super(ROIControl, self).updateTabPanel( current_tab_index )
        self.adjustROIRect( current_tab_index )
        
    def setCurrentMapFrame(self, index ):
        self.tabWidget.setCurrentIndex ( index )
        self.adjustROIRect()
        
    def initROIBounds( self, index ):
        mapFrame = MapFrames[ index ]
        ROIcorner0 = mapFrame.getCornerPoint( 0 )    
        ROIcorner1 = mapFrame.getCornerPoint( 1 )           
        self.ROICornerLon0.setText ( "%.1f" % ROIcorner0.x() )
        self.ROICornerLat0.setText ( "%.1f" % ROIcorner0.y() )
        self.ROICornerLon1.setText ( "%.1f" % ROIcorner1.x() )
        self.ROICornerLat1.setText ( "%.1f" % ROIcorner1.y() )
                
    def getView(self):
        return self.tabbedWidget.currentWidget()
        
    def setROI( self, roi ):
        view = self.getView()
        geoPt0 = QtCore.QPointF( roi[0], roi[1] )
        geoPt1 = QtCore.QPointF( roi[2], roi[3] )
        scenePt0 = view.GetScenePointFromGeoPoint( geoPt0 )
        scenePt1 = view.GetScenePointFromGeoPoint( geoPt1 )
        self.UpdateROICoords( roi, scenePt0, scenePt1 )

    def UpdateGeoCoord(self, geoPt ):
        self.PointLon.setText ( "%.1f" % geoPt.x() )
        self.PointLat.setText ( "%.1f" % geoPt.y() )
        self.emit(QtCore.SIGNAL('pointSelected()'))
                
    def UpdateGeoCoords(self, geoPt0, geoPt1, scenePt0, scenePt1 ):
        self.ROICornerLon0.setText ( "%.1f" % geoPt0.x() )
        self.ROICornerLat0.setText ( "%.1f" % geoPt0.y() )
        self.ROICornerLon1.setText ( "%.1f" % geoPt1.x() )
        self.ROICornerLat1.setText ( "%.1f" % geoPt1.y() )
        self.UpdateROIRect( scenePt0, scenePt1 )

    def UpdateROICoords(self, roi, scenePt0, scenePt1 ):
        self.ROICornerLon0.setText ( "%.1f" % roi[0] )
        self.ROICornerLat0.setText ( "%.1f" % roi[1] )
        self.ROICornerLon1.setText ( "%.1f" % roi[2] )
        self.ROICornerLat1.setText ( "%.1f" % roi[3] )
        self.UpdateROIRect( scenePt0, scenePt1 )
        
    def getCurrentMapFrame(self):    
        index = self.getCurrentTabIndex()
        return MapFrames[ index ]
        
    def UpdateROIRect(self, scenePt0, scenePt1 ):
        currentFrame = self.getCurrentMapFrame()
        currentFrame.setRect ( scenePt0.x(), scenePt0.y(), scenePt1.x()-scenePt0.x(), scenePt1.y()-scenePt0.y() )
        self.emit( QtCore.SIGNAL('roiSelected'), self.getROI() )

    def UpdateScenePoint(self, scenePt ):
        pass
        
    def okTriggered(self):
        self.emit(QtCore.SIGNAL('doneConfigure()'))
        self.close()

    def getROI(self):
        return [ float(self.ROICornerLon0.text()), float(self.ROICornerLat0.text()), float(self.ROICornerLon1.text()), float(self.ROICornerLat1.text())   ]      

    def getPoint(self):
        return [ float(self.PointLon.text()), float(self.PointLat.text())  ]      
     
    def adjustROIRect( self, index = 0 ): 
        try:
            geoPt0 = QtCore.QPointF( float(self.ROICornerLon0.text()), float(self.ROICornerLat0.text()) ) 
            geoPt1 = QtCore.QPointF( float(self.ROICornerLon1.text()), float(self.ROICornerLat1.text()) )   
            if( geoPt1.x() < geoPt0.x() ):
                geoPt1.setX( geoPt0.x() )
            if( geoPt1.y() < geoPt0.y() ):
                geoPt1.setY( geoPt0.y() )  
            view = self.getView()         
            scenePt0 = view.GetScenePointFromGeoPoint( geoPt0 )
            scenePt1 = view.GetScenePointFromGeoPoint( geoPt1 )
            self.UpdateROIRect( scenePt0, scenePt1 )
        except: pass

# class ExampleForm(QtGui.QDialog):
#  
#     def __init__(self, parent=None):
#         super(ExampleForm, self).__init__(parent)
#         self.lonRangeType = 1
#         self.fullRoi = [ [ 0.0, -90.0, 360.0, 90.0 ], [ -180.0, -90.0, 180.0, 90.0 ] ]
#         self.roi = self.fullRoi[ self.lonRangeType ]
# 
#         layout = QtGui.QVBoxLayout()
#         
#         self.roiLabel = QtGui.QLabel( "ROI: %s" % str( self.roi )  )
#         layout.addWidget(self.roiLabel)
#         
#         roiButton_layout = QtGui.QHBoxLayout()
#         layout.addLayout(roiButton_layout )
#                  
#         self.selectRoiButton = QtGui.QPushButton('Select ROI', self)
#         roiButton_layout.addWidget( self.selectRoiButton )
#         self.connect( self.selectRoiButton, QtCore.SIGNAL('clicked(bool)'), self.selectRoi )
# 
#         self.resetRoiButton = QtGui.QPushButton('Reset ROI', self)
#         roiButton_layout.addWidget( self.resetRoiButton )
#         self.connect( self.resetRoiButton, QtCore.SIGNAL('clicked(bool)'), self.resetRoi )
#         
#         self.roiSelector = ROISelectionDialog( self.parent() )
#         if self.roi: self.roiSelector.setROI( self.roi )
#         self.connect(self.roiSelector.widget, QtCore.SIGNAL('doneConfigure()'), self.setRoi )
#         
#         self.setLayout(layout)
#         self.setWindowTitle("ROI Selector")
# 
#     def selectRoi( self ): 
#         if self.roi: self.roiSelector.setROI( self.roi )
#         self.roiSelector.show()
# 
#     def resetRoi( self ): 
#         roi0 = self.fullRoi[ self.lonRangeType ]
#         self.roiSelector.setROI( roi0 )        
#         self.roiLabel.setText( "ROI: %s" % str( roi0 )  ) 
#         for i in range( len( self.roi ) ): self.roi[i] = roi0[i] 
# 
#     def setRoi(self):
#         self.roi = self.roiSelector.getROI()
#         self.roiLabel.setText( "ROI: %s" % str( self.roi )  )  
#         
# if __name__ == '__main__':                                                
#     app = QtGui.QApplication(sys.argv)
#     form = ExampleForm()
# 
#     rect = QtGui.QApplication.desktop().availableGeometry()
#     form.resize( 300, 150 )
#     form.show()
#     app.exec_()
# 
# 

