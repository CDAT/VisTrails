###############################################################################
#                                                                             #
# Module:       main menu module                                              #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.llnl.gov/                             #
#                                                                             #
# Description:  UV-CDAT GUI main menu.                                        #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
from PyQt4 import QtGui, QtCore
import os
import commandsRecorderWidget
import customizeUVCDAT
import genutil,cdutil
import preFunctionPopUpWidget
class QMenuWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self,parent)

        ##FIXME: File menu already exists. It should not create another one
        #self.fileMenu = parent.menuBar().addMenu('&File')
        #self.savePlotsAction = QtGui.QAction('&Save Plots...', self)
        #self.savePlotsAction.setStatusTip("Save Displayed Plots")
        #self.fileMenu.addAction(self.savePlotsAction)
        ## self.connect(self.savePlotsAction,QtCore.SIGNAL('triggered ()'),
        ##              parent.root.tool_bar.savePlots)

        self.editMenu = parent.ui.menuEdit
        self.editPreferencesAction = QtGui.QAction('Preferences...', self)
        self.editPreferencesAction.setEnabled(True)
        self.editPreferencesAction.setStatusTip('Edit system preferences')
        self.editMenu.addAction(self.editPreferencesAction)
        self.connect(self.editPreferencesAction, QtCore.SIGNAL('triggered ()'),
                     parent.root.preferences.show)

        #self.tools = parent.ui.menuTools
        self.pcmdiTools = parent.ui.menuPCMDITools
        self.pcmdiTools.setTearOffEnabled(True)
        self.help = parent.ui.menuHelp
        self.root=parent.root

        #recordTeachingAction = self.tools.addAction('Record Commands')
        #recordTeachingAction.setCheckable(True)
        #recordTeachingAction.setChecked(customizeUVCDAT.recordCommands)

        #viewTeachingAction = self.tools.addAction('View Teaching Commands')

        #self.connect(viewTeachingAction, QtCore.SIGNAL('triggered ()'),
        #             self.root.recorder.show)
        ## self.connect(closeTeachingAction, QtCore.SIGNAL('triggered ()'),
        ##              self.closeTeachingCommands)


        self.time = self.pcmdiTools.addMenu("Time Tools")
        self.time.setTearOffEnabled(True)
        m = self.time.addMenu("Bounds Set")
        m.setTearOffEnabled(True)
        m.addAction("Set Bounds For Yearly Data")
        m.addAction("Set Bounds For Monthly Data")
        m.addAction("Set Bounds For Daily Data")
        m.addAction("Set Bounds For Twice-daily Data")
        m.addAction("Set Bounds For 6-Hourly Data")
        m.addAction("Set Bounds For Hourly Data")
        m.addAction("Set Bounds For X-Daily Data")
        self.connect(m,QtCore.SIGNAL("triggered(QAction *)"),self.setBounds)
        self.time.addSeparator()
        for t in ["Extract","Climatology","Departures"]:
            m = self.time.addMenu(t)
            m.setTearOffEnabled(True)
            m.addAction("Annual Means")
            m.addSeparator()
            m.addAction("Seasonal Means")
            for s in ["DJF","MAM","JJA","SON"]:
                m.addAction(s)
            m.addSeparator()
            for s in ["Monthly Means",
                      "JAN","FEB","MAR",
                      "APR","MAY","JUN",
                      "JUL","AUG","SEP",
                      "OCT","NOV","DEC"]:
                m.addAction(s)
            self.connect(m,QtCore.SIGNAL("triggered(QAction *)"),self.seasons)

        # Regridding sub-menu of PCMDITools
        regridMenu = self.pcmdiTools.addMenu("Regridding")
        regridMenu.setTearOffEnabled(True)
        esmf = regridMenu.addMenu("ESMF")
        esmf.setToolTip("Earth System Modeling Framework")
        a1 = esmf.addAction("Linear")
        a2 = esmf.addAction("Conservative")
        a3 = esmf.addAction("Patch")
        a1.setToolTip("Earth System Modeling Framework")
        a2.setToolTip("Earth System Modeling Framework")
        a3.setToolTip("Earth System Modeling Framework")
        a4 = regridMenu.addAction("LibCF")
        a4.setToolTip("LibCF - Linear only")
        a5 = regridMenu.addAction("Regrid2")
        a5.setToolTip("CDMS2 Axial regridding tool")

        a1.triggered.connect(self.regridESMFLinear)
        a2.triggered.connect(self.regridESMFConserve)
        a3.triggered.connect(self.regridESMFPatch)
        a4.triggered.connect(self.regridLibCF)
        a5.triggered.connect(self.regridRegrid2)

