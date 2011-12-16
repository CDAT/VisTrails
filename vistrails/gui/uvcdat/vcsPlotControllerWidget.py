from PyQt4 import QtGui, QtCore
import vcs
import editorGraphicsMethodsWidget
import editorTemplateWidget
import graphicsMethodsWidget
import templatesWidget
import customizeUVCDAT

class QVCSPlotController(QtGui.QWidget):
    """ Widget containing plot options: plot button, plot type combobox, cell
    col and row selection combo box, and an options button """
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.parent = parent
        self.root = parent.root
        ptype = parent.plotOptions.getPlotType()
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        # First we need a vertical splitter to separate the templates/gm section from the plots section

        vsplitter = QtGui.QSplitter(QtCore.Qt.Vertical)



        ##########################################################
        # Graphics Methods and Templates Selection Section
        ##########################################################
        hlayout_choices = QtGui.QHBoxLayout()
        self.templates = templatesWidget.QTemplatesWidget(self)
        hlayout_choices.addWidget(self.templates)
        self.gms = graphicsMethodsWidget.QGraphicsMethodsWidget(ptype,self)
        hlayout_choices.addWidget(self.gms)

        self.choicesFrame =QtGui.QFrame()
        self.choicesFrame.setLayout(hlayout_choices)

        vsplitter.addWidget(self.choicesFrame)

        ##########################################################
        # Plots setup section
        ##########################################################
        parent.plotsSetup.show()
        vsplitter.addWidget(parent.plotsSetup)

        ##########################################################
        # Graphics Method and Templates editor Section
        ##########################################################
        editorFrame = QtGui.QFrame()
        vl = QtGui.QVBoxLayout()
        editorFrame.setLayout(vl)
        
        buttonsFrame = QtGui.QFrame()
        hl = QtGui.QHBoxLayout()
        
        self.apply = QtGui.QPushButton("Apply")
        self.preview = QtGui.QPushButton("Preview")
        self.discard = QtGui.QPushButton("Discard")
        self.discard.setEnabled(False)
        hl.addWidget(self.apply)
        hl.addWidget(self.preview)
        hl.addWidget(self.discard)
        buttonsFrame.setLayout(hl)
        self.editorTab = QtGui.QTabWidget()
        self.editorTab.addTab(editorTemplateWidget.QEditorTemplateWidget(self),"'%s' Template Properties" % self.templates.templateList.currentItem().text())
        self.editorTab.insertTab(1,editorGraphicsMethodsWidget.QEditorGraphicsMethodsWidget(ptype,self),"'%s' %s Graphics Method Properties" % (self.gms.gmList.currentItem().text(),ptype))
        self.editorTab.setCurrentIndex(1)

        vl.addWidget(self.editorTab)
        vl.addWidget(buttonsFrame)
        
        vsplitter.addWidget(editorFrame)


        layout.addWidget(vsplitter)
        
        self.connect(self.apply,QtCore.SIGNAL("clicked()"),self.applyChanges)
        self.connect(self.preview,QtCore.SIGNAL("clicked()"),self.previewChanges)
        self.connect(self.discard,QtCore.SIGNAL("clicked()"),self.discardChanges)
        
        
    def applyChanges(self):
        self.editorTab.widget(1).applyChanges()
        self.discard.setEnabled(False)

    def previewChanges(self):
        self.editorTab.widget(1).previewChanges()
        self.discard.setEnabled(True)

    def discardChanges(self):
        self.editorTab.widget(1).discardChanges()
        self.discard.setEnabled(False)

class QGenericPlotController(QtGui.QWidget):
    """ Widget containing plot widget for non-VCS plots
    """

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.parent = parent
        self.root = parent.root
        ptype = str(parent.plotOptions.getPlotType())
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        if customizeUVCDAT.extraPlotTypes.has_key(ptype):
            self.plot = customizeUVCDAT.extraPlotTypes[ptype]
            if self.plot.widget is not None:
                layout.addWidget(self.plot.widget)
            
        buttonsFrame = QtGui.QFrame()
        hl = QtGui.QHBoxLayout()
        
        self.apply = QtGui.QPushButton("Apply")
        self.preview = QtGui.QPushButton("Preview")
        self.discard = QtGui.QPushButton("Discard")
        self.discard.setEnabled(False)
        hl.addWidget(self.apply)
        hl.addWidget(self.preview)
        hl.addWidget(self.discard)
        buttonsFrame.setLayout(hl)

        layout.addWidget(buttonsFrame)

        self.connect(self.apply,QtCore.SIGNAL("clicked()"),self.applyChanges)
        self.connect(self.preview,QtCore.SIGNAL("clicked()"),
                     self.previewChanges)
        self.connect(self.discard,QtCore.SIGNAL("clicked()"),
                     self.discardChanges)
        
    def updateAliases(self):
        aliases = { self.plot.files[0] : self.parent.currentFileName,
                    self.plot.cells[0].row_name : str(self.parent.plotOptions.getRow()),
                    self.plot.cells[0].col_name : str(self.parent.plotOptions.getCol())
                    }
        selectVariables = self.root.dockVariable.widget().getSelectedDefinedVariables()
        if len(selectVariables) < self.plot.varnum:
            QtGui.QMessageBox.warning(self.parent,
                                      "UV-CDAT",
                                      "Plot %s requires you to select %s variable(s) \
in the definedVariables panel."%(self.plot.name,self.plot.varnum))
            return (False, {})
        for i in range(self.plot.varnum):
            aliases[self.plot.vars[i]] = selectVariables[i].id
            aliases[self.plot.axes[i]] = self.generateCommandsFromVariable(selectVariables[i])
        for a,w in self.plot.alias_widgets.iteritems():
            aliases[a] = w.contents()

        return (True, aliases)
    
    def applyChanges(self):
        ok, aliases = self.updateAliases()
        if ok:
            self.plot.applyChanges(aliases)
            self.discard.setEnabled(False)

    def previewChanges(self):
        ok, aliases = self.updateAliases()
        if ok:    
            self.plot.previewChanges(aliases)
            self.discard.setEnabled(True)

    def discardChanges(self):
        self.plot.discardChanges()
        self.discard.setEnabled(False)

    def fileChanged(self, filename):
        self.plot.alias_values[self.plot.files[0]] = filename
        
    def generateCommandsFromVariable(self, var):
        cmds = []
        axes = var.getAxisIds()
        for a,i in zip(axes,range(len(axes))):
            ax = var.getAxis(i)
            if ax.isTime() == 1:
                values = ax.asComponentTime()
                cmds.append("%s=('%s','%s')"%(a,values[0],values[-1]))
            else:
                values = ax.getValue()
                cmds.append("%s=(%s,%s)"%(a,values[0],values[-1]))
        return ",".join(cmds)
    
    def __del__(self):
        self.plot.widget.setParent(None)
        
