###############################################################################
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#                                                                             #
###############################################################################

from PyQt4 import QtCore, QtGui
import uuid

import os
import cdms2

from esgf import QEsgfBrowser
import axesWidgets
from roiSelector import *
import uvcdatCommons
import customizeUVCDAT
import editVariableWidget
from gui.common_widgets import QDockPushButton
from gui.application import get_vistrails_application
from packages.uvcdat_cdms.init import CDMSVariable
from gui.uvcdat.cdmsCache import CdmsCache

class QBookMarksListWidget(uvcdatCommons.QDragListWidget):
    def keyReleaseEvent(self,event):
        if event.key() in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            item = self.takeItem(self.currentRow())
            if item is not None:
                txt=str(item.text())
                customizeUVCDAT.fileBookmarks.pop(customizeUVCDAT.fileBookmarks.index(txt))
            
            
        #event.accept()

class VariableProperties(QtGui.QDialog):

    FILTER = "CDAT data (*.cdms *.ctl *.dic *.hdf *.nc *.xml)"

    FILETYPE = {'CDAT': ['cdms', 'ctl', 'dic', 'hdf', 'nc', 'xml']}

    def __init__(self, parent=None,mode="add"):
        super(VariableProperties, self).__init__(parent)
        self.setWindowTitle("Load Variable")
        self.setMinimumHeight(400)
        self.roi = [ -180.0, -90.0, 180.0, 90.0 ]
        self.ask = QtGui.QInputDialog()
        self.ask.setWindowModality(QtCore.Qt.WindowModal)
        self.ask.setLabelText("This variable already exists!\nPlease change its name below and click ok to replace it.\n")
        self.mode=mode
        self.axisListHolder = None
        #self.setFloating(True)
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
        #self.connect(self.originTabWidget,QtCore.SIGNAL("currentChanged(int)"),self.tabHasChanged)
        sp = QtGui.QSplitter(QtCore.Qt.Vertical)
        #sc=QtGui.QScrollArea()
        #sc.setWidget(self.originTabWidget)
        #sc.setWidgetResizable(True)
        sp.addWidget(self.originTabWidget)
        self.dims=QtGui.QFrame()
        self.dimsLayout=QtGui.QVBoxLayout()
        self.dims.setLayout( self.dimsLayout )
        sp.addWidget(self.dims)
        v.addWidget(sp)
        h=QtGui.QHBoxLayout()
        self.selectRoiButton = QDockPushButton('Select Region Of Interest (ROI)')
        h.addWidget( self.selectRoiButton )
        s=QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Preferred)
        h.addItem(s)
        self.btnDefine=QDockPushButton("Load")
        h.addWidget(self.btnDefine)
        self.btnDefineClose=QDockPushButton("Load and Close")
        h.addWidget(self.btnDefineClose)
        self.btnDefineAs=QDockPushButton("Load As")
        h.addWidget(self.btnDefineAs)
        self.btnApplyEdits=QDockPushButton("Apply")
        self.btnApplyEdits.setVisible(False)
        h.addWidget(self.btnApplyEdits)
        self.btnSaveEditsAs=QDockPushButton("Save As")
        self.btnSaveEditsAs.setVisible(False)
        h.addWidget(self.btnSaveEditsAs)
        self.btnCancel=QDockPushButton("Close")

        # defaults?
        self.btnDefine.setDefault(False)
        self.btnDefineClose.setDefault(False)
        self.btnDefineAs.setDefault(False)
        self.selectRoiButton.setDefault(False)

        # Disabling at first
        self.btnDefine.setEnabled(False)
        self.btnDefineClose.setEnabled(False)
        self.btnDefineAs.setEnabled(False)
        self.selectRoiButton.setEnabled(False)
        h.addWidget(self.btnCancel)
        v.addLayout(h)
        self.layout=v
        #f=QtGui.QFrame()
        #f.setLayout(v)
        #self.setWidget(f)
        self.setLayout(v)
        self.parent=parent
        self.root = parent.root
        self.varNameInFile = None #store the name of the variable when loaded from file
        self.createFileTab()
        self.createESGFTab()
        self.createOpenDAPTab()
        self.createEditTab()
        self.createInfoTab()
        for i in range(self.originTabWidget.count()):
            if self.originTabWidget.tabText(i) == "Edit":
                self.originTabWidget.setTabEnabled(i,False)

        self.connectSignals()
        sp.setStretchFactor(0,2)
        self.cdmsFile = None
        self.updatingFile = False

        self.roiSelector = ROISelectionDialog( self.parent )
        self.roiSelector.setWindowFlags( self.roiSelector.windowFlags() | Qt.WindowStaysOnTopHint )
        self.connect(self.roiSelector, QtCore.SIGNAL('doneConfigure()'), self.setRoi )
        if self.roi: self.roiSelector.setROI( self.roi )

    ## @classmethod
    ## def instance(klass):
    ##     if not hasattr(klass, '_instance'):
    ##         klass._instance = klass()
    ##     return klass._instance
    
    def closeEvent(self, event):
        super(VariableProperties, self).closeEvent(event)
        self.btnDefine.setVisible(True)
        self.btnDefineAs.setVisible(True)
        self.btnDefineClose.setVisible(True)
        self.btnApplyEdits.setVisible(False)
        self.btnSaveEditsAs.setVisible(False)

    def tabHasChanged(self,index):
        if (index==1) or (index==2):
            self.root.varProp.btnDefine.setEnabled(False)
            self.root.varProp.btnDefineClose.setEnabled(False)
            self.root.varProp.btnDefineAs.setEnabled(False)
            self.root.varProp.selectRoiButton.setEnabled(False)
            if (index==2): self.clearDimensionsWidget()
        elif (index==3):
            self.root.varProp.selectRoiButton.setEnabled(True)
        ## else:
        ##     self.root.varProp.btnDefine.setEnabled(True)
        ##     self.root.varProp.btnDefineClose.setEnabled(True)
        ##     self.root.varProp.btnDefineAs.setEnabled(True)


    def connectSignals(self):
        self.btnCancel.clicked.connect(self.close)
        self.connect(self.ask,QtCore.SIGNAL('accepted()'),self.checkTargetVarName)
        if self.mode=="add":
            self.tbOpenFile.clicked.connect(self.openSelectFileDialog)

            self.connect(self.originTabWidget,QtCore.SIGNAL("currentChanged(int)"),self.tabHasChanged)
            self.connect(self.fileEdit, QtCore.SIGNAL('returnPressed()'),
                         self.updateFileFromReturnPressed)
            self.connect(self.historyList, QtCore.SIGNAL('itemClicked(QListWidgetItem *)'),
                         self.selectFromList)
            self.connect(self.bookmarksList, QtCore.SIGNAL('itemClicked(QListWidgetItem *)'),
                         self.selectFromList)
            self.connect(self.varCombo, QtCore.SIGNAL('activated(const QString&)'),
                         self.variableSelected)
            self.connect(self.bookmarksList,QtCore.SIGNAL("droppedInto"),self.droppedBookmark)

        self.connect(self.root.dockVariable.widget(),QtCore.SIGNAL("setupDefinedVariableAxes"),self.varAddedToDefined)

        ## Define button
        self.btnDefine.clicked.connect(self.defineVarClicked)
        self.btnDefineClose.clicked.connect(self.defineVarCloseClicked)
        self.btnDefineAs.clicked.connect(self.defineAsVarClicked)
        self.connect(self,QtCore.SIGNAL('definedVariableEvent'),self.root.dockVariable.widget().addVariable)
        self.btnApplyEdits.clicked.connect(self.applyEditsClicked)
        self.btnSaveEditsAs.clicked.connect(self.saveEditsAsClicked)
        self.selectRoiButton.clicked.connect( self.selectRoi )

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
        self.bookmarksList=QBookMarksListWidget(type="bookmarks",dropTypes=["history"])
        #self.bookmarksList.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.bookmarksList.setAlternatingRowColors(True)
        self.bookmarksList.setSortingEnabled(True)
        for f in customizeUVCDAT.fileBookmarks:
            self.addBookmark(f)

        h.addWidget(l)
        h.addWidget(self.bookmarksList)
        v.addLayout(h)

        fileTab = QtGui.QFrame()
        fileTab.setLayout(v)

        self.originTabWidget.addTab( fileTab, "File" )

    def createESGFTab(self):
        ## layout = QtGui.QVBoxLayout()
        ## self.esgfBrowser = QEsgfBrowser(self)
        ## layout.addWidget(self.esgfBrowser)
        try:
          esgf = QEsgfBrowser(self)
          #esgf.addGateway(gateway=customizeUVCDAT.defaultEsgfNode)
          esgf.addGateway(gateway=str(self.root.preferences.host_url.currentText()))
        except Exception,err:
            esgf = QtGui.QLabel("No Internet?\nError log: %s"%err)
        self.originTabWidget.addTab(esgf,"ESGF")

    def createOpenDAPTab(self):
        from packages.vtDV3D.RemoteDataBrowser import RemoteDataBrowser
        browser = RemoteDataBrowser()
        self.connect( browser, RemoteDataBrowser.new_data_element, self.processDataAddress )
        self.originTabWidget.addTab(browser,"OpenDAP")
        
    def processDataAddress( self, address ):
        self.originTabWidget.setCurrentIndex( 0 )
        self.fileEdit.setText( address )
        self.updateFile()

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

    def selectRoi( self ):
        if self.roi: self.roiSelector.setROI( self.roi )
        self.roiSelector.show()

    def setRoi(self):
        self.roi = self.roiSelector.getROI()
        self.updateAxesFromRoi()

    def updateAxesFromRoi(self):
        from packages.vtDV3D.CDMS_VariableReaders import getAxisType, AxisType
        #print "Selected roi: %s " % str( self.roi )
        # Add code here to update Lat Lon sliders.
        n = self.axisListHolder.gridLayout.rowCount()
        #print "ok in roi self is: ",n
        for i in range(len(self.axisListHolder.axisWidgets)):
            axis = self.axisListHolder.axisWidgets[i]
            axis_type = getAxisType( axis.axis )  
            if ( axis_type == AxisType.Latitude ) or axis.virtual==1:
                # Ok this is a lat we need to adjust the sliders now.
                lat1 = self.roi[1]
                lat2 = self.roi[3]
                [ lat1, lat2 ] = axis.sliderCombo.checkBounds( [ lat1, lat2 ], axis.axis.parent )
                axis.sliderCombo.updateTopSlider(axis.sliderCombo.findAxisIndex(lat1))
                axis.sliderCombo.updateBottomSlider(axis.sliderCombo.findAxisIndex(lat2))
            if ( axis_type == AxisType.Longitude ) or axis.virtual==1:
                # Ok this is a lat we need to adjust the sliders now.
                lon1 = self.roi[0]
                lon2 = self.roi[2]
                [ lon1, lon2 ] = axis.sliderCombo.checkBounds( [ lon1, lon2 ], axis.axis.parent )
                axis.sliderCombo.updateTopSlider(axis.sliderCombo.findAxisIndex(lon1))
                axis.sliderCombo.updateBottomSlider(axis.sliderCombo.findAxisIndex(lon2))

    def openSelectFileDialog(self):
        file = QtGui.QFileDialog.getOpenFileName(self, 'Open CDAT data file...',
                                                 '',
                                                 VariableProperties.FILTER + ';;All files (*.*)')
        if not file.isNull():
            self.setFileName(file)

    def setFileName(self,fnm):
        self.fileEdit.setText(fnm)
        self.updateFile()

    def updateFileFromReturnPressed(self):
        self.updatingFile = True
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
        if fi.exists() or fnm[:7]=="http://":
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
#                elif name=="CDAT":
#                    # some OpenDAP files don't have an extension trynig to open in CDAT
#                    try:
#                        tmpf=cdms2.open(str(fnm))
#                        tmpf.variables.keys()
#                        tmpf.close()
#                        self.updateCDMSFile(str(fnm))
#                    except:
#                        pass

                elif name=="CDAT":
                    # some OpenDAP files don't have an extension trynig to open in CDAT
                    try:
                        file_path = os.path.expanduser(str(fnm))
                        if file_path in CdmsCache.d:
                            #print "Using cache2 for %s" % file_path
                            tmpf = CdmsCache.d[file_path]
                        else:
                            #print "Loading file2 %s" % file_path
                            tmpf = CdmsCache.d[file_path] = cdms2.open(file_path)
                        tmpf.variables.keys()
                        #tmpf.close()
                        self.updateCDMSFile(file_path)
                    except:
                        pass

            self.updateOtherPlots(other_list)
            self.root.varProp.btnDefine.setEnabled(True)
            self.root.varProp.btnDefineClose.setEnabled(True)
            self.root.varProp.btnDefineAs.setEnabled(True)
            self.root.varProp.selectRoiButton.setEnabled(True)
        else:
            print "Unable to find file %s" % fnm
            self.emit(QtCore.SIGNAL('fileChanged'), None)

            self.historyList.takeItem(0) #remove from history
            if self.historyList.item(0):
                self.historyList.setCurrentRow(0)
                self.setFileName(self.historyList.item(0).text())
            else:
                self.root.varProp.btnDefine.setEnabled(False)
                self.root.varProp.btnDefineClose.setEnabled(False)
                self.root.varProp.btnDefineAs.setEnabled(False)
                self.root.varProp.selectRoiButton.setEnabled(False)  


    def selectFromList(self,item):
        self.setFileName(str(item.text()))

    def updateCDMSFile(self, fn):
        if fn[:7]=="http://":
            ## Maybe add something for my proxy errors here?
            if fn in CdmsCache.d:
                #print "Using cache3 for %s" % fn
                self.cdmsFile = CdmsCache.d[fn]
            else:
                #print "Loading file3 %s" % fn
                self.cdmsFile = CdmsCache.d[fn] = cdms2.open(fn)
            self.root.record("## Open file: %s" % fn)
            self.root.record("cdmsFile = cdms2.open('%s')" % fn)
        else:
            file_path = os.path.expanduser(fn)
            if fn in CdmsCache.d:
                #print "Using cache4 for %s" % file_path
                self.cdmsFile = CdmsCache.d[file_path]
            else:
                #print "Loading file4 %s" % file_path
                self.cdmsFile = CdmsCache.d[file_path] = cdms2.open(file_path)
            self.root.record("## Open file: %s" % file_path)
            self.root.record("cdmsFile = cdms2.open('%s')" % file_path)
        self.updateVariableList()

    def updateOtherPlots(self, namelist):
        self.emit(QtCore.SIGNAL('updateOtherPlots'), namelist)

    def updateVariableList(self):
        self.varCombo.clear()
        if self.cdmsFile!=None:
            # Add Variables sorted based on their dimensions (most dims first)
            curDim = -1
            for (dim, varId) in sorted([(len(var.listdimnames()), var.id)
                                        for var in self.cdmsFile.variables.itervalues()])[::-1]:
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
            
            # manually call this since we listen for activated now
            self.variableSelected(self.varCombo.itemText(1))

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
        self.root.varProp.btnDefine.setEnabled(True)
        self.root.varProp.btnDefineClose.setEnabled(True)
        self.root.varProp.btnDefineAs.setEnabled(True)
        self.root.varProp.selectRoiButton.setEnabled(True)
        

    def clearDimensionsWidget(self):
        if not self.axisListHolder is None:
            self.axisListHolder.destroy()
        it = self.dimsLayout.takeAt(0)
        if it: 
            it.widget().deleteLater()
    ##             it.widget().destroy()
