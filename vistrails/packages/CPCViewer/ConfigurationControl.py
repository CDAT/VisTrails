from __future__ import with_statement
from __future__ import division
#  from GraphEditor import *

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

import sys, collections, math
import os.path
import vtk, time
from compiler.ast import Name
from ColorMapManager import ColorMapManager
from ControlPanel import *
from ROISelection import ROIControl
import vtk.util.numpy_support as VN
import numpy

def isNone(obj):
    return ( id(obj) == id(None) )

class ConfigControlList(QtGui.QWidget):

    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.setLayout( QtGui.QVBoxLayout() )
        self.buttonBox = QtGui.QGridLayout()
        self.layout().addLayout( self.buttonBox )
        self.current_control_row = 0
        self.current_control_col = 0
        self.controls = {}
#        self.scrollArea = QtGui.QScrollArea(self) 
#        self.layout().addWidget(self.scrollArea)
        self.stackedWidget =   QtGui.QStackedWidget( self )
        self.layout().addWidget( self.stackedWidget )
        self.blank_widget = QtGui.QWidget() 
        self.blankWidgetIndex = self.stackedWidget.addWidget( self.blank_widget )
        
    def clear(self):
        self.stackedWidget.setCurrentIndex ( self.blankWidgetIndex )
        
    def refresh(self):
        for ctrl in self.controls.values():
            try: ctrl.refresh()
            except: pass
        
    def addControlRow(self):
        self.current_control_row = self.current_control_row + 1
        self.current_control_col = 0

    def addControl( self, iCatIndex, config_ctrl ):
        control_name = config_ctrl.getName()
        control_index = self.stackedWidget.addWidget( config_ctrl )
        self.controls[ control_name ] = config_ctrl
        self.buttonBox.addWidget( config_ctrl.getButton(), self.current_control_row, self.current_control_col ) 
        self.connect( config_ctrl,  QtCore.SIGNAL('ConfigCmd'), self.configOp )
        self.current_control_col = self.current_control_col + 1
        self.clear()
        
    def configOp( self, args ):
        if ( len(args) > 1 ) and ( args[1] == "Open"):
            config_ctrl = self.controls.get(  args[0], None  )
            if config_ctrl: self.stackedWidget.setCurrentWidget ( config_ctrl )
            else: print>>sys.stderr, "ConfigControlList Can't find control: %s " % args[1]
            self.updateGeometry()
#            self.scrollArea.updateGeometry()
    
class ConfigControlContainer(QtGui.QWidget):
    
    def __init__(self, parent=None):  
        QtGui.QWidget.__init__( self, parent )
        self.setLayout(QtGui.QVBoxLayout())
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setEnabled(True)
        self.layout().addWidget( self.tabWidget )
        self.connect( self.tabWidget, QtCore.SIGNAL("currentChanged(int)"), self.categorySelected )
        
    def addCategory( self, cat_name ):
        config_list = ConfigControlList( self.tabWidget )
        tab_index = self.tabWidget.addTab( config_list, cat_name )
        return tab_index
    
    def selectCategory(self, catIndex ):
        self.tabWidget.setCurrentIndex(catIndex)
    
    def getCategoryName( self, iCatIndex ):
        return str( self.tabWidget.tabText( iCatIndex ) )
    
    def getCategoryConfigList( self, iCatIndex ):
        return self.tabWidget.widget( iCatIndex )        
        
    def categorySelected( self, iCatIndex ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), ( "CategorySelected",  self.tabWidget.tabText(iCatIndex) ) )
        config_list = self.tabWidget.widget ( iCatIndex ) 
        config_list.refresh()

class CPCConfigGui(QtGui.QDialog):

    def __init__(self, point_collection=None ):    
        QtGui.QDialog.__init__( self )     
        self.setWindowFlags(QtCore.Qt.Window)
        self.setModal(False)
        self.setWindowTitle('CPC Plot Config')
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.config_widget = ConfigurationWidget( self, point_collection )
        self.layout().addWidget( self.config_widget ) 
        self.config_widget.build()
        self.resize(1000, 1000)
        
    def newSubset( self, indices ):
        if not isNone(indices) and indices.size > 0:
            self.config_widget.newSubset( indices )

    def pointPicked( self, tseries, point ):
        self.config_widget.pointPicked( tseries, point )
        
    def plotting(self):
        return self.config_widget.plotting()

    def closeDialog( self ):
        self.config_widget.saveConfig()
        self.close()

    def activate(self):
        self.config_widget.activate()
        
    def getConfigWidget(self):
        return self.config_widget

#class CPCInfoVisGui(QtGui.QDialog):
#
#    def __init__(self, point_collection ):    
#        QtGui.QDialog.__init__( self )     
#                
#        self.setWindowFlags(QtCore.Qt.Window)
#        self.setModal(False)
#        self.setWindowTitle('CPC InfoVis Config')
#        layout = QtGui.QVBoxLayout()
#        self.setLayout(layout)
#        self.config_widget = InfoVisWidget( point_collection, self )
#        self.layout().addWidget( self.config_widget ) 
#        self.config_widget.build()
#        self.resize(800, 600)
#
#    def closeDialog( self ):
#        self.config_widget.saveConfig()
#        self.close()
#
#    def activate(self):
#        self.config_widget.activate()
#        
#    def getConfigWidget(self):
#        return self.config_widget

