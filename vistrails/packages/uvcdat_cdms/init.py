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
import os

from info import identifier
from widgets import GraphicsMethodConfigurationWidget
from core.modules.module_registry import get_module_registry
from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from core.utils import InstanceObject
from packages.spreadsheet.basic_widgets import SpreadsheetCell
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
import packages.spreadsheet.celltoolbar_rc
from packages.uvcdat.init import Variable, Plot

canvas = None
original_gm_attributes = {}

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
    
    def to_python_script(self, include_imports=False, ident=""):
        text = ''
        if include_imports:
            text += ident + "import cdms2, cdutil, genutil\n"
        if self.source:
            cdmsfile = self.source.var
        elif self.url:
            text += ident + "cdmsfile = cdms2.open('%s')\n"%self.url
        elif self.file:
            text += ident + "cdmsfile = cdms2.open('%s')\n"%self.file
            
        text += ident + "%s = cdmsfile('%s')\n"%(self.name, self.name)
        if self.axes is not None:
            text += ident + "%s = %s(%s)\n"% (self.name, self.name, self.axes)
        if self.axesOperations is not None:
            text += ident + "axesOperations = eval(%s)\n"%self.axesOperations
            text += ident + "for axis in list(axesOperations):\n"
            text += ident + "    if axesOperations[axis] == 'sum':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal', action='sum')\n"% (self.name, self.name) 
            text += ident + "    elif axesOperations[axis] == 'avg':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis, weight='equal')\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'wgt':\n"
            text += ident + "        %s = cdutil.averager(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'gtm':\n"
            text += ident + "        %s = genutil.statistics.geometricmean(var, axis='(%%s)'%%axis)\n"% (self.name, self.name)
            text += ident + "    elif axesOperations[axis] == 'std':\n"
            text += ident + "        %s = genutil.statistics.std(%s, axis='(%%s)'%%axis)\n"% (self.name, self.name)
        return text
    
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

    @staticmethod
    def applyAxesOperations(var, axesOperations):
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

class CDMSVariableOperation(Module):
    pass

