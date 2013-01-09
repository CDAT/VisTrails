###############################################################################
#                                                                             #
# Module:       Preferences module                                            #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.llnl.gov/                             #
#                                                                             #
# Description:  UV-CDAT GUI preferences.                                      #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
from PyQt4 import QtGui, QtCore
import uvcdatCommons
import cdms2
import os
import customizeUVCDAT

class QAliasesDialog(QtGui.QDialog):
    def __init__(self,parent):
        QtGui.QDialog.__init__(self, parent)
        self.parent=parent
        self.root=parent.root
        self.dim=str(self.root.preferences.aliases.currentText())
        self.setWindowTitle('Aliases for %s' % self.dim)
        v = QtGui.QVBoxLayout(self)
        v.setMargin(0)
        v.setSpacing(0)
        self.setLayout(v)
        l=QtGui.QLabel("Aliases for %s" %self.dim)
        v.addWidget(l)
        l=QtGui.QListWidget()
        if self.dim=="time":
            l.addItems(cdms2.axis.time_aliases)
        elif self.dim=="level":
            l.addItems(cdms2.axis.level_aliases)
        elif self.dim=="latitude":
            l.addItems(cdms2.axis.latitude_aliases)
        elif self.dim=="longitude":
            l.addItems(cdms2.axis.longitude_aliases)
        v.addWidget(l)
        self.list=l

        l=QtGui.QLabel("Add a new alias for %s" %self.dim)
        v.addWidget(l)
        
        self.le=QtGui.QLineEdit()
        v.addWidget(self.le)

        b=QtGui.QPushButton("Add %s"%self.dim)
        v.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.add)
        
        l=QtGui.QLabel("Remove alias for %s" %self.dim)
        b=QtGui.QPushButton("Remove selected %s alias"%self.dim)
        v.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.delAlias)
        b=QtGui.QPushButton("Done")
        v.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.close)

    def add(self):
        alias = str(self.le.text())
        if self.dim=="time":
            if alias in cdms2.axis.time_aliases:
                return
            cdms2.axis.time_aliases.append(alias)
        elif self.dim=="level":
            if alias in cdms2.axis.level_aliases:
                return
            cdms2.axis.level_aliases.append(alias)
        elif self.dim=="latitude":
            if alias in cdms2.axis.latitude_aliases:
                return
            cdms2.axis.latitude_aliases.append(alias)
        elif self.dim=="longitude":
            if alias in cdms2.axis.longitude_aliases:
                return
            cdms2.axis.longitude_aliases.append(alias)
        self.list.addItem(alias)
    def delAlias(self):
        alias = str(self.le.text())
        try:
            if self.dim=="time":
                cdms2.axis.time_aliases.remove(alias)
            elif self.dim=="level":
                cdms2.axis.level_aliases.remove(alias)
            elif self.dim=="latitude":
                cdms2.axis.latitude_aliases.remove(alias)
            elif self.dim=="longitude":
                cdms2.axis.longitude_aliases.remove(alias)
        except:
            pass