#class InfoVisWidget(QtGui.QWidget):
#
#    def __init__(self, point_collection, parent=None ):    
#        QtGui.QWidget.__init__(self, parent)
#        self.point_collection = point_collection
#        self.metadata = point_collection.getMetadata()
#        layout = QtGui.QVBoxLayout()
#        self.setLayout(layout)
#        self.cfgManager = ConfigManager( self )
#        self.tagged_controls = []
#                            
#    def addControl( self, iCatIndex, config_ctrl, id = None ):
#        config_list = self.configContainer.getCategoryConfigList( iCatIndex )
#        config_list.addControl( iCatIndex, config_ctrl )
#        self.tagged_controls.append( config_ctrl )
#    
#    def parameterValueChanged( self, args ):
#        self.processParameterChange( args )
##        print "parameterValueChanged: ", str(args)
#        for config_ctrl in self.tagged_controls:
#            if config_ctrl:
#                config_ctrl.processParameterChange( args )
#
#    def processParameterChange( self, args ):
#        if ( len(args) >= 5 ):
#            name = args[0]
#            trange = [ None, None ]
#            for iArg in range( 1, len(args) ):
#                if args[iArg] == 'rmin':
#                    trange[0] = args[iArg+1]
#                elif args[iArg] == 'rmax':
#                    trange[1] = args[iArg+1]
#                elif args[iArg] == 'name':
#                    name = args[iArg+1]
#            if trange[0] <> None:
#                self.pc_widget.setSelectionRange( name, trange[0], trange[1] )
#                                    
#    def addConfigControl(self, iCatIndex, config_ctrl, id = None ):
#        config_ctrl.build()
#        self.addControl( iCatIndex, config_ctrl, id )
#        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
#        self.connect( config_ctrl.getParameter(), QtCore.SIGNAL("ValueChanged"), self.parameterValueChanged )
#                
#    def configTriggered( self, args ):
#        print "configTriggered: ", str(args)
#        self.emit( QtCore.SIGNAL("ConfigCmd"), args )
#        for config_ctrl in self.tagged_controls:
#            if config_ctrl:
#                config_ctrl.processExtConfigCmd( args )
#        if args[1] == 'EndConfig':
#            self.pc_widget.render()
#
#    def addCategory(self, categoryName ):
#        return self.configContainer.addCategory( categoryName )
#
#    def addControlRow( self, tab_index ):
#        cfgList = self.configContainer.getCategoryConfigList( tab_index )
#        cfgList.addControlRow()
#        
#    def activate(self):
#        self.cfgManager.initParameters()
#        self.configContainer.selectCategory( self.iVariablesCatIndex )
#                           
#    def getCategoryName( self, iCatIndex ):
#        return self.configContainer.getCategoryName( iCatIndex )
#    
#    def askToSaveChanges(self):
#        self.emit( QtCore.SIGNAL("Close"), self.getParameterPersistenceList() )
#
#    def build( self, **args ):
#        self.pc_widget = ParallelCoordinatesWidget()
#        self.layout().addWidget( self.pc_widget )
#        
#        self.configContainer = ConfigControlContainer( self )
#        self.layout().addWidget( self.configContainer )       
#        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
#
#        self.iVariablesCatIndex = self.addCategory( 'Variables' )
#        
#        included_varids = []
#        for var_id in self.metadata:
#            raw_data = self.point_collection.getVarData( var_id )
#            if id(raw_data) <> id(None):
#                var_rec = self.metadata[ var_id ]
#                vrange = var_rec[2]
#                if vrange[1] > vrange[0]:
#                    thresh_cparm = self.cfgManager.addParameter( self.iVariablesCatIndex, var_id, ptype="Threshold Range", rmin=vrange[0], rmax=vrange[1], ctype = 'Leveling' )
#                    self.addConfigControl( self.iVariablesCatIndex, VarRangeControl( thresh_cparm, title=var_rec[0], units=var_rec[1] ) )
#                    included_varids.append( var_id )
#
#        self.pc_widget.createTable( self.metadata, included_varids, self.point_collection )
#
#    def saveConfig(self):
#        self.cfgManager.saveConfig()

#     def generateParallelCoordinatesChart( self ):
#         from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
#         w = QtGui.QFrame()
#         iren = QVTKRenderWindowInteractor( w )
#         
# #        from QVTKWidget import QVTKWidget
# #         input = self.inputModule().getOutput() 
# #         ptData = input.GetPointData()
# #         narrays = ptData.GetNumberOfArrays()
#         arrays = []
#         # Create a table with some points in it...
#         table = vtk.vtkTable()
#         for varid in self.metadata.keys():
#             var_rec = self.metadata[ varid ]
#             raw_data = self.point_collection.getVarData( varid )
#             if id(raw_data) <> id(None):
#                 col = vtk.vtkFloatArray()
#                 col.SetName( varid )
#                 nTup = raw_data.size
#                 col.SetNumberOfTuples( nTup )
#                 col.SetNumberOfComponents(1)
#                 col.SetVoidArray( raw_data, nTup, 1 )
#                 table.AddColumn( col  )                  
#         
#         # Set up a 2D scene, add an XY chart to it
#         view = vtk.vtkContextView()
# #        view.SetRenderer( self.renderer )    
# #        view.SetRenderWindow( self.renderer.GetRenderWindow() )
#         renderer = view.GetRenderer()
#         renderer.SetBackground(1.0, 1.0, 1.0)
#         renwin = view.GetRenderWindow()
#         renwin.RemoveRenderer(renderer)
#         iren.AddRenderer( renderer )
# 
#         
#         chart = vtk.vtkChartParallelCoordinates()
#         
# #         brush = vtk.vtkBrush()
# #         brush.SetColorF (0.1,0.1,0.1)
# #         chart.SetBackgroundBrush(brush)
#         
#         # Create a annotation link to access selection in parallel coordinates view
#         annotationLink = vtk.vtkAnnotationLink()
#         # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
#         # See vtkSelectionNode doc for field and content type enum values
#         annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
#         annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
#         # Connect the annotation link to the parallel coordinates representation
#         chart.SetAnnotationLink(annotationLink)
#         
#         view.GetScene().AddItem(chart)
#                 
#         
#         chart.GetPlot(0).SetInput(table)
#         
#         def selectionCallback(caller, event):
#                 annSel = annotationLink.GetCurrentSelection()
#                 if annSel.GetNumberOfNodes() > 0:
#                         idxArr = annSel.GetNode(0).GetSelectionList()
#                         if idxArr.GetNumberOfTuples() > 0:
#                                 print VN.vtk_to_numpy(idxArr)
#         
#         # Set up callback to update 3d render window when selections are changed in 
#         #       parallel coordinates view
#         annotationLink.AddObserver("AnnotationChangedEvent", selectionCallback)
#                 
# #        view.ResetCamera()
# #        view.Render()       
# #        view.GetInteractor().Start()
#         return w 


