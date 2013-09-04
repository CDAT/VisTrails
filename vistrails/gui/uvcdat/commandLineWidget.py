#
# The Ultra-scale Visual Climate Data Analysis Tools (UV-CDAT) 
# - commandLind Widget
#
###############################################################################
#                                                                             #
# Module:       CommandLind Widget                                            #
#                                                                             #
# Copyright:    "See file Legal.htm for copyright information."               #
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#               website: http://uv-cdat.org/                                  #
#                                                                             #
# Description:  This is the main widget containing the "Command Line Window", #
#               which executes Python commands. The Python Shell/Window       #
#               gives the user access into Python's interactive mode. This    #
#               tool has been slightly modified to allow VCDAT to register    #
#               commands for reproducibility - a feature necessary for        #
#               underlying workflow and provenance procedures.                #
#                                                                             #
#               This class is called from the VCDAT Tab Window.               #
#                                                                             #
# Version:      6.0                                                           #
#                                                                             #
###############################################################################
#
from PyQt4 import QtGui, QtCore
import vcs, os, sys, string
import __main__
import systemCommands
import customizeUVCDAT
import uvcdatCommons
import re
import keyword
import traceback
import StringIO

def isidentifier(s):
    s = s.strip()
    if s in keyword.kwlist:
        return False
    return re.match(r'^[a-z_][a-z0-9_]*$', s, re.I) is not None
        
class QCommandLineType(QtGui.QLineEdit):
    """ Command line events to trap the up, down, left, right arrow button 
    events for the Qt Line Edit. """

    def keyPressEvent(self,event):
        if event.key() in (QtCore.Qt.Key_Up, ):
            if len(systemCommands.commandHistory) == 0:
                return
            systemCommands.command_num += 1
            if systemCommands.command_num > len(systemCommands.commandHistory):
                systemCommands.command_num = len(systemCommands.commandHistory)
            command = systemCommands.commandHistory[len(systemCommands.commandHistory) - systemCommands.command_num]
            self.setText( command )
            self.setFocus()
        elif event.key() in (QtCore.Qt.Key_Down, ):
            systemCommands.command_num -= 1
            if systemCommands.command_num <= 0:
                systemCommands.command_num = 0
                command = ""
            else:
                command = systemCommands.commandHistory[len(systemCommands.commandHistory) - systemCommands.command_num]
            self.setText( command )
            self.setFocus()
        elif (event.key() == QtCore.Qt.Key_U and event.modifiers() == QtCore.Qt.MetaModifier):
            self.clear()
            self.setFocus()
        QtGui.QLineEdit.keyPressEvent(self,event)
        
    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat("definedVariables"):
            event.accept()
        else:
            event.ignore()
        
    def dropEvent(self,event):
        event.accept()
        varNames = str(event.mimeData().text());
        if ',' in varNames:
            varNames = '(%s)'%varNames
        ctxt = str(self.text())
        self.setText(ctxt+varNames)
        self.setFocus()
        