class QPreferencesDialog(QtGui.QDialog):

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.parent=parent
        self.root=parent.root
        self._status_bar = QtGui.QStatusBar(self)
        self.setWindowTitle('UV-CDAT Preferences')
        layout = QtGui.QHBoxLayout(self)
        layout.setMargin(0)
        layout.setSpacing(0)
        self.setLayout(layout)

        f = QtGui.QFrame()
        layout.addWidget(f)
        
        l = QtGui.QVBoxLayout(f)
        f.setLayout(l)
        
        self._tab_widget = QtGui.QTabWidget(f)
        l.addWidget(self._tab_widget)
        self._tab_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                       QtGui.QSizePolicy.Expanding)

        self._tab_widget.addTab(self.guiTab(self),"GUI")
        self._tab_widget.addTab(self.varTab(self),"Variables")
        self._tab_widget.addTab(self.ioTab(self),"I/O")
        self._tab_widget.addTab(self.vcsTab(self),"VCS")
        self._tab_widget.addTab(self.esgfTab(self),"ESGF")

    def esgfTab(self,parent):
        tab= QtGui.QFrame()
        l=QtGui.QVBoxLayout()
        tab.setLayout(l)
        h=QtGui.QHBoxLayout()
        lb=QtGui.QLabel("File Retrieval Limit")
        self.file_retrieval_limit=QtGui.QLineEdit()
        self.file_retrieval_limit.setText("500")
        h.addWidget(lb)
        h.addWidget(self.file_retrieval_limit)
        l.addLayout(h)
        self.connect(self.file_retrieval_limit,QtCore.SIGNAL('editingFinished()'),self.get_file_limit)
        return tab

    def get_file_limit(self):
        self.file_limit=str(self.file_retrieval_limit.text()).strip()
        if not self.file_limit.isdigit():
            m=QtGui.QMessageBox()
            m.setText("You must enter a number for the file retrieval limit")
            m.exec_()
	    #QtGui.QMessageBox.warning(self, "Message", "You must enter a number for the file retrieval limit",QMessageBox.Ok)

    def varTab(self,parent):
        tab= QtGui.QFrame()
        l=QtGui.QVBoxLayout()
        tab.setLayout(l)
        self.squeeze = QtGui.QCheckBox("Squeeze Dimensions")
        self.squeeze.setEnabled(True)
        self.squeeze.setChecked(customizeUVCDAT.squeezeVariables)
        l.addWidget(self.squeeze)
        h=QtGui.QHBoxLayout()
        lb=QtGui.QLabel("Dimensions Aliases")
        self.aliases = QtGui.QComboBox()
        self.aliases.addItems(["choose","time","level","latitude","longitude"])
        h.addWidget(lb)
        h.addWidget(self.aliases)
        l.addLayout(h)
        self.connect(self.aliases,QtCore.SIGNAL('activated(int)'),self.showAliases)
        return tab

    def showAliases(self):
        if str(self.root.preferences.aliases.currentText())=="choose":
            return
        d= QAliasesDialog(self)
        d.exec_()
        
    
    def guiTab(self,parent):
        tab= QtGui.QFrame()
        l=QtGui.QVBoxLayout()
        tab.setLayout(l)
        self.confirmB4Exit = QtGui.QCheckBox("Confirm Before Exiting")
        self.confirmB4Exit.setChecked(customizeUVCDAT.confirmB4Exit)
        self.confirmB4Exit.setEnabled(True)
        l.addWidget(self.confirmB4Exit)
        self.saveB4Exit = QtGui.QCheckBox("Save State Before Exiting")
        self.saveB4Exit.setChecked(customizeUVCDAT.saveB4Exit)
        self.saveB4Exit.setEnabled(True)
        l.addWidget(self.saveB4Exit)
        b=QtGui.QPushButton("Save GUI State Now")
        self.connect(b,QtCore.SIGNAL("clicked()"),self.saveState)
        b.setEnabled(True)
        l.addWidget(b)
        return tab
    
    def ioTab(self,parent):
        tab= QtGui.QFrame()
        l=QtGui.QVBoxLayout()
        tab.setLayout(l)
        nc = uvcdatCommons.QFramedWidget("NetCDF Settings")
        self.netCDF3 = nc.addCheckBox("Generate NetCDF 3 Format Files")
        self.ncShuffle = nc.addCheckBox("Shuffle")
        if cdms2.getNetcdfShuffleFlag():
            self.ncShuffle.setChecked(True)
        self.ncDeflate = nc.addCheckBox("Deflate",newRow=True)
        if cdms2.getNetcdfDeflateFlag():
            self.ncDeflate.setChecked(True)
        self.ncDeflateLevel = nc.addLabeledSlider("Deflate Level",newRow=True,minimum=0,maximum=9)
        self.ncDeflateLevel.setTickInterval(1)
        self.ncDeflateLevel.setTickPosition(QtGui.QSlider.TicksAbove)
        self.ncDeflateLevel.setValue(cdms2.getNetcdfDeflateLevelFlag())
        self.connect(self.netCDF3,QtCore.SIGNAL("stateChanged(int)"),self.nc)
        self.connect(self.ncShuffle,QtCore.SIGNAL("stateChanged(int)"),self.nc)
        self.connect(self.ncDeflate,QtCore.SIGNAL("stateChanged(int)"),self.nc)
        self.connect(self.ncDeflateLevel,QtCore.SIGNAL("valueChanged(int)"),self.nc)
        l.addWidget(nc)
        printers = uvcdatCommons.QFramedWidget("Printers Settings")
        printers.setEnabled(False)
        l.addWidget(printers)
        return tab

    def vcsTab(self,parent):
        tab= QtGui.QFrame()
        l=QtGui.QVBoxLayout()
        tab.setLayout(l)
        self.saveVCS = QtGui.QPushButton("Save VCS Settings")
        self.connect(self.saveVCS,QtCore.SIGNAL("clicked()"),self.root.canvas[0].saveinitialfile)
        l.addWidget(self.saveVCS)

        fonts = sorted(self.root.canvas[0].listelements("font"))
        #fonts.pop(fonts.index("default"))
        font = uvcdatCommons.QFramedWidget("Fonts")
        self.vcsFont = c = font.addLabeledComboBox("Default Font",fonts)
        c.setCurrentIndex(fonts.index(self.root.canvas[0].getfontname(1)))
        self.connect(c,QtCore.SIGNAL("currentIndexChanged(int)"),self.newDefaultFont)

        b = font.addButton("Load a font for file",newRow=True)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.addFont)
        l.addWidget(font)

        aspect = uvcdatCommons.QFramedWidget("Aspect Ratio")
        self.aspectType=aspect.addRadioFrame("Type",["None","Auto (lat/lon)","Custom"])
        self.aspectCustom=aspect.addLabeledLineEdit("Custom value (Y=n*X) n:")
        self.connect(self.aspectType.buttonGroup,QtCore.SIGNAL("buttonClicked(int)"),self.aspectClicked)
        default=customizeUVCDAT.defaultAspectRatio
        for b in self.aspectType.buttonGroup.buttons():
            if str(b.text())==default:
                #b.setChecked(True)
                b.click()
                
