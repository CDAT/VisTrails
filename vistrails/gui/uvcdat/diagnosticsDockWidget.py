from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem
     
from ui_diagnosticsDockWidget import Ui_DiagnosticDockWidget
import tempfile

import metrics.frontend.uvcdat
from metrics.frontend.options import Options
import metrics.frontend.defines as defines

import metrics.fileio.findfiles
import metrics.packages.diagnostic_groups
from metrics.common.utilities import natural_sort

class DiagnosticsDockWidget(QtGui.QDockWidget, Ui_DiagnosticDockWidget):
   dg_menu = metrics.packages.diagnostic_groups.diagnostics_menu()  # typical item: 'AMWG':AMWG
   diagnostic_set_name = "Not implemented"
   # for now. ugly though. needs fixed.
   opts = Options()
   observation1 = None
   observations1 = None
   observation2 = None
   observations2 = None
   ft1 = None
   ft2 = None
   obsft1 = None
   obsft2 = None
   useObs1 = 0
   useObs2 = 0
   useDS1 = 0
   useDS2 = 0
   ds1path = ''
   ds2path = ''
   obs1path = ''
   obs2path = ''
   dfiles1 = None
   dfiles2 = None
   obs1files = None
   obs2files = None
   ds_menu = None
   region_box = None
   Types = dg_menu.keys()
   standard_alltypes = ["AMWG","LMWG","OMWG", "PCWG", "MPAS", "WGNE", "Metrics"]
   DisabledTypes = list( set(standard_alltypes) - set(Types) )
   AllTypes = Types + DisabledTypes

   def __init__(self, parent=None):
      super(DiagnosticsDockWidget, self).__init__(parent)
      self.setupUi(self)
      
      import metrics.frontend.uvcdat
      import os
      # For speed of entry; these will be set to '/' for the real check-in.
      self.DS1PathLabel.setText('/')
      self.opts._opts['path'].append(str(self.DS1PathLabel.text()))
      self.DS2PathLabel.setText('/')
      self.opts._opts['path'].append(str(self.DS2PathLabel.text()))
      self.obs1PathLabel.setText('/')
      self.opts._opts['obspath'].append(str(self.obs1PathLabel.text()))
      self.obs2PathLabel.setText('/')
      self.opts._opts['obspath'].append(str(self.obs2PathLabel.text()))
        
      self.tmppth = os.path.join(os.environ['HOME'],"tmp")
      if not os.path.exists(self.tmppth):
         os.makedirs(self.tmppth)

      self.DiagnosticGroup = None
      self.diagnostic_set = None
      self.variables = ['N/A',]
      self.seasons = None # will be set when DiagnosticGroup is made

      # some of this is set in the .ui file, but make sure we have a knonw, consistent state anyway
      self.DS1checkBox.setEnabled(True)
      self.DS2checkBox.setEnabled(True)
      self.Obs1checkBox.setEnabled(True)
      self.Obs2checkBox.setEnabled(True)
#       self.obs1TranslateCheck.setChecked(False)
#       self.obs2TranslateCheck.setChecked(False)

      # disable/hide stuff for now
      # Presumably ds1 will be used; at least since it starts off checked, it probably should be enabled
      self.changeState('ds1', True)
      self.changeState('ds2', False)
      self.changeState('obs1', False)
      self.changeState('obs2', False)

      self.DS2GroupBox.setVisible(False)
      self.obs1GroupBox.setVisible(False)
      self.obs2GroupBox.setVisible(False)

      # only used by a few lmwg sets currently
      self.RegionLabel.setEnabled(False)
      self.comboBoxRegion.setEnabled(False)
      
      # only used by a few amwg sets currently
      self.VarOptionsLabel.setEnabled(False)
      self.comboBoxAux.setEnabled(False)

      self.checkedItem = None
        
      # Add to the top-level menu
      self.setupDiagnosticsMenu()
        
      # Populate the types first.
      self.comboBoxType.addItems(DiagnosticsDockWidget.Types)

      # setup signals
      self.comboBoxType.currentIndexChanged.connect(self.setupDiagnosticTree)
      self.comboBoxVar.currentIndexChanged.connect(self.variableChanged)
      self.comboBoxRegion.currentIndexChanged.connect(self.regionChanged)

      self.treeWidget.itemChanged.connect(self.itemChecked)
      self.treeWidget.itemActivated.connect(self.itemActivated)
      self.treeWidget.itemClicked.connect(self.plotsetchanged)
      
      self.DS1checkBox.stateChanged.connect(self.DS1Changed)
      self.DS2checkBox.stateChanged.connect(self.DS2Changed)
      self.Obs1checkBox.stateChanged.connect(self.obs1Changed)
      self.Obs2checkBox.stateChanged.connect(self.obs2Changed)

      self.pickDS1Path.clicked.connect(self.setDS1Path)
      self.pickDS2Path.clicked.connect(self.setDS2Path)
      self.pickObs1Path.clicked.connect(self.setObs1Path)
      self.pickObs2Path.clicked.connect(self.setObs2Path)