class QCommandLine(QtGui.QWidget):
    """ This is the main widget containing the "Command Line Tab Window", 
    which executes CDAT and Python commands. The Python Shell/Window gives the 
    user access into Python's interactive mode. This tool has been slightly 
    modified to allow VCDAT to register keystrokes for reproducibility - a 
    feature necessary for underlying workflow and provenance procedures. """

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        #-----------------------------------------------------------------------
        # create objects instance for the Qt Command Line and Text Window
        #-----------------------------------------------------------------------
        self.root=parent.root
        # create objects
        label = QtGui.QLabel("Enter CDAT command and press Return")
        self.dumpToWindow = False
        self.le = QCommandLineType()
        self.te = QtGui.QTextEdit()
        self.te.setReadOnly(True)

        #-----------------------------------------------------------------------
        # redirect stderr and stdout to the ouput window
        # if stdout, then the text will be colored black, else if an 
        # error occurs (i.e., stderr), then show the text in red
        #-----------------------------------------------------------------------
        sys.stdout = systemCommands.OutLog( self, self.te, None, sys.stdout )
        sys.stderr = systemCommands.OutLog( self, self.te, 
                                                customizeUVCDAT.errorColor, 
                                                sys.stderr )

        #-----------------------------------------------------------------------
        # layout
        #-----------------------------------------------------------------------
        layout = QtGui.QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setMargin(6)
        layout.addWidget(self.te)
        layout.addWidget(label)
        layout.addWidget(self.le)
        self.setLayout(layout)



        ## Scientifc Buttons
        self.topLay = QtGui.QGridLayout()
        self.Lay=self.topLay
        layout.addLayout(self.Lay)
        self.row=0
        self.col=0
        self.direction = "col"

        styles = customizeUVCDAT.scientificButtonsStyles
        self.addButton(text='SIN', styles=styles)
        self.addButton(text='COS', styles=styles)
        self.addButton(text='TAN', styles=styles)
        self.addButton(text='ABS',styles=styles)
        self.newCol()

        styles = customizeUVCDAT.scientificButtonsStyles
        self.addButton(text='ARCSIN', styles=styles)
        self.addButton(text='ARCCOS', styles=styles)
        self.addButton(text='ARCTAN', styles=styles)
        self.addButton(text='STD',styles=styles)
        self.newCol()

        styles = customizeUVCDAT.scientificButtonsStyles
        self.addButton(text='x^2',styles=styles)
        self.addButton(text='sqRT',styles=styles)
        self.addButton(text='1/x',styles=styles)
        self.addButton(text='x^y', styles=styles)
        self.newCol()

        styles = customizeUVCDAT.scientificButtonsStyles
        self.addButton(text='LN', styles=styles)
        self.addButton(text='LOG', styles=styles)
        self.addButton(text='e^x', styles=styles)
        self.addButton(text='10^x', styles=styles)
        self.newCol()

        styles = customizeUVCDAT.scientificButtonsStyles
        self.addButton(text='x<y', styles=styles)
        self.addButton(text='x>y', styles=styles)
        self.addButton(text='x<>y', styles=styles)
        self.addButton(text='x==y', styles=styles)
        self.newCol()

        styles = customizeUVCDAT.scientificButtonsStyles
        self.addButton(text='REGRID', 
                        tip='Spatially regrid the first selected Defined \
Variable\nto the second selected Defined Variable.',styles=styles)
        self.addButton(text='MASK', 
                          tip='Mask variable 2 where variable 1 is "true".',
                          styles=styles)
        self.addButton(text='GET_MASK',
                          tip='Get variable mask',styles=styles)
        self.addButton(text='GROWER', 
                          tip='"Grows" variable 1 and variable 2 so that they \
end up having the same dimensions\n(order of variable 1 plus any extra dims)',
                       styles=styles)
        self.newCol()

        styles = customizeUVCDAT.operatorButtonsStyles
        self.addButton(QtCore.Qt.Key_Plus, '+', styles=styles)
        self.addButton(QtCore.Qt.Key_Minus, '-', styles=styles)
        self.addButton(QtCore.Qt.Key_Asterisk, '*', styles=styles)
        self.addButton(QtCore.Qt.Key_Slash, '/', styles=styles)
  
        #self.connect(self,QtCore.SIGNAL("keyRelease"),self.key)
        #-----------------------------------------------------------------------
        # connect signal - if the return key is pressed, then call run_command
        #-----------------------------------------------------------------------
        self.connect(self.le, QtCore.SIGNAL("returnPressed(void)"),
                     self.run_command)


    def newRow(self,col=0):
        self.row+=1
        self.col=col
        
    def newCol(self,row=0):
        self.row=row
        self.col+=1

    def addButton(self, key=None, text="", extraRow=0, extraCol=0,icon=None, 
                  tip=None,styles={}):
        """Adds a CalcButton"""
        button = uvcdatCommons.CalcButton(text,icon=icon,tip=tip,styles=styles,
                                          signal="clickedCalculator")
        button.associated_key =key
        self.Lay.addWidget(button, self.row, self.col, 1+extraRow, 1+extraCol)
        self.connect(button, QtCore.SIGNAL('clickedCalculator'),
                    self.issueCmd)
        if self.direction == "row":
            self.col+=1
        else:
            self.row+=1

            
    def issueCmd(self,button):
        st=""
        nm=""
        vars = []
        txt = str(button.text())
        pressEnter=False
        selected = self.root.dockVariable.widget().varList.selectedItems()
        # Funcs that can take many many many variables
        if txt  in ["*","+","/","-"]:
            if len(selected)==0:
                st=txt
            elif len(selected)==1:
                if len(str(self.le.text()))==0:
                    st = selected[0].varName+txt
                else:
                    st = txt+selected[0].varName
            else:
                if txt == "+":
                    nm="add_"
                elif txt == "-":
                    nm="sub_"
                elif txt == "/":
                    nm="div_"
                elif txt == "*":
                    nm="mul_"
                st = selected[0].varName
                nm+=selected[0].varName
                for s in selected[1:]:
                    st+=txt+s.varName
                    nm+="_%s" % s.varName
                nm+=" = "
                #self.root.dockVariable.widget().unselectItems(selected)
                #vistrails
                for s in selected:
                    vars.append(s.varName)
                if str(self.le.text())=="" :
                    pressEnter=True
        # 2 variable commands
        elif txt in ["x<y","x>y","x<>y","x==y"]:
            if len(selected)!=2:
                st=txt[1:-1]
            else:
                vars = [selected[0].varName,selected[1].varName]
                st=selected[0].varName+txt[1:-1]+selected[1].varName
                if txt[1:-1]=="<":
                    nm="less_"
                if txt[1:-1]==">":
                    nm="greater_"
                if txt[1:-1]=="<>":
                    nm="notequal_"
                if txt[1:-1]=="==":
                    nm="equal_"
                nm+=selected[0].varName+"_"+selected[1].varName+" = "
                #self.root.dockVariable.widget().unselectItems(selected)
                if str(self.le.text())=="" :
                    pressEnter=True
        elif txt == "x^y":
            if len(selected)!=2:
                st="MV2.power("
            else:
                vars = [selected[0].varName,selected[1].varName]
                st="MV2.power(%s,%s)" % (selected[0].varName,selected[1].varName)
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="power_"+selected[0].varName+"_"+selected[1].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
        elif txt == "REGRID":
            if len(selected)==0:
                st=".regrid(" 
            if len(selected)==1:
                vars = [selected[0].varName]
                st="StandardGrid.regrid(%s)" % ( selected[0].varName )
                self.root.dockVariable.widget().unselectItems(selected)
                nm="regrid_"+selected[0].varName +" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                vars = [selected[0].varName,selected[1].varName]
                st="%s.regrid(%s.getGrid())" % (
                                     selected[0].varName,selected[1].varName)
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="regrid_"+selected[0].varName+"_"+selected[1].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
        elif txt == "MASK":
            if len(selected)!=2:
                st="MV2.masked_where("
            else:
                vars = [selected[0].varName,selected[1].varName]
                st="MV2.masked_where(%s,%s)" % (
                                    selected[0].varName,selected[1].varName)
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="maskedwhere_"+selected[0].varName+"_"+selected[1].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
        elif txt == "GET_MASK":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.getmask(%s)" % (selected[0].varName)
                nm=selected[0].varName+"_mask = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.getmask("
        elif txt == "GROWER":
            if len(selected)!=2:
                st="genutil.grower("
            else:
                vars = [selected[0].varName,selected[1].varName]
                st="genutil.grower(%s,%s)" % (
                                     selected[0].varName,selected[1].varName)
                #self.root.dockVariable.widget().unselectItems(selected)
                nm= "%s_grown_to_%s, %s_grown_to_%s = " % (
                                               vars[0], vars[1], vars[1], vars[0])

                if str(self.le.text())=="" :
                    pressEnter=True
        # ! variable only
        elif txt == "x^2":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="%s**2" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="square_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="**2"
        elif txt == "sqRT":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.sqrt(%s)" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="sqrt_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.sqrt("
        elif txt == "1/x":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="1/%s" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="invert_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="1/"
        elif txt == "LN":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.log(%s)" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="ln_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.log("
        elif txt == "LOG":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.log10(%s)" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="log10_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.log10("
        elif txt == "e^x":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.exp(%s)" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="exp_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.exp("
        elif txt == "10^x":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.power(10,%s)" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="power10_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.power(10,"
        elif txt == "ABS":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.absolute(%s)" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="abs_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.absolute(,"
        elif txt in ["SIN","ARCSIN","COS","ARCCOS","TAN","ARCTAN"]:
            if len(selected)==1:
                vars = [selected[0].varName]
                st="MV2.%s(%s)" % (txt.lower(),selected[0].varName)
                #self.root.dockVariable.widget().unselectItems(selected)
                nm=txt.lower()+"_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="MV2.%s(," % (txt.lower())
        elif txt == "STD":
            if len(selected)==1:
                vars = [selected[0].varName]
                st="genutil.statistics.std(%s)" % (
                                             txt.lower(),selected[0].varName)
                #self.root.dockVariable.widget().unselectItems(selected)
                nm="std_"+selected[0].varName+" = "
                if str(self.le.text())=="" :
                    pressEnter=True
            else:
                st="genutil.statistics.std(," % (txt.lower())
        elif txt == "Clear":
            self.le.clear()
        elif txt == "Del":
            st = str(self.le.text())[:-1]
            self.le.clear()
        elif txt == "Enter":
            pressEnter = True
        elif txt == "Plot":
            if len(str(self.le.text()))!=0:
                res = self.run_command()
                self.root.dockVariable.widget().unselectItems(selected)
                self.root.dockVariable.widget().selectVariableFromName(res)
                self.root.tabView.widget(1).plot()
            elif len(selected)!=0:
                self.root.tabView.widget(1).plot()
        elif txt == "=":
            if len(selected)==1:
                st = "%s =" % selected[0].varName
                #self.root.dockVariable.widget().unselectItems(selected)
            else:
                st="="
        elif txt == "PI":
            st="numpy.pi"
        elif txt=="e":
            st="numpy.e"
        elif txt == "+/-":
            st = str(self.le.text())
            if st[:2]=="-(" and st[-1]==")" and st.count("(")==st.count(")"):
                st=st[2:-1]
            else:
                if len(st)==0 and len(selected)==1:
                    st = "-%s" % selected[0].varName
                    #self.root.dockVariable.widget().unselectItems(selected)
                else:
                    st="-(%s)" % st
            self.le.clear()
        else:
            st=txt
            
        #make sure name is unique
        newname = nm[:-3].strip()        
        items = self.root.dockVariable.widget().getItems(project=False)
        varNameSet = set([str(it.text()).split()[1] for it in items])
        suffix = ""
        if newname in varNameSet:
            suffix = 1
            while (newname + str(suffix)) in varNameSet:
                suffix += 1
            newname = newname + str(suffix)
            nm = newname + nm[-3:]
            
        if st!="":
            if pressEnter:
                orst = st
                st="%s%s" % (nm,st)
            self.le.setText(str(self.le.text())+st)
        if pressEnter:
            self.run_command(processed=True)
            #send command to project controller to be stored as provenance
            from api import get_current_project_controller
            prj_controller = get_current_project_controller()
            varname = nm[:-3].strip()
            prj_controller.calculator_command(vars, txt, orst, varname)
            
            varnames = varname.split(',')
            varname = varnames[0].strip()
            tmp = prj_controller.create_exec_new_variable_pipeline(varname)
            if tmp is not None:
                tmp.id = varname
                self.root.dockVariable.widget().addVariable(tmp)
                
            if len(varnames) == 2:
                varname2 = varnames[1].strip()
                tmp2 = prj_controller.create_exec_new_variable_pipeline(varname2)
                if tmp2 is not None:
                    tmp2.id = varname2
                    self.root.dockVariable.widget().addVariable(tmp2)
            
        self.le.setFocus()

    def run_command(self,processed=False):
        self.dumpToWindow = True
        """ Event that processes the CDAT/Python command and displays the 
        stdout or stderr in the text editor window. """
        #-----------------------------------------------------------------------
        # isolate the command and display it in the text editor window
        #-----------------------------------------------------------------------
        command = str(self.le.text())    # read the command
        # strip leading and/or trailing whitespaces from the command
        command = command.strip()  
        if command == "":
            return
        # set the text editor output window text to black
        self.te.setTextColor( QtGui.QColor(0,0,0)) 
        commandLine =  ">>> " + command + "\n"
        # display the command in the text window
        self.te.insertPlainText( commandLine )     

        #-----------------------------------------------------------------------
        # append the command to the list and rest the list number to 0
        #-----------------------------------------------------------------------
        if command != "": systemCommands.commandHistory.append( command )
        systemCommands.command_num = 0

        #-----------------------------------------------------------------------
        # execute the command and clear the line entry if no error occurs
        #-----------------------------------------------------------------------
#        results = "temp_results_holder"
#        acommand = "temp_results_holder = %s"  % command
#        exec( "import MV2,genutil,cdms2,vcs,cdutil,numpy", __main__.__dict__ )
#        self.le.clear()
#        try:
#            exec( command, __main__.__dict__ )
#        except Exception:
#            #print exception to the command window    
#            errorText = StringIO.StringIO()
#            errorText.write('Your command produced an error.\n')
#            errorText.write('-'*60+'\n')
#            traceback.print_exc(file=errorText)
#            errorText.write('-'*60)
#            self.te.insertPlainText(errorText.getvalue())

#        res = self.root.stick_main_dict_into_defvar(None)
        #-----------------------------------------------------------------------
        # record the command for preproducibility
        #-----------------------------------------------------------------------
        clist = command.split("=", 1)
        varname = clist[0].strip()
        
        self.root.record("## Command sent from prompt by user")
        
        if len(clist) > 1:
            self.root.record(command)
        else:
            self.root.record("%s = %s" % (varname, command))
            
        
        if not processed and len(clist) > 1 and isidentifier(varname):
            pycommand = clist[1].strip()
            # project controller will only capture the results that return 
            # a variable
            #send command to project controller to be stored as provenance
            from api import get_current_project_controller
            prj_controller = get_current_project_controller()
            prj_controller.process_typed_calculator_command(varname,pycommand)
            
            tmp = prj_controller.create_exec_new_variable_pipeline(varname)
            if tmp is not None:
                tmp.id = varname
                self.root.dockVariable.widget().addVariable(tmp)
        self.le.clear()
        self.dumpToWindow = False
        return varname
