from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem
     
from ui_diagnosticsDockWidget import Ui_DiagnosticDockWidget

class DiagnosticsDockWidget(QtGui.QDockWidget, Ui_DiagnosticDockWidget):
    
    Types = ["AMWG", ]
    DisabledTypes = ["LMWG","OMWG", "PCWG", "MPAS", "WGNE", "Metrics"]
    AllTypes = Types + DisabledTypes

    def __init__(self, parent=None):
        super(DiagnosticsDockWidget, self).__init__(parent)
        self.setupUi(self)
        
        #initialize data
        #@todo: maybe move data to external file to be read in
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
        
        self.variables = sorted(set(['T','TREFHT', 'Willmott', 'TREFHT', 'Legates', 'PRECT', 'TREFHT', 'JRA25', 'PREH2O', 'PSL', 'SHFLX', 'LHFLX', 'TREFHT', 'ERA-Interim', 'PREH2O', 'PSL', 'ERA40', 'LHFLX', 'PREH2O', 'MODIS', 'PREH2O', 'TGCLDLWP', 'NVAP', 'PREH2O', 'TGCLDLWP', 'AIRS', 'PREH2O', 'Woods', 'LHFLX', 'QFLX', 'GPCP', 'PRECT', 'CMAP', 'PRECT', 'UWisc', 'TGCLDLWP', 'SSM/I', 'PRECT', 'PREH2O', 'TRMM', 'PRECT', 'Large-Yeager', 'SHFLX', 'QFLX', 'FLNS', 'FSNS', 'CERES-EBAF', 'FLUT', 'FLUTC', 'FSNTOA', 'FSNTOAC', 'LWCF', 'SWCF', 'CERES', 'FLUT', 'FLUTC', 'FSNTOA', 'FSNTOAC', 'LWCF', 'SWCF', 'ERBE', 'FLUT', 'FLUTC', 'FSNTOA', 'FSNTOAC', 'LWCF', 'SWCF', 'ISCCP', 'FLDS', 'FLDSC', 'FLNS', 'FLNSC', 'FSDS', 'FSDSC', 'FSNS', 'FSNSC', 'LWCFSRF', 'SWCFSRF', 'ISCCP', 'CLDHGH', 'CLDHGH', 'CLDLOW', 'CLDLOW', 'CLDMED', 'CLDMED', 'CLDTOT', 'CLDTOT', 'Warren', 'CLDLOW', 'CLDTOT', 'CLOUDSAT', 'CLDTOT', 'CLDLOW', 'CLDMED', 'CLDHGH', 'CFMIP', 'CALIPSO', 'CLDTOT_CAL', 'CLDLOW_CAL', 'CLDMED_CAL', 'CLDHGH_CAL', 'ISCCP-COSP', 'CLDTOT_ISCCPCOSP', 'CLDTHICK_ISCCPCOSP', 'MISR', 'CLDTOT_MISR', 'CLDTHICK_MISR', 'MODIS-COSP', 'CLDTOT_MODIS', 'CLDTHICK_MODIS', 'Additional', 'CALIPSO', 'CLDTOT_CAL', 'CLDLOW_CAL', 'CLDMED_CAL', 'CLDHGH_CAL', 'CLOUDSAT-COSP', 'CLDTOT_CS2', 'ISCCP-COSP', 'CLDTOT_ISCCPCOSP', 'CLDLOW_ISCCPCOSP', 'CLDMED_ISCCPCOSP', 'CLDHGH_ISCCPCOSP', 'CLDTHICK_ISCCPCOSP', 'MEANPTOP_ISCCPCOSP', 'MEANCLDALB_ISCCPCOSP', 'MISR', 'CLDTOT_MISR', 'CLDLOW_MISR', 'CLDMED_MISR', 'CLDHGH_MISR', 'CLDTHICK_MISR', 'MODIS-COSP', 'CLDTOT_MODIS', 'CLDLOW_MODIS', 'CLDMED_MODIS', 'CLDHGH_MODIS', 'CLDTHICK_MODIS', 'CLIMODIS', 'CLWMODIS', 'IWPMODIS', 'LWPMODIS', 'PCTMODIS', 'REFFCLIMODIS', 'REFFCLWMODIS', 'TAUILOGMODIS', 'TAUWLOGMODIS', 'TAUTLOGMODIS', 'TAUIMODIS', 'TAUWMODIS', 'TAUTMODIS']))
        self.observations = ['Obs 1', 'Obs 2', 'Obs 3']
        self.seasons = ['DJF', 'JJA', 'MJJ', 'ASO', 'ANN']
        
        #setup signals
        self.comboBoxType.currentIndexChanged.connect(self.setupDiagnosticTree)
        self.buttonBox.clicked.connect(self.buttonClicked)
        self.treeWidget.itemChanged.connect(self.itemChecked)
        
        #keep track of checked item so we can unckeck it if another is checked
        self.checkedItem = None
        
        self.setupDiagnosticsMenu()
        
        self.comboBoxType.addItems(DiagnosticsDockWidget.Types)
        self.comboBoxVariable.addItems(self.variables)
        #self.comboBoxVariable.set("TREFHT")
        self.comboBoxObservation.addItems(self.observations)
        self.comboBoxSeason.addItems(self.seasons)
        
    def setupDiagnosticsMenu(self):
        menu = self.parent().menuBar().addMenu('&Diagnostics')
        
        def generateCallBack(x):
            def callBack():
                self.diagnosticTriggered(x)
            return callBack
        
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
        
    def setupDiagnosticTree(self, index):
        diagnosticType = str(self.comboBoxType.itemText(index))
        self.treeWidget.clear()
        print "Got: ",diagnosticType,self.groups[diagnosticType]
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
        
    def buttonClicked(self, button):
        role = self.buttonBox.buttonRole(button) 
        if role == QtGui.QDialogButtonBox.ApplyRole:
            self.applyClicked()
        elif role == QtGui.QDialogButtonBox.RejectRole:
            self.cancelClicked()
            
    def applyClicked(self):

        diagnostic = str(self.checkedItem.text(0))
        #group = str(self.checkedItem.parent().text(0))
        #Never name something 'type', it's a reserved word! type = str(self.comboBoxType.currentText())
        observation = str(self.comboBoxObservation.currentText())
        variable = str(self.comboBoxVariable.currentText())
        season = str(self.comboBoxSeason.currentText())
        print "diagnostic: %s" % diagnostic
        print "observation: %s" % observation
        print "variable: %s" % variable
        print "season: %s" % season
        # initial test, first cut:
        # This stuff should go elsewhere...
        import os
        from metrics.amwg import setup_filetable, get_plot_data
        # The paths have to be chosen by the user, unless we know something about the system...
        path1 = os.path.join(os.environ["HOME"],'cam_output/b30.009.cam2.h0.06.xml')
        path2 = os.path.join(os.environ["HOME"],'obs_data')
        filt2="filt=f_startswith('NCEP')"
        filetable1 = setup_filetable(path1,os.environ['HOME']+'/tmp')
        filetable2 = setup_filetable(path2,os.environ['HOME']+'/tmp',search_filter=filt2)
        #
        plot_set = diagnostic[0:diagnostic.find('-')] # e.g. '3','4a', etc.
        ps = get_plot_data( plot_set, filetable1, filetable2, variable, season )
        if ps is None:
            print "I got back a None!!!!"
            return None
        res = ps.results()
        if res is None:
            print "Results were None!"
            return None
        # Note: it would be useful to get some immediate feedback as to whether the code is
        # busy, or finished with the current task.
        # For now, print the first result.  Really, we want to plot them all...
        if type(res) is list:
            print "res was list nothing more happens!"
            res30 = res[0]
        else:
            res30 = res
        pvars = res30.vars
        labels = res30.labels
        title = res30.title
        presentation = res30.presentation
        print "pvars:",pvars
        print "labels:",labels
        print "title:",title
        print "presentation:",presentation
        print "Finished"
            

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