#       self.obs1TranslateCheck.stateChanged.connect(self.obs1trans)
#       self.obs2TranslateCheck.stateChanged.connect(self.obs2trans)

      self.comboBoxSeason.setEnabled(False)
      self.comboBoxVar.setEnabled(False)

      self.buttonBox.clicked.connect(self.buttonClicked)

#      self.comboBoxSeason.addItems(['Seasons'])
#      self.comboBoxRegion.addItems(['Regions'])
#      self.comboBoxVar.addItems(['Variables'])
#      self.comboBoxAux.addItems(['Var Options'])
      # that's basically all we can/should do until someone selects some directories, etc
      # disable some widgets until the metrics code implements the feature. perhaps these should be hidden instead?

#       self.DS1ShortnameEdit.setEnabled(False)#
#       self.DS1TimeRangeCheck.setEnabled(False)
#       self.DS1StartLabel.setEnabled(False)
#       self.DS1StartEdit.setEnabled(False)
#       self.DS1EndLabel.setEnabled(False)
#       self.DS1EndEdit.setEnabled(False)
#       self.DS2ShortnameEdit.setEnabled(False)
#       self.DS2TimeRangeCheck.setEnabled(False)
#       self.DS2StartLabel.setEnabled(False)
#       self.DS2StartEdit.setEnabled(False)
      #self.DS2EndLabel.setEnabled(False)
#       self.DS2EndEdit.setEnabled(False)
#       self.obs1TranslateCheck.setEnabled(False)
#       self.obs2TranslateCheck.setEnabled(False)


   # used for enabling/disabling controls en masse
   def changeState(self, field, value):
      if field == 'ds1':
         self.pickDS1Path.setEnabled(value)
         self.DS1PathLabel.setEnabled(value)
#          self.DS1ShortnameEdit.setEnabled(value)#
         self.DS1FilterEdit.setEnabled(value)
         self.DS1FilterLabel.setEnabled(value)
#         self.DS1TimeRangeCheck.setEnabled(value)
#         self.DS1StartLabel.setEnabled(value)
#         self.DS1StartEdit.setEnabled(value)
#         self.DS1EndLabel.setEnabled(value)
#         self.DS1EndEdit.setEnabled(value)
         self.useDS1 = value
      if field == 'ds2':
         self.pickDS2Path.setEnabled(value)
         self.DS2PathLabel.setEnabled(value)
#          self.DS2ShortnameEdit.setEnabled(value)
         self.DS2FilterEdit.setEnabled(value)
         self.DS2FilterLabel.setEnabled(value)
#         self.DS2TimeRangeCheck.setEnabled(value)
#         self.DS2StartLabel.setEnabled(value)
#         self.DS2StartEdit.setEnabled(value)
#         self.DS2EndLabel.setEnabled(value)
#         self.DS2EndEdit.setEnabled(value)
         self.useDS2 = value
      if field == 'obs1':
         self.obs1PathLabel.setEnabled(value)
         self.pickObs1Path.setEnabled(value)
#         self.obs1TranslateCheck.setEnabled(value)
         self.comboBoxObservation1.setEnabled(value)
         self.useObs1 = value
      if field == 'obs2':
         self.obs2PathLabel.setEnabled(value)
         self.pickObs2Path.setEnabled(value)
