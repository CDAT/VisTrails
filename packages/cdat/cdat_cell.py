from PyQt4 import QtCore, QtGui
from core.modules.vistrails_module import Module, ModuleError, NotCacheable
from core.modules.basic_modules import Constant
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_cell import QCellWidget, QCellToolBar
from packages.spreadsheet.basic_widgets import SpreadsheetCell, CellLocation
from packages.spreadsheet.spreadsheet_event import DisplayCellEvent
from cdatguiwrap import VCSQtManager
import vcs
import genutil
import cdutil
import time
import api
import re
import MV2

""" This file contains all of the classes related to the Vistrails Modules (the
boxes).  Eventually Variable and GraphicsMethod should be replaced by generating
the proper graphics method, cdms2, MV2, etc... modules """

class Variable(Module):
    """ Get the updated transient variable """
    
    def compute(self):
        # *** IMPORTANT ***
        # Once someone figures out how to pass the tvariable object, to this
        # module none of the computation in this method is necessary 
        
        # Check ports
#        if not self.hasInputFromPort('cdmsfile'):
#            raise ModuleError(self, "'cdmsfile' is mandatory.")
#        if not self.hasInputFromPort('id'):
#            raise ModuleError(self, "'id' is mandatory.")

        # Get input from ports
        if self.hasInputFromPort('inputVariable'):
            var = self.getInputFromPort('inputVariable')
        else:    
            if self.hasInputFromPort('cdmsfile'):
                cdmsfile = self.getInputFromPort('cdmsfile')
            if self.hasInputFromPort('id'):
                id = self.getInputFromPort('id')
            # Get the variable
            varType = self.getVarType(id, cdmsfile)
            if (varType == 'variable'):
                var = cdmsfile.__call__(id)
            elif (varType == 'axis'):
                varID = self.getAxisID(id)            
                axis = getattr(cdmsfile, 'axes')[varID]
                var = MV2.array(axis)
                var.setAxis(0, axis)
            elif (varType == 'weighted-axis'):
                varID, axisID = self.getVarAndAxisID(id)
                var = cdmsfile.__call__(varID)            
                var = genutil.getAxisWeightByName(var, axisID)
                var.id = varID +'_' + axisID + '_weight'
            else:
                var = None


        axes = self.forceGetInputFromPort('axes') # None if no input
        axesOperations = self.forceGetInputFromPort('axesOperations') # None if no input
        # Eval the variable with the axes
        if axes is not None and var is not None:
            try:
                var = eval("var(%s)"%axes)
            except Exception, e:
                raise ModuleError(self, "Invalid 'axes' specification: %s"%str(e))

        # Apply axes ops to the variable
        if axesOperations is not None:
            var = self.applyAxesOperations(var, axesOperations)

        self.setResult('variable', var)

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

    def getVarType(self, varID, file):
        if varID in list(getattr(file, 'variables')):
            return 'variable'
        elif varID in list(getattr(file, 'axes')):
            return 'axis'
        elif re.compile('(.+)(_)(.+)(_)axis').match(varID):
            return 'axis'
        elif re.compile('(.+)(_)(.+)(_)weight').match(varID):
            return 'weighted-axis'        

    def getVarAndAxisID(self, varID):
        """ Get the varID and axisID from a string with format:
        varID_axisID_weight """
        
        match = re.compile('(.+)(_)(.+)(_)(weight)').match(varID)
        if match:
            return (match.group(1), match.group(3))

        return None

    def getAxisID(self, varID):
        """ Get the axisID from a string with format: varID_axisID_axis """

        match = re.compile('(.+)(_)(.+)(_)(axis)').match(varID)
        if match:
            return match.group(3)

        return varID

class Quickplot(Variable):
    """ Quickplot is identical to Variable except we will only have a single
    quickplot module in a pipeline. """

    def foo(self):
        return

class GraphicsMethod(Module, NotCacheable):
    """ GraphicsMethod initializes the vcs canvas and gets the graphics method
    and modify it's attributes """
    
    def compute(self):
        # Check required input ports
        if not self.hasInputFromPort('gmName'):
            return
        if not self.hasInputFromPort('plotType'):
            return
        if not self.hasInputFromPort('slab1'):
            return
        
        # Get required input
        gmName = self.getInputFromPort('gmName')
        plotType = self.getInputFromPort('plotType')

        # GraphicsMethod doesn't need slab1/slab2 as input.  It can be passed
        # directly to CDATCell but I pass it to graphics method so it looks
        # nicer in the pipeline.
        slab1 = self.getInputFromPort('slab1')
        if self.hasInputFromPort('slab2'):
            self.setResult('slab2', self.getInputFromPort('slab2'))
                           
        # Initialize the canvas and get the graphics method
        canvas = vcs.init()
        gm = canvas.get_gm(plotType.lower(), gmName)

        # Modify the graphics method's attributes
        if self.hasInputFromPort('color_1'):
            gm.color_1 = self.getInputFromPort('color_1')
        if self.hasInputFromPort('color_2'):
            gm.color_2 = self.getInputFromPort('color_2')
        if self.hasInputFromPort('level_1'):
            gm.level_1 = self.getInputFromPort('level_1')
        if self.hasInputFromPort('level_2'):
            gm.level_2 = self.getInputFromPort('level_2')
        # TODO: more gm attributes ...

        # Add canvas / slab to output Ports
        self.setResult('slab1', slab1)
        self.setResult('canvas', canvas)
        
