'''
Created on Feb 26, 2014

@author: tpmaxwell
'''

import math, time, sys, random
from sets import Set
from PyQt4 import QtCore, QtGui

#!/usr/bin/env python
'''
Created on Nov 4, 2011

@author: tpmaxwel
Based on PyQt example code by Riverbank Computing.
'''

LegacyAbsValueTransferFunction = 0
LinearTransferFunction = 1 
PosValueTransferFunction = 2  
NegValueTransferFunction = 3  
AbsValueTransferFunction = 4

PositiveValues = 0
NegativeValues = 1
AllValues = 2

def bound( val, bounds ): return max( min( val, bounds[1] ), bounds[0] )

def str2f( data ): return "[ %s ]" % ( ", ".join( [ '%.2f' % value for value in data ] ) )

def flt2str( fval ): 
    aval = abs( fval )
    if ( fval == 0.0 ): return "0.0"
    if ( aval >= 1000000 ) or ( aval < 0.001 ): return ( "%.2e" % fval )
    if ( aval >= 1000 ): return ( "%.0f" % fval )
    if ( aval >= 100 ): return ( "%.1f" % fval )
    if ( aval >= 1 ): return ( "%.2f" % fval )
    if ( aval < 0.01 ): return ( "%.4f" % fval )
    return ( "%.3f" % fval )

def pt2str( pt ): return "( %.2f, %.2f )" % ( pt.x(), pt.y() ) 

class TransferFunction( QtCore.QObject ):
    
    def __init__(self, tf_type, **args ):
        QtCore.QObject.__init__( self )
        self.type = tf_type
        self.data = args.get( 'data', None )
        self.points = []
                
    def setType(self, tf_type ):
        self.type = tf_type

    def getTransferFunctionPoints( self, data ):
        self.data = [ list(data_pt) for data_pt in data ]
        self.points = []
        for data_pt in data:
            args = data_pt[2] if len( data_pt ) > 2 else {}
            n = NodeData( dx0=data_pt[0], y0=data_pt[1],  **args )
            self.points.append( n )
        return self.points
    
    def setDataPoint( self, index, x, y ):
        data_pt = self.data[ index ]
        data_pt[0] = x
        data_pt[1] = y
        
    def getScaledData( self, xbounds ):
        dx = xbounds[1] - xbounds[0]
        sdata = [ ( ( d[0]-xbounds[0] ) / dx, d[1] ) for d in self.data ] 
        return sdata

    def addTransferFunctionPoint( self, new_data_pt, **args ):
        new_points = []
        new_data = []
        new_node = None
        bounds=[ self.data[0][0], 0.0, self.data[-1][0], 1.0 ]
        for node, data_pt in zip( self.points, self.data ): 
            if (new_node == None) and ( new_data_pt[0] < data_pt[0] ):
                new_node = NodeData( dx0=new_data_pt[0], y0=new_data_pt[1], bounds=bounds,  **args )
                new_points.append( new_node )
                new_data.append( list(new_data_pt) )
            new_points.append( node )
            new_data.append( list(data_pt) )
        self.points = new_points
        self.data = new_data
        return new_points
                    
def getScaledPoint( p ):   
    if len(p) > 4: return ( p[0] + p[4] * ( p[2] - p[0] ), p[1] + p[4] * ( p[3] - p[1] ) )
    return p

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