#         self.obs2TranslateCheck.setEnabled(value)
         self.comboBoxObservation2.setEnabled(value)
         self.useObs2 = value

   def ds1Enabled(self, state):
      self.changeState('ds1', button)

   def ds2Enabled(self, button):
      self.changeState('ds2', button)

   def obs1Enabled(self, button):
      self.changeState('obs1', button)

   def obs2Enabled(self, button):
      self.changeState('obs2', button)

   def regionChanged(self, index):
      rl = defines.all_regions.keys()
      rl.sort()
      if index != -1:
         self.region_box = defines.all_regions[rl[index]]
      else:
         self.region_box = None

   def obs1trans(self, state):
      print 'This is for translating var names between datasets and obs sets'
      print 'obs1 trans clicked - state: ', state
      pass

   def obs2trans(self, state):
      print 'This is for translating var names between datasets and obs sets'
      print 'obs2 trans clicked - state: ', state
      pass

   def setObs1Path(self, button):
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Observations 1 Path", self.obs1PathLabel.text())
      p = str(pa)
      self.obs1PathLabel.setText(p)
      self.opts._opts['obspath'][0] = p
      self.prepareObs1()

   def setObs2Path(self, button):
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Observations 2 Path", self.obs2PathLabel.text())
      p = str(pa)
      self.obs2PathLabel.setText(p)
      self.opts._opts['obspath'][1] = p
      self.prepareObs2()

   def setDS1Path(self, button):
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Dataset 1 Path", self.DS1PathLabel.text())
      p = str(pa)
      self.DS1PathLabel.setText(p)
      self.opts._opts['path'][0] = p
      self.prepareDS1()

   def setDS2Path(self, button):
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Dataset 2 Path", self.DS2PathLabel.text())
      p = str(pa)
      self.DS2PathLabel.setText(p)
      self.opts._opts['path'][1] = p
      self.prepareDS2()

   def prepareDS1(self):
      if self.opts._opts['path'][0] == None:
         print 'No dataset1 path selected'
      else:
         self.dfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, pathid=0)
         self.ft1 = metrics.fileio.filetable.basic_filetable(self.dfiles1, self.opts)
         self.setupDiagnosticTree(self.comboBoxType.currentIndex())

   def prepareDS2(self):
      if self.opts._opts['path'][1] == None:
         print 'No dataset2 path selected'
      else:
         self.dfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, pathid=1)
         self.ft2 = metrics.fileio.filetable.basic_filetable(self.dfiles2, self.opts)
         self.setupDiagnosticTree(self.comboBoxType.currentIndex())

   def prepareObs1(self):
      if self.opts._opts['obspath'][0] == None:
         print 'No observation directory selected'
      else:
         print 'Processing observation data in ', self.opts._opts['obspath'][0]
         self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0,
                                                                     path=self.opts['obspath'][0],
                                                                     filter=self.opts['filter2'])
         #self.obsft1 = metrics.fileio.filetable.basic_filetable(self.obsfiles1, self.opts)

         self.observations1 = None
         self.obs1_menu = self.obsfiles1.check_filespec()
         if type(self.obs1_menu) is dict:
            self.observations1 = self.obs1_menu.keys()
         self.diagnostic_set_name = "Not implemented"
         if self.observations1==None:
            print "WARNING: No data found for observations directory"
         if type(self.observations1) is list:
            self.observations1.sort()
            self.comboBoxObservation1.setDuplicatesEnabled(False)
            self.comboBoxObservation1.addItems(self.observations1)
            i = self.comboBoxObservation1.findText("NCEP")
            self.comboBoxObservation1.setCurrentIndex(i)

         if type(self.observations1) is list:
            self.observation1 = str(self.comboBoxObservation1.currentText())
            if(len(self.observation1) > 0):
               self.opts._opts['filter2'] = self.obs1_menu[self.observation1]
            else:
               self.opts._opts['filter2'] = None
         else:
            self.opts._opts['filter2'] = None

         self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0,
                                                                     path=self.opts['obspath'][0],
                                                                     filter=self.opts['filter2'])
         self.obsft1 = metrics.fileio.filetable.basic_filetable(self.obsfiles1, self.opts)
         #self.obsft = self.obsfiles.setup_filetable(self.tmppth, "obs")
         # obs should be populated now

   def prepareObs2(self):
      if self.opts._opts['obspath'][1] == None:
         print 'No observation directory selected'
      else:
         print 'Processing observation data in ', self.opts._opts['obspath'][1]
         self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=1,
                                                                     path=self.opts['obspath'][1],
                                                                     filter=self.opts['filter2'])
         #self.obsft2 = metrics.fileio.filetable.basic_filetable(self.obsfiles2, self.opts)


         self.observations2 = None
         self.obs2_menu = self.obsfiles2.check_filespec()
         if type(self.obs2_menu) is dict:
            self.observations2 = self.obs2_menu.keys()
         self.diagnostic_set_name = "Not implemented"
         if self.observations2==None:
            print "WARNING: No data found for observations directory"
         if type(self.observations2) is list:
            self.observations2.sort()
            self.comboBoxObservation2.setDuplicatesEnabled(False)
            self.comboBoxObservation2.addItems(self.observations2)
            i = self.comboBoxObservation2.findText("NCEP")
            self.comboBoxObservation2.setCurrentIndex(i)

         if type(self.observations2) is list:
            self.observation2 = str(self.comboBoxObservation2.currentText())
            self.opts._opts['filter2'] = self.obs2_menu[self.observation2]
         else:
            self.opts._opts['filter2'] = None

         self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=1,
                                                                     path=self.opts['obspath'][1],
                                                                     filter=self.opts['filter2'])
         self.obsft2 = metrics.fileio.filetable.basic_filetable(self.obsfiles2, self.opts)
         #self.obsft = self.obsfiles.setup_filetable(self.tmppth, "obs")
         # obs should be populated now


   # This adds the main menu field and adds the event handlers for each diagnostic type
   # selected via the main menu or the combobox
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
        
