from core.modules.basic_modules import String
from packages.scikit_learn.matrix import Matrix
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from PyQt4 import QtGui
from matplotlib.widgets import  RectangleSelector
from matplotlib.transforms import Bbox
import numpy as np
import os
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

from core.bundles import py_import
try:
    mpl_dict = {'linux-ubuntu': 'python-matplotlib',
                'linux-fedora': 'python-matplotlib'}
    matplotlib = py_import('matplotlib', mpl_dict)
    matplotlib.use('Qt4Agg', warn=False)
    pylab = py_import('pylab', mpl_dict)
except Exception, e:
    from core import debug
    debug.critical("Exception: %s" % e)
    
packagePath = os.path.dirname( __file__ )

################################################################################
class LinkedWidget(QCellWidget):
    """
    """
    
    def __init__(self, parent=None):
        """ LinkedWidget(parent: QWidget) -> LinkedWidget
        Initialize the widget with its central layout
        """
        
        QCellWidget.__init__(self, parent)
        centralLayout = QtGui.QVBoxLayout()
        self.setLayout(centralLayout)
        centralLayout.setMargin(0)
        centralLayout.setSpacing(0)
        
        # Create a new Figure Manager and configure it
        pylab.figure(str(self))
        self.figManager = pylab.get_current_fig_manager()
        self.figManager.toolbar.hide()
        self.layout().addWidget(self.figManager.window)
        
        self.inputPorts = None;
        self.selectedIds = []
        
        CoordinationManager.Instance().register(self)
    
    def deleteLater(self):
        """ deleteLater() -> None        
        Overriding PyQt deleteLater to free up resources
        
        """
        # Destroy the old one if possible
        if self.figManager:
            try:                    
                pylab.close(self.figManager.canvas.figure)
                # There is a bug in Matplotlib backend_qt4. It is a
                # wrong command for Qt4. Just ignore it and continue
                # to destroy the widget
            except:
                pass
            
            self.figManager.window.deleteLater()
        QCellWidget.deleteLater(self)
        
    def updateContents(self, inputPorts=None):
        """ updateContents(inputPorts: tuple) -> None
        Update the widget contents based on the input data
        """
        if inputPorts is not None: self.inputPorts = inputPorts
        
        # select our figure
        fig = pylab.figure(str(self))
        pylab.setp(fig, facecolor='w')

        # matplotlib plot
        self.draw(fig)
        
        # Set Selectors
        self.rectSelector = RectangleSelector(pylab.gca(), self.onselect, drawtype='box', 
                                              rectprops=dict(alpha=0.4, facecolor='yellow'),
                                              )
        self.rectSelector.set_active(True)
        
        
        # reset selectedIds
        self.selectedIds = []
        self.update()
        
        # Capture window into history for playback
        # Call this at the end to capture the image after rendering
        QCellWidget.updateContents(self, inputPorts)
        
    def onselect(self, eclick, erelease):
        raise NotImplementedError("Please Implement this method") 
    
    def draw(self, fig):
        raise NotImplementedError("Please Implement this method") 

