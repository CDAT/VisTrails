from core.modules.vistrails_module import Module, NotCacheable
from core.modules.basic_modules import Integer, Float, String, List
from packages.NumSciPy.Array import NDArray
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from PyQt4 import QtGui
from matplotlib.widgets import  RectangleSelector
from packages.vtDV3D.DV3DCell import *

from core.bundles import py_import
try:
    mpl_dict = {'linux-ubuntu': 'python-matplotlib',
                'linux-fedora': 'python-matplotlib'}
    matplotlib = py_import('matplotlib', mpl_dict)
    matplotlib.use('Qt4Agg', warn=False)
    pylab = py_import('pylab', mpl_dict)
except Exception, e:
    debug.critical("Exception: %s" % e)
    
packagePath = os.path.dirname( __file__ )

################################################################################

class ProjectionWidget(QCellWidget):
    """ ProjectionWidget is a widget to show 2D projections. It has some interactive
    features like, show labels, selections, and synchronization.
    """
    
    def __init__(self, parent=None):
        """ ProjectionWidget(parent: QWidget) -> ProjectionWidget
        Initialize the widget with its central layout
        
        """
        QCellWidget.__init__(self, parent)
        centralLayout = QtGui.QVBoxLayout()
        self.setLayout(centralLayout)
        centralLayout.setMargin(0)
        centralLayout.setSpacing(0)
        
        self.figManager = None
        self.rectSelector = None
        self.showLabels = False
        self.inputPorts = None;
        
        self.toolBarType = QProjectionToolBar

    def updateContents(self, inputPorts=None):
        """ updateContents(inputPorts: tuple) -> None
        Update the widget contents based on the input data
        """
        if inputPorts is not None: self.inputPorts = inputPorts
        
        # draw in which canvas?
#        self.inputPorts = inputPorts;
        self.draw()
        newFigManager = pylab.get_current_fig_manager()
        
        if self.figManager != None:
            print 'removing widget'
            # Remove the old figure manager
            self.figManager.window.hide()
            self.layout().removeWidget(self.figManager.window)
            
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
                del self.figManager

        # Add the new one in
        self.layout().addWidget(newFigManager.window)

        # Save back the manager
        self.figManager = newFigManager
        self.update()
        
    def draw(self):
        (_matrix, title, _colors, labels) = self.inputPorts
        matrix = _matrix.array
        colors = _colors.array if _colors is None else 'b'
        
        # Update the new figure canvas
        fig = pylab.figure()
        
        pylab.setp(fig, facecolor='w')
        pylab.axis('off')
        pylab.get_current_fig_manager().toolbar.hide()
        
        pylab.title(title)
        pylab.scatter( matrix[:,0], matrix[:,1], 
                       c=colors, cmap=pylab.cm.Spectral, 
                       marker='o')
  
        print 'DRAWWWWW: ', self.showLabels
        if self.showLabels and labels is not None:
            for label, x, y in zip(labels, matrix[:, 0], matrix[:, 1]):
                pylab.annotate(
                    str(label), 
                    xy = (x, y), 
                    xytext = (5, 5),
                    textcoords = 'offset points',
                    bbox = dict(boxstyle = 'round,pad=0.2', fc = 'yellow', alpha = 0.5),
                )
        
        # selections
        self.rectSelector = RectangleSelector(pylab.gca(), 
                                              self.onselect, 
                                              drawtype='box', 
                                              rectprops=dict(alpha=0.4, facecolor='yellow')
                                             )
        self.rectSelector.set_active(True)

    def onselect(self, eclick, erelease):
        'eclick and erelease are matplotlib events at press and release'
        print ' startposition : (%f, %f)' % (eclick.xdata, eclick.ydata)
        print ' endposition   : (%f, %f)' % (erelease.xdata, erelease.ydata)
        print ' used button   : ', eclick.button
  


class ProjectionView(SpreadsheetCell):
    """
    """
    my_namespace = 'views'
    name         = '2D Projection view'
    
    _input_ports = [('matrix',    NDArray, False),
                    ('title',     String,  False),
                    ('colors',    NDArray, False),
                    ('labels',    List,    False),
                   ]

    def compute(self):
        """ compute() -> None        
        """
        matrix = self.getInputFromPort('matrix')
        title  = self.forceGetInputFromPort('title', '')
        colors = self.forceGetInputFromPort('colors', None)
        labels = self.forceGetInputFromPort('labels', None)
        
        self.displayAndWait(ProjectionWidget, (matrix, title, colors, labels))
            
#    def compute(self):
#        matrix = self.getInputFromPort('matrix').array
#        colors = self.getInputFromPort('colors').array if self.hasInputFromPort('colors') else 'b'
#            
#        
#        fig = pylab.figure()
#        pylab.setp(fig, facecolor='w')
#        pylab.axis('off')
#        pylab.get_current_fig_manager().toolbar.hide()
#        
#        pylab.title(self.forceGetInputFromPort('title', '2D - Projection'))
#        pylab.scatter( matrix[:,0], matrix[:,1], 
#                       c=colors, cmap=pylab.cm.Spectral, 
#                       marker='o')
#
#        # draw labels
#        if self.hasInputFromPort('labels'):
#            labels = self.getInputFromPort('labels')
#            for label, x, y in zip(labels, matrix[:, 0], matrix[:, 1]):
#                pylab.annotate(
#                    str(label), 
#                    xy = (x, y), 
#                    xytext = (5, 5),
#                    textcoords = 'offset points',
#                    bbox = dict(boxstyle = 'round,pad=0.2', fc = 'yellow', alpha = 0.5),
#                )
#        
#        self.setResult('source', '')

class parallelcoordinates(Module):
    """
    """
    pass

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
        