class NodeData( QtCore.QObject ):
    RED = 0
    BLUE = 1
    YELLOW = 2
    CYAN = 3
    MAGENTA = 4
    GRAY = 5
    
    def __init__(self, **args ):
        QtCore.QObject.__init__( self )
        self.ix0 = args.get( "ix0", None )
        self.y0 = args.get( "y0", None )
        self.ix1 = args.get( "ix1", None )
        self.y1 = args.get( "y1", None )
        self.s = args.get( "s", 0.5 )
        self.color = args.get( "color", NodeData.YELLOW )
        self.free = args.get( "free", False )
        self.index =  args.get( "index", -1 )
        self.dx0 = args.get( "dx0", None )
        self.dx1 = args.get( "dx1", None )
        self.spt0 = None
        self.spt1 = None
        self.vector = None

    def setDataPoint(self, x, y ):
        self.dx0 = x 
        self.y0 = y

    def setImageVectorData(self, ipt1, s ): 
        self.ix1 = ipt1[0] 
        self.y1 = ipt1[1]  
        self.s = s 

    def getDataPoint(self):
        return ( self.dx0, self.y0 )

    def getDataEndPoint(self):
        return ( self.dx1, self.y1 ) if self.dx1 else None
    
    def getDataPosition( self ): 
        if self.dx1 == None: return [ self.dx0, self.y0 ]
        return [ self.dx0 + self.s * ( self.dx1 - self.dx0 ), self.y0 + self.s * ( self.y1 - self.y0 ) ]
        
    def getImagePosition( self ): 
        if self.ix1 == None: return [ self.ix0, self.y0 ]
        return [ self.ix0 + self.s * ( self.ix1 - self.ix0 ), self.y0 + self.s * ( self.y1 - self.y0 ) ]
    
    def getScenePoint(self):
        return self.spt0

    def getSceneEndPoint(self):
        return self.spt1
    
    def getScenePosition(self):
        vector = self.getVector()
        if vector and (self.s > 0.0):
            return vector.getPoint( self.s  ) 
        return self.spt0
    
    def getVector(self):
        if (self.vector == None) and (self.spt1 <> None):
            self.vector = MovementConstraintVector( self.spt0, self.spt1 )
        return self.vector

class NodeData1( QtCore.QObject ):
    RED = 0
    BLUE = 1
    YELLOW = 2
    CYAN = 3
    MAGENTA = 4
    GRAY = 5
    
    def __init__(self, **args ):
        QtCore.QObject.__init__( self )
        self.y0 = args.get( "y0", None )
        self.y1 = args.get( "y1", None )
        self.s = args.get( "s", 0.5 )
        self.color = args.get( "color", NodeData.YELLOW )
        self.free = args.get( "free", True )
        self.index =  args.get( "index", -1 )
        self.dx0 = args.get( "x", None )
        self.dx1 = args.get( "dx1", None )
        self.xbound = args.get( "xbound", False )
        self.spt0 = None
        self.spt1 = None
        self.vector = None

    def getDataPoint(self):
        return ( self.dx0, self.y0  )

    def x(self):
        return self.dx0

    def y(self):
        return self.y0

    def setDataPoint(self, x, y ):
        self.dx0 = x 
        self.y0 = y

    def getDataEndPoint(self):
        return ( self.dx1, self.y1 ) if self.dx1 else None
    
    def getDataPosition( self ): 
        if self.dx1 == None: return [ self.dx0, self.y0 ]
        return [ self.dx0 + self.s * ( self.dx1 - self.dx0 ), self.y0 + self.s * ( self.y1 - self.y0 ) ]

    def getImagePosition( self ): 
        if self.ix1 == None: return [ self.ix0, self.y0 ]
        return [ self.ix0 + self.s * ( self.ix1 - self.ix0 ), self.y0 + self.s * ( self.y1 - self.y0 ) ]
            
    def getScenePoint(self):
        return self.spt0

    def getSceneEndPoint(self):
        return self.spt1
    
    def getScenePosition(self):
        vector = self.getVector()
        if vector and (self.s > 0.0):
            return vector.getPoint( self.s  ) 
        return self.spt0
    
    def getVector(self):
        if (self.vector == None) and (self.spt1 <> None):
            self.vector = MovementConstraintVector( self.spt0, self.spt1 )
        return self.vector
    
