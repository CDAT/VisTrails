from PyQt4 import QtCore, QtGui

import os
import cdms2

from qtbrowser.esgf import QEsgfBrowser
from qtbrowser.commandLineWidget import QCommandLine
from qtbrowser import axesWidgets
from qtbrowser import vcdatCommons
from qtbrowser import customizeVCDAT

class VariableProperties(QtGui.QDialog):
    FILTER = "CDAT data (*.cdms *.ctl *.dic *.hdf *.nc *.xml)"

    FILETYPE = {'CDAT': ['cdms', 'ctl', 'dic', 'hdf', 'nc', 'xml']}
        
    def __init__(self, parent=None):
        super(VariableProperties, self).__init__(parent)
        v=QtGui.QVBoxLayout()
        l=QtGui.QLabel("Load From")
        v.addWidget(l)
        self.originTabWidget=QtGui.QTabWidget(self)
        sp = QtGui.QSplitter(QtCore.Qt.Vertical)
        sp.addWidget(self.originTabWidget)
        self.dims=QtGui.QFrame()
        sp.addWidget(self.dims)
        v.addWidget(sp)
        h=QtGui.QHBoxLayout()
        s=QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Maximum)
        h.addItem(s)
        self.btnDefine=QtGui.QPushButton("Define")
        h.addWidget(self.btnDefine)
        self.btnDefineAs=QtGui.QPushButton("Define As")
        h.addWidget(self.btnDefineAs)
        self.btnCancel=QtGui.QPushButton("Cancel")
        h.addWidget(self.btnCancel)
        v.addLayout(h)
        self.layout=v
        self.setLayout(v)
        self.parent=parent
        self.root = parent.root
        self.createFileTab()
        self.createESGFTab()
        self.createCalculatorTab()
        self.createDimensions()
        self.connectSignals()
        
    ## @classmethod
    ## def instance(klass):
    ##     if not hasattr(klass, '_instance'):
    ##         klass._instance = klass()
    ##     return klass._instance

    def connectSignals(self):
        self.btnCancel.clicked.connect(self.close)
        self.tbOpenFile.clicked.connect(self.openSelectFileDialog)
        self.connect(self.fileEdit, QtCore.SIGNAL('returnPressed()'),
                     self.updateFile)
        self.connect(self.historyList, QtCore.SIGNAL('itemClicked(QListWidgetItem *)'),
                     self.selectFromList)
        self.connect(self.bookmarksList, QtCore.SIGNAL('itemClicked(QListWidgetItem *)'),
                     self.selectFromList)
        ## FIXME: signal when dropping to bookmarks so it sticks for next time
        self.connect(self.varCombo, QtCore.SIGNAL('currentIndexChanged(const QString&)'),
                     self.variableSelected)

        ## Define button
        self.btnDefine.clicked.connect(self.defineVarClicked)
        self.connect(self,QtCore.SIGNAL('definedVariableEvent'),self.root.dockVariable.widget().addVariable)
        self.connect(self.bookmarksList,QtCore.SIGNAL("droppedInto"),self.droppedBookmark)


    def droppedBookmark(self,event):
        text = str(event.mimeData().text())
        self.addBookmark(text)

    def addBookmark(self,txt):
        duplicate=False
        for i in range(self.bookmarksList.count()):
            it = self.bookmarksList.item(i)
            if it.text()==txt:
                duplicate=True
                break
            
        if duplicate is False:
            self.bookmarksList.addItem(txt)
            customizeVCDAT.fileBookmarks.append(txt)
            
    def createFileTab(self):
        #Top Part
        ## File Select Section
        v=QtGui.QVBoxLayout()
        h=QtGui.QHBoxLayout()
        l=QtGui.QLabel("File")
        h.addWidget(l)
        self.fileEdit=QtGui.QLineEdit()
        h.addWidget(self.fileEdit)
        self.tbOpenFile=QtGui.QToolButton()
        self.tbOpenFile.setText('...')
        self.tbOpenFile.setToolTip('View and select files')
        h.addWidget(self.tbOpenFile)
        v.addLayout(h)

        ## Variable Select part
        h=QtGui.QHBoxLayout()
        l=QtGui.QLabel("Variable(s):")
        l.setSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        h.addWidget(l)
        self.varCombo=QtGui.QComboBox()
        self.varCombo.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Fixed)
        h.addWidget(self.varCombo)
        v.addLayout(h)

        ## Bottom Part
        h=QtGui.QHBoxLayout()
        l=QtGui.QLabel("History:")
        self.historyList=vcdatCommons.QDragListWidget(type="history")
        self.historyList.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Preferred)
        self.historyList.setAlternatingRowColors(True)
        h.addWidget(l)
        h.addWidget(self.historyList)
        l=QtGui.QLabel("Bookmarks:")
        self.bookmarksList=vcdatCommons.QDragListWidget(type="bookmarks",dropTypes=["history"])
        self.bookmarksList.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Preferred)
        self.bookmarksList.setAlternatingRowColors(True)
        self.bookmarksList.setSortingEnabled(True)
        for f in customizeVCDAT.fileBookmarks:
            self.addBookmark(f)
            
        h.addWidget(l)
        h.addWidget(self.bookmarksList)
        v.addLayout(h)
        
        f=QtGui.QFrame()
        f.setLayout(v)

        self.originTabWidget.addTab(f,"File")

    def createESGFTab(self):
        ## layout = QtGui.QVBoxLayout()
        ## self.esgfBrowser = QEsgfBrowser(self)
        ## layout.addWidget(self.esgfBrowser)
        self.originTabWidget.addTab(QEsgfBrowser(self),"ESGF")
    
    def createCalculatorTab(self):
        self.calculator = QCommandLine(self)
        self.originTabWidget.addTab(self.calculator,"Existing")


    def createDimensions(self):
        self.dimsLayout=QtGui.QVBoxLayout()
        l=QtGui.QLabel("Dimensions")
        self.dimsLayout.addWidget(l)
        self.dims.setLayout(self.dimsLayout)
        
    def openSelectFileDialog(self):
        file = QtGui.QFileDialog.getOpenFileName(self, 'Open CDAT data file...',
                                                 self.root.dockVariable.lastDirectory,
                                                 VariableProperties.FILTER + ';;All files (*.*)')
        if not file.isNull():
            self.setFileName(file)

    def setFileName(self,fnm):
        self.fileEdit.setText(fnm)
        self.updateFile()

    def updateFile(self):
        fnm = self.fileEdit.text()
        fi = QtCore.QFileInfo(fnm)
        ft = str(fi.suffix())
        for i in range(self.historyList.count()):
            it = self.historyList.item(i)
            if it.text()==fnm:
                self.historyList.takeItem(i)
                break
        self.historyList.insertItem(0,fnm)
        self.historyList.setCurrentRow(0)
        # I imagine that there will be filetypes that both ParaView and
        # CDAT will know how to deal with them.
        if fi.exists() or fn[:7]=="http://":
            if fi.exists():
            	self.root.dockVariable.lastDirectory=str(fi.dir().path())
            self.emit(QtCore.SIGNAL('fileChanged'), str(fnm))
            other_list = []
            for name, types in VariableProperties.FILETYPE.iteritems():
                if ft in types:
                    if name == 'CDAT':
                        self.updateCDMSFile(str(fnm))

                    if name not in other_list:
                        other_list.append(name)
            
            self.updateOtherPlots(other_list)
        else:
            self.emit(QtCore.SIGNAL('fileChanged'), None)

    def selectFromList(self,item):
        self.setFileName(str(item.text()))
        
    def updateCDMSFile(self, fn):
        if fn[:7]=="http://":
            ## Maybe add something for my proxy errors here?
            self.cdmsFile = cdms2.open(fn)
            self.root.record("## Open file: %s" % fn)
            self.root.record("cdmsFile = cdms2.open('%s')" % fn)
        else:
            self.cdmsFile = cdms2.open(fn)
            self.root.record("## Open file: %s" % fn)
            self.root.record("cdmsFile = cdms2.open('%s')" % fn)
        self.updateVariableList()
        
    def updateOtherPlots(self, namelist):
        self.emit(QtCore.SIGNAL('updateOtherPlots'), namelist)
        
    def updateVariableList(self):
        self.varCombo.clear()
        if self.cdmsFile!=None:
            # Add Variables sorted based on their dimensions
            curDim = -1
            for (dim, varId) in sorted([(len(var.listdimnames()), var.id)
                                        for var in self.cdmsFile.variables.itervalues()]):
                if dim!=curDim:
                    curDim = dim
                    count = self.varCombo.count()
                    self.varCombo.insertSeparator(count)
                    self.varCombo.model().item(count, 0).setText('%dD VARIABLES' % dim)
                var = self.cdmsFile.variables[varId]
                varName = var.id + ' ' + str(var.shape) + ' ['
                
                if hasattr(var, 'long_name'):
                    varName += var.long_name
                if hasattr(var, 'units') and var.units!='':
                    if varName[-1]!='[': varName += ' '
                    varName += var.units
                varName += ']'
                self.varCombo.addItem(varName, QtCore.QVariant(QtCore.QStringList(['variables', var.id])))

            # Add Axis List
            count = self.varCombo.count()
            self.varCombo.insertSeparator(count)
            self.varCombo.model().item(count, 0).setText('AXIS LIST')
            for axis in self.cdmsFile.axes.itervalues():
                axisName = axis.id + " (" + str(len(axis)) + ") - [" + axis.units + ":  (" + str(axis[0]) + ", " + str(axis[-1]) + ")]"                
                self.varCombo.addItem(axisName, QtCore.QVariant(QtCore.QStringList(['axes', axis.id])))

            # By default, select first var
            self.varCombo.setCurrentIndex(1)
            
    def variableSelected(self, varName):
        if varName == '':
            return