class GraphWidget(QtGui.QWidget):
    
    def __init__(self, parent=None):
        from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        QtGui.QWidget.__init__(self, parent)
        self.plotMap = {}
        self.updateCount = 0
        self.renderPeriod = 5
        self.table = None
        
        centralLayout = QtGui.QVBoxLayout()
        self.setLayout(centralLayout)
        centralLayout.setMargin(0)
        centralLayout.setSpacing(0)
        self.selectionRanges = {}
                
        self.view = vtk.vtkContextView()
        self.widget = QVTKRenderWindowInteractor(self,  rw=self.view.GetRenderWindow(), iren=self.view.GetInteractor() )
        self.chart = vtk.vtkChartXY()
        self.view.GetScene().AddItem(self.chart)

        self.layout().addWidget(self.widget)

        # Create a annotation link to access selection in parallel coordinates view
        self.annotationLink = vtk.vtkAnnotationLink()
        # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
        # See vtkSelectionNode doc for field and content type enum values
        self.annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
        self.annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
        # Connect the annotation link to the parallel coordinates representation
        self.chart.SetAnnotationLink(self.annotationLink)
        self.annotationLink.AddObserver("AnnotationChangedEvent", self.selectionCallback)
        
    def render(self):
        self.updatePCPlot()
        self.view.GetRenderWindow().Render()

        
    def createPlot(self, series_index, varname, ts_data ):
        firstRun = ( self.table == None )
        if firstRun:  
            self.table = vtk.vtkTable()
            self.table.Initialize()
            
        col = self.table.GetColumn( series_index )
        if col == None:
            col = vtk.vtkFloatArray()
                
    
#         col = vtk.vtkFloatArray()
#         vrange = [ ts_data.min(), ts_data.max() ]
#         self.axisMap[ varid ] = len( ranges ), vrange
#         col.SetName( varname )
#         nTup = ts_data.size
#         col.SetNumberOfTuples( nTup )
#         col.SetNumberOfComponents(1)
#         col.SetVoidArray( ts_data, nTup, 1 )
#         self.table.AddColumn( col  ) 
#         ranges.append( vrange ) 
#         print " Set column %s, Range: %s, data range = %s " % ( varid, str(vrange), str((ss_raw_data.min(),ss_raw_data.max())))
#                 
# 
#         self.plot.SetInput( self.table )   
#         na = self.chart.GetNumberOfAxes()
#         for i in range(na):
#             vrange = ranges[i]
#             self.chart.GetAxis(i).SetRange(vrange[0], vrange[1])
#             self.chart.GetAxis(i).SetBehavior(vtk.vtkAxis.FIXED)
#             print " Set column range[%d], Range: %s" % ( i, str(vrange) )
# #            self.chart.GetAxis(i).SetPosition(vtk.vtkAxis.LEFT)
# #            self.chart.GetAxis(i).GetTitleProperties().SetOrientation(30)
#         self.widget.Initialize()
#      
#         self.chart.RecalculateBounds()   
#         self.plot.Update()    
#         self.chart.Update()

    def selectionCallback(self, caller, event):  
        pass      

class TimeseriesPlot(QtGui.QWidget):

    def __init__(self, parent=None):
        from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        QtGui.QWidget.__init__(self, parent)
        self.axisMap = {}
        self.table = None
        
        centralLayout = QtGui.QVBoxLayout()
        self.setLayout(centralLayout)
        centralLayout.setMargin(0)
        centralLayout.setSpacing(0)
        self.selectionRanges = {}
                
        self.view = vtk.vtkContextView()
        self.widget = QVTKRenderWindowInteractor(self,  rw=self.view.GetRenderWindow(), iren=self.view.GetInteractor() )
        self.chart = vtk.vtkChartXY()
        self.view.GetScene().AddItem(self.chart)

        self.layout().addWidget(self.widget)

        # Create a annotation link to access selection in parallel coordinates view
        self.annotationLink = vtk.vtkAnnotationLink()
        # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
        # See vtkSelectionNode doc for field and content type enum values
        self.annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
        self.annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
        # Connect the annotation link to the parallel coordinates representation
        self.chart.SetAnnotationLink(self.annotationLink)
        self.annotationLink.AddObserver("AnnotationChangedEvent", self.selectionCallback)

    def setSelectionIndices( self, indices ):
        self.updateSelection( indices )

    def render(self):
        self.updatePCPlot()
        self.view.GetRenderWindow().Render()
                
    def updateSelection(self, selectedIds):
        if len(selectedIds)==0: return
        print " Update Selection: %d nodes" % len(selectedIds)

        Ids = VN.numpy_to_vtkIdTypeArray( numpy.array(selectedIds), deep=True )

        node = vtk.vtkSelectionNode()
        node.SetContentType(vtk.vtkSelectionNode.INDICES)
        node.SetFieldType(vtk.vtkSelectionNode.POINT)
        node.SetSelectionList(Ids)
        
        selection = vtk.vtkSelection()
        selection.AddNode(node)
        
        self.annotationLink.SetCurrentSelection(selection)
        self.widget.Render()
        
    def setSelectionRange(self, colName, min, max ):
        try:
            iAxis, vrange = self.axisMap[colName]
            ext = vrange[1] - vrange[0]
            normalized_range = ( (min-vrange[0])/ext, (max-vrange[0])/ext  )
            self.selectionRanges[ colName ] = iAxis, normalized_range, (min, max), vrange
        except:
            print "Error in setSelectionRange for colName ", str( colName )