class Node( QtGui.QGraphicsItem ):
    Type = QtGui.QGraphicsItem.UserType + 1
    

    def __init__(self, id, graphWidget, **args ):
        super(Node, self).__init__()
        self.id = id
        self.graph = graphWidget
        self.edgeList = []
        self.bounds = args.get( 'bounds', None )
        self.newPos = QtCore.QPointF()
        self.coupledNodes = Set()
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QtGui.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)
        self.xbounded = False
        self.reset()
        
    def reset(self):
        self.index = -1
        self.colorIndex = NodeData.YELLOW
        self.posConstraintVector = None 
        
    def setBounds( self, bnds ):
        self.bounds = list(bnds)
        
    def getColors(self):
        if self.colorIndex == NodeData.RED: return ( QtCore.Qt.red, QtCore.Qt.darkRed )
        if self.colorIndex == NodeData.BLUE: return ( QtCore.Qt.blue, QtCore.Qt.darkBlue )
        if self.colorIndex == NodeData.YELLOW: return ( QtCore.Qt.yellow, QtCore.Qt.darkYellow )
        if self.colorIndex == NodeData.CYAN: return ( QtCore.Qt.cyan, QtCore.Qt.darkCyan )
        if self.colorIndex == NodeData.MAGENTA: return ( QtCore.Qt.magenta, QtCore.Qt.darkMagenta )
        return ( QtCore.Qt.gray, QtCore.Qt.darkGray )
        
    def addCoupledNode( self, node ):
        self.coupledNodes.add( node )
        node.coupledNodes.add( self )
        
    def setPosScaled( self, s ):
        assert ( self.posConstraintVector <> None ), "Error, Position Constraint Vector not defined"
        pos = self.posConstraintVector.getPoint( s )
        self.setPos( pos )
        
    def mouseMoveEvent ( self,  mouseEvent ):
        if self.posConstraintVector == None:
            if self.bounds == None:
                super(Node, self).mouseMoveEvent( mouseEvent )
            else:
                pos = self.mapToScene( mouseEvent.pos() )
                if pos.x() < self.bounds[0]:  pos.setX( self.bounds[0] )
                if pos.x() > self.bounds[2]:  pos.setX( self.bounds[2] )
                if pos.y() < self.bounds[1]:  pos.setY( self.bounds[1] )
                if pos.y() > self.bounds[3]:  pos.setY( self.bounds[3] )
