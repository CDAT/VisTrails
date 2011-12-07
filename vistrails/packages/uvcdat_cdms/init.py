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
from widgets import GraphicsMethodConfigurationWidget
from core.modules.module_registry import get_module_registry
from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from core.utils import InstanceObject
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from packages.uvcdat.init import Variable, Plot

canvas = None

def expand_port_specs(port_specs, pkg_identifier=None):
    if pkg_identifier is None:
        pkg_identifier = identifier
    reg = get_module_registry()
    out_specs = []
    for port_spec in port_specs:
        if len(port_spec) == 2:
            out_specs.append((port_spec[0],
                              reg.expand_port_spec_string(port_spec[1],
                                                          pkg_identifier)))
        elif len(port_spec) == 3:
            out_specs.append((port_spec[0],
                              reg.expand_port_spec_string(port_spec[1],
                                                          pkg_identifier),
                              port_spec[2])) 
    return out_specs


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
    
    def to_python(self):
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
        return var
    
    @staticmethod
    def from_module(module):
        from pipeline_helper import CDMSPipelineHelper
        var = Variable.from_module(module)
        var.axes = CDMSPipelineHelper.get_fun_value_from_module(module, 'axes')
        var.axesOperations = CDMSPipelineHelper.get_fun_value_from_module(module, 'axesOperations')
        var.__class__ = CDMSVariable
        return var
        
    def compute(self):
        self.axes = self.forceGetInputFromPort("axes")
        self.axesOperations = self.forceGetInputFromPort("axesOperations")
        self.get_port_values()
        self.var = self.to_python()
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
                                      ("variable2", "CDMSVariable", True),
                                      ("graphicsMethodName", "basic:String"),
                                      ("template", "basic:String"),
                                      ('datawc_calendar', 'basic:String', True),
                                      ('datawc_timeunits', 'basic:String', True),
                                      ('datawc_x1', 'basic:String', True),
                                      ('datawc_x2', 'basic:String', True),
                                      ('datawc_y1', 'basic:String', True),
                                      ('datawc_y2', 'basic:String', True),
                                      ('xticlabels1', 'basic:String', True),
                                      ('xticlabels2', 'basic:String', True),
                                      ('yticlabels1', 'basic:String', True),
                                      ('yticlabels2', 'basic:String', True),
                                      ('xmtics1', 'basic:String', True),
                                      ('xmtics2', 'basic:String', True),
                                      ('ymtics1', 'basic:String', True),
                                      ('ymtics2', 'basic:String', True),
                                      ('projection', 'basic:String', True)])
    _output_ports = expand_port_specs([("self", "CDMSPlot")])

    gm_attributes = [ 'datawc_calendar', 'datawc_timeunits',
                      'datawc_x1', 'datawc_x2', 'datawc_y1', 'datawc_y2',
                      'xticlabels1', 'xticlabels2', 'yticlabels1', 'yticlabels2', 
                      'xmtics1', 'xmtics2', 'ymtics1', 'ymtics2', 'projection']
    
    plot_type = None

    def __init__(self):
        Plot.__init__(self)
        self.template = "starter"
        self.graphics_method_name = "default"
        self.kwargs = {}
        self.default_values = {}
        
    def compute(self):
        Plot.compute(self)
        self.graphics_method_name = \
                self.forceGetInputFromPort("graphicsMethodName", "default")
        #self.set_default_values()
        self.template = self.forceGetInputFromPort("template", "starter")
        
        if not self.hasInputFromPort('variable'):
            raise ModuleError(self, "'variable' is mandatory.")
        self.var = self.getInputFromPort('variable')
        
        self.var2 = None
        if self.hasInputFromPort('variable2'):
            self.var2 = self.getInputFromPort('variable2')
            
        for attr in self.gm_attributes:
            if self.hasInputFromPort(attr):
                setattr(self,attr,self.getInputFromPort(attr))

    def to_module(self, controller):
        module = Plot.to_module(self, controller, identifier)
        functions = []
        
        #only when graphics_method_name is different from default the user can
        #change the values of the properties
        if self.graphics_method_name != "default":
            functions.append(("graphicsMethodName", [self.graphicsMethodName]))
            for attr in self.gm_attributes:
                if getattr(self,attr) != self.default_values[attr]:
                    functions.append((attr, [getattr(self,attr)]))
        if self.template != "starter":
            functions.append(("template", [self.template]))
            
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        

    def set_default_values(self, gmName=None):
        self.default_values = {}
        if gmName is None:
            gmName = self.graphics_method_name
        if self.plot_type is not None:
            canvas = get_canvas()
            method_name = "get"+str(self.plot_type).lower()
            gm = getattr(canvas,method_name)(gmName)
            for attr in self.gm_attributes:
                setattr(self,attr,str(getattr(gm,attr)))
                self.default_values[attr] = str(getattr(gm,attr))
    
    @staticmethod
    def get_canvas_graphics_method( plotType, gmName):
        method_name = "get"+str(plotType).lower()
        return getattr(get_canvas(),method_name)(gmName)
    
    @classmethod    
    def get_initial_values(klass, gmName):
        cgm = CDMSPlot.get_canvas_graphics_method(klass.plot_type, gmName)
        attribs = {}
        for attr in klass.gm_attributes:
            attribs[attr] = str(getattr(cgm,attr))
        return InstanceObject(**attribs)
        
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
            args = [plot.var.var]
            if hasattr(plot, "var2") and plot.var2 is not None:
                args.append(plot.var2.var)
            args.append(plot.template)
            cgm = self.get_graphics_method(plot.plot_type, plot.graphics_method_name)
            if plot.graphics_method_name != 'default':
                for k in plot.gm_attributes:
                    if hasattr(plot,k):
                        if k in ['level_1', 'level_2', 'color_1',
                                 'color_2', 'legend', 'levels',
                                 'missing']:
                            setattr(cgm,k,eval(getattr(plot,k)))
                        else:
                            try:
                                setattr(cgm,k,eval(getattr(plot,k)))
                            except:
                                setattr(cgm,k,str(getattr(plot,k)))
            kwargs = plot.kwargs             
            self.canvas.plot(cgm,*args,**kwargs)

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

    def get_graphics_method(self, plotType, gmName):
        method_name = "get"+str(plotType).lower()
        return getattr(self.canvas,method_name)(gmName)
    
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

