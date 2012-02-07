###############################################################################
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#                                                                             #
###############################################################################
from PyQt4 import QtCore,QtGui
import uvcdatCommons
import customizeUVCDAT
import os


class QPageLayoutWidget(QtGui.QWidget):
    def __init__(self,parent=None):
        hPol = QtGui.QSizePolicy.Fixed
        vPol = QtGui.QSizePolicy.Fixed
        pol = QtGui.QSizePolicy(hPol,vPol)
        QtGui.QWidget.__init__(self,parent)
        self.parent=parent
        self.root=parent.root
        self.nlines=0
        self.removeQIcon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'remove.gif'))
        self.offQIcon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'off.gif'))
        self.onQIcon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'on.gif'))

        vlayout = QtGui.QVBoxLayout()
        vlayout.setMargin(0)
        vlayout.setSpacing(0)
        
        f=QtGui.QFrame()
        f.setSizePolicy(pol)
        f.setContentsMargins(uvcdatCommons.noMargins)
        h=QtGui.QHBoxLayout()
        h.setMargin(0)
        h.setSpacing(0)
        f.setLayout(h)
        b = QtGui.QPushButton("Create New Page Layout Line")
        l = QtGui.QLabel("Page Layout Section")
        h.addWidget(l)        
        h.addWidget(b)
        vlayout.addWidget(f)

        s = QtGui.QScrollArea()
        s.setContentsMargins(uvcdatCommons.noMargins)
        f =QtGui.QFrame()
        f.setContentsMargins(uvcdatCommons.noMargins)
        f.setSizePolicy(pol)
        self.setSizePolicy(pol)
        self.vlayout = QtGui.QVBoxLayout()
        self.vlayout.setMargin(0)
        self.vlayout.setSpacing(0)
        f.setLayout(self.vlayout)
        vlayout.addWidget(s)
        self.addLine()
        s.setWidget(f)
        s.setWidgetResizable(True)
        self.setLayout(vlayout)
        self.connect(b,QtCore.SIGNAL('clicked()'),self.addLine)


    def removeLine(self,*args):
        for i in range(self.nlines):
            remove =self.vlayout.itemAt(i).widget().layout().itemAt(0).widget()
            if remove.widget.isChecked():
                self.vlayout.itemAt(i).widget().destroy()
                self.vlayout.removeItem(self.vlayout.itemAt(i))
                self.vlayout.update()
                self.nlines-=1
                break
                
    def changedPriority(self,*args):
        for i in range(self.nlines):
            line = self.vlayout.itemAt(i).widget().layout()
            n = line.count()
            
    def onOff(self):
        for i in range(self.nlines):
            line = self.vlayout.itemAt(i).widget().layout()
            n = line.count()
            onoff =line.itemAt(1).widget()
            
            if onoff.widget.isChecked():
                onoff.widget.setIcon(self.onQIcon)
                onoff.label.setText("On")
            else:
                onoff.widget.setIcon(self.offQIcon)
                onoff.label.setText("Off")
        
    def addLine(self):
        hPol = QtGui.QSizePolicy.Fixed
        vPol = QtGui.QSizePolicy.Fixed
        pol = QtGui.QSizePolicy(hPol,vPol)
        f=QtGui.QFrame()
        f.setContentsMargins(uvcdatCommons.noMargins)
        f.setSizePolicy(pol)
        h=QtGui.QHBoxLayout()
        h.setMargin(0)
        h.setSpacing(0)
        f.setLayout(h)
        
        tmp = QtGui.QToolButton()
        tmp.setIcon(self.removeQIcon)
        tmp.setCheckable(True)
        tmp.setChecked(False)
        h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"Remove",widgetSizePolicy=pol))
        self.connect(tmp,QtCore.SIGNAL("clicked()"),self.removeLine,self.nlines)
        
        tmp = QtGui.QToolButton()
        tmp.setIcon(self.onQIcon)
        tmp.setCheckable(True)
        tmp.setChecked(True)
        h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"On",widgetSizePolicy=pol))
        self.connect(tmp,QtCore.SIGNAL("clicked()"),self.onOff)
 
        tmp = uvcdatCommons.QDropLineEdit(types=["templates",])
        self.connect(tmp,QtCore.SIGNAL("droppedInto"),self.droppedTemplate)
        p = QtGui.QPalette()
        p.setBrush(p.Base,customizeUVCDAT.templatesColor)
        tmp.setPalette(p)
        tmpW=uvcdatCommons.QLabeledWidgetContainer(tmp,"Template",widgetSizePolicy=pol)
        tmpW.setToolTip("Type or drag a template from list above")
        h.addWidget(tmpW)
        tmp = uvcdatCommons.QDropLineEdit(types=["graphicmethods",])
        p = QtGui.QPalette()
        p.setBrush(p.Base,customizeUVCDAT.gmsColor)
        tmp.setPalette(p)
        self.connect(tmp,QtCore.SIGNAL("droppedInto"),self.droppedGM)
        tmpW=uvcdatCommons.QLabeledWidgetContainer(tmp,"GM",widgetSizePolicy=pol)
        tmpW.setToolTip("Type or drag a GM from list above")
        h.addWidget(tmpW)

        tmp = uvcdatCommons.QDropLineEdit(types=["definedVariables",])
        self.connect(tmp,QtCore.SIGNAL("droppedInto"),self.droppedVariable)
        tmpW=uvcdatCommons.QLabeledWidgetContainer(tmp,"Variable",widgetSizePolicy=pol)
        tmpW.setToolTip("Type or drag a variable from 'Defined Variables' list")
        h.addWidget(tmpW)

        tmp = QtGui.QDoubleSpinBox()
        tmp.setMinimum(0)
        tmp.setSingleStep(1.)
        tmp.setValue(1.)
        self.connect(tmp,QtCore.SIGNAL("valueChanged(double)"),self.changedPriority)
        h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"P.",widgetSizePolicy=pol))

        if uvcdatCommons.useVistrails:
            tmp = QtGui.QComboBox()