#                print " Set pos: ", str( pos ), str( mouseEvent.pos() )
                self.setPos( pos )
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
        
    def setXBounded( self, xbounded ):
        self.xbounded = xbounded
        
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
            colors = self.getColors()
    
            gradient = QtGui.QRadialGradient(-3, -3, 10)
            if option.state & QtGui.QStyle.State_Sunken:
                gradient.setCenter(3, 3)
                gradient.setFocalPoint(3, 3)
                gradient.setColorAt(1, QtGui.QColor(colors[0]).light(120))
                gradient.setColorAt(0, QtGui.QColor(colors[1]).light(120))
            else:
                gradient.setColorAt(0, colors[0])
                gradient.setColorAt(1, colors[1])
    
            painter.setBrush(QtGui.QBrush(gradient))
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
            painter.drawEllipse(-10, -10, 20, 20)
            
    def isSelected(self):
        return self.graph.checkSelection( self.index )

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edgeList: edge.adjust()
            if self.isSelected():
                self.setSelected(True)
                try:    newPos = value.toPointF() 
                except: newPos = value                 
                scaledPos = self.posConstraintVector.getScaling( newPos ) if self.posConstraintVector else float('NaN')                
                self.graph.itemMoved( self.id, newPos.x(), newPos.y(), scaledPos )
            else: self.setSelected(False)
        return super(Node, self).itemChange(change, value)

    def mousePressEvent(self, event):
        self.update()
        self.graph.updateSelection( self.index )
        self.setSelected(True)
        super(Node, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.update()
        self.graph.clearSelection()
        self.setSelected(False)
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

    def getScaling( self, pt ):
        if abs(self.unitVector.dx()) > abs(self.unitVector.dy()): 
            return ( pt.x() - self.unitVector.x1() )  / ( self.unitVector.dx() * self.length )
        else:
            return ( pt.y() - self.unitVector.y1() ) / ( self.unitVector.dy() * self.length )
    
    def getProjectedPoint( self, pt0 ):
        rel_pt0 = pt0 - self.p1()
        S = ( rel_pt0.x() * self.unitVector.dx() + rel_pt0.y() * self.unitVector.dy() ) 
        s = S/self.length
        new_pt = self.getPoint( s )
        return new_pt, s
    
class GraphScene(QtGui.QGraphicsScene):

    def __init__( self, parent ):
        super(GraphScene, self).__init__( parent )
        
    def mousePressEvent ( self,  mouseEvent ):
        super(GraphScene, self).mousePressEvent( mouseEvent )
        self.emit( QtCore.SIGNAL('mousePressEvent'), mouseEvent )

        
class GraphWidget(QtGui.QGraphicsView):
    
    xAxis = 0
    yAxis = 1
    
    configNone = 0  
    configBounds = 1 
    configShape = 2 
    
    nodeMovedSignal = QtCore.SIGNAL("nodeMoved(int,float,float,float)") 
    transferFunctionEditedSignal = QtCore.SIGNAL("transferFunctionEditedSignal") 
    moveCompletedSignal = QtCore.SIGNAL("moveCompleted()") 
    
    def __init__(self, **args ):
        super(GraphWidget, self).__init__()
        self.nodes = []
        self.edges = []
        self.size = args.get( 'size', (400, 400) )
        self.nticks = args.get( 'nticks', ( 5, 5 ) )
        self.graphUpdateIndex = 0
        self.graphUpdatePeriod = 5
        self.selectedNodeIndex = -99 
        self.tickLen = 12
        self.tickLabels = ( [], [] )
        self.bounds = None
        self.maxNNodes = 15
        self.labelTextAlignment = [ QtCore.Qt.AlignHCenter, QtCore.Qt.AlignRight ]
        self.buildTickLabelRects()
        self.configType = args.get( 'configType', self.configNone )
        self.hasChanges = False
        self.needsRebuild = True

        scene = GraphScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        scene.setSceneRect( 0, 0, self.size[0], self.size[1] )
        self.connect( scene, QtCore.SIGNAL('mousePressEvent'), self.processGraphMouseClick )
        self.setScene(scene)
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setViewportUpdateMode(QtGui.QGraphicsView.BoundingRectViewportUpdate)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)

        self.scale(0.8, 0.8)
        self.setMinimumSize( self.size[0]+100, self.size[1] )
        self.setWindowTitle("Simple Graph")
        self.tf_map = { "Pos Value" : PosValueTransferFunction, "Neg Value" : NegValueTransferFunction, "Absolute Value" : AbsValueTransferFunction }
        self.functions = {} 
        self.currentTransferFunction = None
        self.defaultTransferFunctionType = args.get( 'default_type', AbsValueTransferFunction )
        self.addTransferFunction( 'default' )

    def getTransferFunctionPoints( self, node_data, **args ):
        self.data = []
        for data_pt in node_data: 
            n = NodeData( x=data_pt[0], y=data_pt[1],  **args )
            self.data.append( n )
        return self.data
    
    def addTransferFunctionPoint( self, new_data_pt, **args ):
        new_points = []
        new_node = None
        bounds=[ self.data[0].x(), 0.0, self.data[-1].x(), 1.0 ]
        for node in self.data:
            if (new_node == None) and ( new_data_pt[0] < node.x() ):
                new_node = NodeData( x=new_data_pt[0], y=new_data_pt[1], bounds=bounds,  **args )
                new_points.append( new_node )
            new_points.append( node )
        self.data = new_points
        return new_points
        
    def clearSelection( self ):
        self.selectedNodeIndex = -99
        
    def getTransferFunctionTypes(self):
        return self.tf_map
        
    def checkSelection( self, index ):