class CDMSUnaryVariableOperation(CDMSVariableOperation):
    _input_ports = expand_port_specs([("input_var", "CDMSVariable"),
                                      ("varname", "basic:String"),
                                      ("python_command", "basic:String")
                                      ])
    _output_ports = expand_port_specs([("output_var", "CDMSVariable")])
    
    def to_python(self):
        self.python_command = self.python_command.replace(self.var.name, "self.var.var")
        var = eval(self.python_command)
        return var
    
    def to_python_script(self, ident=""):
        text = ident + "%s = %s\n"%(self.varname,
                                    self.python_command)
        return text
    
    def compute(self):
        if not self.hasInputFromPort('input_var'):
            raise ModuleError(self, "'input_var' is mandatory.")
        if not self.hasInputFromPort("varname"):
            raise ModuleError(self, "'varname' is mandatory.")
        if not self.hasInputFromPort("python_command"):
            raise ModuleError(self, "'python_command' is mandatory.")
        self.var = self.getInputFromPort('input_var')
        self.varname = self.getInputFromPort("varname")
        self.python_command = self.getInputFromPort("python_command")
        self.outvar = CDMSVariable(filename=None,name=self.varname)
        self.outvar.var = self.to_python()
        self.setResult("output_var", self.outvar)
    
    @staticmethod
    def from_module(module):
        from pipeline_helper import CDMSPipelineHelper
        op = CDMSUnaryVariableOperation()
        op.varname = CDMSPipelineHelper.get_fun_value_from_module(module, 'varname')
        op.python_command = CDMSPipelineHelper.get_fun_value_from_module(module, 'python_command')
        return op
        
    def to_module(self, controller, pkg_identifier=None):
        reg = get_module_registry()
        if pkg_identifier is None:
            pkg_identifier = identifier
        module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name(pkg_identifier, self.__class__.__name__))
        functions = []
        if self.varname is not None:
            functions.append(("varname", [self.name]))
        if self.python_command is not None:
            functions.append(("python_command", [self.python_command]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module        
            
class CDMSBinaryVariableOperation(CDMSVariableOperation):
    _input_ports = expand_port_specs([("input_var1", "CDMSVariable"),
                                      ("input_var2", "CDMSVariable"),
                                      ("varname", "basic:String"),
                                      ("python_command", "basic:String")
                                      ])
    _output_ports = expand_port_specs([("output_var", "CDMSVariable")])
    
    def compute(self):
        if not self.hasInputFromPort('input_var1'):
            raise ModuleError(self, "'input_var1' is mandatory.")
        
        if not self.hasInputFromPort('input_var2'):
            raise ModuleError(self, "'input_var2' is mandatory.")
        
        if not self.hasInputFromPort("varname"):
            raise ModuleError(self, "'varname' is mandatory.")
        
        if not self.hasInputFromPort("python_command"):
            raise ModuleError(self, "'python_command' is mandatory.")
        
        self.var1 = self.getInputFromPort('input_var1')
        self.var2 = self.getInputFromPort('input_var2')
        self.varname = self.getInputFromPort("varname")
        self.python_command = self.getInputFromPort("python_command")
        self.outvar = CDMSVariable(filename=None,name=self.varname)
        self.outvar.var = self.to_python()
        self.setResult("output_var", self.outvar)
        
    def to_python(self):
        self.python_command = self.python_command.replace(self.var1.name, "self.var1.var")
        self.python_command = self.python_command.replace(self.var2.name, "self.var2.var")
        var = eval(self.python_command)
        return var
        
    def to_python_script(self, ident=""):
        text = ident + "%s = %s\n"%(self.varname,
                                    self.python_command)
        return text
    
    @staticmethod
    def from_module(module):
        from pipeline_helper import CDMSPipelineHelper
        op = CDMSBinaryVariableOperation()
        op.varname = CDMSPipelineHelper.get_fun_value_from_module(module, 'varname')
        op.python_command = CDMSPipelineHelper.get_fun_value_from_module(module, 'python_command')
        return op
    
    def to_module(self, controller, pkg_identifier=None):
        reg = get_module_registry()
        if pkg_identifier is None:
            pkg_identifier = identifier
        module = controller.create_module_from_descriptor(
            reg.get_descriptor_by_name(pkg_identifier, self.__class__.__name__))
        functions = []
        if self.varname is not None:
            functions.append(("varname", [self.name]))
        if self.python_command is not None:
            functions.append(("python_command", [self.python_command]))
        functions = controller.create_functions(module, functions)
        for f in functions:
            module.add_function(f)
        return module
        
        
class CDMSPlot(Plot, NotCacheable):
    _input_ports = expand_port_specs([("variable", "CDMSVariable"),
                                      ("variable2", "CDMSVariable", True),
                                      ("graphicsMethodName", "basic:String"),
                                      ("template", "basic:String"),
                                      ('datawc_calendar', 'basic:Integer', True),
                                      ('datawc_timeunits', 'basic:String', True),
                                      ('datawc_x1', 'basic:Float', True),
                                      ('datawc_x2', 'basic:Float', True),
                                      ('datawc_y1', 'basic:Float', True),
                                      ('datawc_y2', 'basic:Float', True),
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
        NotCacheable.__init__(self)
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
    
    @classmethod
    def from_module(klass, module):
        from pipeline_helper import CDMSPipelineHelper
        plot = klass()
        plot.graphics_method_name = CDMSPipelineHelper.get_graphics_method_name_from_module(module)
        for attr in plot.gm_attributes:
            setattr(plot,attr, CDMSPipelineHelper.get_value_from_function(module, attr))
        plot.template = CDMSPipelineHelper.get_template_name_from_module(module)
        return plot

    def set_default_values(self, gmName=None):
        self.default_values = {}
        if gmName is None:
            gmName = self.graphics_method_name
        if self.plot_type is not None:
            canvas = get_canvas()
            method_name = "get"+str(self.plot_type).lower()
            gm = getattr(canvas,method_name)(gmName)
            for attr in self.gm_attributes:
                setattr(self,attr,getattr(gm,attr))
                self.default_values[attr] = getattr(gm,attr)
    
    @staticmethod
    def get_canvas_graphics_method( plotType, gmName):
        method_name = "get"+str(plotType).lower()
        return getattr(get_canvas(),method_name)(gmName)
    
    @classmethod    
    def get_initial_values(klass, gmName):
        global original_gm_attributes
        return original_gm_attributes[klass.plot_type][gmName]
#        cgm = CDMSPlot.get_canvas_graphics_method(klass.plot_type, gmName)
#        attribs = {}
#        for attr in klass.gm_attributes:
#            attribs[attr] = getattr(cgm,attr)
#        return InstanceObject(**attribs)
      
class CDMSTDMarker(Module):
    _input_ports = expand_port_specs([("status", "basic:List", True),
                                      ("line", "basic:List", True),
                                      ("id", "basic:List", True),
                                      ("id_size", "basic:List", True),
                                      ("id_color", "basic:List", True),
                                      ("id_font", "basic:List", True),
                                      ("symbol", "basic:List", True),
                                      ("color", "basic:List", True),
                                      ("size", "basic:List", True),
                                      ("xoffset", "basic:List", True),
                                      ("yoffset", "basic:List", True),
                                      ("linecolor", "basic:List", True),
                                      ("line_size", "basic:List", True),
                                      ("line_type", "basic:List", True)])
    _output_ports = expand_port_specs([("self", "CDMSTDMarker")])

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
    startIndex = 2 #this should be the current number of canvas objects created 
    maxIndex = 7
    usedIndexes = []
    
    def __init__(self, parent=None):
        QCellWidget.__init__(self, parent)
        self.toolBarType = QCDATWidgetToolBar        
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
                        if k in ['legend']:
                            setattr(cgm,k,eval(getattr(plot,k)))
                        else:
                            setattr(cgm,k,getattr(plot,k))
                        #print k, " = ", getattr(cgm,k)
                            
            kwargs = plot.kwargs             
            self.canvas.plot(cgm,*args,**kwargs)

        spreadsheetWindow.setUpdatesEnabled(True)
        self.update()
        
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
        
    def dumpToFile(self, filename):
        """ dumpToFile(filename: str, dump_as_pdf: bool) -> None
        Dumps itself as an image to a file, calling grabWindowPixmap """
        self.saveToPNG(filename)
        
    def saveToPNG(self, filename):
        """ saveToPNG(filename: str) -> bool
        Save the current widget contents to an image file
        
        """
        
        self.canvas.png(filename)
        
    def saveToPDF(self, filename):
        """ saveToPDF(filename: str) -> bool
        Save the current widget contents to a pdf file
        
        """   
        self.canvas.pdf(filename, width=11.5)
        
    def exportToFile(self):
        file = QtGui.QFileDialog.getSaveFileName(
                self, "Select a File to Export the Plot",
                ".", "Images (*.png *.gif);;PDF file (*.pdf);;SVG file (*.svg)")
        if not file.isNull():
            filename = str(file)
            (_,ext) = os.path.splitext(filename)
            if  ext.upper() == '.PDF':
                self.canvas.pdf(filename, width=11.5)
            elif ext.upper() == ".PNG":
                self.canvas.png(filename, width=11.5)
            elif ext.upper() == ".SVG":
                self.canvas.svg(filename, width=11.5)
            elif ext.upper() == ".GIF":
                self.canvas.gif(filename, width=11.5)
        
class QCDATWidgetToolBar(QCellToolBar):
    """
    QCDATWidgetToolBar derives from QCellToolBar to give CDMSCell
    a customizable toolbar
    
    """
    def createToolBar(self):
        """ createToolBar() -> None
        This will get call initially to add customizable widgets
        
        """
        self.appendAction(QCDATWidgetExport(self))
        
class QCDATWidgetExport(QtGui.QAction):
    """
    QCDATWidgetExport is the action to export the plot 
    of the current cell to a file

    """
    def __init__(self, parent=None):
        """ QCDATWidgetExport(icon: QIcon, parent: QWidget)
                                   -> QCDATWidgetExport
        Setup the image, status tip, etc. of the action
        
        """
        QtGui.QAction.__init__(self,
                               QtGui.QIcon(":/images/file_save.png"),
                               "Export the current plot as an image",
                               parent)
        self.setStatusTip("Export the current plot as an image")

    def triggeredSlot(self, checked=False):
        """ toggledSlot(checked: boolean) -> None
        Execute the action when the button is clicked
        
        """
        
        cellWidget = self.toolBar.getSnappedWidget()
        cellWidget.exportToFile()

    def updateStatus(self, info):
        """ updateStatus(info: tuple) -> None
        Updates the status of the button based on the input info
        
        """
        from api import _app
        (sheet, row, col, cellWidget) = info
        selectedCells = sorted(sheet.getSelectedLocations())

        # Will not show up if there is no cell selected  
        proj_controller = _app.uvcdatWindow.get_current_project_controller()
        sheetName = sheet.getSheetName()        
        if (len(selectedCells)==1 and 
            proj_controller.is_cell_ready(sheetName,row,col)):
                self.setVisible(True)
        else:
            self.setVisible(False)

_modules = [CDMSVariable, CDMSPlot, CDMSCell, CDMSTDMarker, CDMSVariableOperation,
            CDMSUnaryVariableOperation, CDMSBinaryVariableOperation]

def get_input_ports(plot_type):
    if plot_type == "Boxfill":
        return expand_port_specs([('boxfill_type', 'basic:String', True),
                                  ('color_1', 'basic:Integer', True),
                                  ('color_2', 'basic:Integer', True),
                                  ('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:List', True),
                                  ('fillareaindices', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('level_1', 'basic:Float', True),
                                  ('level_2', 'basic:Float', True),
                                  ('missing', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ])
    elif plot_type == "Isofill":
        return expand_port_specs([('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:List', True),
                                  ('fillareaindices', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('missing', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Isoline":
        return expand_port_specs([('label', 'basic:String', True),
                                  ('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('level', 'basic:List', True),
                                  ('line', 'basic:List', True),
                                  ('linecolors', 'basic:List', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ('linewidths', 'basic:List', True),
                                  ('text', 'basic:List', True),
                                  ('textcolors', 'basic:List', True),
                                  ('clockwise', 'basic:List', True),
                                  ('scale', 'basic:List', True),
                                  ('angle', 'basic:List', True),
                                  ('spacing', 'basic:List', True)
                                  ]) 
    elif plot_type == "Meshfill":
        return expand_port_specs([('levels', 'basic:List', True),
                                  ('ext_1', 'basic:String', True),
                                  ('ext_2', 'basic:String', True),
                                  ('fillareacolors', 'basic:List', True),
                                  ('fillareaindices', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('legend', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ('missing', 'basic:Integer', True),
                                  ('mesh', 'basic:String', True),
                                  ('wrap', 'basic:List', True)
                                  ]) 
    elif plot_type == "Outfill":
        return expand_port_specs([('outfill', 'basic:List', True),
                                  ('fillareacolor', 'basic:List', True),
                                  ('fillareaindex', 'basic:List', True),
                                  ('fillareastyle', 'basic:String', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Outline":
        return expand_port_specs([('outline', 'basic:List', True),
                                  ('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Scatter":
        return expand_port_specs([('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Vector":
        return expand_port_specs([('scale', 'basic:Float', True),
                                  ('alignment', 'basic:String', True),
                                  ('type', 'basic:String', True),
                                  ('reference', 'basic:Float', True),
                                  ('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "XvsY":
        return expand_port_specs([('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
                                  ('xaxisconvert', 'basic:String', True),
                                  ('yaxisconvert', 'basic:String', True),
                                  ]) 
    elif plot_type == "Xyvsy":
        return expand_port_specs([('linecolor', 'basic:Integer', True),
                                  ('line', 'basic:String', True),
                                  ('linewidth', 'basic:Integer', True),
                                  ('markercolor', 'basic:Integer', True),
                                  ('marker', 'basic:String', True),
                                  ('markersize', 'basic:Integer', True),
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
        return expand_port_specs([('detail', 'basic:Integer', True),
                                  ('max', 'basic:String', True),
                                  ('quadrans', 'basic:Integer', True),
                                  ('skillColor', 'basic:Integer', True),
                                  ('skillValues', 'basic:List', True),
                                  ('skillDrawLabels', 'basic:String', True),
                                  ('skillCoefficient', 'basic:List', True),
                                  ('referencevalue', 'basic:Float', True),
                                  ('arrowlength', 'basic:Float', True),
                                  ('arrowangle', 'basic:Float', True),
                                  ('arrowbase', 'basic:Float', True),
                                  ('cmtics1', 'basic:String', True),
                                  ('cticlabels1', 'basic:String', True),
                                  ('Marker', 'CDMSTDMarker', True),
                                  ]) 
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
                'skillValues','skillColor','skillDrawLabels','skillCoefficient',
                'referencevalue','arrowlength','arrowangle','arrowbase',
                'xmtics1', 'xticlabels1', 'ymtics1', 
                'yticlabels1','cmtics1', 'cticlabels1', 'Marker']
    
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
    def get_is_cacheable_method():
        def is_cacheable(self):
            return False
        return is_cacheable
    
    klass = type('CDMS' + plot_type, (CDMSPlot,), 
                 {'__init__': get_init_method(),
                  'plot_type': plot_type,
                  '_input_ports': get_input_ports(plot_type),
                  'gm_attributes': get_gm_attributes(plot_type),
                  'is_cacheable': get_is_cacheable_method()})
    # print 'adding CDMS module', klass.__name__
    _modules.append((klass,{'configureWidgetType':GraphicsMethodConfigurationWidget}))

def initialize(*args, **keywords):
    global original_gm_attributes
    for plot_type in ['Boxfill', 'Isofill', 'Isoline', 'Meshfill', 'Outfill', \
                  'Outline', 'Scatter', 'Taylordiagram', 'Vector', 'XvsY', \
                  'Xyvsy', 'Yxvsx']:
        canvas = get_canvas()
        method_name = "get"+plot_type.lower()
        attributes = get_gm_attributes(plot_type)
        gms = canvas.listelements(str(plot_type).lower())
        original_gm_attributes[plot_type] = {}
        for gmname in gms:
            gm = getattr(canvas,method_name)(gmname)
            attrs = {}
            for attr in attributes:
                attrs[attr] = getattr(gm,attr)
            original_gm_attributes[plot_type][gmname] = InstanceObject(**attrs)
   
    