#        self.updateCount = self.updateCount  + 1
#        if self.updateCount % self.renderPeriod == 0:
#            self.render()    
#        print " SetSelectionRange[%d]: Axis-%d -> %s %s " % ( self.updateCount, iAxis, str( normalized_range ), str( ( min, max ) ) )

    def resetPCPlot(self):
        plot = self.chart.GetPlot(0)        
        plot.ResetSelectionRange()
        self.selectionRanges = {}
        
    def updatePCPlot(self):
        plot = self.chart.GetPlot(0)        
        plot.ResetSelectionRange()
        for iAxis, normalized_range, scaled_range, full_range in self.selectionRanges.values():
            plot.SetSelectionRange( iAxis, full_range[0], full_range[1] )
        plot.Update()
        
    def createTable(self, metadata, varids, point_collection, point_indices=None ):
        firstRun = ( self.table == None )
        if firstRun:  self.table = vtk.vtkTable()
        self.table.Initialize()

#         else:
#             for iCol in range( self.table.GetNumberOfColumns () ):
#                 self.table.RemoveColumn( iCol )
        ranges = []
        for varid in varids:
            var_rec = metadata[ varid ]
            raw_data = point_collection.getVarData( varid )
            if not isNone(raw_data):                
                ss_raw_data = raw_data[ point_indices ] if not isNone(point_indices) else raw_data[:]
                col = vtk.vtkFloatArray()
                vrange = var_rec[2]
                self.axisMap[ varid ] = len( ranges ), vrange
                col.SetName( varid )
                nTup = ss_raw_data.size
                col.SetNumberOfTuples( nTup )
                col.SetNumberOfComponents(1)
                col.SetVoidArray( ss_raw_data, nTup, 1 )
                self.table.AddColumn( col  ) 
                ranges.append( vrange ) 
                print " Set column %s, Range: %s, data range = %s " % ( varid, str(vrange), str((ss_raw_data.min(),ss_raw_data.max())))
                

        points = self.chart.AddPlot(vtk.vtkChart.POINTS)
        points.SetInputData(self.table, 0, 1)
        points.SetColor(0, 0, 0, 255)
        points.SetWidth(1.0)
        points.SetMarkerStyle(vtk.vtkPlotPoints.CROSS)

#         self.plot.SetInputData( self.table )   
#         na = self.chart.GetNumberOfAxes()
#         for i in range(na):
#             vrange = ranges[i]
#             self.chart.GetAxis(i).SetRange(vrange[0], vrange[1])
#             self.chart.GetAxis(i).SetBehavior(vtk.vtkAxis.FIXED)
#             print " Set column range[%d], Range: %s" % ( i, str(vrange) )
# #            self.chart.GetAxis(i).SetPosition(vtk.vtkAxis.LEFT)
# #            self.chart.GetAxis(i).GetTitleProperties().SetOrientation(30)
        self.widget.Initialize()
     
        self.chart.RecalculateBounds()    
        self.chart.Update()

    def selectionCallback(self, caller, event):        
        annSel = self.annotationLink.GetCurrentSelection()
        if annSel.GetNumberOfNodes() > 0:
            idxArr = annSel.GetNode(0).GetSelectionList()
            if idxArr.GetNumberOfTuples() > 0:
                selection_indices = VN.vtk_to_numpy(idxArr)
                print " Selected %d nodes ********************* " % selection_indices.size   

class ParallelCoordinatesWidget(QtGui.QWidget):
    
    def __init__(self, parent=None):
        from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        QtGui.QWidget.__init__(self, parent)
        self.axisMap = {}
        self.updateCount = 0
        self.renderPeriod = 5
        self.table = None
        
        centralLayout = QtGui.QVBoxLayout()
        self.setLayout(centralLayout)
        centralLayout.setMargin(0)
        centralLayout.setSpacing(0)
        self.selectionRanges = {}
                
        self.view = vtk.vtkContextView()
        self.widget = QVTKRenderWindowInteractor(self,  rw=self.view.GetRenderWindow(), iren=self.view.GetInteractor() )
        self.chart = vtk.vtkChartParallelCoordinates()
        self.view.GetScene().AddItem(self.chart)

        self.layout().addWidget(self.widget)

        # Create a annotation link to access selection in parallel coordinates view
        self.annotationLink = vtk.vtkAnnotationLink()
        # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
        # See vtkSelectionNode doc for field and content type enum values
        self.annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
        self.annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
        # Connect the annotation link to the parallel coordinates representation
        self.chart.SetAnnotationLink(self.annotationLink)
        self.annotationLink.AddObserver("AnnotationChangedEvent", self.selectionCallback)
        
    def setSelectionIndices( self, indices ):
        self.updateSelection( indices )

    def render(self):
        self.updatePCPlot()
        self.view.GetRenderWindow().Render()
                
    def updateSelection(self, selectedIds):
        if len(selectedIds)==0: return
        print " Update Selection: %d nodes" % len(selectedIds)

        Ids = VN.numpy_to_vtkIdTypeArray( numpy.array(selectedIds), deep=True )

        node = vtk.vtkSelectionNode()
        node.SetContentType(vtk.vtkSelectionNode.INDICES)
        node.SetFieldType(vtk.vtkSelectionNode.POINT)
        node.SetSelectionList(Ids)
        
        selection = vtk.vtkSelection()
        selection.AddNode(node)
        
        self.annotationLink.SetCurrentSelection(selection)
        self.widget.Render()
        
    def setSelectionRange(self, colName, min, max ):
        try:
            iAxis, vrange = self.axisMap[colName]
            ext = vrange[1] - vrange[0]
            normalized_range = ( (min-vrange[0])/ext, (max-vrange[0])/ext  )
            self.selectionRanges[ colName ] = iAxis, normalized_range, (min, max), vrange
        except:
            print "Error in setSelectionRange for colName ", str( colName )