#        self.defineVarButton.setEnabled(not varName.isNull()) # Enable define button
        varName = str(varName).split()[0]
        # Send signal to setup axisList in 'quickplot' tab
        self.root.record("## Open a variable in file")
        self.root.record("cdmsFileVariable = cdmsFile['%s']" % varName)

        # Create and setup the axislist
        axisList = axesWidgets.QAxisList(self.cdmsFile, varName, self)
        axisList.setupVariableAxes()
        N=self.dimsLayout.count()
        while N>1:
            it = self.dimsLayout.takeAt(N-1)
            it.widget().destroy()
            del(it)
            self.dims.update()
            N=self.dimsLayout.count()
        self.dimsLayout.addWidget(axisList)
        ## FIXME
        #self.updateVarInfo(axisList)
        
    def updateVarInfo(self, axisList):
        """ Update the text box with the variable's information """
        if axisList is None:
            return
        
        var = axisList.getVar()
        varInfo = ''
        for line in var.listall():
            varInfo += line + '\n'
##        print "TEXT:",varInfo
##        self.varInfoWidget.setText(varInfo)
    def defineVarClicked(self,*args):
        self.getUpdatedVarCheck()

    def getUpdatedVarCheck(self,targetId=None):
        """ Return a new tvariable object with the updated information from
        evaluating the var with the current user selected args / options
        """
        axisList = self.dimsLayout.itemAt(1).widget()

        if targetId is not None:
            tid = targetId
        elif axisList.cdmsFile is None:
            tid = axisList.var.id
        else:
            tid = axisList.var

        ## ## Ok at that point we need to figure out if 
        ## if self.tabWidget.tabExists(tid) and targetId is None:
        ##     self.ask.setTextValue(tid)
        ##     self.ask.show()
        ##     self.ask.exec_()
        ## else:
        ##     self.getUpdatedVar(tid)
        self.getUpdatedVar(tid)

    def getUpdatedVar(self,targetId):
        axisList = self.dimsLayout.itemAt(1).widget()
        kwargs = self.generateKwArgs()
        # Here we try to remove useless keywords as we record them
        cmds = ""
        for k in kwargs:
            if k=='order':
                o = kwargs[k]
                skip = True
                for i in range(len(o)):
                    if int(o[i])!=i:
                        skip = False
                        break
                if skip:
                    continue
            cmds += "%s=%s," % (k, repr(kwargs[k]))
        cmds=cmds[:-1]
        updatedVar = axisList.getVar()(**kwargs)

        # Get the variable after carrying out the: def, sum, avg... operations
        updatedVar = axisList.execAxesOperations(updatedVar)
        self.root.record("## Defining variable in memory")

        if axisList.cdmsFile is None:
            oid = updatedVar.id
        else:
            oid = "cdmsFileVariable"
        updatedVar.id = targetId
        self.root.record("%s = %s(%s)" % (targetId,oid,cmds))
        ## Squeeze?
        if self.root.preferences.squeeze.isChecked():
            updatedVar=updatedVar(squeeze=1)
            self.root.record("%s = %s(squeeze=1)" % (targetId,targetId))

        self.emit(QtCore.SIGNAL('definedVariableEvent'),updatedVar)
        return updatedVar
    
    def generateKwArgs(self, axisList=None):
        """ Generate and return the variable axes keyword arguments """
        if axisList is None:
            axisList = self.dimsLayout.itemAt(1).widget()

        kwargs = {}        
        for axisWidget in axisList.getAxisWidgets():
            if not axisWidget.isHidden():
                kwargs[axisWidget.axis.id] = axisWidget.getCurrentValues()

        # Generate additional args
        #kwargs['squeeze'] = 0
        kwargs['order'] = axisList.getAxesOrderString()
        return kwargs