################################################################################
class ProjectionWidget(LinkedWidget):
    """ ProjectionWidget is a widget to show 2D projections. It has some interactive
    features like, show labels, selections, and synchronization.
    """
    def __init__(self, parent=None):
        LinkedWidget.__init__(self, parent)
        
        self.showLabels = False
        self.toolBarType = QProjectionToolBar
        
    def draw(self, fig):
        """draw(fig: Figure) ->None
        code using matplotlib.
        Use self.fig and self.figManager
        """
        
        (self.matrix, title) = self.inputPorts
        
        # for faster access
        id2pos = {idd:pos for (pos, idd) in enumerate(self.matrix.ids)}
        circleSize = np.ones(self.matrix.ids.shape)
        for selId in self.selectedIds:
            circleSize[id2pos[selId]] = 4
        
        pylab.clf()
        pylab.axis('off')
        
        pylab.title(title)
        pylab.scatter( self.matrix.values[:,0], self.matrix.values[:,1], 
#                       c=colors, cmap=pylab.cm.Spectral,
                       s=40,
                       linewidth=circleSize,
                       marker='o')
  
        # draw labels
        if self.showLabels and self.matrix.labels is not None:
            for label, xy in zip(self.matrix.labels, self.matrix.values):
                pylab.annotate(
                    str(label), 
                    xy = xy, 
                    xytext = (5, 5),
                    textcoords = 'offset points',
                    bbox = dict(boxstyle = 'round,pad=0.2', fc = 'yellow', alpha = 0.5),
                )
        
        self.figManager.canvas.draw()
        
    def onselect(self, eclick, erelease):
        left, bottom = min(eclick.xdata, erelease.xdata), min(eclick.ydata, erelease.ydata)
        right, top = max(eclick.xdata, erelease.xdata), max(eclick.ydata, erelease.ydata)
        region = Bbox.from_extents(left, bottom, right, top)
        
        selectedIds = []
        for (xy, idd) in zip(self.matrix.values, self.matrix.ids):
            if region.contains(xy[0], xy[1]):
                selectedIds.append(idd)
        CoordinationManager.Instance().notifyModules(selectedIds)

class ProjectionView(SpreadsheetCell):
    """
    """
    my_namespace = 'views'
    name         = '2D Projection View'
    
    _input_ports = [('matrix',    Matrix, False),
                    ('title',     String,  False)
                   ]

    def compute(self):
        """ compute() -> None        
        """
        matrix = self.getInputFromPort('matrix')
        title  = self.forceGetInputFromPort('title', '')
        self.displayAndWait(ProjectionWidget, (matrix, title))


################################################################################
class ParallelCoordinatesWidget(QCellWidget):
    def __init__(self, parent=None):
        QCellWidget.__init__(self, parent)
        
        centralLayout = QtGui.QVBoxLayout()
        self.setLayout(centralLayout)
        centralLayout.setMargin(0)
        centralLayout.setSpacing(0)
                
        self.view = vtk.vtkContextView()
        self.widget = QVTKRenderWindowInteractor(self, 
                                                 rw=self.view.GetRenderWindow(),
                                                 iren=self.view.GetInteractor()
                                                )

        chart = vtk.vtkChartParallelCoordinates()
        self.view.GetScene().AddItem(chart)

        # Create a table with some points in it
        arrX = vtk.vtkFloatArray()
        arrX.SetName("XAxis")
        arrC = vtk.vtkFloatArray()
        arrC.SetName("Cosine")
        arrS = vtk.vtkFloatArray()
        arrS.SetName("Sine")
        arrS2 = vtk.vtkFloatArray()
        arrS2.SetName("Tan")

        numPoints = 200
        inc = 7.5 / (numPoints-1)

        import math
        for i in range(numPoints):
            arrX.InsertNextValue(i * inc)
            arrC.InsertNextValue(math.cos(i * inc) + 0.0)
            arrS.InsertNextValue(math.sin(i * inc) + 0.0)
            arrS2.InsertNextValue(math.tan(i * inc) + 0.5)

        table = vtk.vtkTable()
        table.AddColumn(arrX)
        table.AddColumn(arrC)
        table.AddColumn(arrS)
        table.AddColumn(arrS2)

        # Create blue to gray to red lookup table
        lut = vtk.vtkLookupTable()
        lutNum = 256
        lut.SetNumberOfTableValues(lutNum)
        lut.Build()

        ctf = vtk.vtkColorTransferFunction()
        ctf.SetColorSpaceToDiverging()
        cl = []
        # Variant of Colorbrewer RdBu 5
        cl.append([float(cc)/255.0 for cc in [202, 0, 32]])
        cl.append([float(cc)/255.0 for cc in [244, 165, 130]])
        cl.append([float(cc)/255.0 for cc in [140, 140, 140]])
        cl.append([float(cc)/255.0 for cc in [146, 197, 222]])
        cl.append([float(cc)/255.0 for cc in [5, 113, 176]])
        vv = [float(xx)/float(len(cl)-1) for xx in range(len(cl))]
        vv.reverse()
        for pt,color in zip(vv,cl):
            ctf.AddRGBPoint(pt, color[0], color[1], color[2])

        for ii,ss in enumerate([float(xx)/float(lutNum) for xx in range(lutNum)]):
            cc = ctf.GetColor(ss)
            lut.SetTableValue(ii,cc[0],cc[1],cc[2],1.0)

        lut.SetAlpha(0.25)
        lut.SetRange(-1, 1)

        chart.GetPlot(0).SetInput(table)
        chart.GetPlot(0).SetScalarVisibility(1)
        chart.GetPlot(0).SetLookupTable(lut)
        chart.GetPlot(0).SelectColorArray("Cosine")

        self.widget.Initialize()
        
        self.layout().addWidget(self.widget)

        # Create a annotation link to access selection in parallel coordinates view
        self.annotationLink = vtk.vtkAnnotationLink()
        # If you don't set the FieldType explicitly it ends up as UNKNOWN (as of 21 Feb 2010)
        # See vtkSelectionNode doc for field and content type enum values
        self.annotationLink.GetCurrentSelection().GetNode(0).SetFieldType(1)     # Point
        self.annotationLink.GetCurrentSelection().GetNode(0).SetContentType(4)   # Indices
        # Connect the annotation link to the parallel coordinates representation
        chart.SetAnnotationLink(self.annotationLink)
        self.annotationLink.AddObserver("AnnotationChangedEvent", self.selectionCallback)

