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
   obs1_menu = None
   obs2_menu = None
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
   obsfiles1 = None
   obsfiles2 = None
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
      self.DS2PathLabel.setText('/')
      self.obs1PathLabel.setText('/')
      self.obs2PathLabel.setText('/')
        
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

      self.DS1Climos.stateChanged.connect(self.DS1climosChanged)
      self.DS2Climos.stateChanged.connect(self.DS2climosChanged)

      self.pickDS1Path.clicked.connect(self.setDS1Path)
      self.pickDS2Path.clicked.connect(self.setDS2Path)
      self.pickObs1Path.clicked.connect(self.setObs1Path)
      self.pickObs2Path.clicked.connect(self.setObs2Path)

      self.comboBoxObservation1.currentIndexChanged.connect(self.obs1ListChanged)
      self.comboBoxObservation2.currentIndexChanged.connect(self.obs2ListChanged)
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
      pa = None
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Observations 1 Path", self.obs1PathLabel.text())
      if pa == None or len(pa) == 0:
         print 'BAD/NO PATH SELECTED'
         return
      p = str(pa)
      self.obs1PathLabel.setText(p)
      if len(self.opts._opts['obs']) == 0:
         self.opts._opts['obs'].append({})

      self.opts._opts['obs'][0]['path'] = p
      self.prepareObs1()

   def setObs2Path(self, button):
      pa = None
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Observations 2 Path", self.obs2PathLabel.text())
      p = str(pa)
      if pa == None or len(pa) == 0:
         print 'BAD/NO PATH SELECTED'
         return
      self.obs2PathLabel.setText(p)
      if len(self.opts._opts['obs']) == 0:
         print 'Please select a first obs set'
         return
         
      if len(self.opts._opts['obs']) == 1:
         self.opts._opts['obs'].append({})
      if len(self.opts._opts['obs']) == 2:
         self.opts._opts['obs'][1]['path'] = p

      self.prepareObs2()

   def setDS1Path(self, button):
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Dataset 1 Path", self.DS1PathLabel.text())
      p = str(pa)
      self.DS1PathLabel.setText(p)
#      print 'self.opts_opts:'
#      print self.opts._opts
#      print 'self.opts._opts[\'model\']:'
#      print self.opts._opts['model']
#      print 'done'
      if len(self.opts._opts['model']) == 0:
         self.opts._opts['model'].append({})
         self.opts._opts['model'][0]['path'] = p
      else: # must already have a model 0, just upate path
         self.opts._opts['model'][0]['path'] = p

      if self.DS1Climos.isChecked() == True:
         print 'DS1 Climos was checked'
         self.opts._opts['model'][0]['climos'] = 'yes'
      else:
         print 'DS1 climos was not checked'
         self.opts._opts['model'][0]['climos'] = 'no'

      self.prepareDS1()

   def setDS2Path(self, button):
      pa = QtGui.QFileDialog.getExistingDirectory(self, "Dataset 2 Path", self.DS2PathLabel.text())
      p = str(pa)
      self.DS2PathLabel.setText(p)
      # Do we already have a model 2? If not, add one.
      if len(self.opts._opts['model']) == 0:
         print 'Please select a model 0 first.'
         return
      if len(self.opts._opts['model']) == 1: 
         self.opts._opts['model'].append({})
         # It should now == 2.
      if len(self.opts._opts['model']) == 2:
         self.opts._opts['model'][1]['path'] = p
         if self.DS2Climos.isChecked() == True:
            print 'DS2 climos was checked'
            self.opts._opts['model'][1]['climos'] = 'yes'
         else:
            print 'DS2 climos was not checked'
            self.opts._opts['model'][1]['climos'] = 'no'

      self.prepareDS2()

   def prepareDS1(self):
      if len(self.opts._opts['model']) == 0 or self.opts._opts['model'][0]['path'] == None:
         print 'No dataset1 path selected'
      else:
         self.dsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, modelid = 0)
         self.ft1 = self.dsfiles1.setup_filetable()

#         self.ft1 = metrics.fileio.findfiles.path2filetable(self.opts, modelid = 0)
         self.setupDiagnosticTree(self.comboBoxType.currentIndex())

   def prepareDS2(self):
      if len(self.opts._opts['model']) < 2 or self.opts._opts['model'][1]['path'] == None:
         print 'No dataset2 path selected'
      else:
         self.dsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, modelid = 1)
         self.ft2 = self.dsfiles2.setup_filetable()

#         self.ft2 = metrics.fileio.findfiles.path2filetable(self.opts, modelid = 1)
         self.setupDiagnosticTree(self.comboBoxType.currentIndex())

   def filefilter_menuitem( self, filefam_menu, widget ):
#      print 'menuitum - type: ', type(filefam_menu)
      if type(filefam_menu) is dict:
         filefam = str(widget.currentText())
      else:  # filefam_menu is True or None
         filefam = ''
#      print 'returning: \'%s\''% filefam
      return filefam

   def fill_filefilter_menu(self, datafiles, widget ):
      filefams = None
      filefam_menu = datafiles.check_filespec()
      print 'filefam_menu: ', filefam_menu
