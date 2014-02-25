from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem
     
from ui_diagnosticsDockWidget import Ui_DiagnosticDockWidget
from pprint import pprint
import tempfile

from core.utils import InstanceObject
from packages.uvcdat_cdms.init import original_gm_attributes, \
        get_gm_attributes, get_canvas

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
        self.obsPath = f.addLabeledLineEdit("Observation (or reference model) Top directory")
        self.obsPath.setText(os.path.join(os.environ['HOME'],'obs_data'))
        b = f.addButton("...",newRow=False)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.getObsPath)
        v.addWidget(f)
        f = uvcdatCommons.QFramedWidget("Data is at:")
        self.dataPath = f.addLabeledLineEdit("Model Top directory")
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
        self.auxmenu = None
        
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
            #self.filetable1 = datafiles.setup_filetable( self.tmppth, "model" )
            #present synchronize_ranges uses a suffix from filetable id, assumes it's 1 or 2:
            self.filetable1 = datafiles.setup_filetable( self.tmppth, "1" )
            # ...was self.filetable1 = metrics.frontend.uvcdat.setup_filetable(self.path1,self.tmppth)
        self.observations = None
        if self.path2 is not None:
            self.datafiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.path2 )
            self.obs_menu = self.datafiles2.check_filespec()
            if type(self.obs_menu) is dict:
                self.observations = self.obs_menu.keys()
        self.diagnostic_set_name = "Not implemented"
        if self.observations==None:
            print "WARNING: No data in second (obs) data set"
        print "Scanned files",self.path1,self.path2
        if type(self.observations) is list:
            for i in range(self.comboBoxObservation.count()):
                self.comboBoxObservation.removeItem(0)
            self.observations.sort()
            self.comboBoxObservation.setDuplicatesEnabled(False)
            self.comboBoxObservation.addItems(self.observations)
            i = self.comboBoxObservation.findText("NCEP")
            self.comboBoxObservation.setCurrentIndex(i)

        if type(self.observations) is list:
            self.observation = str(self.comboBoxObservation.currentText())
            if len(str(self.comboBoxObservation.currentText()).strip())>0:
                #self.filt2="filt=f_startswith('%s')" % self.observation
                self.filt2 = self.obs_menu.get( self.observation, None )
            else:
                self.filt2 = None
        else:
            self.filt2 = None
        self.datafiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.path2, self.filt2 )
        #self.filetable2 = self.datafiles2.setup_filetable( self.tmppth, "obs" )
        #present synchronize_ranges uses a suffix from filetable id, assumes it's 1 or 2:
        self.filetable2 = self.datafiles2.setup_filetable( self.tmppth, "2" )
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
        diagnostic_set_name = str(txt)

        if type(self.observations) is list:
            self.observation = str(self.comboBoxObservation.currentText())
            #filt2="filt=f_startswith('%s')" % self.observation
            if type(self.observation) is str and len(self.observation)>0:
                filt2 = self.obs_menu.get( self.observation, None )
            else:
                filt2 = None
        else:
            filt2 = None
        if filt2!=self.filt2:
            self.filt2 = filt2
            self.datafiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.path2, self.filt2 )
            #self.filetable2 = self.datafiles2.setup_filetable( self.tmppth, "obs" )
            #present synchronize_ranges uses a suffix from filetable id, assumes it's 1 or 2:
            self.filetable2 = self.datafiles2.setup_filetable( self.tmppth, "2" )

        variables = self.DiagnosticGroup.list_variables( self.filetable1, self.filetable2,
                                                              diagnostic_set_name )
        if variables!=self.variables or diagnostic_set_name!=self.diagnostic_set_name:
            self.diagnostic_set_name = diagnostic_set_name
            self.variables = variables
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

        if self.checkedItem is None:
            print "Can't plot.  Try choosing a plot set."
        diagnostic = str(self.checkedItem.text(0))
        #group = str(self.checkedItem.parent().text(0))
        #Never name something 'type', it's a reserved word! type = str(self.comboBoxType.currentText())
        variable = str(self.comboBoxVariable.currentText())
        season = str(self.comboBoxSeason.currentText())
        auxname = str(self.comboBoxAux.currentText())
        print "diagnostic: %s" % diagnostic
        #print "observation: %s" % self.observation
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

        tabcont = self.parent().spreadsheetWindow.get_current_tab_controller()
        for t in tabcont.tabWidgets:
            # I actually expect this loop body to be hit exactly once.
            # Otherwise, I don't know what the GUI is doing.
            dim = t.getDimension()
            Nrows = dim[0]
            Ncolumns = dim[1]
        if type(res) is not list:
            res = [res]
        # I'm keeping this old message as a reminder of scrollable panes, a feature which would be
        # nice to have in the future (but it doesn't work now)...
        #mbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"This diagnostics generated more rows than the number currently disaplyed by your spreadsheet, don't forget to scroll down")

        if len(res)>Nrows*Ncolumns:
            msg = "This diagnostics generated a composite of %s simple plots, which is more than your spreadsheet can dispaly. So some will be lost."%len(res)
            mbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,msg, QString(msg))
            mbox.exec_()
        ires = 0
        for row in range(Nrows):
            for col in range(Ncolumns):
                print "displaying cell for row,column=",row,col
                if ires<len(res):
                    res30 = res[ires]
                else:
                    #res30 = None
                    #...Instead, use the following because it forces a blank cell:
                    res30 = metrics.frontend.uvcdat.uvc_zero_plotspec()
                self.displayCell( res30, row, col )
                ires += 1
        # Here's the old loop, with messages omitted.  The above new loop will clear all the panes.
        #row = 0 
        #column = 0
        #for res30 in res:
        #     if row>=Nrows:
        #        break
        #    self.displayCell(res30,row,column)
        #    column+=1
        #    if column == Ncolumns:
        #        column=0
        #        row+=1
        print "Finished"

    def displayCell(self,res30,row,column,sheet="Sheet 1"):
        """Display result into one cell defined by row/column args"""
        global original_gm_attributes
        projectController = self.parent().get_current_project_controller()
        projectController.clear_cell(sheet,row,column) # There's no visible clearing!
        #...This is necessary to make the cell internally clear; without it the new plot
        # will be overlaid over the old plot.  But this isn't enough to give you a blank cell
        if res30 is None:
            return
        pvars = res30.vars
        labels = res30.labels
        title = res30.title
        presentation = res30.presentation
        print "pvars:",[p.id for p in pvars]
        print "labels:",labels
        print "title:",title
        print "presentation:",presentation
        print "x min,max:",presentation.datawc_x1, presentation.datawc_x2
        print "y min,max:",presentation.datawc_y1, presentation.datawc_y2
        print "res",res30.type
        #define where to drag and drop
        import cdms2
        from packages.uvcdat_cdms.init import CDMSVariable
        for V in pvars:
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
            varDropInfo = (name_in_var_widget, sheet, row, column)
            projectController.variable_was_dropped(varDropInfo)

            # Trying to add method to plot list....
            #from gui.application import get_vistrails_application
            #_app = get_vistrails_application()
            #d = _app.uvcdatWindow.dockPlot
            # simulate drop plot
            pm = projectController.plot_manager
            #print pm._plot_list.keys()
            V=pm._plot_list["VCS"]
            #print V.keys()
            gm = res30.presentation
            from gui.uvcdat.uvcdatCommons import gmInfos
            Gtype = res30.type
            G = V[Gtype]
            #print "G:",G.keys()
            #print get_canvas().listelements(Gtype.lower())
            if not gm.name in G.keys():
                G[gm.name] = pm._registry.add_plot(gm.name,"VCS",None,None,Gtype)
                G[gm.name].varnum = int(gmInfos[Gtype]["nSlabs"])
                
            #add initial attributes to global dict
            canvas = get_canvas()
            method_name = "get"+Gtype.lower()
            attributes = get_gm_attributes(Gtype)

            attrs = {}
            for attr in attributes:
                attrs[attr] = getattr(gm,attr)
            original_gm_attributes[Gtype][gm.name] = InstanceObject(**attrs)
                
            plot = projectController.plot_manager.new_plot('VCS', Gtype, gm.name )
            #plot = projectController.plot_manager.new_plot('VCS', Gtype, "default" )
            plotDropInfo = (plot, sheet, row, column)
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