#### NEXT EDITS HERE FOR DS1 vs DS2 vs OBS....
   def plotsetchanged(self,item,column):
      import metrics.frontend.uvcdat
      txt = str(item.text(item.columnCount()-1))
      ##      print 'need to call init for the thing that was just selected to get pre_compute done'
      
      if 'REGIONAL' in txt.upper():
         rl = defines.all_regions.keys()
         rl.sort()
         for i in range(self.comboBoxRegion.count()):
            self.comboBoxRegion.removeItem(0)
         self.comboBoxRegion.addItems(rl)
         self.RegionLabel.setEnabled(True)
         self.comboBoxRegion.setEnabled(True)
      else:
         self.RegionLabel.setEnabled(False)
         self.comboBoxRegion.setEnabled(False)
         for i in range(self.comboBoxRegion.count()):
            self.comboBoxRegion.removeItem(0)
         

      if self.useObs1 == True:
         if type(self.observations1) is list:
            self.observation1 = str(self.comboBoxObservation1.currentText())
            if type(self.observation1) is str and len(self.observation1) > 0:
               self.opts._opts['filter2'] = self.obs1_menu[self.observation1]
            else:
               self.opts._opts['filter2'] = None
         else:
            self.opts._opts['filter2'] = None

         self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0,
                                                                     path=self.opts['obspath'][0],
                                                                     filter=self.opts['filter2'])
         self.obsft1 = metrics.fileio.filetable.basic_filetable(self.obsfiles1, self.opts)
#         self.obsft = self.obsfiles.setup_filetable(self.tmppth, "obs")

      if self.useObs2 == True:
         if type(self.observations2) is list:
            self.observation2 = str(self.comboBoxObservation2.currentText())
            if type(self.observation2) is str and len(self.observation2) > 0:
               self.opts._opts['filter2'] = self.obs2_menu[self.observation2]
            else:
               self.opts._opts['filter2'] = None
         else:
            self.opts._opts['filter2'] = None

         self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=1,
                                                                     path=self.opts['obspath'][1],
                                                                     filter=self.opts['filter2'])
         self.obsft2 = metrics.fileio.filetable.basic_filetable(self.obsfiles2, self.opts)
#         self.obsft = self.obsfiles.setup_filetable(self.tmppth, "obs")

      self.diagnostic_set_name = str(item.text(column))

      varlist = []
      vtmp = []

      if self.useDS1 == True:
         vtmp = self.DiagnosticGroup.list_variables(self.ft1, diagnostic_set_name = self.diagnostic_set_name)
         varlist = vtmp
      if self.useDS2 == True:
         vtmp = self.DiagnosticGroup.list_variables(self.ft2, diagnostic_set_name = self.diagnostic_set_name)
         varlist = list(set(varlist) & (set(vtmp)))
      if self.useObs1 == True:
         vtmp = self.DiagnosticGroup.list_variables(self.obsft1, diagnostic_set_name = self.diagnostic_set_name)
         varlist = list(set(varlist) & (set(vtmp)))
      if self.useObs2 == True:
         vtmp = self.DiagnosticGroup.list_variables(self.obsft2, diagnostic_set_name = self.diagnostic_set_name)
         varlist = list(set(varlist) & (set(vtmp)))