#        print "checkSelection: ", str( self.selectedNodeIndex )
        return ( index == self.selectedNodeIndex ) 
        
    def setConfigType( self, cType ):
        if cType <> self.configType:
            self.configType = cType
            self.updateGraph()
        
    def buildGraph( self ):
        self.clear()
        node1 = None
        dx = self.size[0]/( self.maxNNodes - 1 )
        for iN in range( self.maxNNodes ):
            node2 = Node(iN,self)
            self.nodes.append( node2 )
#            self.connect( node2, QtCore.SIGNAL('mouseMoveEvent'), self.processNodeMovement )
            x = iN * dx
            node2.setPos( x, self.size[1] )
            self.scene().addItem(node2)
            if node1 <> None: 
                edge = Edge(node1, node2)
                self.scene().addItem( edge )
                self.edges.append( edge )
            node1 = node2
                     
    def setNodeColor(self, nodeIndex, colorIndex ):   
        self.nodes[ nodeIndex ].colorIndex = colorIndex

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
        bounds = self.bounds[0] if iAxis == 0 else self.bounds[1]
        dR = ( bounds[1] - bounds[0] ) / ( self.nticks[iAxis] - 1 )
        for iTick in range( self.nticks[iAxis] ): 
            rect = self.tickLabels[iAxis][iTick]
            coord_value = bounds[0] + dR * iTick
            painter.drawText( rect, self.labelTextAlignment[iAxis], flt2str( coord_value ) )
                     

    def createGraph( self, xbounds, ybounds, data=None ):
        self.data = []
        if data:
            for nodeData in data:
                self.data.append( nodeData )
        self.bounds = ( xbounds, ybounds )
        if len( self.nodes ) == 0: self.buildGraph()
        self.updateGraph()

    def redrawGraph( self, xbounds, ybounds, data ):
        self.getTransferFunctionPoints( data )
        self.createGraph( xbounds, ybounds )
        
    def updateSelection( self, index ):
        self.selectedNodeIndex = index        
            
    def updateGraph(self):
        for iP in range( len( self.data ) ):
            nodeData = self.data[iP]
            node = self.nodes[iP]
            node.reset()
            nodeData.spt0 = self.getScenePoint( nodeData.getDataPoint() )
#            if nodeData.getDataEndPoint():
#                nodeData.spt1 = self.getScenePoint( nodeData.getDataEndPoint(), self.bounds[0], self.bounds[1] )
#                node.setVector ( nodeData.getVector() ) 
#                node.setMovable ( True ) 
#            else: 
            node.setMovable( nodeData.free )                
            node.setPos ( nodeData.getScenePosition() ) 
            node.setVisible ( True )
#            node.setXBounded( nodeData.xbound ) 
#            bnds = nodeData.getBounds()
#            if bnds:
#                sbnds0 = self.getScenePoint( bnds[0:2] )
#                sbnds1 = self.getScenePoint( bnds[2:4] )
#                node.setBounds( sbnds0, sbnds1 ) 
            node.colorIndex = nodeData.color
            node.setSelected ( True )
            
        for iP in range( len( self.data ), self.maxNNodes ):
            node = self.nodes[iP]
            node.setPos ( self.size[0], self.size[1] )
            node.setMovable( False )
            node.setVisible ( False )
        self.updateNodeBounds()
        self.update()

    def updateNodeBounds(self):
        num_nodes = len( self.nodes )
        for iP in range( num_nodes ):
            node = self.nodes[iP]