#        self.updateCount = self.updateCount  + 1
#        if self.updateCount % self.renderPeriod == 0:
#            self.render()    
#        print " SetSelectionRange[%d]: Axis-%d -> %s %s " % ( self.updateCount, iAxis, str( normalized_range ), str( ( min, max ) ) )

    def resetPCPlot(self):
        plot = self.chart.GetPlot(0)        
        plot.ResetSelectionRange()
        self.selectionRanges = {}
        
    def updatePCPlot(self):
        plot = self.chart.GetPlot(0)        
        plot.ResetSelectionRange()
        for iAxis, normalized_range, scaled_range, full_range in self.selectionRanges.values():
            plot.SetSelectionRange( iAxis, full_range[0], full_range[1] )
        plot.Update()
        
    def createTable(self, metadata, varids, point_collection, point_indices=None ):
        firstRun = ( self.table == None )
        if firstRun:  self.table = vtk.vtkTable()
        self.table.Initialize()
        self.plot =  vtk.vtkPlotParallelCoordinates() 
        self.chart.SetPlot( self.plot )    

#         else:
#             for iCol in range( self.table.GetNumberOfColumns () ):
#                 self.table.RemoveColumn( iCol )
        ranges = []
        for varid in varids:
            var_rec = metadata[ varid ]
            raw_data = point_collection.getVarData( varid )
            if not isNone(raw_data):                
                ss_raw_data = raw_data[ point_indices ] if not isNone(point_indices) else raw_data[:]
                col = vtk.vtkFloatArray()
                vrange = var_rec[2]
                self.axisMap[ varid ] = len( ranges ), vrange
                col.SetName( varid )
                nTup = ss_raw_data.size
                col.SetNumberOfTuples( nTup )
                col.SetNumberOfComponents(1)
                col.SetVoidArray( ss_raw_data, nTup, 1 )
                self.table.AddColumn( col  ) 
                ranges.append( vrange ) 
                print " Set column %s, Range: %s, data range = %s " % ( varid, str(vrange), str((ss_raw_data.min(),ss_raw_data.max())))
                

        self.plot.SetInputData( self.table )   
        na = self.chart.GetNumberOfAxes()
        for i in range(na):
            vrange = ranges[i]
            self.chart.GetAxis(i).SetRange(vrange[0], vrange[1])
            self.chart.GetAxis(i).SetBehavior(vtk.vtkAxis.FIXED)
            print " Set column range[%d], Range: %s" % ( i, str(vrange) )
#            self.chart.GetAxis(i).SetPosition(vtk.vtkAxis.LEFT)
#            self.chart.GetAxis(i).GetTitleProperties().SetOrientation(30)
        self.widget.Initialize()
     
        self.chart.RecalculateBounds()   
        self.plot.Update()    
        self.chart.Update()

    def selectionCallback(self, caller, event):        
        annSel = self.annotationLink.GetCurrentSelection()
        if annSel.GetNumberOfNodes() > 0:
            idxArr = annSel.GetNode(0).GetSelectionList()
            if idxArr.GetNumberOfTuples() > 0:
                selection_indices = VN.vtk_to_numpy(idxArr)
                print " Selected %d nodes ********************* " % selection_indices.size   

class TimeseriesPlotControl( ConfigControl ): 

    def __init__(self, configManager, point_collection, cparm, cat_index, **args ):  
        super( TimeseriesPlotControl, self ).__init__( cparm )
        self.point_collection = point_collection
        self.metadata = point_collection.getMetadata()
        self.cat_index = cat_index 
        self.cfgManager = configManager
        self.tagged_controls = []
        self.ext_parameters = {}
        self.point_indices = None

    def build(self):
        super( TimeseriesPlotControl, self ).build()
        var_tab_index, layout = self.addTab( 'Timeseries Plot' )
        self.pc_widget = TimeseriesPlot()
        layout.addWidget( self.pc_widget )
        
        self.configContainer = ConfigControlContainer( self )
        layout.addWidget( self.configContainer )       
        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        
    def configTriggered( self, args ):
        print "configTriggered: ", str(args)
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processExtConfigCmd( args )
        if args[1] == 'EndConfig':
            self.pc_widget.render()

    def pointPicked( self, tseries, point ):
        print " TimeseriesPlotControl: pointPicked, point = %s " % str( point )

    def plotting(self):
        return self.visible()  
        