###      var1 = []
###      var2 = []
###      var3 = []
###      var4 = []
###      print 'PLOTSET CALLING LIST_VARS with set_name ', self.diagnostic_set_name
###      print type(self.diagnostic_set_name)
###      print self.DiagnosticGroup
###      print 'THAT WAS DIAGNOSTIC GROUP'
###
###      #diagnostic = str(self.checkedItem.text(0))
####      print 'calling ds_menu[',diagnostic
###      print 'self.diagname: ', self.diagnostic_set_name
###      if self.useDS1 == True:
###         var1 = self.DiagnosticGroup.list_variables(self.ft1, diagnostic_set_name = self.diagnostic_set_name)
####         obj = self.ds_menu[str(self.diagnostic_set_name)](self.ft1, None, None, None, aux=None)
####         var1 = obj.varlist
###      if self.useDS2 == True:
###         var2 = self.DiagnosticGroup.list_variables(self.ft2, diagnostic_set_name = self.diagnostic_set_name)
####         obj = self.ds_menu[str(self.diagnostic_set_name)](self.ft2, None, None, None, aux=None)
####         var2 = obj.varlist
###      if self.useObs1 == True:
###         var3 = self.DiagnosticGroup.list_variables(self.obsft1, diagnostic_set_name = self.diagnostic_set_name)
####         obj = self.ds_menu[str(self.diagnostic_set_name)](self.obsft1, None, None, None, aux=None)
####         var3 = obj.varlist
###      if self.useObs2 == True:
###         var4 = self.DiagnosticGroup.list_variables(self.obsft2, diagnostic_set_name = self.diagnostic_set_name)
####         obj = self.ds_menu[str(self.diagnostic_set_name)](self.obsft2, None, None, None, aux=None)
####      if self.useDS1 == 1:
####         var1 = self.DiagnosticGroup.list_variables(self.ft1, diagnostic_set_name=self.diagnostic_set_name)
####      if self.useDS2 == 1:
####         var2 = self.DiagnosticGroup.list_variables(self.ft2, diagnostic_set_name=self.diagnostic_set_name)
####      if self.useObs == 1:
####         var3 = self.DiagnosticGroup.list_variables(self.obsft, diagnostic_set_name=self.diagnostic_set_name)
###
###      print 'GOT VARS LISTS'
###      varset = set(var1).union(set(var2)).union(set(var3)).union(set(var4))
###      vars = list(varset)

      varlist.sort()
      self.variables = varlist

      for i in range(self.comboBoxVar.count()):
         self.comboBoxVar.removeItem(0)

      self.comboBoxVar.addItems(self.variables)
      self.comboBoxVar.setEnabled(True)
      self.comboBoxSeason.setEnabled(True)

#### variableChanged needs connected to comboBoxVar changes        
   def variableChanged(self, index):
      ## populate the aux menu, if appropriate
      self.varmenu = self.DiagnosticGroup.all_variables(self.ft1, self.ft2, self.diagnostic_set_name)
      varname = str(self.comboBoxVar.currentText())

      if varname in self.varmenu.keys():
         variable = self.varmenu[varname]( varname, self.diagnostic_set_name, self.DiagnosticGroup )
         self.auxmenu = variable.varoptions()
      else:
         self.auxmenu = None
      for i in range(self.comboBoxAux.count()):
         self.comboBoxAux.removeItem(0)
      self.comboBoxAux.setEnabled(False)
      if self.auxmenu is not None:
         self.comboBoxAux.addItems( sorted(self.auxmenu.keys()) )
         self.comboBoxAux.setEnabled(True)

   def setupDiagnosticTree(self, index):
      if index == -1:
         index = 0
      diagnosticType = str(self.comboBoxType.itemText(index))
      self.treeWidget.clear()
