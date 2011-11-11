###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: vistrails@sci.utah.edu
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################

from cdat_cell import QCDATWidget, CDATCell
from core.modules.vistrails_module import (Module, ModuleError, NotCacheable)
from packages.spreadsheet.spreadsheet_controller import spreadsheetController
from packages.spreadsheet.spreadsheet_event import DisplayCellEvent
from PyQt4 import QtCore, QtGui

class quickplot(Module, NotCacheable):
    """hackiness to push a cdat plot to our spreadsheet.
       needs: QCDATWidget ref
              cdms2.open()d dataset
              blah this is out of date variable name"""

    def compute(self):
        args = []
        if not self.hasInputFromPort('dataset'):
            raise ModuleError(self, "'dataset' is mandatory.")
        if not self.hasInputFromPort('plot'):
            raise ModuleError(self, "'plot' is mandatory.")

        dataset = self.getInputFromPort('dataset')
        plotType = self.getInputFromPort('plot')
        axes = self.forceGetInputFromPort('axes')
        inCanvas = self.forceGetInputFromPort('canvas')

        if axes!=None:
            try:
                kwargs = eval(axes)
            except:
                raise ModuleError(self, "Invalid 'axes' specification", axes)
            dataset = dataset(**kwargs)

        outCanvas = None
        if inCanvas!=None:
            inCanvas.plot(dataset, 'ASD', plotType)
            outCanvas = inCanvas
        else:
            ev = DisplayCellEvent()
            ev.vistrail = {'locator': None, 'version': -1, 'actions': []}
            ev.cellType = QCDATWidget
            ev.inputPorts = (dataset, 'ASD', plotType)
            
            QtCore.QCoreApplication.processEvents()
            spreadsheetWindow = spreadsheetController.findSpreadsheetWindow()
            
            cdatWidget = spreadsheetWindow.displayCellEvent(ev)
            if cdatWidget!=None:
                outCanvas = cdatWidget.canvas
                
        self.setResult('dataset', dataset)
        self.setResult('canvas', outCanvas)