#            self.dimsLayout.removeItem(it)
            del(it)

    def fillDimensionsWidget(self,axisList):
        self.clearDimensionsWidget()
        self.axisListHolder = axisList
        self.dimsLayout.insertWidget(0,axisList)
        self.updateVarInfo(axisList)
        self.dims.update()
        self.update()

#    def fillDimensionsWidget1(self,axisList):
#        if not self.axisListHolder is None:
#            self.axisListHolder.destroy()
#        N=self.dimsLayout.count()
#        while N>1:
#            it = self.dimsLayout.takeAt(N-1)
#            it.widget().deleteLater()
###             it.widget().destroy()
#            self.dimsLayout.removeItem(it)
#            del(it)
#            self.dims.update()
#            self.update()
#            N=self.dimsLayout.count()
#        self.axisListHolder = axisList
#        self.dimsLayout.addWidget(axisList)
#        self.updateVarInfo(axisList)


    def updateVarInfo(self, axisList):
        from packages.vtDV3D.CDMS_VariableReaders import getAxisType, AxisType
        
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
            axis_type = getAxisType(axis.axis)
            if axis_type in [ AxisType.Latitude, AxisType.Longitude ] or axis.virtual==1:
                showRoi = True
        if showRoi:
            self.selectRoiButton.setHidden(False)
        else:
            self.selectRoiButton.setHidden(True)

    def setupEditTab(self,var):
        self.varEditArea.takeWidget()
        self.varEditArea.setWidget(editVariableWidget.editVariableWidget(var,parent=self.parent,root=self.root))

    def defineVarClicked(self,*args):
        self.getUpdatedVarCheck()

    def defineVarCloseClicked(self,*args):
        self.getUpdatedVarCheck()
        self.close()

    def defineAsVarClicked(self, *args):
        ok = False
        (qtname, ok) = QtGui.QInputDialog.getText(self, "UV-CDAT Variable Definition",
                                                  "New variable name:",
                                                  mode=QtGui.QLineEdit.Normal,
                                                  text="")
        if ok:
            self.getUpdatedVarCheck(str(qtname))

    def getUpdatedVarCheck(self,targetId=None):
        """ Return a new tvariable object with the updated information from
        evaluating the var with the current user selected args / options
        """
        axisList = self.dimsLayout.itemAt(0).widget()

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
        if self.updatingFile:
            self.updatingFile = False
            return
        axisList = self.dimsLayout.itemAt(0).widget()
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
#        uvar=axisList.getVar()
#        if isinstance(uvar,cdms2.axis.FileAxis):
#            updatedVar = cdms2.MV2.array(uvar)
#        else:
#            updatedVar = uvar(**kwargs)

        # Get the variable after carrying out the: def, sum, avg... operations
