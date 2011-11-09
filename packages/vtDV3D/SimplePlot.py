'''
Created on Nov 4, 2011

@author: tpmaxwel
Based on PyQt example code by Riverbank Computing.
'''

#!/usr/bin/env python

import math, time, sys, random
from vtUtilities import *
from sets import Set
from PyQt4 import QtCore, QtGui

class Edge(QtGui.QGraphicsItem):
    Pi = math.pi
    TwoPi = 2.0 * Pi

    Type = QtGui.QGraphicsItem.UserType + 2

    def __init__(self, sourceNode, destNode):
        super(Edge, self).__init__()

        self.sourcePoint = QtCore.QPointF()
        self.destPoint = QtCore.QPointF()

        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source = sourceNode
        self.dest = destNode
        self.source.addEdge(self)
        self.dest.addEdge(self)
        self.adjust()

    def type(self):
        return Edge.Type

    def sourceNode(self):
        return self.source

    def setSourceNode(self, node):
        self.source = node
        self.adjust()

    def destNode(self):
        return self.dest

    def setDestNode(self, node):
        self.dest = node
        self.adjust()

    def adjust(self):
        if not self.source or not self.dest:
            return

        line = QtCore.QLineF(self.mapFromItem(self.source, 0, 0), self.mapFromItem(self.dest, 0, 0))
        length = line.length()

        self.prepareGeometryChange()

        if length > 20.0:
            edgeOffset = QtCore.QPointF((line.dx() * 10) / length, (line.dy() * 10) / length)

            self.sourcePoint = line.p1() + edgeOffset if self.source.isMovable() else line.p1()
            self.destPoint = line.p2() - edgeOffset if self.dest.isMovable() else line.p2()
        else:
            self.sourcePoint = line.p1()
            self.destPoint = line.p1()

    def boundingRect(self):
        if not self.source or not self.dest:
            return QtCore.QRectF()

        penWidth = 1.0
        extra = (penWidth) / 2.0

        return QtCore.QRectF(self.sourcePoint, QtCore.QSizeF(self.destPoint.x() - self.sourcePoint.x(),
                        self.destPoint.y() - self.sourcePoint.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def paint(self, painter, option, widget):
        if not self.source or not self.dest:
            return

        # Draw the line itself.
        line = QtCore.QLineF(self.sourcePoint, self.destPoint)

        if line.length() == 0.0:
            return

        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(line)

class Node(QtGui.QGraphicsItem):
    Type = QtGui.QGraphicsItem.UserType + 1

    def __init__(self, graphWidget, **args ):
        super(Node, self).__init__()

        self.graph = graphWidget
        self.edgeList = []
        self.newPos = QtCore.QPointF()
        self.posConstraintVector = None 
        self.coupledNodes = Set()

        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QtGui.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)
        
    def addCoupledNode( self, node ):
        self.coupledNodes.add( node )
        node.coupledNodes.add( self )
        
    def setPosScaled( self, s ):
        assert ( self.posConstraintVector <> None ), "Error, Position Constraint Vector not defined"
        pos = self.posConstraintVector.getPoint( s )
        self.setPos( pos )
        
    def mouseMoveEvent ( self,  mouseEvent ):
        if self.posConstraintVector == None:
            super(Node, self).mouseMoveEvent( mouseEvent )
        else:
            pos = self.mapToScene( mouseEvent.pos() )
            proj_pos, s = self.posConstraintVector.getProjectedPoint( pos )
            self.setPos( proj_pos )
            for node in self.coupledNodes: node.setPosScaled( s )

    def type(self):
        return Node.Type

    def setVector( self, vector ):
        self.posConstraintVector = vector
        self.setMovable( True )
    
    def setMovable( self, isMovable ):
        self.setFlag( QtGui.QGraphicsItem.ItemIsMovable, isMovable )
        for edge in self.edgeList: edge.adjust()
        
    def isMovable(self):
        return ( self.flags() & QtGui.QGraphicsItem.ItemIsMovable )

    def addEdge(self, edge):
        self.edgeList.append(edge)

    def edges(self):
        return self.edgeList

    def advance(self):
        if self.newPos == self.pos():
            return False

        self.setPos(self.newPos)
        return True

    def boundingRect(self):
        adjust = 2.0
        return QtCore.QRectF(-10 - adjust, -10 - adjust, 23 + adjust, 23 + adjust)

    def shape(self):
        path = QtGui.QPainterPath()
        path.addEllipse(-10, -10, 20, 20)
        return path

    def paint(self, painter, option, widget):
        if self.isMovable():
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtCore.Qt.darkGray)
            painter.drawEllipse(-7, -7, 20, 20)
    
            gradient = QtGui.QRadialGradient(-3, -3, 10)
            if option.state & QtGui.QStyle.State_Sunken:
                gradient.setCenter(3, 3)
                gradient.setFocalPoint(3, 3)
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.yellow).light(120))
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.darkYellow).light(120))
            else:
                gradient.setColorAt(0, QtCore.Qt.yellow)
                gradient.setColorAt(1, QtCore.Qt.darkYellow)
    
            painter.setBrush(QtGui.QBrush(gradient))
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
            painter.drawEllipse(-10, -10, 20, 20)

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edgeList: edge.adjust()
            self.graph.itemMoved()

        return super(Node, self).itemChange(change, value)

    def mousePressEvent(self, event):
        self.update()
        super(Node, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.update()
        super(Node, self).mouseReleaseEvent(event)

class MovementConstraintVector( QtCore.QLineF ):
    
    def __init__(self, pt0, pt1 ):
        super(MovementConstraintVector, self).__init__( pt0, pt1 )
        self.length = self.length()
        self.unitVector = self.unitVector()

        
    def getPoint( self, s ):
        if s > 1.0:   return self.p2()
        if s < 0.0:   return self.p1()
        S = s*self.length
        dp = QtCore.QPointF( S * self.unitVector.dx(), S * self.unitVector.dy()  )
        new_pt = self.p1() + dp
        return new_pt
    
    def getProjectedPoint( self, pt0 ):
        rel_pt0 = pt0 - self.p1()
        S = ( rel_pt0.x() * self.unitVector.dx() + rel_pt0.y() * self.unitVector.dy() ) 
        s = S/self.length
        new_pt = self.getPoint( s )
        return new_pt, s
        
class GraphWidget(QtGui.QGraphicsView):
    
    xAxis = 0
    yAxis = 1
    
    def __init__(self, **args ):
        super(GraphWidget, self).__init__()
        self.nodes = []
        self.edges = []
        self.size = args.get( 'size', (400, 400) )
        self.nticks = args.get( 'nticks', ( 5, 5 ) )
        self.tickLen = 12
        self.tickLabels = ( [], [] )
        self.bounds = None
        self.labelTextAlignment = [ QtCore.Qt.AlignHCenter, QtCore.Qt.AlignRight ]
        self.buildTickLabelRects()

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        scene.setSceneRect( 0, 0, self.size[0], self.size[1] )
        self.setScene(scene)
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setViewportUpdateMode(QtGui.QGraphicsView.BoundingRectViewportUpdate)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)

        self.scale(0.8, 0.8)
        self.setMinimumSize( self.size[0]+100, self.size[1] )
        self.setWindowTitle("Simple Graph")
        
    def buildGraph( self, nNodes ):
        self.clear()
        node1 = None
        dx = self.size[0]/( nNodes - 1 )
        for iN in range(nNodes):
            node2 = Node(self)
            self.nodes.append( node2 )
            x = iN * dx
            node2.setPos( x, self.size[1] )
            self.scene().addItem(node2)
            if node1 <> None: 
                edge = Edge(node1, node2)
                self.scene().addItem( edge )
                self.edges.append( edge )
            node1 = node2

    def drawTickMark( self, painter, scene_value, axis ):
        if axis == self.xAxis:
            p0 = QtCore.QPointF( scene_value, self.size[1] )
            dp = QtCore.QPointF( 0.0, self.tickLen/2 )
        else:
            p0 = QtCore.QPointF( 0.0, self.size[1] - scene_value )
            dp = QtCore.QPointF( self.tickLen/2, 0.0 )        
        line = QtCore.QLineF( p0 + dp, p0 - dp )
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(line)
            
    def clear(self):
        for node in self.nodes: 
            node = self.scene().removeItem ( node )
            del node
        for node in self.edges:
            edge = self.scene().removeItem ( node )
            del edge
        self.nodes = []
        self.edges = []

    def clearAxis( self, painter, iAxis ):
         for iTick in range( self.nticks[iAxis] ): 
            rect = self.tickLabels[iAxis][iTick]
            painter.fillRect ( rect, QtGui.QColor( 255, 255, 255 ) )
        
    def updateAxis( self, painter, iAxis ):
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen( QtCore.Qt.black )
        dR = ( self.bounds[iAxis][1] - self.bounds[iAxis][0] ) / ( self.nticks[iAxis] - 1 )
        for iTick in range( self.nticks[iAxis] ): 
            rect = self.tickLabels[iAxis][iTick]
            coord_value = self.bounds[iAxis][0] + dR * iTick
            painter.drawText( rect, self.labelTextAlignment[iAxis], flt2str( coord_value ) )
                     
    def createGraph( self, xbounds, ybounds, data ):
        self.data = []
        last_point = None
        for point in data:
            if point[0] > xbounds[0]:
                if last_point <> None:
                    s = ( xbounds[0] - last_point[0] ) / ( point[0] - last_point[0] )
                    yval = last_point[1] + ( point[1] - last_point[1] ) * s
                    self.data.append( (xbounds[0],yval,False) )
                    last_point = None
                self.data.append( point )
            else: last_point = point
        self.bounds = ( xbounds, ybounds )
        if len( self.nodes ) <> len( self.data ):
            self.buildGraph( len( self.data ) )
        for iP in range( len( self.data ) ):
            ptdata = self.data[iP]
            if len( ptdata ) == 3:
                x, y = self.getScenePoint( ptdata, xbounds, ybounds )
                self.nodes[iP].setPos ( x, y )
                self.nodes[iP].setMovable( ptdata[2] )
            else:
                x0, y0 = self.getScenePoint( ptdata[0:2], xbounds, ybounds )
                x1, y1 = self.getScenePoint( ptdata[2:4], xbounds, ybounds )
                vector = MovementConstraintVector( QtCore.QPointF( x0, y0 ), QtCore.QPointF( x1, y1 ) )
                pt0 = vector.getPoint( ptdata[4] )
                self.nodes[iP].setPos ( pt0 )
                self.nodes[iP].setVector ( vector )
                if len( ptdata ) > 5: self.nodes[iP].addCoupledNode( self.nodes[ ptdata[5] ] )
        self.update()
            
    def getScenePoint(self, point, xbounds, ybounds ):
        dx = ( point[0] - xbounds[0] ) / ( xbounds[1] - xbounds[0] )
        dy = ( point[1] - ybounds[0] ) / ( ybounds[1] - ybounds[0] )
        x = self.size[0] * dx
        y = self.size[1] * ( 1.0 - dy )
        return x, y

    def getScenePos( self, point, bounds, isHorizontal ):
        dp = ( point[0] - bounds[0] ) / ( bounds[1] - xbounds[0] )
        if isHorizontal: return self.size[0] * dp  
        else: return self.size[1] * ( 1.0 - dp )
        
    def itemMoved(self):
        pass

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Up:
            pass
        elif key == QtCore.Qt.Key_Down:
            pass
        elif key == QtCore.Qt.Key_Left:
            pass
        elif key == QtCore.Qt.Key_Right:
            pass
        elif key == QtCore.Qt.Key_Plus:
            self.scaleView(1.2)
        elif key == QtCore.Qt.Key_Minus:
            self.scaleView(1 / 1.2)
        elif key == QtCore.Qt.Key_Space or key == QtCore.Qt.Key_Enter:
            xbounds = [ random.random()*0.4, 0.6 + random.random()*0.4 ]
            ybounds = [ 0.0, 1.0 ]
            npts = 7
            dx = ( xbounds[1]-xbounds[0] ) / ( npts - 1 )
            data = [ ( xbounds[0]+dx*i, random.random(), (random.random() > 0.5) ) for i in range(npts) ]
            widget.createGraph( xbounds, ybounds, data )
        else:
            super(GraphWidget, self).keyPressEvent(event)

    def wheelEvent(self, event):
        self.scaleView(math.pow(2.0, -event.delta() / 240.0))
        
    def drawForeground ( self, painter, rect):
        super(GraphWidget, self).drawForeground( painter, rect )
        if self.bounds:
            self.updateAxis( painter, self.xAxis ) 
            self.updateAxis( painter, self.yAxis ) 

    def drawBackground(self, painter, rect):
        # Shadow.
        sceneRect = self.sceneRect()
        rightShadow = QtCore.QRectF(sceneRect.right(), sceneRect.top() + 5, 5, sceneRect.height())
        bottomShadow = QtCore.QRectF(sceneRect.left() + 5, sceneRect.bottom(), sceneRect.width(), 5)
        if rightShadow.intersects(rect) or rightShadow.contains(rect):
            painter.fillRect(rightShadow, QtCore.Qt.darkGray)
        if bottomShadow.intersects(rect) or bottomShadow.contains(rect):
            painter.fillRect(bottomShadow, QtCore.Qt.darkGray)

        # Fill.
        gradient = QtGui.QLinearGradient(sceneRect.topLeft(), sceneRect.bottomRight())
        gradient.setColorAt(0, QtCore.Qt.white)
        gradient.setColorAt(1, QtCore.Qt.lightGray)
        painter.fillRect(rect.intersect(sceneRect), QtGui.QBrush(gradient))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(sceneRect)

        # Text.
        textRect = QtCore.QRectF(sceneRect.left() + 4, sceneRect.top() - 20, sceneRect.width() - 4, sceneRect.height() - 4)
        message =  "Drag the nodes, or drag in the Spreadsheet cell."

        font = painter.font()
        font.setBold(True)
        font.setPointSize(14)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.lightGray)
        painter.drawText( textRect.translated(2, 2), message )
        painter.setPen( QtCore.Qt.black )
        painter.drawText( textRect, message )
         
        axis = [ self.xAxis, self.yAxis ]                   
        for iAxis in range(2):
            for iTick in range( self.nticks[iAxis] ): 
                dt = self.size[iAxis]/float( self.nticks[iAxis] - 1 ) 
                self.drawTickMark( painter, iTick*dt, axis[iAxis] )

    def buildTickLabelRects(self):
        self.tickLabels = ( [], [] )
        text_height = 14
        text_width = 85                   
        for iAxis in range(2):
            for iTick in range( self.nticks[iAxis] ): 
                dt = self.size[iAxis]/float( self.nticks[iAxis] - 1 ) 
                if iAxis == self.xAxis:
                    rect = QtCore.QRectF( iTick*dt-text_width/2, self.size[1]+self.tickLen, text_width, text_height )
                else:
                    rect = QtCore.QRectF( -(text_width+self.tickLen), self.size[1]-(iTick*dt+text_height/2), text_width, text_height )
                self.tickLabels[iAxis].append( rect )
                
    def scaleView(self, scaleFactor):
        factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
        if factor < 0.07 or factor > 100:
            return
        self.scale(scaleFactor, scaleFactor)


if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    widget = GraphWidget( size=(400,300), nticks=(4,4) )
    xbounds = [ 0.0, 1.0 ]
    ybounds = [ 0.0, 1.0 ]
    data = [ (0.0,0.0,False), (0.4,0.0,0.0,1.0,0.0), (0.6,0.0,0.4,1.0,0.5), (0.6,1.0,False), (0.6,0.0,0.8,1.0,0.5,2), (0.8,0.1,False), (1.0,0.0,False), ]
    widget.createGraph( xbounds, ybounds, data )
    widget.show()

    sys.exit(app.exec_())