#        l.addWidget(aspect)
        
        return tab

    def aspectClicked(self,*args):
        if self.aspectType.buttonGroup.checkedId()==-4:
            self.aspectCustom.label.setEnabled(True)
            self.aspectCustom.setEnabled(True)
        else:
            self.aspectCustom.label.setEnabled(False)
            self.aspectCustom.setEnabled(False)
        customizeUVCDAT.defaultAspectRatio=str(self.aspectType.buttonGroup.checkedButton().text())
    def nc(self):
        if self.netCDF3.isChecked():
            cdms2.useNetcdf3()
            self.ncShuffle.setEnabled(False)
            self.ncDeflate.setEnabled(False)
            self.ncDeflateLevel.setEnabled(False)
        else:
            self.ncShuffle.setEnabled(True)
            self.ncDeflate.setEnabled(True)
            self.ncDeflateLevel.setEnabled(True)
            if self.ncShuffle.isChecked():
                cdms2.setNetcdfShuffleFlag(1)
            else:
                cdms2.setNetcdfShuffleFlag(0)
            if self.ncDeflate.isChecked():
                cdms2.setNetcdfDeflateFlag(1)
            else:
                cdms2.setNetcdfDeflateFlag(0)
            cdms2.setNetcdfDeflateLevelFlag(self.ncDeflateLevel.value())

    def saveState(self):
        fnm=os.path.join(os.environ["HOME"],"PCMDI_GRAPHICS","customizeUVCDAT.py")
        f=open(fnm,"w")
        customizeUVCDAT.squeezeVariables=self.squeeze.isChecked()
        customizeUVCDAT.ncShuffle=cdms2.getNetcdfShuffleFlag()
        customizeUVCDAT.ncDeflate=cdms2.getNetcdfDeflateFlag()
        customizeUVCDAT.ncDeflateLevel=cdms2.getNetcdfDeflateLevelFlag()
        customizeUVCDAT.timeAliases=cdms2.axis.time_aliases
        customizeUVCDAT.levelAliases=cdms2.axis.level_aliases
        customizeUVCDAT.longitudeAliases=cdms2.axis.latitude_aliases
        customizeUVCDAT.latitudeAliases=cdms2.axis.longitude_aliases
        customizeUVCDAT.confirmB4Exit=self.confirmB4Exit.isChecked()
        customizeUVCDAT.saveB4Exit=self.saveB4Exit.isChecked()
        ## Last directory used
        if isinstance(self.root.dockVariable.lastDirectory,str):
            customizeUVCDAT.lastDirectory = self.root.dockVariable.lastDirectory
        else:
            customizeUVCDAT.lastDirectory = str(self.root.dockVariable.lastDirectory.path())
            
        print >> f, "import PyQt4"
        for a in dir(customizeUVCDAT):
            v=getattr(customizeUVCDAT,a)
            if isinstance(v,QtGui.QColor):
                print >> f, a, "=PyQt4.QtGui.QColor(",v.rgb(),")"
            elif type(v)==type(QtGui) or a[:1]=="_":
                pass
            else:
                print >>f, a,"=",repr(v)
        f.close()
        return
    
    def newDefaultFont(self):
        fnm = str(self.vcsFont.currentText())
        self.root.canvas[0].setdefaultfont(fnm)
        
    def addFont(self):
        fpth = str(QtGui.QFileDialog.getOpenFileName(self,"font",filter ="Fonts (*.ttf) ;; All (*.*)"))
        fnm = os.path.split(fpth)[1].lower()
        if fnm[-4:]==".ttf":
            fnm=fnm[:-4]
        fnm=fnm.replace(" ","_")
        fontsold = sorted(self.root.canvas[0].listelements("font"))
        try:
            self.root.canvas[0].addfont(fpth,fnm)
        except Exception,err:
            return
        fontsnew = sorted(self.root.canvas[0].listelements("font"))
        for i in range(len(fontsnew)):
            if not fontsnew[i] in fontsold:
                ## ok that the new one
                self.vcsFont.insertItem(i,fontsnew[i])
                
        