#            if iP == 0:
#                node.setBounds( [ 0, 0, 0, self.size[1] ] ) 
#            elif iP == (num_nodes-1):
#                node.setBounds( [ self.size[0], 0, self.size[0], self.size[1] ] ) 
            if node.xbounded:
                node.setBounds( [ node.x(), 0, node.x(), self.size[1] ] ) 
            else:
                n0 = node.pos() if iP == (num_nodes-1) else self.nodes[iP-1].pos()
                n1 = node.pos() if iP == (num_nodes-1) else self.nodes[iP+1].pos()
                node.setBounds( [ n0.x(), 0, n1.x(), self.size[1] ] ) 
        self.update()
            
    def getScenePoint(self, point ):
        xbounds = self.bounds[0]
        ybounds = self.bounds[1]
        dx = ( point[0] - xbounds[0] ) / ( xbounds[1] - xbounds[0] )
        dy = ( point[1] - ybounds[0] ) / ( ybounds[1] - ybounds[0] )
        x = self.size[0] * dx
        y = self.size[1] * ( 1.0 - dy )
        return QtCore.QPointF( x, y )

    def getDataPoint(self, sx, sy ):
        xbounds, ybounds = self.bounds[0], self.bounds[1]
        dx = bound( sx, [ 0, self.size[0] ] ) / float( self.size[0] )
        dy = bound( sy, [ 0, self.size[1] ] ) / float( self.size[1] )
        x = xbounds[0] + dx * ( xbounds[1] - xbounds[0] )
        y = ybounds[1] - dy * ( ybounds[1] - ybounds[0] )
        return x, y

#    def getScenePos( self, point, bounds, isHorizontal ):
#        dp = ( point[0] - bounds[0] ) / ( bounds[1] - xbounds[0] )
#        if isHorizontal: return self.size[0] * dp  
#        else: return self.size[1] * ( 1.0 - dp )

    def itemMoved(self, index, sx, sy, s ):
        if ( self.graphUpdateIndex % self.graphUpdatePeriod ) == 0:
            x, y = self.getDataPoint( sx, sy )
            self.emit( self.nodeMovedSignal, index, x, y, s )
            self.hasChanges = True
            self.updateNodeData( index, x, y )
        self.graphUpdateIndex = self.graphUpdateIndex + 1
        self.updateNodeBounds()
        
    def updateNodeData( self, index, x, y ):
#        print 'updateNode %d Data' % index, str( (x,y ) )
        nodeData = self.data[index]
        nodeData.setDataPoint( x, y )
        if self.currentTransferFunction:
            self.currentTransferFunction.setDataPoint( index, x, y ) 
            self.emit( self.transferFunctionEditedSignal, self.currentTransferFunction.getScaledData( self.bounds[0] ) )

    def mouseReleaseEvent( self, event ):
        super(GraphWidget, self).mouseReleaseEvent(event)
        if self.hasChanges:
            self.emit( self.moveCompletedSignal )
            self.hasChanges = False

    def processGraphMouseClick( self, event ):
        if event.modifiers() & QtCore.Qt.ShiftModifier :
            spt = event.scenePos() 
            x, y = self.getDataPoint( spt.x(), spt.y() )
#            print "Add point: ", str( [ x, y ] ), str( ( spt.x(), spt.y() ) )
            nodes = self.currentTransferFunction.addTransferFunctionPoint( [ x, y ] )
            self.createGraph( self.bounds[0], self.bounds[1], nodes )

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
        message =  "Drag graph nodes, shift-click on graph to add nodes."

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

    def addTransferFunction( self, name, **args ):
        self.currentTransferFunction = TransferFunction( self.defaultTransferFunctionType, **args ) 
        self.functions[ name ]  = self.currentTransferFunction
                           
    def updateTransferFunctionType( self, value ):
        if self.currentTransferFunction: self.currentTransferFunction.setType( self.tf_map[ str(value) ] )
        self.emit( QtCore.SIGNAL('update') )
        
    def setTransferFunctionType( self, tf_type ):
        if self.currentTransferFunction:
            if tf_type in self.tf_map.values(): 
                self.currentTransferFunction.type = tf_type

    def getTransferFunctionType( self ):
        if self.currentTransferFunction: return self.currentTransferFunction.type
        return self.defaultTransferFunctionType   

