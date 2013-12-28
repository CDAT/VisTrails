from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem
     
from ui_diagnosticsDockWidget import Ui_DiagnosticDockWidget
import tempfile

import metrics.frontend.uvcdat
import metrics.fileio.findfiles
import metrics.diagnostic_groups
import uvcdatCommons

class QDiagnosticsDataLocationWindow(QtGui.QDialog):
    def __init__(self, parent=None):
        import os
        super(QDiagnosticsDataLocationWindow,self).__init__(parent)
        v = QtGui.QVBoxLayout()
        self.setLayout(v)
        f = uvcdatCommons.QFramedWidget("Where to find the data")
        self.obsPath = f.addLabeledLineEdit("Observation Top directory")
        self.obsPath.setText(os.path.join(os.environ['HOME'],'obs_data'))
        b = f.addButton("...",newRow=False)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.getObsPath)
        v.addWidget(f)
        f = uvcdatCommons.QFramedWidget("Data is at:")
        self.dataPath = f.addLabeledLineEdit("Data Top directory")
        self.dataPath.setText(os.path.join(os.environ["HOME"],'cam_output'))
        b = f.addButton("...",newRow=False)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.getDataPath)
        v.addWidget(f)
        h=QtGui.QHBoxLayout()
        b=QtGui.QPushButton("Apply")
        self.connect(b,QtCore.SIGNAL("clicked()"),self.apply)
        h.addWidget(b)
        b=QtGui.QPushButton("Close")
        self.connect(b,QtCore.SIGNAL("clicked()"),self.hide)
        h.addWidget(b)
        v.addLayout(h)

    def apply(self):
        self.parent().path1 = str(self.dataPath.text())
        self.parent().path2 = str(self.obsPath.text())
        self.parent().scanFiles()
        self.hide()

    def getObsPath(self):
        d = QtGui.QFileDialog.getExistingDirectory(self,"Select Obs Top Directory",self.obsPath.text())
        self.obsPath.setText(d)

    def getDataPath(self):
        d = QtGui.QFileDialog.getExistingDirectory(self,"Select Data Top Directory",self.dataPath.text())
        self.dataPath.setText(d)