#      self.treeWidget.itemChanged.connect(self.plotsetchanged)
      self.DiagnosticGroup = DiagnosticsDockWidget.dg_menu[diagnosticType]()
      # ds_menu and seasons depend on self.DiagnosticGroup (only), so they are best
      # set right after self.DiagnosticGroup is set...
      self.ds_menu = self.DiagnosticGroup.list_diagnostic_sets()
      self.seasons = self.DiagnosticGroup.list_seasons()
      # Note that the following loop calls plotsetchanged()
      for diagnostic_set in natural_sort(self.ds_menu.keys()):
         diagnosticItem = QtGui.QTreeWidgetItem(self.treeWidget, [diagnostic_set])
         diagnosticItem.setFlags(diagnosticItem.flags() & (~Qt.ItemIsSelectable))
         diagnosticItem.setCheckState(0, Qt.Unchecked)

      for i in range(self.comboBoxSeason.count()):
         self.comboBoxSeason.removeItem(0)
      self.comboBoxSeason.addItems(self.seasons)

      # no variables should be available yet
      self.comboBoxVar.addItems(['Select Diag Set'])
      self.comboBoxRegion.addItems(['Region'])
      self.comboBoxAux.addItems(['Var Options'])
      self.comboBoxVar.setEnabled(False)
      self.comboBoxSeason.setEnabled(False)


        
   def obs1Changed(self, state):
      if state == QtCore.Qt.Checked:
         self.useObs1 = 1
         self.obs1GroupBox.setEnabled(True)
         self.obs1GroupBox.setVisible(True)
         self.changeState('obs1', True)
      else:
         self.useOBs1 = 0
         self.obs1GroupBox.setEnabled(False)
         self.obs1GroupBox.setVisible(False)
         self.changeState('obs1', False)

   def obs2Changed(self, state):
      if state == QtCore.Qt.Checked:
         self.useObs2 = 1
         self.obs2GroupBox.setEnabled(True)
         self.obs2GroupBox.setVisible(True)
         self.changeState('obs2', True)
      else:
         self.useOBs2 = 0
         self.obs2GroupBox.setEnabled(False)
         self.obs2GroupBox.setVisible(False)
         self.changeState('obs2', False)

   def DS1Changed(self, state):
      if state == QtCore.Qt.Checked:
         self.useDS1 = 1
         self.DS1GroupBox.setEnabled(True)
         self.DS1GroupBox.setVisible(True)
         self.changeState('ds1', True)
      else:
         self.useDS1 = 0
         # should we hide DS1 groupbox?
         self.DS1GroupBox.setEnabled(False)
         self.changeState('ds1', False)

   def DS2Changed(self, state):
      if state == QtCore.Qt.Checked:
         self.useDS2 = 1
         self.DS2GroupBox.setEnabled(True)
         self.DS2GroupBox.setVisible(True)
         self.changeState('ds2', True)
      else:
         self.useDS2 = 0
         self.DS2GroupBox.setEnabled(False)
         self.DS2GroupBox.setVisible(False)
         self.changeState('ds2', False)

   def buttonClicked(self, button):
        role = self.buttonBox.buttonRole(button) 
        if role == QtGui.QDialogButtonBox.ApplyRole:
            self.applyClicked()
        elif role == QtGui.QDialogButtonBox.RejectRole:
            self.cancelClicked()
            
            ### NEEDS EDITED
   def applyClicked(self):
        from metrics.frontend.uvcdat import setup_filetable, get_plot_data, diagnostics_template

        if self.checkedItem is None:
            msg = "Please choose a diagnostic to plot."
            mbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning, msg, QString(msg))
            mbox.exec_()
            return None
        diagnostic = str(self.checkedItem.text(0))
        #group = str(self.checkedItem.parent().text(0))
        #Never name something 'type', it's a reserved word! type = str(self.comboBoxType.currentText())
        variable = str(self.comboBoxVar.currentText())
        auxname = str(self.comboBoxAux.currentText())
        season = str(self.comboBoxSeason.currentText())

        # region_box was set when region was clicked.
        print "diagnostic: %s" % diagnostic
        print "observation1: %s" % self.observation1
        print "observation2: %s" % self.observation2
        print "variable: %s" % variable
        print "auxiliary option: %s" % auxname
        print "region_box: %s" %self.region_box
        print "season: %s" % season
        # initial test, first cut:
        # This stuff should go elsewhere...
        import os
        #...was self.filetable2 = setup_filetable(self.path2,self.tmppth,search_filter=filt2)
        # ( replacement moved to __init__ and plotsetchanged)
        ft2 = None
        ft1 = None
        if(self.useDS1 == 1): #ds1
            ft1 = self.ft1
            if(self.useDS2 == 1):
               ft2 = self.ft2
            if(self.useObs1 == 1):
               ft2 = self.obsft1
            if(self.useObs2 == 1):
               ft2 = self.obsft2
        elif self.useDS2 == 1: #just ds2, or ds2+obs
            ft1 = self.ft2
            if(self.useObs1 == 1):
               ft2 = self.obsft1
            if(self.useObs2 == 1):
               ft2 = self.obsft2
        else: # just observation
            if(self.useObs1 == 1):
               ft1 = self.obsft1
            if(self.useObs2 == 1):
               ft2 = self.obsft2

        if(ft1 == None):
            return 
        
        if self.auxmenu is None:
            aux = None
        else:
            aux = self.auxmenu[auxname]


         ### ADDED STR() HERE. NOT SURE IF IT WAS NEEDED YET ###
        self.diagnostic_set_name = str(diagnostic)
        self.plot_spec = self.ds_menu[diagnostic](ft1, ft2, variable, season, self.region_box, aux)

        ps = self.plot_spec
        if ps is None:
            print "Can't plot, plot_set is None!!!!"
            return None
        res = ps.results()
        if res is None:
            print "Can't plot, plot_set results were None!"
            return None


        tabcont = self.parent().spreadsheetWindow.get_current_tab_controller()
        for t in tabcont.tabWidgets:
            dim = t.getDimension()
            Nrows = dim[0]
            Ncolumns = dim[1]
        if type(res) is not list:
            res = [res]

        # I'm keeping this old message as a reminder of scrollable panes, a feature which would be
        # nice to have in the future (but it doesn't work now)...
        #mbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"This diagnostics generated more rows than the number currently disaplyed by your spreadsheet, don't forget to scroll down")

        if len(res)>Nrows*Ncolumns:
            msg = "This diagnostics generated a composite of %s simple plots, which is more than your spreadsheet can display."%len(res)
            mbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning, msg, QString(msg))
            mbox.exec_()
        ires = 0
        for row in range(Nrows):
            for col in range(Ncolumns):
               print 'displaying cell for row, col: ', row, col
               if ires<len(res):
                  res30 = res[ires]
               else:
                  res30 = None
               self.displayCell(res30, row, col)
               ires += 1

   def displayCell(self, res30, row, column, sheet="Sheet 1"):
      """Display result into one cell defined by row/col args"""
      projectController = self.parent().get_current_project_controller()
      projectController.get_sheet_widget(sheet).deleteCell(row,column)
      projectController.enable_animation = False  # I (JfP) don't know why I need this, it didn't
                                                  # used to be necessary.
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
      from core.utils import InstanceObject

      from metrics.frontend.uvcdat import diagnostics_template
      tm = diagnostics_template()  # template name is 'diagnostic'
      for V in pvars:
         V.title = title        # VCS looks the title of the variable, not the plot.
         V.long_name = V.title  # VCS overrides title with long_name!
         tmplDropInfo = ('diagnostic', sheet, row, column)
         projectController.template_was_dropped(tmplDropInfo)
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
         V=pm._plot_list["VCS"]
         gm = res30.presentation
         from packages.uvcdat_cdms.init import get_canvas, get_gm_attributes, original_gm_attributes
         from gui.uvcdat.uvcdatCommons import gmInfos
         Gtype = res30.type
         G = V[Gtype]
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
   def itemActivated(self, item):
      print 'ITEM ACTIVATED. SET UP VAR LIST NOW'
      pass

   def itemClicked(self, item, column):
      print 'itemClicked called. This should not have occurred.'