class InfoGridControl( ConfigControl ): 
    
    def __init__(self, configManager, point_collection, cparm, cat_index, **args ):  
        super( InfoGridControl, self ).__init__( cparm )
        self.point_collection = point_collection
        self.metadata = point_collection.getMetadata()
        self.cat_index = cat_index 
        self.cfgManager = configManager
        self.tagged_controls = []
        self.ext_parameters = {}
        self.point_indices = None
        
    def newSubset( self, indices ):
        if not isNone(indices): 
            self.point_indices = indices
            if self.pc_widget.isVisible():
                pass
#                self.pc_widget.setSelectionIndices( indices )
#                 self.pc_widget.createTable( self.metadata, self.included_varids, self.point_collection, indices )
        
    def setExternalParameter(self, pname, parm ):
        self.ext_parameters[ pname ] = parm
                            
    def addControl( self, iCatIndex, config_ctrl, id = None ):
        config_list = self.configContainer.getCategoryConfigList( iCatIndex )
        config_list.addControl( iCatIndex, config_ctrl )
        self.tagged_controls.append( config_ctrl )
    
    def parameterValueChanged( self, args ):
        self.processParameterChange( args )
#        print "parameterValueChanged: ", str(args)
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processParameterChange( args )

    def processParameterChange( self, args ):
        if ( len(args) >= 5 ):
            trange = [ extract_arg( args, 'rmin', offset=1 ), extract_arg( args, 'rmax', offset=1 ) ]
            name = extract_arg( args, 'name', offset=1, defval=args[0] )
            if (trange[0] <> None) and (trange[1] <> None):
                self.pc_widget.setSelectionRange( name, trange[0], trange[1] )
                                    
    def addConfigControl(self, iCatIndex, config_ctrl, id = None ):
        config_ctrl.build()
        self.addControl( iCatIndex, config_ctrl, id )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        self.connect( config_ctrl.getParameter(), QtCore.SIGNAL("ValueChanged"), self.parameterValueChanged )
                
    def configTriggered( self, args ):
        print "configTriggered: ", str(args)
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processExtConfigCmd( args )
        if args[1] == 'EndConfig':
            self.pc_widget.render()

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )

    def addControlRow( self, tab_index ):
        cfgList = self.configContainer.getCategoryConfigList( tab_index )
        cfgList.addControlRow()
                                   
    def getCategoryName( self, iCatIndex ):
        return self.configContainer.getCategoryName( iCatIndex )
    
    def build(self):
        super( InfoGridControl, self ).build()
        var_tab_index, layout = self.addTab( 'Parallel Coordinates' )
        self.pc_widget = ParallelCoordinatesWidget()
        layout.addWidget( self.pc_widget )
        
        self.configContainer = ConfigControlContainer( self )
        layout.addWidget( self.configContainer )       
        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )

        self.iVariablesCatIndex = self.addCategory( 'Variables' )
        
        self.included_varids = []
        for var_id in self.metadata:
            raw_data = self.point_collection.getVarData( var_id )
            if not isNone(raw_data):
                var_rec = self.metadata[ var_id ]
                vrange = var_rec[2]
                if vrange[1] > vrange[0]:
                    thresh_cparm = self.ext_parameters.get( var_id, None ) 
                    if thresh_cparm == None:
                        thresh_cparm = self.cfgManager.addParameter( self.cat_index, "Threshold Range", rmin=vrange[0], rmax=vrange[1], ctype = 'Leveling', varname=var_id )
                    else:
                        thresh_cparm.setScaledRange( vrange )
                    self.addConfigControl( self.iVariablesCatIndex, VarRangeControl( thresh_cparm, title=var_rec[0], units=var_rec[1] ) )
                    self.included_varids.append( var_id )

        self.pc_widget.createTable( self.metadata, self.included_varids, self.point_collection )
                     
