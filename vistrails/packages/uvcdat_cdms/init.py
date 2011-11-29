from PyQt4 import QtCore, QtGui

from cdatguiwrap import VCSQtManager
import vcs
import genutil
import cdutil
import cdms2
import time
import api
import re
import MV2

from info import identifier

from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from packages.uvcdat.init import Variable, Plot
from packages.uvcdat.init import expand_port_specs as _expand_port_specs

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    return _expand_port_specs(port_specs, pkg_identifier)

class CDMSVariable(Variable):
    _input_ports = expand_port_specs([("axes", "basic:String"),
                                      ("axesOperations", "basic:String")])
    _output_ports = expand_port_specs([("self", "CDMSVariable")])

    def __init__(self, filename=None, url=None, source=None, name=None, \
                     load=False, axes=None, axesOperations=None):
        Variable.__init__(self, filename, url, source, name, load)
        self.axes = axes
        self.axesOperations = axesOperations
        self.var = None

    def to_module(self, controller):
        # note that the correct module is returned because we use
        # self.__class__.__name__
        module = Variable.to_module(self, controller, identifier)
        functions = []
        if self.axes is not None:
            functions.append(("axes", [self.axes]))
        if self.axesOperations is not None:
            functions.append(("axesOperations", [self.axesOperations]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        

    def compute(self):
        self.axes = self.forceGetInputFromPort("axes")
        self.axesOperations = self.forceGetInputFromPort("axesOperations")
        self.get_port_values()
        if self.source:
            cdmsfile = self.source.var
        elif self.url:
            cdmsfile = cdms2.open(self.url)
        elif self.file:
            cdmsfile = cdms2.open(self.file)
        var = cdmsfile.__call__(self.name)
        if self.axes is not None:
            try:
                var = eval("var(%s)"% self.axes)
            except Exception, e:
                raise ModuleError(self, "Invalid 'axes' specification: %s" % \
                                      str(e))
        if self.axesOperations is not None:
            var = self.applyAxesOperations(var, self.axesOperations)

        self.var = var
        self.setResult("self", self)

    def applyAxesOperations(self, var, axesOperations):
        """ Apply axes operations to update the slab """
        try:
            axesOperations = eval(axesOperations)
        except:
            raise TypeError("Invalid string 'axesOperations'")

        for axis in list(axesOperations):
            if axesOperations[axis] == 'sum':
                var = cdutil.averager(var, axis="(%s)" % axis, weight='equal',
                                      action='sum')
            elif axesOperations[axis] == 'avg':
                var = cdutil.averager(var, axis="(%s)" % axis, weight='equal')
            elif axesOperations[axis] == 'wgt':
                var = cdutil.averager(var, axis="(%s)" % axis)
            elif axesOperations[axis] == 'gtm':
                var = genutil.statistics.geometricmean(var, axis="(%s)" % axis)
            elif axesOperations[axis] == 'std':
                var = genutil.statistics.std(var, axis="(%s)" % axis)
        return var

class CDMSPlot(Plot):
    _input_ports = expand_port_specs([("variable", "CDMSVariable"),
                                      ("graphicsMethod", "CDMSGraphicsMethod"),
                                      ("graphicsMethodName", "basic:String"),
                                      ("template", "basic:String")])
    _output_ports = expand_port_specs([("self", "CDMSPlot")])

    def __init__(self):
        Plot.__init__(self)
        self.template = "starter"
        self.plot_type = None
        self.graphics_method = None
        self.graphics_method_name = "default"
        self.kwargs = {}

    def compute(self):
        Plot.compute(self)
        self.graphics_method = self.forceGetInputFromPort("graphicsMethod")
        if not self.graphics_method:
            self.graphics_method_name = \
                self.forceGetInputFromPort("graphicsMethodName", "default")
        self.forceGetInputFromPort("template", "starter")

    def to_module(self, controller):
        module = Plot.to_module(self, controller, identifier)
        functions = []
        if self.graphics_method_name != "default":
            functions.append(("graphicsMethodName", [self.graphicsMethodName]))
        if self.template != "starter":
            functions.append(("template", [self.template]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        

class CDMSGraphicsMethod(Module):
    # FIXME fill this in
    pass

# class CDMSBoxfill(CDMSPlot):
#     def __init__(self):
#         CDMSPlot.__init__(self)
#         self.plot_type = 'Boxfill'

class CDMSCell(SpreadsheetCell):
    _input_ports = expand_port_specs([("plot", "CDMSPlot")])

    def compute(self):
        input_ports = []
        for plot in self.getInputListFromPort('plot'):
            input_ports.append(plot)
        self.cellWidget = self.displayAndWait(QCDATWidget, input_ports)

class QCDATWidget(QCellWidget):
    """ QCDATWidget is the spreadsheet cell widget where the plots are displayed.
    The widget interacts with the underlying C++, VCSQtManager through SIP.
    This enables QCDATWidget to get a reference to the Qt MainWindow that the
    plot will be displayed in and send signals (events) to that window widget.
    windowIndex is an index to the VCSQtManager window array so we can 
    communicate with the C++ Qt windows which the plots show up in.  If this 
    number is no longer consistent with the number of C++ Qt windows due to 
    adding or removing vcs.init() calls, then when you plot, it will plot into a
    separate window instead of in the cell and may crash.
    vcdat already creates 5 canvas objects
    
    """
    startIndex = 1 #this should be the current number of canvas objects created 
    maxIndex = 6
    usedIndexes = []
    
    def __init__(self, parent=None):
        QCellWidget.__init__(self, parent)        
        self.window = None
        self.canvas =  None
        self.windowId = -1
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout) 
         
    def createCanvas(self):
        windowIndex = self.startIndex
        while (windowIndex in QCDATWidget.usedIndexes and 
                   windowIndex <= QCDATWidget.maxIndex):
            windowIndex += 1
        if windowIndex > QCDATWidget.maxIndex:
            raise ModuleError(self, "Maximum number of vcs.Canvas objects achieved.\
Please delete unused CDAT Cells in the spreadsheet.")
        else:
            print "using canvas ", windowIndex
            if windowIndex > len(vcs.canvaslist):
                self.canvas = vcs.init()
            else:
                self.canvas = vcs.canvaslist[windowIndex-1]
            self.windowId = windowIndex
            QCDATWidget.usedIndexes.append(self.windowId)
             
    def updateContents(self, inputPorts):
        """ Get the vcs canvas, setup the cell's layout, and plot """        
        spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
        spreadsheetWindow.setUpdatesEnabled(False)

        # Set the canvas
        # if inputPorts[0] is not None:
        #     self.canvas = inputPorts[0]
        if self.canvas is None:
            try:
                self.createCanvas()
            except ModuleError, e:
                spreadsheetWindow.setUpdatesEnabled(True)
                raise e
        #print self.windowId, self.canvas
        if self.window is not None:
            self.layout().removeWidget(self.window)
            
        self.window = VCSQtManager.window(self.windowId)
        self.layout().addWidget(self.window)
        self.window.setVisible(True)    
        # Place the mainwindow that the plot will be displayed in, into this
        # cell widget's layout
           
        self.canvas.clear()
        # Plot
        for plot in inputPorts:
            # print "PLOT TYPE:", plot.plot_type
            args = [plot.var, plot.template, plot.plot_type, 
                    plot.graphics_method_name]
            kwargs = plot.kwargs
            self.canvas.plot(*args, **kwargs)

        # if len(inputPorts) > 3:
        #     gm = inputPorts[1]
        #     args = inputPorts[2]
        #     kwargs = inputPorts[3]
        #     if gm is not None:
        #         if isinstance(gm, Gfb):
        #             cgm = self.canvas.getboxfill(gm._name)
        #             for (k,v) in gm.options.iteritems():
        #                 setattr(cgm,k,v)
        #     self.canvas.plot(*args, **kwargs)

        spreadsheetWindow.setUpdatesEnabled(True)

    def deleteLater(self):
        """ deleteLater() -> None        
        Make sure to free render window resource when
        deallocating. Overriding PyQt deleteLater to free up
        resources
        """
        #we need to re-parent self.window or it will be deleted together with
        #this widget. The immediate parent is also deleted, so we will set to
        # parent of the parent widget
        if self.window is not None:
            self.window.setParent(self.parent().parent())
            self.window.setVisible(False)
        self.canvas = None
        self.window = None
        
        QCDATWidget.usedIndexes.remove(self.windowId)
        QCellWidget.deleteLater(self)    


_modules = [CDMSVariable, CDMSPlot, CDMSGraphicsMethod, CDMSCell]

for plot_type in ['Boxfill', 'Isofill', 'Isoline', 'Meshfill', 'Outfill', \
                      'Outline', 'Scatter', 'Taylordiagram', 'Vector', 'XvsY', \
                      'Xyvsy', 'Yxvsx']:
    def get_init_method(pt):
        def __init__(self):
            CDMSPlot.__init__(self)
            self.plot_type = pt
        return __init__
    klass = type('CDMS' + plot_type, (CDMSPlot,), 
                 {'__init__': get_init_method(plot_type)})
    # print 'adding CDMS module', klass.__name__
    _modules.append(klass)
    