#this will be moved to be parsed from xml        
class Gfb(Module):
    _input_ports = [('name', '(edu.utah.sci.vistrails.basic:String)'),
                    ('datawc_x1', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('datawc_x2', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('datawc_y1', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('datawc_y2', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('level_1', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('level_2', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('projection', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('yticlabels2', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('yticlabels1', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('xticlabels1', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('xticlabels2', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('ymtics1', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('xmtics1', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('ymtics2', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('xmtics2', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('color_1', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('color_2', '(edu.utah.sci.vistrails.basic:Float)', True),
                    ('boxfill_type', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('fillareacolors', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('datawc_calendar', '(edu.utah.sci.vistrails.basic:Integer)', True),
                    ('missing', '(edu.utah.sci.vistrails.basic:Integer)', True),
                    ('ext_1', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('levels', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('legend', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('datawc_timeunits', '(edu.utah.sci.vistrails.basic:String)', True),
                    ('ext_2', '(edu.utah.sci.vistrails.basic:String)', True),
                    ]
    def __init__(self):
        Module.__init__(self)
        self._name = ''
        self.options = {}
        
    def compute(self):
        self._name = self.getInputFromPort('name')
        for port in Gfb._input_ports:
            if port[0] != 'name' and self.hasInputFromPort(port):
                self.options[port[0]] = self.getInputFromPort(port)
                
class CDATCell(SpreadsheetCell, NotCacheable):
    def __init__(self):
        SpreadsheetCell.__init__(self)
        self.cellWidget = None
        
    def compute(self):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """
        # Check required input ports
        
        if not self.hasInputFromPort('slab1'):
            raise ModuleError(self, "'slab1' is mandatory.")
        if not self.hasInputFromPort('template'):
            raise ModuleError(self, "'template' is mandatory.")
        if not self.hasInputFromPort('plotType'):
            raise ModuleError(self, "'plotType' is mandatory.")

        # Build up the argument list
        args = []
        slab1 = self.getInputFromPort('slab1')
        args.append(self.getInputFromPort('slab1'))
        if self.hasInputFromPort('slab2'):
            args.append(self.getInputFromPort('slab2'))
        
        args.append(self.getInputFromPort('template'))
        args.append(self.getInputFromPort('plotType'))
        if self.hasInputFromPort('gmName'):
            args.append(self.getInputFromPort('gmName'))

        # Build up plot keyword args ...
        kwargs = {}
        if self.hasInputFromPort('continents'):
            kwargs['continents'] = self.getInputFromPort('continents')
        
        # Set the cell row / col
        self.location = CellLocation()
        if self.hasInputFromPort('row'):
            self.location.row = self.getInputFromPort('row')
        if self.hasInputFromPort('col'):
            self.location.col = self.getInputFromPort('col')
        
        canvas = None
        if self.hasInputFromPort('canvas'):
            canvas = self.getInputFromPort('canvas')
        gm = None
        if self.hasInputFromPort('gm'):
            gm = self.getInputFromPort('gm')
        # Plot into the cell
        inputPorts = (canvas, gm, args, kwargs)
        self.cellWidget = self.displayAndWait(QCDATWidget, inputPorts)        
        self.setResult('canvas', self.cellWidget.canvas)        

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
    startIndex = 5 #this should be the current number of canvas objects created 
    maxIndex = 8
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
                   windowIndex <= 8):
            windowIndex += 1
        if windowIndex > 8:
            raise ModuleError(self, "Maximum number of vcs.Canvas objects achieved.\
Please delete unused CDAT Cells in the spreadsheet.")
        else:
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
        if inputPorts[0] is not None:
            self.canvas = inputPorts[0]
        if self.canvas is None:
            self.createCanvas()
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
        if len(inputPorts) > 3:
            gm = inputPorts[1]
            args = inputPorts[2]
            kwargs = inputPorts[3]
            if gm is not None:
                if isinstance(gm, Gfb):
                    cgm = self.canvas.getboxfill(gm._name)
                    for (k,v) in gm.options.iteritems():
                        setattr(cgm,k,v)
            self.canvas.plot(*args, **kwargs)

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
        self.window.setParent(self.parent().parent())
        self.window.setVisible(False)
        self.canvas = None
        self.window = None
        
        QCDATWidget.usedIndexes.remove(self.windowId)
        QCellWidget.deleteLater(self)    