#      print 'filefam_menu: ', filefam_menu
#      print 'type: ', type(filefam_menu)
      if type(filefam_menu) is dict:
         filefams = filefam_menu.keys()
      elif filefam_menu == None:
         print 'No data found in %s' % datafiles
      if type(filefams) is list:
#         print 'filefams was a list: ', filefams
         filefams.sort()
         widget.setDuplicatesEnabled(False)
         widget.addItems(filefams)
#         i = widget.findText(default)
#         widget.setCurrentIndex(max(i,0)) # 0 if findText didn't find text
         widget.setCurrentIndex(0)

      filefam = self.filefilter_menuitem(filefam_menu, widget)

      return filefams, filefam_menu, filefam
   def obs1ListChanged(self):
      # Have we already populated the obs1_menu? If so, then just update obsfiles/ft/options.
      print 'New index: ', self.comboBoxObservation1.currentText()
      self.observation1 = str(self.comboBoxObservation1.currentText())
      if self.obs1_menu != None:
         self.opts._opts['obs'][0]['filter'] = self.obs1_menu[self.observation1]
      self.prepareObs1(flag=1)

   def obs2ListChanged(self):
      print 'New index: ', self.comboBoxObservation2.currentText() 
      self.observation2 = str(self.comboBoxObservation2.currentText())
      if self.obs2_menu != None:
         self.opts._opts['obs'][1]['filter'] = self.obs2_menu[self.observation2]
      self.prepareObs2(flag=1)

   def prepareObs1(self, flag=None):
      if len(self.opts._opts['obs']) == 0 or self.opts._opts['obs'][0]['path'] == None:
         print 'No observation directory selected'
      else:
         if flag == None:
            print 'Processing observation data in ', self.opts._opts['obs'][0]['path']
            self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0)

            # So now we need to see if the user wants a filter.
            # I believe all we need to do is set up the combobox with a list of 
            # possible filters based on the obs set which has now been selected.
            # much of that work is done with check_filespec().
            # When the user clicks Apply it has to re-fetch the menu item selected
   
            self.observations1, self.obs1_menu, self.observation2 = \
               self.fill_filefilter_menu(self.obsfiles1, self.comboBoxObservation1)

            self.opts._opts['obs'][0]['filter'] = self.obs1_menu[self.observation1]
            print 'opts obs 0 filter set to: ', self.opts._opts['obs'][0]['filter']
         
         # If flag is passed just do this stuff.
#         self.opts._opts['obs'][0]['filter'] = str(self.comboBoxObservation1.currentText())

         self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0)

         self.obsft1 = self.obsfiles1.setup_filetable()

         self.updateVarList()
         # obs should be populated now

   def prepareObs2(self, flag=None):
      if len(self.opts._opts['obs']) != 2 or self.opts._opts['obs'][1]['path'] == None:
         print 'No second observation directory selected'
      else:
         if flag == None:
            print 'Processing observation data in ', self.opts._opts['obs'][1]['path']
            self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=1)

            self.observations2, self.obs2_menu, self.observation2 =\
               self.fill_filefilter_menu(self.obsfiles2, self.comboBoxObservation2)

            self.opts._opts['obs'][1]['filter'] = self.obs2_menu[self.observation2]
            print 'opts obs1 filter set to: ', self.opts._opts['obs'][1]['filter']

         self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles( self.opts, obsid=1)
         self.obsft2 = self.obsfiles2.setup_filetable()

         self.updateVarList()

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
               self.opts._opts['obs'][0]['filter'] = self.obs1_menu[self.observation1]
            else:
               self.opts._opts['obs'][0]['filter'] = None
         else:
            self.opts._opts['obs'][0]['filter'] = None

         self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0)
         #self.obsft1 = metrics.fileio.filetable.basic_filetable(self.obsfiles1, self.opts._opts)
         self.obsft1 = self.obsfiles1.setup_filetable()

      if self.useObs2 == True:
         if type(self.observations2) is list:
            self.observation2 = str(self.comboBoxObservation2.currentText())
            if type(self.observation2) is str and len(self.observation2) > 0 and len(self.opts._opts['obs']) == 2:
               self.opts._opts['obs'][1]['filter'] = self.obs2_menu[self.observation2]
            else:
               self.opts._opts['obs'][1]['filter'] = None
         else:
            if len(self.opts._opts['obs']) == 2:
               self.opts._opts['obs'][1]['filter'] = None

         self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=1)
         #self.obsft2 = metrics.fileio.filetable.basic_filetable(self.obsfiles2, self.opts._opts)
         self.obsft2 = setlf.obsfiles2.setup_filetable()

      self.diagnostic_set_name = str(item.text(column))

      varlist = []
      model = []
      obs = []
      if self.useDS1:
         model.append(self.ft1)
      if self.useDS2:
         model.append(self.ft2)
      if self.useObs1:
         obs.append(self.obsft1)
      if self.useObs2:
         obs.append(self.obsft2)
      varlist = self.DiagnosticGroup.list_variables(model, obs, diagnostic_set_name = self.diagnostic_set_name)

      varlist.sort()
      self.variables = varlist

      for i in range(self.comboBoxVar.count()):
         self.comboBoxVar.removeItem(0)

      self.comboBoxVar.addItems(self.variables)
      self.comboBoxVar.setEnabled(True)
      self.comboBoxSeason.setEnabled(True)

   def updateVarList(self):
      if self.diagnostic_set_name == "Not implemented":
         return
      else:
         varlist = []
         model = []
         obs = []
         if self.useDS1:
            model.append(self.ft1)
         if self.useDS2:
            model.append(self.ft2)
         if self.useObs1:
            obs.append(self.obsft1)
         if self.useObs2:
            obs.append(self.obsft2)
         varlist = self.DiagnosticGroup.list_variables(model, obs, diagnostic_set_name = self.diagnostic_set_name)
   
         varlist.sort()
         self.variables = varlist

         for i in range(self.comboBoxVar.count()):
            self.comboBoxVar.removeItem(0)
         self.comboBoxVar.addItems(self.variables)




