###############################################################################
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#                                                                             #
###############################################################################

from PyQt4 import QtCore, QtGui

import os
import cdms2

from esgf import QEsgfBrowser
from commandLineWidget import QCommandLine
import axesWidgets
from roiSelector import *
import uvcdatCommons
import customizeUVCDAT
import editVariableWidget
from gui.common_widgets import QDockPushButton

# Paraview related imports
from paraviewconnection import ParaViewConnectionDialog
from pvprocessfile import PVProcessFile
from pvtabwidget import PVTabWidget
from packages.uvcdat_cdms.init import CDMSVariable
from packages.uvcdat_pv.init import PVVariable

class VariableProperties(QtGui.QDockWidget):

    FILTER = "CDAT data (*.cdms *.ctl *.dic *.hdf *.nc *.xml)"

    FILETYPE = {'CDAT': ['cdms', 'ctl', 'dic', 'hdf', 'nc', 'xml']}
        
    def __init__(self, parent=None,mode="add"):
        super(VariableProperties, self).__init__(parent)
        self.setWindowTitle("Load Variable")
        self.setMinimumHeight(400)
        self.roi = [ -180.0, -90.0, 180.0, 90.0 ]
        self.ask = QtGui.QInputDialog()
        self.ask.setWindowModality(QtCore.Qt.WindowModal)
        self.ask.setLabelText("This variable already exist!\nPlease change its name bellow or press ok to replace it\n")
        self.mode=mode
        self.axisListHolder = None
        v=QtGui.QVBoxLayout()
        if mode=="add":
            self.label=QtGui.QLabel("Load From")
        else:
            self.label=QtGui.QLabel("Edit Variable")
        v.addWidget(self.label)
        P=parent.root.size()
        self.resize(QtCore.QSize(P.width()*.8,P.height()*.9))
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.originTabWidget=QtGui.QTabWidget(self)
        sp = QtGui.QSplitter(QtCore.Qt.Vertical)
        sc=QtGui.QScrollArea()
        sc.setWidget(self.originTabWidget)
        sc.setWidgetResizable(True)
        sp.addWidget(sc)
        self.dims=QtGui.QFrame()
        sp.addWidget(self.dims)
        v.addWidget(sp)
        h=QtGui.QHBoxLayout()
        s=QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Preferred)
        h.addItem(s)
        self.btnDefine=QDockPushButton("Define")
        h.addWidget(self.btnDefine)
        self.btnDefineAs=QDockPushButton("Define As")
        h.addWidget(self.btnDefineAs)
        self.btnCancel=QDockPushButton("Close")
        h.addWidget(self.btnCancel)
        v.addLayout(h)
        self.layout=v
        f=QtGui.QFrame()
        f.setLayout(v)
        self.setWidget(f)
        self.parent=parent
        self.root = parent.root
        self.varNameInFile = None #store the name of the variable when loaded from file
        self.createFileTab()
        self.createESGFTab()
        self.createPVTab()
        self.createEditTab()
        self.createInfoTab()
        for i in range(self.originTabWidget.count()):
            if self.originTabWidget.tabText(i) == "Edit":
                self.originTabWidget.setTabEnabled(i,False)

        self.createDimensions()
        self.connectSignals()
        sp.setStretchFactor(0,2)
        self._paraviewConnectionDialog = ParaViewConnectionDialog(self)
        self._pvProcessFile = PVProcessFile()
        
    ## @classmethod
    ## def instance(klass):
    ##     if not hasattr(klass, '_instance'):
    ##         klass._instance = klass()
    ##     return klass._instance

    def connectSignals(self):
        self.btnCancel.clicked.connect(self.close)
        self.connect(self.ask,QtCore.SIGNAL('accepted()'),self.checkTargetVarName)
        if self.mode=="add":
            self.tbOpenFile.clicked.connect(self.openSelectFileDialog)
            self.connect(self.fileEdit, QtCore.SIGNAL('returnPressed()'),
                         self.updateFile)
            self.connect(self.historyList, QtCore.SIGNAL('itemClicked(QListWidgetItem *)'),
                         self.selectFromList)
            self.connect(self.bookmarksList, QtCore.SIGNAL('itemClicked(QListWidgetItem *)'),
                         self.selectFromList)
            self.connect(self.varCombo, QtCore.SIGNAL('currentIndexChanged(const QString&)'),
                         self.variableSelected)
            self.connect(self.bookmarksList,QtCore.SIGNAL("droppedInto"),self.droppedBookmark)
            
            # Paraview
            # @NOTE: Disabled this feature for now
            #self.pvTabWidget.serverConnectButton.clicked.connect(self.onClickConnectServer)
            self.pvTabWidget.pvPickLocalFileButton.clicked.connect(self.selectRemoteFile)
        
        self.connect(self.root.dockVariable.widget(),QtCore.SIGNAL("setupDefinedVariableAxes"),self.varAddedToDefined)

        ## Define button
        self.btnDefine.clicked.connect(self.defineVarClicked)
        self.btnDefineAs.clicked.connect(self.defineAsVarClicked)
        self.connect(self,QtCore.SIGNAL('definedVariableEvent'),self.root.dockVariable.widget().addVariable)

    def checkTargetVarName(self):
        result = None
        while result is None:
            result = self.ask.result()
            value = self.ask.textValue()
        if result == 1: # make sure we pressed Ok and not Cancel
            if str(value)!=self.checkAgainst:
                self.getUpdatedVarCheck(str(value))
            else:
                self.getUpdatedVar(str(value))


    def varAddedToDefined(self,var):
        axisList = axesWidgets.QAxisList(None,var,self)
        self.axisListHolder = axisList
        self.updateVarInfo(axisList)

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
            customizeUVCDAT.fileBookmarks.append(txt)
            
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
        l.setSizePolicy(QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Preferred)
        self.historyList=uvcdatCommons.QDragListWidget(type="history")
        #self.historyList.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.historyList.setAlternatingRowColors(True)
        #for i in self.parent.historyList:
        #    self.historyList.addItem(i)
        h.addWidget(l)
        h.addWidget(self.historyList)
        v.addLayout(h)
        
        h=QtGui.QHBoxLayout()
        l=QtGui.QLabel("Bookmarks:")
        l.setSizePolicy(QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Preferred)
        self.bookmarksList=uvcdatCommons.QDragListWidget(type="bookmarks",dropTypes=["history"])
        #self.bookmarksList.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.bookmarksList.setAlternatingRowColors(True)
        self.bookmarksList.setSortingEnabled(True)
        for f in customizeUVCDAT.fileBookmarks:
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
        esgf = QEsgfBrowser(self)
        ##esgf.addGateway(gateway=customizeUVCDAT.defaultEsgfNode)
        self.originTabWidget.addTab(esgf,"ESGF")

    
    def createInfoTab(self):
        info = QtGui.QFrame()
        v=QtGui.QVBoxLayout()
        l=QtGui.QLabel("Variable Information")
        v.addWidget(l)
        sc=QtGui.QScrollArea()
        sc.setWidgetResizable(True)
        self.varInfoWidget = QtGui.QTextEdit()
        self.varInfoWidget.setReadOnly(True)
        sc.setWidget(self.varInfoWidget)
        v.addWidget(sc)
        info.setLayout(v)
        self.originTabWidget.addTab(info,"Info")

    def createEditTab(self):
        self.varEditArea=QtGui.QScrollArea()
        self.varEditArea.setWidgetResizable(True)
        self.originTabWidget.addTab(self.varEditArea,"Edit")

    def createDimensions(self):
        self.dimsLayout=QtGui.QVBoxLayout()
        labelLayout = QtGui.QHBoxLayout()
        l=QtGui.QLabel("Dimensions")
        labelLayout.addWidget(l)
        
        self.selectRoiButton = QDockPushButton('Select ROI', self)
        labelLayout.addWidget( self.selectRoiButton )        
        self.connect( self.selectRoiButton, QtCore.SIGNAL('clicked(bool)'), self.selectRoi )        
        self.roiSelector = ROISelectionDialog( self.parent )
        self.connect(self.roiSelector, QtCore.SIGNAL('doneConfigure()'), self.setRoi )
        if self.roi: self.roiSelector.setROI( self.roi )
        
        self.dims.setLayout( self.dimsLayout )
        self.dimsLayout.addLayout( labelLayout )

    def selectRoi( self ): 
        if self.roi: self.roiSelector.setROI( self.roi )
        self.roiSelector.show()

    def setRoi(self):
        self.roi = self.roiSelector.getROI()
        self.updateAxesFromRoi()

    def updateAxesFromRoi(self):
        print "Selected roi: %s " % str( self.roi )
        # Add code here to update Lat Lon sliders.
        n = self.axisListHolder.gridLayout.rowCount()
        print "ok in roi self is: ",n
        for i in range(len(self.axisListHolder.axisWidgets)):
            axis = self.axisListHolder.axisWidgets[i]
            if axis.axis.isLatitude() or axis.virtual==1:
                # Ok this is a lat we need to adjust the sliders now.
                lat1 = self.roi[1]
                lat2 = self.roi[3]
                axis.sliderCombo.updateTopSlider(axis.sliderCombo.findAxisIndex(lat1))
                axis.sliderCombo.updateBottomSlider(axis.sliderCombo.findAxisIndex(lat2))
            if axis.axis.isLongitude() or axis.virtual==1:
                # Ok this is a lat we need to adjust the sliders now.
                lon1 = self.roi[0]
                lon2 = self.roi[2]
                axis.sliderCombo.updateTopSlider(axis.sliderCombo.findAxisIndex(lon1))
                axis.sliderCombo.updateBottomSlider(axis.sliderCombo.findAxisIndex(lon2))

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
        self.cdmsFile = None
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
            self.varNameInFile = None
            return