def get_input_ports(plot_type):
    if plot_type == "Boxfill":
        return expand_port_specs([('boxfill_type', 'basic:String', True),
                                  ('color_1', 'basic:String', True),
                                  ('color_2', 'basic:String', True),
                                  ('levels', 'basic:String', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:String', True),
                                  ('fillareaindices', 'basic:String', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('level_1', 'basic:String', True),
                                  ('level_2', 'basic:String', True),
                                  ('missing', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ])
    elif plot_type == "Isofill":
        return expand_port_specs([('levels', 'basic:String', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:String', True),
                                  ('fillareaindices', 'basic:String', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('missing', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Isoline":
        return expand_port_specs([('label', 'basic:String', True),
                                  ('levels', 'basic:String', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:String', True),
                                  ('fillareaindices', 'basic:String', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('level', 'basic:String', True),
                                  ('line', 'basic:String', True),
                                  ('linecolors', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ('linewidths', 'basic:String', True),
                                  ('text', 'basic:String', True),
                                  ('textcolors', 'basic:String', True),
                                  ('clockwise', 'basic:String', True),
                                  ('scale', 'basic:String', True),
                                  ('angle', 'basic:String', True),
                                  ('spacing', 'basic:String', True)
                                  ]) 
    elif plot_type == "Meshfill":
        return expand_port_specs([('levels', 'basic:String', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:String', True),
                                  ('fillareaindices', 'basic:String', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ('missing', 'basic:String', True),
                                  ('mesh', 'basic:String', True),
                                  ('wrap', 'basic:String', True)
                                  ]) 
    elif plot_type == "Outfill":
        return expand_port_specs([('outfill', 'basic:String', True),
                                  ('fillareacolor', 'basic:String', True),
                                  ('fillareaindex', 'basic:String', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Outline":
        return expand_port_specs([('outline', 'basic:String', True),
                                  ('linecolor', 'basic:String', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Scatter":
        return expand_port_specs([('markercolor', 'basic:String', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Vector":
        return expand_port_specs([('scale', 'basic:String', True),
                                  ('alignment', 'basic:String', True),
                                  ('type', 'basic:String', True),
                                  ('reference', 'basic:String', True),
                                  ('linecolor', 'basic:String', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "XvsY":
        return expand_port_specs([('linecolor', 'basic:String', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:String', True),
                                  ('markercolor', 'basic:String', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Xyvsy":
        return expand_port_specs([('linecolor', 'basic:String', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:String', True),
                                  ('markercolor', 'basic:String', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Yxvsx":
        return expand_port_specs([('linecolor', 'basic:String', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:String', True),
                                  ('markercolor', 'basic:String', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type=="Taylordiagram":
        ### TODO!!!!
        return []
    else:
        return []
def get_gm_attributes(plot_type):
    if plot_type == "Boxfill":
        return  ['boxfill_type', 'color_1', 'color_2' ,'datawc_calendar', 
                    'datawc_timeunits', 'datawc_x1', 'datawc_x2', 'datawc_y1', 
                    'datawc_y2', 'levels','ext_1', 'ext_2', 'fillareacolors', 
                    'fillareaindices', 'fillareastyle', 'legend', 'level_1', 
                    'level_2', 'missing', 'projection', 'xaxisconvert', 'xmtics1', 
                    'xmtics2', 'xticlabels1', 'xticlabels2', 'yaxisconvert', 
                    'ymtics1', 'ymtics2', 'yticlabels1', 'yticlabels2']
        
    elif plot_type == "Isofill":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'levels','ext_1', 'ext_2', 
                'fillareacolors', 'fillareaindices', 'fillareastyle', 'legend', 
                'missing', 'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
        
    elif plot_type == "Isoline":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'projection', 'xaxisconvert', 'xmtics1', 
                'xmtics2', 'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2', 'label', 'level', 'levels', 
                'line', 'linecolors','linewidths','text','textcolors','clockwise',
                'scale', 'angle','spacing']
    elif plot_type == "Meshfill":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'levels','ext_1', 'ext_2', 
                'fillareacolors', 'fillareaindices', 'fillareastyle', 'legend', 
                'missing', 'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2', 'mesh', 'wrap']
    elif plot_type == "Outfill":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'outfill',
                'fillareacolor', 'fillareaindex', 'fillareastyle',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Outline":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 'outline',
                'linecolor', 'line', 'linewidth',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Scatter":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2', 
                'markercolor', 'marker', 'markersize',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Vector":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','scale','alignment','type','reference',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "XvsY":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','markercolor', 'marker', 'markersize',
                'projection', 'xaxisconvert', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Xyvsy":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','markercolor', 'marker', 'markersize',
                'projection', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'yaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Yxvsx":
        return ['datawc_calendar', 'datawc_timeunits', 'datawc_x1', 'datawc_x2', 
                'datawc_y1', 'datawc_y2',
                'linecolor', 'line', 'linewidth','markercolor', 'marker', 'markersize',
                'projection', 'xmtics1', 'xmtics2',
                'xticlabels1', 'xticlabels2', 'xaxisconvert', 'ymtics1', 
                'ymtics2', 'yticlabels1', 'yticlabels2']
    elif plot_type == "Taylordiagram":
        return ['detail','max','quadrans',
                'skillValues','skillColors','skillDrawLabels','skillCoefficient',
                'referencevalue','arrowlength','arrowangle','arrowbase',
                'xmtics1', 'xmtics2', 'xticlabels1', 'xticlabels2',
                'ymtics1', 'ymtics2', 'yticlabels1', 'yticlabels2',
                'cmtics1', 'cticlabels1', 'Marker',
                ]
    
def get_canvas():
    global canvas
    if canvas is None:
        canvas = vcs.init()
    return canvas
    
for plot_type in ['Boxfill', 'Isofill', 'Isoline', 'Meshfill', 'Outfill', \
                  'Outline', 'Scatter', 'Taylordiagram', 'Vector', 'XvsY', \
                  'Xyvsy', 'Yxvsx']:
    def get_init_method():
        def __init__(self):
            CDMSPlot.__init__(self)
            #self.plot_type = pt
        return __init__
    klass = type('CDMS' + plot_type, (CDMSPlot,), 
                 {'__init__': get_init_method(),
                  'plot_type': plot_type,
                  '_input_ports': get_input_ports(plot_type),
                  'gm_attributes': get_gm_attributes(plot_type)})
    # print 'adding CDMS module', klass.__name__
    _modules.append((klass,{'configureWidgetType':GraphicsMethodConfigurationWidget}))
    