#        updatedVar = axisList.execAxesOperations(updatedVar)
        updatedVar = axisList.getVar()
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
        
        #this used to be an actual transientvariable, now it's just a filevariable
        #updatedVar.id = targetId
        
        self.root.record("%s = %s(%s)" % (targetId,oid,cmds))
        ## Squeeze?
        if updatedVar.rank() !=0:
            if self.root.preferences.squeeze.isChecked():
                #updatedVar=updatedVar(squeeze=1)
                self.root.record("%s = %s(squeeze=1)" % (targetId,targetId))
                kwargs['squeeze']=1
        else:
            val = QtGui.QMessageBox()
            val.setText("%s = %f" % (updatedVar.id,float(updatedVar)))
            val.exec_()




        # Send information to controller so the Variable can be reconstructed
        # later. The best way is by emitting a signal to be processed by the
        # main window. When this panel becomes a global panel, then we will do
        # that. For now I will talk to the main window directly.

        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        def get_kwargs_str(kwargs_dict):
            kwargs_str = ""
            for k, v in kwargs_dict.iteritems():
                if k == 'order':
                    o = kwargs_dict[k]
                    skip = True
                    for i in range(len(o)):
                        if int(o[i])!=i:
                            skip = False
                            break
                    if skip:
                        continue
                kwargs_str += "%s=%s," % (k, repr(v))
            return kwargs_str
        axes_ops_dict = axisList.getAxesOperations()
        url = None
        if hasattr(self.cdmsFile, "uri"):
            url = self.cdmsFile.uri
        cdmsVar = None
        if not computed_var:
            cdmsVar = CDMSVariable(filename=self.cdmsFile.id, url=url, name=targetId,
                                   varNameInFile=original_id,
                                   axes=get_kwargs_str(kwargs),
                                   axesOperations=str(axes_ops_dict))
            controller.add_defined_variable(cdmsVar)
        else:
            controller.copy_computed_variable(original_id, targetId,
                                              axes=get_kwargs_str(kwargs),
                                              axesOperations=str(axes_ops_dict))

        updatedVar = controller.create_exec_new_variable_pipeline(targetId)

        if updatedVar is None:
            return axisList.getVar()

        if not computed_var:
            self.emit(QtCore.SIGNAL('definedVariableEvent'),(updatedVar,cdmsVar))
        else:
            self.emit(QtCore.SIGNAL('definedVariableEvent'),updatedVar)

        if(self.varEditArea.widget()):
            self.varEditArea.widget().var = updatedVar
            axisList.setVar(updatedVar)

        self.updateVarInfo(axisList)
        return updatedVar

    def generateKwArgs(self, axisList=None):
        """ Generate and return the variable axes keyword arguments """
        if axisList is None:
            axisList = self.dimsLayout.itemAt(0).widget()

        kwargs = {}
        for axisWidget in axisList.getAxisWidgets():
            if not axisWidget.isHidden():
                kwargs[axisWidget.axis.id] = axisWidget.getCurrentValues()

        # Generate additional args
        #kwargs['squeeze'] = 0
        kwargs['order'] = axisList.getAxesOrderString()
        return kwargs

    def applyEditsClicked(self):
        varname = self.varEditArea.widget().var.id
        self.getUpdatedVar(varname)
        
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        
        controller.variableEdited(varname)
        
    def saveEditsAsClicked(self):
        self.defineAsVarClicked()