#        self.defineVarButton.setEnabled(not varName.isNull()) # Enable define button
        varName = str(varName).split()[0]
        # Send signal to setup axisList in 'quickplot' tab
        self.root.record("## Open a variable in file")
        self.root.record("cdmsFileVariable = cdmsFile['%s']" % varName)
        self.varNameInFile = varName
        # Create and setup the axislist
        axisList = axesWidgets.QAxisList(self.cdmsFile, varName, self)
        axisList.setupVariableAxes()
        self.axisListHolder = axisList
        self.fillDimensionsWidget(axisList)

    def fillDimensionsWidget(self,axisList):
        if not self.axisListHolder is None:
            self.axisListHolder.destroy()
        N=self.dimsLayout.count()
        while N>1:
            it = self.dimsLayout.takeAt(N-1)
            it.widget().deleteLater()
##             it.widget().destroy()
            self.dimsLayout.removeItem(it)
            del(it)
            self.dims.update()
            self.update()
            N=self.dimsLayout.count()
        self.axisListHolder = axisList
        self.dimsLayout.addWidget(axisList)
        self.updateVarInfo(axisList)
        
    def updateVarInfo(self, axisList):
        """ Update the text box with the variable's information """
        if axisList is None:
            return
        
        var = axisList.getVar()
        varInfo = ''
        for line in var.listall():
            varInfo += line + '\n'
        self.varInfoWidget.setText(varInfo)
        showRoi = False
        for i in range(len(self.axisListHolder.axisWidgets)):
            axis = self.axisListHolder.axisWidgets[i]
            if axis.axis.isLatitude() or axis.virtual==1 or axis.axis.isLongitude() or axis.virtual==1:
                showRoi = True
        if showRoi:
            self.selectRoiButton.setHidden(False)
        else:
            self.selectRoiButton.setHidden(True)
            
    def setupEditTab(self,var):
        self.varEditArea.takeWidget()
        self.varEditArea.setWidget(editVariableWidget.editVariableWidget(var,parent=self.parent,root=self.root))

        
    def defineVarClicked(self,*args):
        if self.originTabWidget.currentIndex() in [0, 1, 3]:
            self.getUpdatedVarCheck()
        elif self.originTabWidget.currentIndex() == 2:
            #paraview
            self.getVarFromPVTab()
          
    def defineAsVarClicked(self, *args):
        ok = False
        (qtname, ok) = QtGui.QInputDialog.getText(self, "UV-CDAT Variable Definition",
                                                  "New variable name:", 
                                                  mode=QtGui.QLineEdit.Normal, 
                                                  text="")
        if ok:
            self.getUpdatedVarCheck(str(qtname))
            
    def getVarFromPVTab(self):
        filename = self._pvProcessFile._fileName
        varName = str(self.pvTabWidget.cbVar.currentText()).strip()
        kwargs ={}
        
        #FIXME: need to check if the variable already exists
        self.root.dockVariable.widget().addVariable(varName,type_="PARAVIEW")
        from api import _app
        controller = _app.uvcdatWindow.get_current_project_controller()
        pvVar = PVVariable(filename=filename, name=varName)
        controller.add_defined_variable(pvVar)
        # controller.add_defined_variable(filename, varName, kwargs)
        
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

        exists = False
        for it in self.root.dockVariable.widget().getItems(project=False):
            if tid == str(it.text()).split()[1]:
                exists = True
        ## Ok at that point we need to figure out if 
        if exists:
            self.checkAgainst = tid
            self.ask.setTextValue(tid)
            self.ask.show()
            self.ask.exec_()
        else:
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
        if self.varNameInFile is not None:
            original_id = self.varNameInFile
            computed_var = False
        else:
            original_id = updatedVar.id
            computed_var = True
        updatedVar.id = targetId
        self.root.record("%s = %s(%s)" % (targetId,oid,cmds))
        ## Squeeze?
        if self.root.preferences.squeeze.isChecked():
            updatedVar=updatedVar(squeeze=1)
            self.root.record("%s = %s(squeeze=1)" % (targetId,targetId))
            kwargs['squeeze']=1

        
        
        # Send information to controller so the Variable can be reconstructed
        # later. The best way is by emitting a signal to be processed by the
        # main window. When this panel becomes a global panel, then we will do
        # that. For now I will talk to the main window directly.
        
        from api import _app
        controller = _app.uvcdatWindow.get_current_project_controller()
        def get_kwargs_str(kwargs_dict):
            kwargs_str = ""
            for k, v in kwargs_dict.iteritems():
                if k != 'order':
                    kwargs_str += "%s=%s," % (k, repr(v))
            return kwargs_str
        axes_ops_dict = axisList.getAxesOperations()
        url = None
        if hasattr(self.cdmsFile, "uri"):
            url = self.cdmsFile.uri
        if not computed_var:
            cdmsVar = CDMSVariable(filename=self.cdmsFile.id, url=url, name=targetId,
                                   varNameInFile=original_id, 
                                   axes=get_kwargs_str(kwargs), 
                                   axesOperations=str(axes_ops_dict))
            self.emit(QtCore.SIGNAL('definedVariableEvent'),(updatedVar,cdmsVar))
            controller.add_defined_variable(cdmsVar)
        else:
            self.emit(QtCore.SIGNAL('definedVariableEvent'),updatedVar)
            controller.copy_computed_variable(original_id, targetId,
                                              axes=get_kwargs_str(kwargs), 
                                              axesOperations=str(axes_ops_dict))    
        
        self.updateVarInfo(axisList)
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
    
    def openRemoteFile(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, 
                                                     "%s - Select File" % QtGui.QApplication.applicationName(),
                                                     QtCore.QDir.homePath(), "Files (%s)" % " ".join("*.*"))
        return fileName

    def populateVariables(self, variables):
        # @NOTE (Aashish): Commented out for now until
        # we know the right thing to do
        self.pvTabWidget.populateVars(variables)

    def processFile(self, fileName):
        #print fileName
        self._pvProcessFile.setFileName(fileName)
        #print self._pvProcessFile.getPointVariables()
        #print self._pvProcessFile.getCellVariables()

        # First clear all previous entries
        # @NOTE (Aashish) Commented out for now
        #self.listWidget.clear()

        # Now populate (in the case of POP, we will have have only Variables)
        #self.populateVariables(self._pvProcessFile.getPointVariables())
        #self.populateVariables(self._pvProcessFile.getCellVariables()) 
        self.populateVariables(self._pvProcessFile.getVariables())

    def updateConnectionStatus(self, isConnected):
        if isConnected:
            self.pvTabWidget.serverConnectButton.setText("Connected")
        else:
            self.pvTabWidget.serverConnectButton.setText("Connect")

    def selectRemoteFile(self):
        fileName = self.openRemoteFile()
        self.processFile(fileName)
        self.pvTabWidget.pvSelectedFileLineEdit.setText(fileName)

    def onClickConnectServer(self):
        isConnected = self._paraviewConnectionDialog.isConnected()
        self.updateConnectionStatus(isConnected);
        if isConnected:
            self.selectRemoteFile()
        else:
            accepted = self._paraviewConnectionDialog.exec_()
            if accepted == QtGui.QDialog.Rejected:
                return
            self._paraviewConnectionDialog.connect()
            isConnected = self._paraviewConnectionDialog.isConnected()      
            if isConnected:             
                self.selectRemoteFile()

            self.updateConnectionStatus(isConnected);       
            
    def createPVTab(self):        
        self.pvTabWidget = PVTabWidget(self)    
        self.originTabWidget.addTab(self.pvTabWidget,"ParaView")
