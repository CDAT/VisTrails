from matrix import Matrix
from config_reader import ConfigReader, WriteVarsIntoDataFile, ReadData
from core.modules.module_registry import get_module_registry
from plots import Coordinator, Dendrogram, ParallelCoordinates, TaylorDiagram, SeriesPlot
from core import debug
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
_modules = [(Matrix,                {'namespace':Matrix.my_namespace,                'name':Matrix.name}),
            (ConfigReader,          {'namespace':ConfigReader.my_namespace,          'name':ConfigReader.name}),
            (WriteVarsIntoDataFile, {'namespace':WriteVarsIntoDataFile.my_namespace, 'name':WriteVarsIntoDataFile.name}),
            (ReadData,              {'namespace':ReadData.my_namespace,              'name':ReadData.name}),
            (SeriesPlot,            {'namespace':SeriesPlot.my_namespace,            'name':SeriesPlot.name}),
            (Dendrogram,            {'namespace':Dendrogram.my_namespace,            'name':Dendrogram.name}),
            (TaylorDiagram,         {'namespace':TaylorDiagram.my_namespace,         'name':TaylorDiagram.name}),
            (ParallelCoordinates,   {'namespace':ParallelCoordinates.my_namespace,   'name':ParallelCoordinates.name})
            ]

reg = get_module_registry()
reg.add_module(Coordinator)
reg.add_output_port(Coordinator, "self", Coordinator)