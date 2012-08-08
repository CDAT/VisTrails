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
    _input_ports = [('variables', List),
                    ('title',     String),
                    ('xlabel',    String),
                    ('ylabel',    String)]
    _output_ports = [('source',   String)]

    
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


class TaylorDiagram(Module):
    _input_ports = [('stats',      NDArray),
                    ('title',      String),
                    ('showLegend', Boolean)]
    _output_ports = [('source',    String)]
    
    def compute(self):
        stats = self.getInputFromPort('stats').array
        title = self.forceGetInputFromPort('title', '')
        
        fig = pylab.figure()
        pylab.setp(fig, facecolor='w')
        pylab.get_current_fig_manager().toolbar.hide()

        dia = taylor_diagram.TaylorDiagram(stats[0][0], stats[0][1], fig=fig, label='')
        
        # add models to Taylor diagram
        for i, (stddev,corrcoef) in enumerate(zip(stats[1:,0], stats[1:,1])):
            dia.add_sample(stddev, corrcoef,
                           marker='$%d$' % (i+1),
                           ms=10, ls='',
                           mfc='k', mec='k')

        # Add grid
        dia.add_grid()

        # Add RMS contours, and label them
        contours = dia.add_contours(levels=5, colors='0.5') # 5 levels in grey
        pylab.clabel(contours, inline=1, fontsize=10, fmt='%.1f')

        # Add a figure legend and title
        fig.legend(dia.samplePoints,
                   [ p.get_label() for p in dia.samplePoints ],
                   numpoints=1, prop=dict(size='small'), loc='upper right')
        fig.suptitle("Taylor diagram", size='x-large') # Figure title
        
        self.setResult('source', "")
    
################################################################################

_modules = [ConfigReader, WriteVarsIntoDataFile, ORNLPlotLines, TaylorDiagram]

