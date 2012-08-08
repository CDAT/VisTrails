import core.modules
import core.modules.module_registry
from core.modules.basic_modules import File, String, Boolean, List
from packages.NumSciPy.Array import NDArray
from core.modules.vistrails_module import Module, NotCacheable, InvalidOutput
from core import debug
from config_reader import ConfigReader, WriteVarsIntoDataFile
import taylor_diagram
import time
import urllib
from packages.scikit_learn.views import LinkedWidget, CoordinationManager
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from matplotlib.transforms import Bbox
import numpy as np
import string


from core.bundles import py_import
try:
    mpl_dict = {'linux-ubuntu': 'python-matplotlib',
                'linux-fedora': 'python-matplotlib'}
    matplotlib = py_import('matplotlib', mpl_dict)
    matplotlib.use('Qt4Agg', warn=False)
    pylab = py_import('pylab', mpl_dict)
except Exception, e:
    debug.critical("Exception: %s" % e)

################################################################################
class ORNLPlotLines(Module):
    _input_ports = [('variables',List),
                    ('title',    String),
                    ('xlabel',   String),
                    ('ylabel',   String)]
    _output_ports = [('source',  String)]

    
    def compute(self):
        fig = pylab.figure()
        pylab.setp(fig, facecolor='w')
        if self.hasInputFromPort('title'):
            pylab.title(self.getInputFromPort('title'))
        if self.hasInputFromPort('xlabel'):
            pylab.xlabel(self.getInputFromPort('xlabel'))
        if self.hasInputFromPort('ylabel'):
            pylab.ylabel(self.getInputFromPort('ylabel'))
        if self.hasInputFromPort('bins'):
            bins = self.getInputFromPort('bins')
        

        vars = self.getInputFromPort('variables')
        for var in vars:
            pylab.plot(var.var.data)
        
        pylab.get_current_fig_manager().toolbar.hide()
        self.setResult('source', "")

################################################################################
class TaylorDiagramWidget(LinkedWidget):
    def __init__(self, parent=None):
        LinkedWidget.__init__(self, parent)
        
        self.markers = ['o','D','h','H','_','8','p',',','+','.','s','*',
                        'd',3,0,1,2,7,4,5,6,'1','3','4','2','v','<','>','^','|','x']
        self.cm = pylab.cm.Spectral
        
    def draw(self, fig):
        (_stats, _ids, labels, _colors, title, showLegend) = self.inputPorts
        stats    = _stats.array
        self.ids = _ids.array if _ids is not None else np.linspace(1, stats.shape[0], stats.shape[0])
        colors   = _colors.array if _colors is not None else np.ones(stats.shape[0])

        
        self.Xs = stats[:,0]*stats[:,1]
        self.Ys = stats[:,0]*np.sin(np.arccos(stats[:,1]))
        
        pylab.clf()
        label = labels[0] if labels is not None else 'Reference'
        dia = taylor_diagram.TaylorDiagram(stats[0][0], stats[0][1], fig=fig, label=label)
        dia.samplePoints[0].set_color('r')  # Mark reference point as a red star
        if self.ids[0] in self.selectedIds: dia.samplePoints[0].set_markeredgewidth(3)
        
        # add models to Taylor diagram
        for i, (_id, stddev,corrcoef) in enumerate(zip(self.ids[1:], stats[1:,0], stats[1:,1])):
            label = labels[i+1] if labels is not None else ''
            size = 3 if _id in self.selectedIds else 1
            dia.add_sample(stddev, corrcoef,
                           marker=self.markers[i],
                           ls='',
                           mfc=self.cm(colors[i]),
                           mew = size,
                           label=label
                           )

        # Add grid
        dia.add_grid()

        # Add RMS contours, and label them
        contours = dia.add_contours(levels=5, colors='0.5') # 5 levels in grey
        pylab.clabel(contours, inline=1, fontsize=10, fmt='%.1f')

        # Add a figure legend and title
        if labels is not None:
            fig.legend(dia.samplePoints,
                       [ p.get_label() for p in dia.samplePoints ],
                       numpoints=1, prop=dict(size='small'), loc='upper right')
        fig.suptitle(title, size='x-large') # Figure title
        self.figManager.canvas.draw()
    
    def onselect(self, eclick, erelease):
        left, bottom = min(eclick.xdata, erelease.xdata), min(eclick.ydata, erelease.ydata)
        right, top = max(eclick.xdata, erelease.xdata), max(eclick.ydata, erelease.ydata)
        region = Bbox.from_extents(left, bottom, right, top)
        
        selectedIds = []
        for (x, y, idd) in zip(self.Xs, self.Ys, self.ids):
            if region.contains(x, y):
                selectedIds.append(idd)
        CoordinationManager.Instance().notifyModules(selectedIds)


class TaylorDiagram(SpreadsheetCell):
    """
    """
    _input_ports = [('stats',      NDArray, False),
                    ('ids',        NDArray, False),
                    ('labels',     List,    False),
                    ('colors',     NDArray, False),
                    ('title',      String,  False),
                    ('showLegend', Boolean, False),
                    ]
    
    def compute(self):
        """ compute() -> None        
        """
        stats      = self.getInputFromPort('stats')
        ids        = self.forceGetInputFromPort('ids', None)
        labels     = self.forceGetInputFromPort('labels', None)
        colors     = self.forceGetInputFromPort('colors', None)
        title      = self.forceGetInputFromPort('title', '')
        showLegend = self.forceGetInputFromPort('showLegend', True)
        self.displayAndWait(TaylorDiagramWidget, (stats, ids, labels, colors, title, showLegend))

_modules = [ConfigReader, WriteVarsIntoDataFile, ORNLPlotLines, TaylorDiagram]