class ConfigurationWidget(QtGui.QWidget):

    def __init__(self, parent=None, point_collection=None ):    
        QtGui.QWidget.__init__(self, parent)
        self.point_collection = point_collection
        self.metadata = point_collection.getMetadata() if point_collection else {}
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.cfgManager = ConfigManager( self, defvar=point_collection.var.id )        

        self.tagged_controls = []
                        
        self.scrollArea = QtGui.QScrollArea(self) 
        self.scrollArea.setFrameStyle(QtGui.QFrame.NoFrame)      
        self.scrollArea.setWidgetResizable(True)
        
        self.configContainer = ConfigControlContainer( self.scrollArea )
        self.scrollArea.setWidget( self.configContainer )
        self.scrollArea.setSizePolicy( QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding )
        layout.addWidget(self.scrollArea)       
        self.connect( self.configContainer, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        
    def newSubset( self, indices ):
        for ctrl in self.tagged_controls:
            ctrl.newSubset( indices )

    def pointPicked( self, tseries, point ):
        for ctrl in self.tagged_controls:
            ctrl.pointPicked( tseries, point  )
            
    def plotting(self):
        for ctrl in self.tagged_controls:
            if ctrl.plotting(): return True
        return False

    def addControl( self, iCatIndex, config_ctrl, id = None ):
        config_list = self.configContainer.getCategoryConfigList( iCatIndex )
        config_list.addControl( iCatIndex, config_ctrl )
        self.tagged_controls.append( config_ctrl )
    
    def parameterValueChanged( self, args ):
#        print "parameterValueChanged: ", str(args)
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processParameterChange( args )
                    
    def addConfigControl(self, iCatIndex, config_ctrl, id = None ):
#        config_ctrl.setMetadata( self.cfgManager.getMetadata()  )
        config_ctrl.build(  )
        self.addControl( iCatIndex, config_ctrl, id )
        self.connect( config_ctrl, QtCore.SIGNAL("ConfigCmd"), self.configTriggered )
        self.connect( config_ctrl.getParameter(), QtCore.SIGNAL("ValueChanged"), self.parameterValueChanged )
                
    def configTriggered( self, args ):
        self.emit( QtCore.SIGNAL("ConfigCmd"), args )
        for config_ctrl in self.tagged_controls:
            if config_ctrl:
                config_ctrl.processExtConfigCmd( args )

    def addCategory(self, categoryName ):
        return self.configContainer.addCategory( categoryName )

    def addControlRow( self, tab_index ):
        cfgList = self.configContainer.getCategoryConfigList( tab_index )
        cfgList.addControlRow()
        
    def activate(self):
        self.cfgManager.initParameters()
        self.configContainer.selectCategory( self.iSubsetCatIndex )
                           
    def getCategoryName( self, iCatIndex ):
        return self.configContainer.getCategoryName( iCatIndex )
    
    def askToSaveChanges(self):
        self.emit( QtCore.SIGNAL("Close"), self.getParameterPersistenceList() )

    def build( self, **args ):
        init_roi = args.get( 'roi', ( 0, -90, 360, 90 ) )
        defvar = self.cfgManager.getMetadata( 'defvar' )
        self.iColorCatIndex = self.addCategory( 'Color' )
        cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Color Scale", wpos=0.5, wsize=1.0, ctype = 'Leveling' )
        self.addConfigControl( self.iColorCatIndex, ColorScaleControl( cparm ) )       
        cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Color Map", Colormap="jet", Invert=1, Stereo=0, Colorbar=0  )
        self.addConfigControl( self.iColorCatIndex, ColormapControl( cparm ) )  
             
        self.iSubsetCatIndex = self.addCategory( 'Subsets' )
        cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "Slice Planes",  xpos=0.5, ypos=0.5, zpos=0.5, xhrwidth=0.0025, xlrwidth=0.005, yhrwidth=0.0025, ylrwidth=0.005 )
        self.addConfigControl( self.iSubsetCatIndex, SlicerControl( cparm, wrange=[ 0.0001, 0.02 ] ) ) # , "SlicerControl" )
        var_rec = self.metadata[ defvar ]
        vrange = var_rec[2]
        thresh_cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "Threshold Range", rmin=vrange[0], rmax=vrange[1], ctype = 'Leveling', varname=defvar )
        self.addConfigControl( self.iSubsetCatIndex, VolumeControl( thresh_cparm ) )
        roi_cparm = self.cfgManager.addParameter( self.iSubsetCatIndex, "ROI", roi=init_roi  )
        self.addConfigControl( self.iSubsetCatIndex, ROIControl( roi_cparm ) )

        op_cparm = self.cfgManager.addParameter( self.iColorCatIndex, "Opacity Scale", rmin=0.0, rmax=1.0, ctype = 'Range'  )
        self.addConfigControl( self.iColorCatIndex, OpacityScaleControl( op_cparm, thresh_cparm, vbounds=self.metadata.get('vbounds', [ 0.0, 1.0 ] ) ) )       
                
        self.iPointsCatIndex = self.addCategory( 'Points' )
        cparm = self.cfgManager.addParameter( self.iPointsCatIndex, "Point Size",  cats = [ ("Low Res", "# Pixels", 1, 20, 10 ), ( "High Res", "# Pixels",  1, 10, 3 ) ] )
        self.addConfigControl( self.iPointsCatIndex, PointSizeSliderControl( cparm ) )
        cparm = self.cfgManager.addParameter( self.iPointsCatIndex, "Max Resolution", value=1.0 )
        self.addConfigControl( self.iPointsCatIndex, SliderControl( cparm ) )
        self.GeometryCatIndex = self.addCategory( 'Geometry' )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Projection", choices = [ "Lat/Lon", "Spherical" ], init_index=0 )
        self.addConfigControl( self.GeometryCatIndex, RadioButtonSelectionControl( cparm ) )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Vertical Scaling", value=0.5 )
        self.addConfigControl( self.GeometryCatIndex, SliderControl( cparm ) )
        vertical_vars = args.get( 'vertical_vars', [] )
        vertical_vars.insert( 0, "Levels" )
        cparm = self.cfgManager.addParameter( self.GeometryCatIndex, "Vertical Variable", choices = vertical_vars, init_index=0  )
        self.addConfigControl( self.GeometryCatIndex, RadioButtonSelectionControl( cparm ) )

        self.AnalysisCatIndex = self.addCategory( 'Analysis' )
        cparm = self.cfgManager.addParameter( self.AnalysisCatIndex, "Animation" )
        self.addConfigControl( self.AnalysisCatIndex, AnimationControl( cparm ) )
        cparm = self.cfgManager.addParameter( self.AnalysisCatIndex, "InfoGrid" )
        igc = InfoGridControl( self.cfgManager, self.point_collection, cparm, self.AnalysisCatIndex )
        igc.setExternalParameter( defvar, thresh_cparm )
        self.addConfigControl( self.AnalysisCatIndex, igc )

        cparm = self.cfgManager.addParameter( self.AnalysisCatIndex, "Timeseries" )
        tsc = TimeseriesPlotControl( self.cfgManager, self.point_collection, cparm, self.AnalysisCatIndex )
        self.addConfigControl( self.AnalysisCatIndex, tsc )
        
    def saveConfig(self):
        self.cfgManager.saveConfig()

              
