from core.modules.vistrails_module import Module, NotCacheable
from core.modules.basic_modules import Integer, Float, String, List
from packages.NumSciPy.Array import NDArray

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

class ProjectionView(NotCacheable, Module):
    """
    """
    my_namespace = 'views'
    name         = '2D Projection view'
    
    _input_ports = [('matrix',    NDArray, False),
                    ('title',     String,  False),
                    ('colors',    NDArray, False),
                    ('labels',    List,    False),
                   ]
    _output_ports = [('source', '(edu.utah.sci.vistrails.basic:String)')]

    def compute(self):
        matrix = self.getInputFromPort('matrix').array
        colors = self.getInputFromPort('colors').array if self.hasInputFromPort('colors') else 'b'
            
        
        fig = pylab.figure()
        pylab.setp(fig, facecolor='w')
        pylab.axis('off')
        pylab.get_current_fig_manager().toolbar.hide()
        
        pylab.title(self.forceGetInputFromPort('title', '2D - Projection'))
        pylab.scatter( matrix[:,0], matrix[:,1], 
                       c=colors, cmap=pylab.cm.Spectral, 
                       marker='o')

        # draw labels
        if self.hasInputFromPort('labels'):
            labels = self.getInputFromPort('labels')
            for label, x, y in zip(labels, matrix[:, 0], matrix[:, 1]):
                pylab.annotate(
                    str(label), 
                    xy = (x, y), 
                    xytext = (5, 5),
                    textcoords = 'offset points',
                    bbox = dict(boxstyle = 'round,pad=0.2', fc = 'yellow', alpha = 0.5),
                )
        
        self.setResult('source', '')

class parallelcoordinates(Module):
    """
    """
    pass