class DiagnosticsDockWidget(QtGui.QDockWidget, Ui_DiagnosticDockWidget):
    
    dg_menu = metrics.diagnostic_groups.diagnostics_menu()  # typical item: 'AMWG':AMWG
    Types = dg_menu.keys()
    standard_alltypes = ["AMWG","LMWG","OMWG", "PCWG", "MPAS", "WGNE", "Metrics"]
    DisabledTypes = list( set(standard_alltypes) - set(Types) )
    AllTypes = Types + DisabledTypes


    def __init__(self, parent=None):
        super(DiagnosticsDockWidget, self).__init__(parent)
        self.setupUi(self)
       
        import metrics.frontend.uvcdat
        import os
        # Path selection window
        self.dataLocationWindow = QDiagnosticsDataLocationWindow(self)
        self.dataLocationWindow.hide()
        # The paths have to be chosen by the user, unless we know something about the system...
        self.path1 = None
        self.path2 = None
        self.tmppth = os.path.join(os.environ['HOME'],"tmp")
        if not os.path.exists(self.tmppth):
            os.makedirs(self.tmppth)

        self.scanFiles()
        #initialize data
        #@todo: maybe move data to external file to be read in
        """ formerly was...
        self.groups = {'AMWG': ['1- Table of Global and Regional Means and RMS Error',
                                '2- Line Plots of Annual Implied Northward Transport',
                                '3- Line Plots of  Zonal Means',
                                '4- Vertical Contour Plots Zonal Means',
                                '4a- Vertical (XZ) Contour Plots Meridional Means', 
                                '5- Horizontal Contour Plots of Seasonal Means',
                                '6- Horizontal Vector Plots of Seasonal Means',
                                '7- Polar Contour and Vector Plots of Seasonal Means',
                                '8- Annual Cycle Contour Plots of Zonal Means ',
                                '9- Horizontal Contour Plots of DJF-JJA Differences', 
                                '10- Annual Cycle Line Plots of Global Mean',
                                '11- Pacific Annual Cycle, Scatter Plots',
                                '12- Vertical Profile from 17 Selected Stations',
                                '13- Cloud Simulators plots',
                                '14- Taylor diagrams',
                                '15- Annual Cycle at Select Stations Plots',],
                       'LMWG': {'LMWG Group 1': ['Diagnostics 10', 
                                                 'Diagnostics 11', 
                                                 'Diagnostics 12'],
                                'LMWG Group 2': ['Diagnostics 13',
                                                 'Diagnostics 14', 
                                                 'Diagnostics 15',],
                                'LMWG Group 3': ['Diagnostics 16',
                                                 'Diagnostics 17', 
                                                 'Diagnostics 18',]}}
        """
        
        self.DiagnosticGroup = None
        self.diagnostic_set = None
        self.variables = ['N/A',]
        # jfp was:
        #self.observations = ['AIRS', 'ARM', 'CALIPSOCOSP', 'CERES', 'CERES-EBAF', 'CERES2', 'CLOUDSAT', 'CLOUDSATCOSP', 'CRU', 'ECMWF', 'EP.ERAI', 'ERA40', 'ERAI', 'ERBE', 'ERS', 'GPCP', 'HadISST', 'ISCCP', 'ISCCPCOSP', 'ISCCPD1', 'ISCCPFD', 'JRA25', 'LARYEA', 'LEGATES', 'MISRCOSP', 'MODIS', 'MODISCOSP', 'NCEP', 'NVAP', 'SHEBA', 'SSMI', 'TRMM', 'UWisc', 'WARREN', 'WHOI', 'WILLMOTT', 'XIEARKIN']
        self.seasons = None # will be set when DiagnosticGroup is made
        #...was self.seasons = ['DJF', 'JJA', 'MJJ', 'ASO', 'ANN']
        
        #setup signals
        self.comboBoxType.currentIndexChanged.connect(self.setupDiagnosticTree)
        self.buttonBox.clicked.connect(self.buttonClicked)
        self.treeWidget.itemChanged.connect(self.itemChecked)
        
        #keep track of checked item so we can unckeck it if another is checked
        self.checkedItem = None
        
        self.setupDiagnosticsMenu()
        
        self.comboBoxType.addItems(DiagnosticsDockWidget.Types)
        i=self.comboBoxType.findText("3- Line Plots of  Zonal Means")

        if i>-1:
            self.comboBoxType.setCurrentindex(i)

        self.comboBoxSeason.addItems(self.seasons)
        
    def scanFiles(self):
        if self.path1 is not None:
            datafiles = metrics.fileio.findfiles.dirtree_datafiles( self.path1 )
            self.filetable1 = datafiles.setup_filetable( self.tmppth, "model" )
            # ...was self.filetable1 = metrics.frontend.uvcdat.setup_filetable(self.path1,self.tmppth)
        if self.path2 is not None:
            self.datafiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.path2 )
            self.obs_menu = self.datafiles2.check_filespec()
            self.observations = self.obs_menu.keys()
        else:
            self.observations = None
        self.diagnostic_set_name = "Not implemented"
        if self.observations==None:
            print "WARNING: No data in second (obs) data set"
        print "Scanned files",self.path1,self.path2
        if type(self.observations) is list:
            self.observations.sort()
            self.comboBoxObservation.setDuplicatesEnabled(False)
            self.comboBoxObservation.addItems(self.observations)
            i = self.comboBoxObservation.findText("NCEP")
            self.comboBoxObservation.setCurrentIndex(i)

        if type(self.observations) is list:
            self.observation = str(self.comboBoxObservation.currentText())
            #filt2="filt=f_startswith('%s')" % self.observation
            filt2 = self.obs_menu[self.observation]
        else:
            filt2 = None
        self.datafiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.path2, filt2 )
        self.filetable2 = self.datafiles2.setup_filetable( self.tmppth, "obs" )
        if self.path1 is not None:
            self.setupDiagnosticTree(0)

    def setupDiagnosticsMenu(self):
        menu = self.parent().menuBar().addMenu('&Diagnostics')
        
        def generateCallBack(x):
            def callBack():
                self.diagnosticTriggered(x)
            return callBack
        
        #Adding an action for settings
        action = QtGui.QAction("Set Data Location",self)
        action.setStatusTip("how to access data")
        action.triggered.connect(self.dataLocationWindow.show)
        menu.addAction(action)

        for diagnosticType in DiagnosticsDockWidget.AllTypes:
            action = QtGui.QAction(diagnosticType, self)
            action.setEnabled(diagnosticType in DiagnosticsDockWidget.Types)
            action.setStatusTip(diagnosticType + " Diagnostics")
            action.triggered.connect(generateCallBack(diagnosticType))
            menu.addAction(action)
            
    def diagnosticTriggered(self, diagnosticType):
        index = self.comboBoxType.findText(diagnosticType)
        self.comboBoxType.setCurrentIndex(index)
        self.show()
        self.raise_()
        
    def plotsetchanged(self,item,column):
        if self.path1 is None or self.path2 is None:
            return
        import metrics.frontend.uvcdat
        txt = item.text(item.columnCount()-1)
        self.diagnostic_set_name = str(txt)

        if type(self.observations) is list:
            self.observation = str(self.comboBoxObservation.currentText())
            #filt2="filt=f_startswith('%s')" % self.observation
            if type(self.observation) is str and len(self.observation)>0:
                filt2 = self.obs_menu[self.observation]
            else:
                filt2 = None
        else:
            filt2 = None
        self.datafiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.path2, filt2 )
        self.filetable2 = self.datafiles2.setup_filetable( self.tmppth, "obs" )

        self.variables = self.DiagnosticGroup.list_variables( self.filetable1, self.filetable2,
                                                              self.diagnostic_set_name )
        for i in range(self.comboBoxVariable.count()):
            self.comboBoxVariable.removeItem(0)

        self.comboBoxVariable.addItems(self.variables)
        i = self.comboBoxVariable.findText("TREFHT")
        if i>-1:
            self.comboBoxVariable.setCurrentIndex(i)
        self.comboBoxVariable.currentIndexChanged.connect(self.variablechanged)
        self.variablechanged(i)

    def variablechanged(self,index):
        if self.path1 is None or self.path2 is None:
            return
        # Variable's auxiliary options
        self.varmenu = self.DiagnosticGroup.all_variables( self.filetable1, self.filetable2,
                                                           self.diagnostic_set_name )
        varname = str(self.comboBoxVariable.currentText())
        if varname in self.varmenu.keys():
            variable = self.varmenu[varname]( varname, self.diagnostic_set_name, self.DiagnosticGroup )
            self.auxmenu = variable.varoptions()
        else:
            self.auxmenu = None
        for i in range(self.comboBoxAux.count()):
            self.comboBoxAux.removeItem(0)
        if self.auxmenu is not None:
            self.comboBoxAux.addItems( sorted(self.auxmenu.keys()) )
        

    def setupDiagnosticTree(self, index):
        diagnosticType = str(self.comboBoxType.itemText(index))
        self.treeWidget.clear()
        self.treeWidget.itemChanged.connect(self.plotsetchanged)
        self.DiagnosticGroup = DiagnosticsDockWidget.dg_menu[diagnosticType]()
        """ formerly was:
        if isinstance(self.groups[diagnosticType],dict):
            for groupName, groupValues in self.groups[diagnosticType].items():
                groupItem = QtGui.QTreeWidgetItem(self.treeWidget, [groupName])
                for diagnostic in groupValues:
                    diagnosticItem = QtGui.QTreeWidgetItem(groupItem, [diagnostic])
                    diagnosticItem.setFlags(diagnosticItem.flags() & (~Qt.ItemIsSelectable))
                    diagnosticItem.setCheckState(0, Qt.Unchecked)
        else:
            for diagnostic in self.groups[diagnosticType]:
                diagnosticItem = QtGui.QTreeWidgetItem(self.treeWidget, [diagnostic])
                diagnosticItem.setFlags(diagnosticItem.flags() & (~Qt.ItemIsSelectable))
                diagnosticItem.setCheckState(0, Qt.Unchecked)
          """
        # ds_menu and seasons depend on self.DiagnosticGroup (only), so they are best
        # set right after self.DiagnosticGroup is set...
        self.ds_menu = self.DiagnosticGroup.list_diagnostic_sets()
        self.seasons = self.DiagnosticGroup.list_seasons()
        # Note that the following loop calls plotsetchanged()
        for diagnostic_set in sorted(self.ds_menu.keys()):
            diagnosticItem = QtGui.QTreeWidgetItem(self.treeWidget, [diagnostic_set])
            diagnosticItem.setFlags(diagnosticItem.flags() & (~Qt.ItemIsSelectable))
            diagnosticItem.setCheckState(0, Qt.Unchecked)


        
    def buttonClicked(self, button):
        role = self.buttonBox.buttonRole(button) 
        if role == QtGui.QDialogButtonBox.ApplyRole:
            self.applyClicked()
        elif role == QtGui.QDialogButtonBox.RejectRole:
            self.cancelClicked()
            
    def applyClicked(self):
        from metrics.frontend.uvcdat import setup_filetable, get_plot_data

        diagnostic = str(self.checkedItem.text(0))
        #group = str(self.checkedItem.parent().text(0))
        #Never name something 'type', it's a reserved word! type = str(self.comboBoxType.currentText())
        variable = str(self.comboBoxVariable.currentText())
        season = str(self.comboBoxSeason.currentText())
        auxname = str(self.comboBoxAux.currentText())
        print "diagnostic: %s" % diagnostic
        print "observation: %s" % self.observation
        print "season: %s" % season
        print "variable: %s" % variable
        print "auxiliary option: %s" % auxname
        # initial test, first cut:
        # This stuff should go elsewhere...
        import os
        #...was self.filetable2 = setup_filetable(self.path2,self.tmppth,search_filter=filt2)
        # ( replacement moved to __init__ and plotsetchanged)
        if self.auxmenu is None:
            aux = None
        else:
            aux = self.auxmenu[auxname]
        self.diagnostic_set_name = diagnostic
        self.plot_spec = self.ds_menu[diagnostic](
            self.filetable1, self.filetable2, variable, season, aux )
        ps = self.plot_spec
        if ps is None:
            print "Can't plot, plot_spec is None!!!!"
            return None
        print "computing plot....",
        res = ps.compute()
        print "...finished computing plot"
        if res is None:
            print "Can't plot, plot_spec results were None!"  # TO DO: should be printed in plot window
            return None
        # TO DO: it would be useful to get some immediate feedback as to whether the code is
        # busy, or finished with the current task.
        # For now, print the first result.  Really, we want to plot them all...
        row = 0 
        column = 0
        Ncolumns = 2 # TODO: Figure out how columns are actually displayed so we switch row accordingly
        Nrows = 2 # TODO: Figure out how many rows are displayed so that we can warn users some plots may need scrolling
        if type(res) is list:
            print "Plot data is a list.  We'll just use the first item"   # TO DO: show all the plots!
            res30 = res[0]
        else:
            res30 = res
        for res30 in res:
            self.displayCell(res30,row,column)
            column+=1
            if column == Ncolumns:
                column=0
                row+=1
        if row>Nrows:
            mbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"This diagnostics generated more rows than the number currently disaplyed by your spreadsheet, don't forget to scroll down")
            mbox._exec()
        print "Finished"

    def displayCell(self,res30,row,column,sheet="Sheet 1"):
        """Display result into one cell defined by row/column args"""
        pvars = res30.vars
        labels = res30.labels
        title = res30.title
        presentation = res30.presentation
        print "pvars:",pvars
        print "labels:",labels
        print "title:",title
        print "presentation:",presentation
        #define where to drag and drop
        import cdms2
        from packages.uvcdat_cdms.init import CDMSVariable
        projectController = self.parent().get_current_project_controller()
        #Clear the cell
        projectController.clear_cell(sheet,column,row)
        for V in pvars:
            # We really need to fix the 2-line plots.  Scale so that both variables use the
            # same axes!  The Diagnostics package can provide upper and lower bounds for the
            # axes (important for a composite plot) and the graphics should follow that.
            # That's for contour (Isofill) as well as line (Yxvsx) and other plots.
            #V[0]=220  # temporary kludge for TREFHT, plot set 3
            #V[1]=305  # temporary kludge for TREFHT, plot set 3
            # Until I know better storing vars in tempfile....
            f = tempfile.NamedTemporaryFile()
            filename = f.name
            f.close()
            fd = cdms2.open(filename,"w")
            fd.write(V)
            fd.close()
            cdmsFile = cdms2.open(filename)
            #define name of variable to appear in var widget
            name_in_var_widget = V.id
            #get uri if exists
            url = None
            if hasattr(cdmsFile, 'uri'):
                url = cdmsFile.uri
            #create vistrails module
            cdmsVar = CDMSVariable(filename=cdmsFile.id, url=url, name=name_in_var_widget,
                                    varNameInFile=V.id)

            #get variable widget and project controller
            definedVariableWidget = self.parent().dockVariable.widget()

            #add variable to display widget and controller
            definedVariableWidget.addVariable(V)
            projectController.add_defined_variable(cdmsVar)

            # simulate drop variable
            varDropInfo = (name_in_var_widget, sheet, col, row)
            projectController.variable_was_dropped(varDropInfo)

            # Trying to add method to plot list....
            #from gui.application import get_vistrails_application
            #_app = get_vistrails_application()
            #d = _app.uvcdatWindow.dockPlot
            # simulate drop plot
            #plot = projectController.plot_manager.new_plot('VCS', res30.type, res30.presentation )
            plot = projectController.plot_manager.new_plot('VCS', res30.type, "default" )
            plotDropInfo = (plot, sheet, col, row)
            projectController.plot_was_dropped(plotDropInfo)

    def cancelClicked(self):
        self.close()
            
    def itemChecked(self, item, column):
        if item.checkState(column) == Qt.Checked:
            if self.checkedItem is not None:
                self.treeWidget.blockSignals(True)
                self.checkedItem.setCheckState(column, Qt.Unchecked)
                self.treeWidget.blockSignals(False)
            self.checkedItem = item
        else:
            self.checkedItem = None