#        self.regridPopup = QtGui.QAction("RGPU", self)
#        self.regridPopup.setEnabled(True)
#        self.regridPopup.setStatusTip("Set Regridding choices")
#        pu = regridMenu.addAction(self.regridPopup), type(self.regridPopup)
#        print pu, '= regridMenu.addAction(self.regridPopup)'
#        pu.triggered.connect(self.regridPopup.show)

        stats = self.pcmdiTools.addMenu("Statistics")
        stats.setTearOffEnabled(True)
        self.statsFuncs = {"Mean" : {"func":cdutil.averager,"nargsMin":1,"nargsMax":2},
                           "Variance" :{"func":genutil.statistics.variance,"nargsMin":1,"nargsMax":2,"choices":["centered","biased",],"entries":["max_pct_missing"]},
                           "Standard Deviation" : {"func":genutil.statistics.std,"nargsMin":1,"nargsMax":2,"choices":["centered","biased",],"entries":["max_pct_missing"]},
                           "Root Mean Square" : {"func":genutil.statistics.rms,"nargsMin":2,"nargsMax":3,"choices":["centered","biased",],"entries":["max_pct_missing"]},
                           "Correlation" : {"func":genutil.statistics.correlation,"nargsMin":2,"nargsMax":3,"choices":["centered","biased",],"entries":["max_pct_missing"]},
                           "Lagged Corelation" : {"func":genutil.statistics.laggedcorrelation,"nargsMin":2,"nargsMax":2,"choices":["centered","partial","biased","noloop",("lag",[None,len])]},
                           "Covariance" : {"func":genutil.statistics.covariance,"nargsMin":2,"nargsMax":3,"choices":["centered","biased",],"entries":["max_pct_missing"]},
                           "Lagged Covariance" : {"func":genutil.statistics.laggedcovariance,"nargsMin":2,"nargsMax":2,"choices":["centered","partial","noloop",("lag",[None,len])]},
                           "Autocorrelation" : {"func":genutil.statistics.autocorrelation,"nargsMin":1,"nargsMax":1,"choices":["centered","partial","biased","noloop",("lag",[None,len])]},
                           "Autocovariance" : {"func":genutil.statistics.autocovariance,"nargsMin":1,"nargsMax":1,"choices":["centered","partial","noloop",("lag",[None,len])]},
                           "Mean Absolute Difference" : {"func":genutil.statistics.meanabsdiff,"nargsMin":2,"nargsMax":3,"choices":["centered",]},
                           "Linear Regression": {"func":genutil.statistics.linearregression,"nargsMin":1,"nargsMax":2,"choices":[("error",[0,1,2,3]),"probability","nointercept","noslope"]},
                           "Geometric Mean":{"func":genutil.statistics.geometricmean,"nargsMin":1,"nargsMax":1},
                           "Median":{"func":genutil.statistics.median,"nargsMin":1,"nargsMax":1},
                           "Rank (in %)":{"func":genutil.statistics.rank,"nargsMin":1,"nargsMax":1},
                           }
        for nm in sorted(self.statsFuncs.keys()):
            a = stats.addAction(nm)
            a.setToolTip(self.statsFuncs[nm]["func"].__doc__)
        self.connect(stats,QtCore.SIGNAL("triggered(QAction *)"),self.stats)

        vert = self.pcmdiTools.addMenu("Vertical Dims")
        vert.setTearOffEnabled(True)
        self.vertFuncs = {"Reconstruct Pressure: P=B*Ps+A*P0" : {"func":cdutil.vertical.reconstructPressureFromHybrid,"nargsMin":4,"nargsMax":4,"axes":False},
                          "Linear interpolation" : {"func":cdutil.vertical.linearInterpolation,"nargsMin":2,"nargsMax":3,"axes":False},
                          "Log-Linear interpolation" : {"func":cdutil.vertical.logLinearInterpolation,"nargsMin":2,"nargsMax":3,"axes":False},
                          }
        for nm in sorted(self.vertFuncs.keys()):
            a = vert.addAction(nm)
            a.setToolTip(self.vertFuncs[nm]["func"].__doc__)
        self.connect(vert,QtCore.SIGNAL("triggered(QAction *)"),self.vert)

        filters = self.pcmdiTools.addMenu("Filters")
        filters.setTearOffEnabled(True)
        self.filterFuncs = {"Running Average" : {"func":genutil.filters.runningaverage,"nargsMin":1,"nargsMax":1,"choices":[("N",[len,]),],"multiAxes":False},
                            "121 Filter" : {"func":genutil.filters.smooth121,"nargsMin":1,"nargsMax":1,"multiAxes":False},
                            "Custom Filter" : {"func":genutil.filters.custom1D,"nargsMin":2,"nargsMax":2,"multiAxes":False},
                            }
        for nm in sorted(self.filterFuncs.keys()):
            a = filters.addAction(nm)
            a.setToolTip(self.filterFuncs[nm]["func"].__doc__)
        self.connect(filters,QtCore.SIGNAL("triggered(QAction *)"),self.filters)

        nsdfiles = self.pcmdiTools.addMenu("Not Self Describing Files")
        nsdfiles.setTearOffEnabled(True)
        self.nsdfilesFuncs = {"Read ASCII File" : {"func":genutil.ASCII.readAscii,
                                                   "nargsMin":0,"nargsMax":0,
                                                   "choices":[("header",list(range(50))),],
                                                   "axes":False,
                                                   "entries":["ids","shape","next","separators"],
                                                   "fileEntries":["text_file",]},
                              ## "Read ASCII File in Columns" : {"func":genutil.ASCII.readAsciiCols,
                              ##                                 "nargsMin":0,"nargsMax":0,
                              ##                                 "choices":[("header",list(range(50))),("cskip",list(range(25))),("cskip_type",["columns","rows"]),"axis","idrow"],
                              ##                                 "axes":False,
                              ##                                 "entries":["ids","separators"],
                              ##                                 "fileEntries":["text_file",]},
                            }
        for nm in sorted(self.nsdfilesFuncs.keys()):
            a = nsdfiles.addAction(nm)
            a.setToolTip(self.nsdfilesFuncs[nm]["func"].__doc__)
        self.connect(nsdfiles,QtCore.SIGNAL("triggered(QAction *)"),self.nsdfiles)


        self.errorMsg=QtGui.QErrorMessage()
        self.errorMsg.hide()
        self.hide()

    def stats(self,action):
        nm = str(action.text())
        self.pop = preFunctionPopUpWidget.preFuncPopUp(parent=self,defs=self.statsFuncs[nm])
        self.pop.show()
    def vert(self,action):
        nm = str(action.text())
        self.pop = preFunctionPopUpWidget.preFuncPopUp(parent=self,defs=self.vertFuncs[nm])
    def filters(self,action):
        nm = str(action.text())
        self.pop = preFunctionPopUpWidget.preFuncPopUp(parent=self,defs=self.filterFuncs[nm])
    def nsdfiles(self,action):
        nm = str(action.text())
        self.pop = preFunctionPopUpWidget.preFuncPopUp(parent=self,defs=self.nsdfilesFuncs[nm])


    def seasons(self,action):
        menu = str(action.parentWidget().title())
        nm = str(action.text())
        rec = "## Computing "
        ## First which season ?
        if nm == "Annual Means":
            func = cdutil.times.YEAR
            funcnm = 'cdutil.times.YEAR'
        elif nm == "Seasonal Means":
            func = cdutil.times.SEASONALCYCLE
            funcnm = 'cdutil.times.SEASONALCYCLE'
        elif nm == "Monthly Means":
            func = cdutil.times.ANNUALCYCLE
            funcnm = 'cdutil.times.ANNUALCYCLE'
        else:
            func = getattr(cdutil.times,nm)
            funcnm = "cdutil.times.%s" % nm
        vtdesc = nm
        ## Now which operator?
        if menu == "Climatology":
            func = func.climatology
            funcnm+=".climatology"
            rec = "climatological "
            vtdesc = "climatological " + nm.lower()
        elif menu == "Departures":
            func=func.departures
            funcnm+=".departures"
            rec = "departures from "
            vtdesc = "departures from " + nm.lower()
        rec += nm.lower()
        selectedVars=self.root.dockVariable.widget().getSelectedDefinedVariables()
        for v in selectedVars:
            tmp = func(v)
            ext = "".join(nm.lower().split())
            newid = "%s_%s" % (v.id,ext)
            if menu != "Extract":
                newid+=menu.lower()
            tmp.id = newid
            self.root.dockVariable.widget().addVariable(tmp)
            self.root.record(rec)
            self.root.record("%s = %s(%s)" % (newid,funcnm,v.id))
            #send command to project controller to be stored as provenance
            from api import get_current_project_controller
            prj_controller = get_current_project_controller()
            vtfuncnm = "%s(%s)"%(funcnm,v.id)
            prj_controller.calculator_command([v.id], vtdesc, vtfuncnm, newid)


    def setBounds(self,action):
        nm = str(action.text())
        if nm == "Set Bounds For X-Daily Data":
            self.bDialog = QtGui.QInputDialog()
            ## self.bDialog.setInputMode(QtGui.QInputDialog.DoubleInput)
            val,ok = self.bDialog.getDouble(self,"Reset Time Bounds to X-Hourly", "Frequency (# of samples per day)")
            if ok is False or val <= 0.:
                return
        selectedVars=self.root.dockVariable.widget().getSelectedDefinedVariables()
        for v in selectedVars:
            vtnm = nm
            if nm == "Set Bounds For Yearly Data":
                cdutil.times.setTimeBoundsYearly(v)
                self.root.record("## Set Bounds For Yearly Data")
                self.root.record("cdutil.times.setTimeBoundsYearly(%s)" % v.id)
            elif nm == "Set Bounds For Monthly Data":
                cdutil.times.setTimeBoundsMonthly(v)
                self.root.record("## Set Bounds For Monthly Data")
                self.root.record("cdutil.times.setTimeBoundsMonthly(%s)" % v.id)
            elif nm == "Set Bounds For Daily Data":
                cdutil.times.setTimeBoundsDaily(v)
                self.root.record("## Set Bounds For Daily Data")
                self.root.record("cdutil.times.setTimeBoundDaily(%s)" % v.id)
            elif nm == "Set Bounds For Twice-daily Data":
                cdutil.times.setTimeBoundsDaily(v,2)
                self.root.record("## Set Bounds For Twice-daily Data")
                self.root.record("cdutil.times.setTimeBoundDaily(%s,2)" % v.id)
            elif nm == "Set Bounds For 6-Hourly Data":
                cdutil.times.setTimeBoundsDaily(v,4)
                self.root.record("## Set Bounds For 6-Hourly Data")
                self.root.record("cdutil.times.setTimeBoundDaily(%s,4)" % v.id)
            elif nm == "Set Bounds For Hourly Data":
                cdutil.times.setTimeBoundsDaily(v,24)
                self.root.record("## Set Bounds For Hourly Data")
                self.root.record("cdutil.times.setTimeBoundDaily(%s,24)" % v.id)
            elif nm == "Set Bounds For X-Daily Data":
                cdutil.times.setTimeBoundsDaily(v,val)
                self.root.record("## Set Bounds For X-Daily Data")
                self.root.record("cdutil.times.setTimeBoundDaily(%s,%g)" % (v.id,val))
                vtnm = "%s:%g"%(nm,val)
            #send command to project controller to be stored as provenance
            from api import get_current_project_controller
            prj_controller = get_current_project_controller()
            prj_controller.change_defined_variable_time_bounds(v.id, vtnm)


    def regridESMFPatch(self):
        self.regridFunc("'esmf'", "'Patch'")

    def regridESMFConserve(self):
        self.regridFunc("'esmf'", "'Conserve'")

    def regridESMFLinear(self):
        self.regridFunc("'esmf'", "'Linear'")

    def regridLibCF(self):
        self.regridFunc("'LibCF'", "'Linear'")

    def regridRegrid2(self):
        self.regridFunc("'Regrid2'", "''")

    def regridFunc(self, regridTool, regridMethod):
        """
        Run the regrid method from selected variables and store on the 
        command line
        @param regridTool ESMF, LibCF, Regrid2
        @param regridMethod Conserve, Linear, Patch
        """
        import systemCommands
        import __main__
        from gui.application import get_vistrails_application
        from api import get_current_project_controller
        _app = get_vistrails_application()

        QText = QtGui.QTextEdit()
        QLine = QtGui.QLineEdit()
        prj_controller = get_current_project_controller()

        useVars=self.root.dockVariable.widget().getSelectedDefinedVariables()
        sV = self.root.dockVariable.widget().varList.selectedItems()

        if len(useVars) > 2:
            print "\nOnly two variables can be selected to regrid"
            return

        argsStr = "regridTool = %s, regridMethod = %s" % (regridTool, regridMethod)
        # Get the variables
        vSrc = sV[0]
        vDst = sV[1]
        vSrcName = vSrc.varName
        vDstName = vDst.varName
        useSrc = useVars.pop(0)
        useDst = useVars.pop(0)
        varname = "regrid_%s_%s" % (vSrcName, vDstName)
#        varname = "regridVar"
        rhsCommand = "%s.regrid(%s.getGrid(), %s)" % \
                          (vSrcName, vDstName, argsStr)
        pycommand = "%s = %s" % (varname, rhsCommand)
        QLine.setText(QtCore.QString(pycommand.strip()))
        QText.setTextColor(QtGui.QColor(0,0,0))
        commandLine = ">>> " + pycommand + "\n"
        QText.insertPlainText(commandLine)
        systemCommands.commandHistory.append(pycommand)
        systemCommands.command_num = 0

        exec( "import MV2,genutil,cdms2,vcs,cdutil,numpy", __main__.__dict__ )
        regridVar = eval(rhsCommand, __main__.__dict__)
        res = self.root.stick_main_dict_into_defvar(None)
        regridVar.id = varname

        _app.uvcdatWindow.dockVariable.widget().addVariable(regridVar)

        self.root.record("## Regrid command sent from PCMDITools->Regridding->%s>%s" % \
                                (regridTool, regridMethod))
        self.root.record(pycommand)
        prj_controller.process_typed_calculator_command(varname, rhsCommand)
        prj_controller.calculator_command(sV, "REGRID", varname, rhsCommand.strip())
        QLine.setFocus()