class ConfigManager(QtCore.QObject):
    
    def __init__( self, controller=None, **args ): 
        QtCore.QObject.__init__( self )
        self.cfgFile = None
        self.cfgDir = None
        self.controller = controller
        self.config_params = {}
        self.iCatIndex = 0
        self.cats = {}
        self.metadata = args
        
    def getMetadata(self, key=None ):
        return self.metadata.get( key, None ) if key else self.metadata

    def addParam(self, key ,cparm ):
        self.config_params[ key ] = cparm
#        print "Add param[%s]" % key
                     
    def saveConfig( self ):
        try:
            f = open( self.cfgFile, 'w' )
            for config_item in self.config_params.items():
                cfg_str = " %s = %s " % ( config_item[0], config_item[1].serialize() )
                f.write( cfg_str )
            f.close()
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile

    def addParameter( self, iCatIndex, config_name, **args ):
        categoryName = self.controller.getCategoryName( iCatIndex ) if self.controller else self.cats[ iCatIndex ]
        cparm = ConfigParameter.getParameter( config_name, **args )
        varname = args.get('varname', None )
        key_tok = [ categoryName, config_name ]
        if varname: key_tok.append( varname )
        self.addParam( ':'.join( key_tok ), cparm )
        return cparm

    def readConfig( self ):
        try:
            f = open( self.cfgFile, 'r' )
            while( True ):
                config_str = f.readline()
                if not config_str: break
                cfg_tok = config_str.split('=')
                parm = self.config_params.get( cfg_tok[0].strip(), None )
                if parm: parm.initialize( cfg_tok[1] )
        except IOError:
            print>>sys.stderr, "Can't open config file: %s" % self.cfgFile                       
        
    def initParameters(self):
        if not self.cfgDir:
            self.cfgDir = os.path.join( os.path.expanduser( "~" ), ".cpc" )
            if not os.path.exists(self.cfgDir): 
                os.mkdir(  self.cfgDir )
        if not self.cfgFile:
            self.cfgFile = os.path.join( self.cfgDir, "cpcConfig.txt" )
        else:
            self.readConfig()            
        emitter = self.controller if self.controller else self
        for config_item in self.config_params.items():
            emitter.emit( QtCore.SIGNAL("ConfigCmd"), ( "InitParm",  config_item[0], config_item[1] ) )

    def getParameterPersistenceList(self):
        plist = []
        for cfg_item in self.config_params.items():
            key = cfg_item[0]
            cfg_spec = cfg_item[1].pack()
            plist.append( ( key, cfg_spec[1] ) )
        return plist

    def initialize( self, parm_name, parm_values ):
        if not ( isinstance(parm_values,list) or isinstance(parm_values,tuple) ):
            parm_values = [ parm_values ]
        cfg_parm = self.config_params.get( parm_name, None )
        if cfg_parm: cfg_parm.unpack( parm_values )

    def getPersistentParameterSpecs(self):
        plist = []
        for cfg_item in self.config_params.items():
            key = cfg_item[0]
            values_decl = cfg_item[1].values_decl()
            plist.append( ( key, values_decl ) )
        return plist
    
    def addCategory(self, cat_name ):
        self.iCatIndex = self.iCatIndex + 1
        self.cats[ self.iCatIndex ] = cat_name
        return self.iCatIndex
    
        
#     def build( self, **args ):
#         self.iColorCatIndex = self.addCategory( 'Color' )
#         cparm = self.addParameter( self.iColorCatIndex, "Color Scale", wpos=0.5, wsize=1.0, ctype = 'Leveling' )
#         cparm = self.addParameter( self.iColorCatIndex, "Opacity Scale", rmin=0.0, rmax=1.0, ctype = 'Range'  )
#         cparm = self.addParameter( self.iColorCatIndex, "Color Map", Colormap="jet", Invert=1, Stereo=0, Colorbar=0  )
#         self.iSubsetCatIndex = self.addCategory( 'Subsets' )
#         cparm = self.addParameter( self.iSubsetCatIndex, "Slice Planes",  xpos=0.5, ypos=0.5, zpos=0.5, xhrwidth=0.0025, xlrwidth=0.005, yhrwidth=0.0025, ylrwidth=0.005 )
#         cparm = self.addParameter( self.iSubsetCatIndex, "Threshold Range", wpos=0.5, wsize=0.2, ctype = 'Leveling' )   
#         self.iPointsCatIndex = self.addCategory( 'Points' )     
#         cparm = self.addParameter( self.iPointsCatIndex, "Point Size",  cats = [ ("Low Res", "# Pixels", 1, 20, 10 ), ( "High Res", "# Pixels",  1, 10, 3 ) ] )
#         cparm = self.addParameter( self.iPointsCatIndex, "Max Resolution", value=1.0 )
#         self.GeometryCatIndex = self.addCategory( 'Geometry' )
#         cparm = self.addParameter( self.GeometryCatIndex, "Projection", choices = [ "Lat/Lon", "Spherical" ], init_index=0 )
#         cparm = self.addParameter( self.GeometryCatIndex, "Vertical Scaling", value=0.5 )
#         cparm = self.addParameter( self.GeometryCatIndex, "Vertical Variable", choices = [], init_index=0  )
#         self.AnalysisCatIndex = self.addCategory( 'Analysis' )
#         cparm = self.addParameter( self.AnalysisCatIndex, "Animation" )
               
if __name__ == '__main__':
    app = QtGui.QApplication(['CPC Config Dialog'])
    
    configDialog = CPCConfigGui()
    configDialog.show()
     
    app.connect( app, QtCore.SIGNAL("aboutToQuit()"), configDialog.closeDialog ) 
    app.exec_() 
 