#        self.inputPorts = None;
#        self.selectedIds = []
#        CoordinationManager.Instance().register(self)
    
    def updateContents(self, inputPorts):
        

        # Capture window into history for playback
        # Call this at the end to capture the image after rendering
        QCellWidget.updateContents(self, inputPorts)

    def selectionCallback(self, caller, event):
        import vtk.util.numpy_support as VN
        annSel = self.annotationLink.GetCurrentSelection()
        if annSel.GetNumberOfNodes() > 0:
                idxArr = annSel.GetNode(0).GetSelectionList()
                if idxArr.GetNumberOfTuples() > 0:
                        print VN.vtk_to_numpy(idxArr)

class ParallelCoordinates(SpreadsheetCell):
    """
    """
    my_namespace = 'views'
    name         = 'Parallel Coordinates View'
    
    _input_ports = [('stats',      Matrix, False)
                    ]
    
    def compute(self):
        """ compute() -> None        
        """
        stats      = Matrix() #None #self.getInputFromPort('stats')
        self.displayAndWait(ParallelCoordinatesWidget, (stats))

###############################################################################
class QCellToolBarShowLabels(QtGui.QAction):
    """
    QCellToolBarShowLabels is the action to show labels per instance.
    """
    def __init__(self, parent=None):
        """ QCellToolBarShowLabels(parent: QWidget)
                                         -> QCellToolBarExportTimeSeries
        Setup the image, status tip, etc. of the action
        """
        QtGui.QAction.__init__(self,
                               QtGui.QIcon(os.path.join( packagePath,  'icons/labels.png' )),
                               "&Show Labels",
                               parent)
        self.setStatusTip("Show labels per instance")
        
    def triggeredSlot(self, checked=False):
        cellWidget = self.toolBar.getSnappedWidget()
        cellWidget.showLabels = not cellWidget.showLabels
        cellWidget.updateContents()

class QProjectionToolBar(QCellToolBar):
    """
    QProjectionToolBar derives from QCellToolBar to give the ...
    a customizable toolbar
    """
    def createToolBar(self):
        """ createToolBar() -> None
        This will get call initially to add customizable widgets
        """
        QCellToolBar.createToolBar(self)
        self.appendAction(QCellToolBarShowLabels(self))
        
###############################################################################

class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

@Singleton
class CoordinationManager:
    """
    CoordinationManager is intended to receive selected element in a view, and
    update all the views registered
    """
    def __init__(self):
        self.modules = []
    
    def notifyModules(self, selectedIds):
        for mod in self.modules:
            mod.selectedIds = selectedIds;
            mod.updateContents();
        
    def register(self, module):
        self.modules.append(module)
    
    def unregister(self, module):
        self.modules.remove(module)


