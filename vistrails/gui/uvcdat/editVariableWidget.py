###############################################################################
#                                                                             #
# Module:       variable editor module                                        #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.llnl.gov/                             #
#                                                                             #
# Description:  UV-CDAT GUI variable editor.                                  #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
from PyQt4 import QtCore,QtGui
from gui.common_widgets import QDockPushButton
from gui.application import get_vistrails_application

class editVariableWidget(QtGui.QWidget):
    def __init__(self,var,parent=None,root=None):
        QtGui.QWidget.__init__(self,parent=parent)
        self.parent=parent
        self.var=var
        try:
            self.root=parent.root
        except:
            self.root=None
        if root is not None:
            self.root=root
          
        self.it=None
        for self.it in parent.getItems(project=False):
            #print var.id,it.projects,it.variable.id,var.__class__,it.variable.__class__
            if self.it.variable is var:
                break
            self.it=None

        l = QtGui.QVBoxLayout()
        self.setLayout(l)
        self.title = QtGui.QLabel("Edit Variable: %s" % var.id)
        self.parent.setWindowTitle("Edit Variable: %s" % var.id)
        l.addWidget(self.title)
        self.modified = False

        projectGroup=QtGui.QGroupBox("Edit Projects")
        l.addWidget(projectGroup)
        v=QtGui.QVBoxLayout()
        self.b=QtGui.QButtonGroup()
        self.b.setExclusive(False)
        for i in range(self.root.workspace.treeProjects.topLevelItemCount()):
            j= i % 3
            if j==0:
                if i!=0 :
                    h=QtGui.QHBoxLayout()
                    v.addLayout(h)
                h=QtGui.QHBoxLayout()
            txt = self.root.workspace.treeProjects.topLevelItem(i).controller.name
            c=QtGui.QCheckBox(txt)
            if self.it is not None and txt in self.it.projects:
                c.setCheckState(QtCore.Qt.Checked)
            #c.stateChanged.connect(self.checkedProject)
            h.addWidget(c)
            self.b.addButton(c)
        self.b.buttonPressed.connect(self.checkedProject)
        v.addLayout(h)
        projectGroup.setLayout(v)
        
        fvar,self.varComboBox,self.varAttributeValue,self.newVarAttributeName = self.attributeEditor("Variable Attributes",self.selVarAttribute,self.modVarAttribute,self.addVarAttribute,self.delVarAttribute)
        items = sorted(list(set(var.listattributes()+['id',])))
        self.varComboBox.addItems(items)
        
        l.addWidget(fvar)
        self.varComboBox.setCurrentIndex(items.index("id"))

        ## Axes section
        faxes = QtGui.QGroupBox("Axes Attributes")
        self.axisGroup = QtGui.QVBoxLayout()
        faxes.setLayout(self.axisGroup)
        fa1 = QtGui.QFrame()
        fa1l=QtGui.QHBoxLayout()
        self.axisGroup.addWidget(fa1)
        fa1.setLayout(fa1l)
        lb = QtGui.QLabel("Axis:")
        fa1l.addWidget(lb)
        items = self.var.listdimnames()
        self.axisComboBox = QtGui.QComboBox()
        self.connect(self.axisComboBox,QtCore.SIGNAL('currentIndexChanged(const QString&)'),self.selAxis)
        #self.connect(self.axisComboBox,QtCore.SIGNAL('activated(int)'),self.selAxis)
        fa1l.addWidget(self.axisComboBox)
        self.axisFrame = QtGui.QFrame()
        self.axisComboBox.addItems(items)

        self.axisGroup.addWidget(self.axisFrame)
        l.addWidget(faxes)
        
    def checkedProject(self,b):
        txt = str(b.text())
        if b.checkState()==QtCore.Qt.Unchecked: # unchecked because when it gets here state hasn't changed yet
            if not txt in self.it.projects:
                self.it.projects.append(txt)
                proj = self.root.get_current_project_controller().name
                if txt == str(proj):
                    self.it.setHidden(False)
                _app = get_vistrails_application()
                controller = _app.uvcdatWindow.get_project_controller_by_name(txt)
                controller.add_defined_variable(self.it.cdmsVar)    
        else:
            if txt in self.it.projects:
                bsum=0
                for a in self.b.buttons():
                    bsum+=int(a.checkState())
                if bsum!=QtCore.Qt.Checked: # ok ifwe have morethan one (one would the one we want to remove)
                    self.it.projects.remove(txt)
                    proj = self.root.get_current_project_controller().name
                    if txt == str(proj):
                        self.it.setHidden(True)
                    _app = get_vistrails_application()
                    controller = _app.uvcdatWindow.get_project_controller_by_name(txt)
                    controller.remove_defined_variable(self.it.varName) 

    def selAxis(self,*args):
        nm = self.axisComboBox.currentText()
        self.axisGroup.removeWidget(self.axisFrame)
        self.axisFrame.deleteLater()
        ax = self.var.getAxis(self.var.getAxisIndex(str(self.axisComboBox.currentText())))

        self.axisFrame,self.axComboBox,self.axAttributeValue,self.newAxAttributeName = self.attributeEditor("Axis Attributes",self.selAxAttribute,self.modAxAttribute,self.addAxAttribute,self.delAxAttribute)
        items = sorted(list(set(ax.attributes.keys()+['id',])))
        self.axComboBox.addItems(items)
        self.axisGroup.addWidget(self.axisFrame)

    def modifiedOn(self):
        txt = str(self.title.text())
        if txt.find("(Modified)")>-1:
            return
        else:
            self.title.setText("%s (Modified)" % txt)
            self.parent.setWindowTitle("%s (Modified)" % txt)
        
    def attributeEditor(self,label,selFunc,modFunc,addFunc,delFunc):
        fax = QtGui.QGroupBox(label)
        lax = QtGui.QVBoxLayout()
        fax.setLayout(lax)
        fa1 = QtGui.QFrame()
        fa1l=QtGui.QHBoxLayout()
        fa1.setLayout(fa1l)
        lax.addWidget(fa1)
        p = QtGui.QComboBox()
        self.connect(p,QtCore.SIGNAL('currentIndexChanged(const QString&)'),selFunc)
        #self.connect(p,QtCore.SIGNAL('activated(int)'),self.selAxAttribute)
        fa1l.addWidget(p)
        attName = QtGui.QLineEdit()
        self.connect(attName,QtCore.SIGNAL("textEdited(const QString&)"),self.modifiedOn)
        fa1l.addWidget(attName)
        b = QDockPushButton("Modify")
        b.setFocusPolicy(QtCore.Qt.NoFocus)
        fa1l.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),modFunc)
        fa2=QtGui.QFrame()
        fa2l=QtGui.QHBoxLayout()
        fa2.setLayout(fa2l)
        lax.addWidget(fa2)
        newAttName = QtGui.QLineEdit()
        fa2l.addWidget(newAttName)
        b = QDockPushButton("Create Attribute")
        b.setFocusPolicy(QtCore.Qt.NoFocus)
        fa2l.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),addFunc)
        b = QDockPushButton("Delete Attribute")
        b.setFocusPolicy(QtCore.Qt.NoFocus)
        fa2l.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),delFunc)
        
        return fax,p,attName,newAttName


        
            
    def selAxAttribute(self):
        ax = self.var.getAxis(self.var.getAxisIndex(str(self.axisComboBox.currentText())))
        self.axAttributeValue.setText(repr(getattr(ax,str(self.axComboBox.currentText()))))

    def modAxAttribute(self):
        axName = str(self.axisComboBox.currentText())
        ax = self.var.getAxis(self.var.getAxisIndex(axName))
        attName = str(self.axComboBox.currentText())
        try:
            attValue=eval(str(self.axAttributeValue.text()).strip())
        except:
            attValue=str(self.axAttributeValue.text()).strip()

        setattr(ax,attName,attValue)
        tit = str(self.title.text()).split("(Modified)")[0]
        self.title.setText(tit)
        self.parent.setWindowTitle(tit)
        
        self.root.record("## Modify attribute %s on axis %s of variable %s" % (attName,ax.id,self.var.id))
        self.root.record("ax = %s.getAxis(%s.getAxisIndex('%s'))" % (self.var.id,self.var.id,axName))
        self.root.record("ax.%s = %s" % (attName,repr(attValue)))
        
        #provenance calls
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        controller.change_defined_variable_axis_attribute(self.var.id, axName, attName, attValue)
       
        
    def addAxAttribute(self):
        axName = str(self.axisComboBox.currentText())
        ax = self.var.getAxis(self.var.getAxisIndex(axName))
        newName=str(self.newAxAttributeName.text()).strip()
        if len(newName)==0:
            return
        atts = sorted(list(set((ax.attributes.keys()+['id',]))))
        if newName in atts:
            return
        setattr(ax,newName,"newAttribute")
        atts = sorted(list(set((ax.attributes.keys()+['id',]))))
        for i in range(len(atts)):
            if atts[i] != str(self.axComboBox.itemText(i)):
                self.axComboBox.insertItem(i,newName)
                break
        self.axComboBox.setCurrentIndex(i)
        self.root.record("## Adding a new attribute to axis %s of variable: %s" % (ax.id,self.var.id))
        self.root.record("ax = %s.getAxis(%s.getAxisIndex('%s'))" % (self.var.id,self.var.id,axName))
        self.root.record("ax.%s = 'newAttribute'" % (newName))
        
        #provenance calls
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        controller.change_defined_variable_axis_attribute(self.var.id, axName, newName, "newAttribute")
        
    def delAxAttribute(self):
        axName = str(self.axisComboBox.currentText())
        ax = self.var.getAxis(self.var.getAxisIndex(axName))
        newName=str(self.newVarAttributeName.text()).strip()
        if len(newName)==0:
            return
        atts = ax.attributes.keys()
        if not newName in atts:
            return
        delattr(ax,newName)

        for i in range(self.axComboBox.count()):
            if str(self.axComboBox.itemText(i)) == newName:
                self.axComboBox.removeItem(i)
                break
        self.axComboBox.setCurrentIndex(0)
    
        #provenance calls
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        controller.remove_defined_variable_axis_attribute(self.var.id, axName, newName)
        
    def selVarAttribute(self):
        self.varAttributeValue.setText(repr(getattr(self.var,str(self.varComboBox.currentText()))))

    def modVarAttribute(self):
        attName = str(self.varComboBox.currentText())
        try:
            attValue=eval(str(self.varAttributeValue.text()).strip())
        except:
            attValue=str(self.varAttributeValue.text()).strip()
        #in case the attribute is the variable id, storing the original one to
        #change it later in vistrails
        var_id = self.var.id
        setattr(self.var,attName,attValue)
        tit = str(self.title.text()).split("(Modified)")[0]
        self.title.setText(tit)
        self.parent.setWindowTitle(tit)
        self.root.record("## Modify attribute %s on variable %s" % (attName,self.var.id))
        self.root.record("%s.%s = %s" % (self.var.id,attName,repr(attValue)))
        
        self.root.dockVariable.widget().updateVars()
        
        #provenance calls
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        controller.change_defined_variable_attribute(var_id, attName, attValue)
        #if attName is id we need also to rename the var in the project controller
        if attName == 'id':
            controller.rename_defined_variable(var_id, attValue)
        
        #self.root.stick_main_dict_into_defvar(None)        
                    
    def addVarAttribute(self):
        newName=str(self.newVarAttributeName.text()).strip()
        if len(newName)==0:
            return
        atts = sorted(list(set((self.var.listattributes()+['id',]))))
        if newName in atts:
            return
        setattr(self.var,newName,"newAttribute")
        atts = sorted(list(set((self.var.listattributes()+['id',]))))
        self.root.record("## Adding a new attribute to variable: %s" % self.var.id)
        self.root.record("%s.%s = 'newAttribute'" % (self.var.id,newName))
        
        for i in range(len(atts)):
            if atts[i] != str(self.varComboBox.itemText(i)):
                self.varComboBox.insertItem(i,newName)
                break
        self.varComboBox.setCurrentIndex(i)
        
        #provenance calls
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        controller.change_defined_variable_attribute(self.var.id, newName, "newAttribute")
    
    def delVarAttribute(self):
        newName=str(self.newVarAttributeName.text()).strip()
        if len(newName)==0:
            return
        atts = self.var.listattributes()
        if not newName in atts:
            return
        delattr(self.var,newName)

        for i in range(self.varComboBox.count()):
            if str(self.varComboBox.itemText(i)) == newName:
                self.varComboBox.removeItem(i)
                break
        self.varComboBox.setCurrentIndex(0)
        #provenance calls
        _app = get_vistrails_application()
        controller = _app.uvcdatWindow.get_current_project_controller()
        controller.remove_defined_variable_attribute(self.var.id, newName)