#      print 'THIS SHOULDNT BE CALLED'
      quit()
      if column == 0:
         if item.checkState(column) == Qt.Checked:
            self.diagnostic_set_name = str(item.text(column))
            var1 = []
            var2 = []
            var3 = []
            var4 = []
            print 'itemCLICKED Calling list_vars'
            print self.DiagnosticGroup
            if self.useDS1 == 1:
               var1 = self.DiagnosticGroup.list_variables(self.ft1, self.diagnostic_set_name)
            if self.useDS2 == 1:
               var2 = self.DiagnosticGroup.list_variables(self.ft2, self.diagnostic_set_name)
            if self.useObs1 == 1:
               var3 = self.DiagnosticGroup.list_variables(self.obsft1, self.diagnostic_set_name)
            if self.useObs2 == 1:
               var4 = self.DiagnosticGroup.list_variables(self.obsft2, self.diagnostic_set_name)
            print 'GOT VARS LISTS. Eventually this hsould be intersection not union'
            varset = set(var1).union(set(var2)).union(set(var3)).union(set(var4))
            vars = list(varset)
            vars.sort()
            self.variables = vars
            for i in range(self.comboBoxVar.count()):
               self.comboBoxVar.removeItem(0)

            self.comboBoxVar.addItems(self.variables)