#### variableChanged needs connected to comboBoxVar changes        
   def variableChanged(self, index):
      ## populate the aux menu, if appropriate
      model = []
      obs = []
      if self.ft1 != None:
         model.append(self.ft1)
      if self.ft2 != None:
         model.append(self.ft2)
      if self.obsft1 != None:
         obs.append(self.obsft1)
      if self.obsft2 != None:
         obs.append(self.obsft2)
         
      self.varmenu = self.DiagnosticGroup.all_variables(model, obs, self.diagnostic_set_name)
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

   def DS1climosChanged(self, state):
      if len(self.opts._opts['model']) >= 1: # so we have set up a model already
         if state == QtCore.Qt.Checked:
            self.opts._opts['model'][0]['climos'] = 'yes'
         else:
            self.opts._opts['model'][0]['climos'] = 'no'
      else:
         self.opts._opts['model'].append({})
         if state == QtCore.Qt.Checked:
            self.opts._opts['model'][0]['climos'] = 'yes'
         else:
            self.opts._opts['model'][0]['climos'] = 'no'

   def DS2climosChanged(self, state):
      if len(self.opts._opts['model']) == 0:
         print 'Please select at least one model.'
         return
      if len(self.opts._opts['model']) == 1:
         self.opts._opts['model'].append({})
      if len(self.opts._opts['model']) == 2:
         if state == QtCore.Qt.Checked:
            self.opts._opts['model'][1]['climos'] = 'yes'
         else:
            self.opts._opts['model'][1]['climos'] = 'no'

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

        # These are two of several cases where we need to get file (or other) information out of
        # the menus because what we have is stale.  The better approach is to update every time the
        # user does something in the menus, and sometimes there's no alternative.  But this was
        # quicker to code...
        self.observation1 = str(self.comboBoxObservation1.currentText())
        if len(self.observation1) > 0:
           if self.opts._opts['obs'][0]['filter'] != self.obs1_menu[self.observation1]:
              self.observation1 = self.filefilter_menuitem(self.obs1_menu, self.comboBoxObservation1)
              self.obsfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=0)
              self.obsft1 = self.obsfiles1.setup_filetable()
        if self.opts._opts['model'][0].get('filter', False) != False and self.DS1FilterEdit.text() != self.opts._opts['model'][0]['filter']:
           self.opts._opts['model'][0]['filter'] = self.DS1FilterEdit.text()
           self.dfiles1 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, modelid=0)
           self.ft1 = self.dfiles1.setup_filetable()
        self.observation2 = str(self.comboBoxObservation2.currentText())
        if len(self.observation2) > 0:
           if len(self.opts._opts['obs']) == 2 and self.opts._opts['obs'][0]['filter'] != self.obs2_menu[self.observation2]:
              self.observation2 = self.filefilter_menuitem(self.obs2_menu, self.comboBoxObservation2)
              self.obsfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, obsid=1)
              self.obsft2 = self.obsfiles2.setup_filetable()
        if len(self.opts._opts['model']) == 2 and self.opts._opts['model'][1].get('filter', False) != False and self.DS2FilterEdit.text() != self.opts._opts['model'][1]['filter']:
           self.opts._opts['model'][1]['filter'] = self.DS2FilterEdit.text()
           self.dfiles2 = metrics.fileio.findfiles.dirtree_datafiles(self.opts, modelid=1)
           self.ft2 = self.dfiles2.setup_filetable()

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
        model = []
        obs = []
        if self.useDS1 == 1:
            model.append(self.ft1)
        if self.useDS2 == 1:
            model.append(self.ft2)
        if self.useObs1 == 1:
            obs.append(self.obsft1)
        if self.useObs2 == 1:
            obs.append(self.obsft2)
            
        if len(model) == 0 and len(obs) == 0:
            return 
        
        if self.auxmenu is None:
            aux = None
        else:
            aux = self.auxmenu[auxname]


         ### ADDED STR() HERE. NOT SURE IF IT WAS NEEDED YET ###
        self.diagnostic_set_name = str(diagnostic)
        self.plot_spec = self.ds_menu[diagnostic](model, obs, variable, season, self.region_box, aux)

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
      if not hasattr(res30,'presentation') or res30.presentation is None or res30.presentation is "text":
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
