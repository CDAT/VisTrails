from core.modules.basic_modules import String
from packages.scikit_learn.matrix import Matrix
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from PyQt4 import QtGui
from matplotlib.widgets import  RectangleSelector
from matplotlib.transforms import Bbox
import numpy as np
import os

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
        circleSize = np.ones(len(self.matrix.ids))
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
    
    def updateSelection(self, selectedIds):
        self.selectedIds = selectedIds
        self.updateContents();
        
    def onselect(self, eclick, erelease):
        left, bottom = min(eclick.xdata, erelease.xdata), min(eclick.ydata, erelease.ydata)
        right, top = max(eclick.xdata, erelease.xdata), max(eclick.ydata, erelease.ydata)
        region = Bbox.from_extents(left, bottom, right, top)
        
        selectedIds = []
        for (xy, idd) in zip(self.matrix.values, self.matrix.ids):
            if region.contains(xy[0], xy[1]):
                selectedIds.append(idd)
        self.updateSelection(selectedIds)
        CoordinationManager.Instance().notifyModules(self, selectedIds)

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
    update all the registered views
    """
    def __init__(self):
        self.modules = []
    
    def notifyModules(self, caller, selectedIds):
        for mod in self.modules:
            if mod is not caller:
                mod.updateSelection(selectedIds);
        
    def register(self, module):
        self.modules.append(module)
    
    def unregister(self, module):
        self.modules.remove(module)