class TransferFunctionConfigurationDialog( QtGui.QDialog ): 
     
    def __init__(self, parent=None, **args):
        QtGui.QDialog.__init__( self, parent )
        self.setWindowTitle("Transfer Function Configuration")
        self.graph = GraphWidget( size=(400,300), nticks=(5,5) )
        self.connect( self.graph, GraphWidget.nodeMovedSignal, self.graphAdjusted )
        self.connect( self.graph, GraphWidget.moveCompletedSignal, self.doneConfig )
        self.setLayout(QtGui.QVBoxLayout())
        
        tf_type_layout = QtGui.QHBoxLayout()
        tf_type_label = QtGui.QLabel( "Transfer Function Type:"  )
        tf_type_layout.addWidget( tf_type_label ) 

        tf_type_combo =  QtGui.QComboBox ( self )
        tf_type_label.setBuddy( tf_type_combo )
        tf_type_combo.setMaximumHeight( 30 )
        tf_type_layout.addWidget( tf_type_combo )
        current_index, index = 0, 0
        tf_map = self.graph.getTransferFunctionTypes()
        for tf_name in tf_map.keys():
            if tf_map[tf_name] == self.graph.defaultTransferFunctionType:
                current_index = index 
            tf_type_combo.addItem( tf_name )
            index = index + 1  
        tf_type_combo.setCurrentIndex( current_index )   
        self.connect( tf_type_combo, QtCore.SIGNAL("currentIndexChanged(QString)"), self.graph.updateTransferFunctionType )  
        self.layout().addLayout( tf_type_layout )
                
        self.closeButton = QtGui.QPushButton('Ok', self)
        self.layout().addWidget( self.graph )         
        self.layout().addWidget(self.closeButton)
        self.connect(self.closeButton, QtCore.SIGNAL('clicked(bool)'), self.close)
        self.closeButton.setShortcut('Enter')
        
    def closeEvent( self, closeEvent ):
        self.emit( QtCore.SIGNAL('close()') )
        QtGui.QDialog.closeEvent( self, closeEvent )  
        
    def doneConfig( self ):
        self.emit( QtCore.SIGNAL('doneConfig()') )    

    def initLeveling(self, range ):
        pass
    
    def graphAdjusted(self, index, value0, value1, value2 ):
        self.emit( QtCore.SIGNAL('config(int,float,float,float)'), index, value0, value1, value2 )
            
    def createGraph( self, xbounds, ybounds =  [ 0.0, 1.0 ]  ):
        data = [ ( vrange[0], ybounds[0] ),  ( vrange[1], ybounds[1] ) ]
        self.graph.redrawGraph( xbounds, ybounds, data )
  
if __name__ == '__main__':

    vrange = [ -25.3, 35.6 ]

    app = QtGui.QApplication(sys.argv)
    
    dialog = TransferFunctionConfigurationDialog()
    vrange = [ -25.3, 35.6 ]
    data = [ ( vrange[0], 0.0, { 'xbound': True } ), ( (vrange[0]+vrange[1])/2.0, 0.5, { } ),  ( vrange[1], 1.0, { 'xbound': True } ) ]
    dialog.updateGraph( vrange, [ 0.0, 1.0 ], data )
    dialog.show()
    
#    widget = GraphWidget( size=(400,300), nticks=(4,4) )
#    xbounds = [ 0.0, 1.0 ]
#    ybounds = [ 0.0, 1.0 ]
##    data = [ (0.0,0.0,False), (0.4,0.0,0.0,1.0,0.0), (0.6,0.0,0.4,1.0,0.5), (0.6,1.0,False), (0.6,0.0,0.8,1.0,0.5,2), (0.8,0.1,False), (1.0,0.0,False), ]
#    widget.createGraph( xbounds, ybounds )
#    widget.show()

    sys.exit(app.exec_())