#            tmp.setSizePolicy(
            for i in ['Auto',1,2,3,4,5,6,7,8]:
                tmp.addItem(str(i))
            h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"Sheet",widgetSizePolicy=pol))
            tmp = QtGui.QComboBox()
            for i in ['Auto',1,2,3,4,5,6,7,8]:
                tmp.addItem(str(i))
            h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"Row",widgetSizePolicy=pol))
            tmp = QtGui.QComboBox()
            for i in ['Auto',1,2,3,4,5,6,7,8]:
                tmp.addItem(str(i))
            h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"Col",widgetSizePolicy=pol))
        else:
            tmp = QtGui.QComboBox()
            for i in [1,2,3,4]:
                tmp.addItem(str(i))
            h.addWidget(uvcdatCommons.QLabeledWidgetContainer(tmp,"Canvas",widgetSizePolicy=pol))

        self.nlines+=1
        self.vlayout.addWidget(f)
        self.vlayout.update()

    def droppedTemplate(self,target):
        for i in range(self.nlines):
            tmp = self.vlayout.itemAt(i)
            h=tmp.widget().layout()
            tmpi = h.itemAt(2).widget()
            if tmpi.widget is target:
                h.itemAt(1).widget().widget.setChecked(True)
                self.onOff()
                break

    def droppedGM(self,target):
        gmtype = str(self.parent.plotOptions.plotTypeCombo.currentText())
        for i in range(self.nlines):
            tmp = self.vlayout.itemAt(i)
            hw=tmp.widget()
            h=hw.layout()
            tmpi=h.itemAt(3).widget()
            tmpw=tmpi.widget
            if tmpw is target:
                tmpi.label.setText(gmtype)
                #Ok at that point we need to possibly add variable windows
                nvars = self.parent.nSlabsRequired(gmtype)
                navar = h.count()-6
                if uvcdtCommons.useVistrails:
                    navar-=1
                if nvars>navar:
                    for i in range(nvars-navar):
                        tmp = uvcdatCommons.QDropLineEdit(types=["definedVariables",])
                        self.connect(tmp,QtCore.SIGNAL("droppedInto"),self.droppedVariable)
                        h.insertWidget(5,uvcdatCommons.QLabeledWidgetContainer(tmp,"Variable %i"%(i+2)))
                        h.update()
                        self.vlayout.update()
                        for j in range(h.count()):
                            t = h.itemAt(j)
                elif nvars<navar:
                    for i in range(navar-nvars):
                        h.itemAt(5).widget().destroy()
                        h.removeItem(h.itemAt(5))
                h.itemAt(1).widget().widget.setChecked(True)
                self.onOff()
                break

    def droppedVariable(self,target):
        for i in range(self.nlines):
            tmp = self.vlayout.itemAt(i)
            h=tmp.widget().layout()
            for j in range(4,h.count()-1):
                tmpi=h.itemAt(j).widget()
                if tmpi.widget is target:
                    #Ok construct the variable name
                    vsel =  tmpi.widget.text()
                    vnm = " ".join(str(vsel).split()[1:2])
                    vsel = " ".join(str(vsel).split()[1:])
                    tmpi.label.setText(vsel)
                    tmpi.widget.setText(vnm)
                    h.itemAt(1).widget().widget.setChecked(True)
                    self.onOff()
                    return


