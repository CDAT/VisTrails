###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: vistrails@sci.utah.edu
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################
from PyQt4 import QtCore, QtGui
from lepl import *
import os
import os.path
import core.debug
from scripts.parse_cdat_xml_file import parse_cdat_xml_file

#assuming xml files are in ./scripts/xml
XMLFILES_PATH = os.path.join(os.path.dirname(__file__),
                             'scripts', 'xml')

class QTranslator(QtCore.QObject):
    def __init__(self, parent=None, shell=None):
        QtCore.QObject.__init__(self, parent)
        self._commands = []
        self.shell = shell 
        self.parser = None
        self.visApp = QtCore.QCoreApplication.instance()
        self.buildParser()
        self.shell_package_loaded = False
        
    def buildParser(self):
        self.parser = CDATParser()
        
    def initSession(self):
        if self.shell is not None:
            self.writeCommands(["cdat = load_package('edu.utah.sci.vistrails.cdat')"])
            self.shell_package_loaded = True
            
    def writeCommands(self, commandlist):
        qcommands = []
        for command in commandlist:
            if command.endswith("\n"):
                command += command[:-1]
            qcommands.append(QtCore.QString(command))
        self.shell.write_and_exec(qcommands)
        
    def commandsReceived(self, command):
        commands = command.split("\n")
        self._commands.extend(commands)
        #print "## ", commands
        if self.parser is not None:
            if not self.shell_package_loaded:
                # we have to delay the initialization to the first command
                # received because VisTrails shell must be already visible or
                # else the shell will not load the package
                self.initSession()
            for c in commands:
                if c != '':
                    newcommands = self.parser.translate(c)
                    self.writeCommands(newcommands)
        else:
            core.debug.log("CDAT Package received commands and they were not parsed")
    
    def showVisTrails(self):
        if hasattr(self.visApp, 'builderWindow'):
            self.visApp.builderWindow.show()
    
    def closeVisTrails(self):
        if not self.visApp.terminating:
            if hasattr(self.visApp, 'builderWindow'):
                self.visApp.builderWindow.close()
            
        
class CDATParser(object):
    def __init__(self):
        self.parser = None
        self.modules = []
        self.load_modules()
        self.initialize()
        self.obj_map = {}
        self.obj_dep_map = {}
        
    def initialize(self):
        #building grammar to identify cdat python commands
        #modules
        cdms2_ = Literal('cdms2')
        cdms2_open = ("cdms2.open")
        vcs_ = Literal('vcs')
        comma = Drop(',') 
        bool   = (Literal('True') | Literal('False'))
        number_ = Real()                                
        str_   = String() | String("'")                 
        comment = (Literal('#') & Any()[:] > "".join) >> 'comment'
        
        args = (Drop('(') & Any()[:] & Drop(')') > "".join) >> 'args'
        
        index = (Drop('[') & Any()[:] & Drop(']') > "".join) >> 'index'
        
        ident = Word(Letter() | '_',
                     Letter() | '_' | Digit())
        func_name = (ident | 
                     cdms2_open) >> 'rfunc'
        func_call = func_name & args
        var = ident >> 'lvar'
        rvar = ident >> 'rvar'
        member = ident >> 'member'
        
        access_vec = rvar & index
        access_vec_call = rvar & index & Drop('.') & func_name & args
        value = (bool | str_ | number_) > "value" 
        
        with DroppedSpace():
            cmd = (comment |
                   var & Drop('=') & func_call |
                   func_call |
                   var & Drop('=') & access_vec_call |
                   var & Drop('=') & access_vec |
                   var & Drop('.') & member & Drop('=') & value) > Node
            line = cmd & Drop('\n') 
            lines = line[:] & cmd
        self.parser = lines.get_parse_string()
    
    def load_modules(self):
        xmlfiles = []
        self.modules = []
        input_files = os.walk(XMLFILES_PATH)
        for (d, tree, files) in input_files:
            for f in files:
                if os.path.isfile(os.path.join(d,f)) and f.endswith(".xml"):
                    xmlfiles.append(os.path.join(d,f))
        for fxml in xmlfiles:
            self.modules.append(parse_cdat_xml_file(fxml))
        
    def translate(self, text):
        p = self.parser(text)
        result = []
        for node in p:
            #print node
            if hasattr(node, 'lvar') and hasattr(node, 'rfunc'):
                if not hasattr(node, 'rvar') and hasattr(node ,'args'):
                    result.extend(self._convert_assign_call(node.rfunc[0],
                                                            node.lvar[0],
                                                            node.args[0]))
                    self.obj_map[node.lvar[0]] = self.get_outputtype(node.rfunc[0])
                elif hasattr(node, 'index') and hasattr(node, 'rvar'):
                    result.extend(self._convert_assign_vector_access_member(node.lvar[0], 
                                                                            node.rvar[0], 
                                                                            node.index[0], 
                                                                            node.rfunc[0], 
                                                                            node.args[0]))
                    
            elif hasattr(node, 'rfunc') and hasattr(node, 'args'):
                result.extend(self._convert_call(node.rfunc[0], node.args[0]))
            elif (hasattr(node, 'lvar') and hasattr(node, 'rvar') and 
                  hasattr(node,'index')):
                result.extend(self._convert_assign_vector_access(node.lvar[0],
                                                                 node.rvar[0],
                                                                 node.index[0]))
                self.obj_map[node.lvar[0]] = self.get_outputtype(node.rvar[0])
            elif (hasattr(node, 'lvar') and hasattr(node, 'member') and
                  hasattr(node, 'value')):
                result.extend(self._convert_assign_member_value(node.lvar[0],
                                                                node.member[0],
                                                                node.value[0])) 
            elif hasattr(node, 'comment'):
                #send comments as they are
                result.append(node.comment[0])

        return result
    
    def get_outputtype(self, funcname):
        def search(name):
            for m in self.modules:
                if name.startswith(m._codepath):
                    for action in m._actions:
                        if name == "%s.%s" %(m._codepath,action._name):
                            return action._outputs[0]._instance[0]
            return None
        res = search(funcname)
        if res is None:
            #check if it is a call function
            if self.obj_map.has_key(funcname):
                res = search("%s.__call__"%(self.obj_map[funcname]))
            if res is None:
                #check if is a __getitem__ function
                res = search("%s.__getitem__"% (self.obj_map[funcname]))
        return res
                
    def process_down_stream_modules(self, var):
        """ This means that there will be a change in var that will require
removing all dependent modules"""
        
        res = ""
        
        if self.obj_dep_map.has_key(var):
            deps = self.obj_dep_map[var]
            for d in deps:
                res += "del %s\n"%d
                res += self.process_down_stream_modules(d)
                del self.obj_map[d]
            self.obj_dep_map[var] = set()
        return res
    
    def add_dependency(self, var, dep):
        if not self.obj_dep_map.has_key(var):
            self.obj_dep_map[var] = set()
            
        self.obj_dep_map[var].add(dep)
         
    def _convert_assign_call(self, funcname, var, args):
        #this dictionary will store the full list of commands. Will create
        # necessary modules
        convert_mapping = {'cdms2.open': "%(var)s = cdat.%(funcname)s()\n%(var)s.uri = %(args)s\n",
                           'cdms2.dataset.CdmsFile': "%(var)s = cdat.cdms2.dataset.__call__()\n\
%(var)s.cdmsfile = %(funcname)s.dataset\n%(var)s.id=%(args)s\n",
                            'cdms2.tvariable.TransientVariable':"%(var)s = cdat.cdat.Variable()\n\
%(var)s.inputVariable = %(funcname)s.variable\n%(var)s.axes=\"%(args)s\"\n"}
        #this other dictionary assumes that the modules were already
        #created and will just change their parameters
        convert_mapping_update = {'cdms2.open': "%(var)s.uri = %(args)s\n",
                                  'cdms2.dataset.CdmsFile': "%(var)s.id=%(args)s\n",
                                  'cdms2.tvariable.TransientVariable':"%(var)s.axes=\"%(args)s\"\n"}
        params = {'funcname':funcname, 'var':var, 'args':args}
        res = ""
        allowed_objects = ['cdms2.dataset.CdmsFile']
        
        if not self.obj_map.has_key(var):
            try:
                res = convert_mapping[funcname]%(params)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping[self.obj_map[funcname]]%(params)
                self.add_dependency(funcname, var)
        else:
            try:
                if self.obj_map[var] in allowed_objects:
                    res = self.process_down_stream_modules(var)
                res += convert_mapping_update[funcname]%(params)
                self.add_dependency(funcname, var)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = self.process_down_stream_modules(var)
                res += convert_mapping_update[self.obj_map[funcname]]%(params)
                self.add_dependency(funcname, var)
        
        return res.split("\n")
                
    def _convert_call(self, funcname, args):
        args = args.split(",")
        res = ""
        if funcname == 'plot':
            if not self.obj_map.has_key('plotcell'):
                res = "plotcell = cdat.cdat.CDATCell()\n"
                res += "plotcell.slab1=%s.variable\n"%args[0]
                self.add_dependency(args[0],'plotcell')
            args.pop(0)
            if not args[0].startswith("'") and not args[0].startswith('"'):
                res += "plotcell.slab2=%s.variable\n"%args[0]
                self.add_dependency(args[0], 'plotcell')
                args.pop(0)  
            col= args[-1].split("=")[1]
            res+= "plotcell.col=%s\n"%col
            args.pop()
            row = args[-1].split("=")[1]
            res+= "plotcell.row=%s\n"%row
            args.pop()
            if len(args) >= 3:
                res+="plotcell.gmName=%s\n"%args[2]
                args.pop(2)
            if len(args) >= 2:
                res+="plotcell.plotType=%s\n"%args[1]
                args.pop(1)
            if len(args) >= 1:
                res+="plotcell.template=%s\n"%args[0]
                args.pop(0)
            if len(args) >= 1:
                print "args left in plot: %s"%args
            res += "run_pipeline()\n"
            self.obj_map['plotcell'] = 'cdat.CDATCell'
        return res.split("\n")

    def _convert_assign_member_value(self, lvar, member, value):
        res = ''
        if self.obj_map.has_key(lvar):
            res += "%s.%s = %s\n"%(lvar, member, value)
        return res.split("\n")
            
    def _convert_assign_vector_access(self, lvar, rvar, index):
        #this dictionary will store the full list of commands. Will create
        # necessary modules
        convert_mapping = {'cdms2.dataset.CdmsFile': "%(lvar)s = cdat.cdms2.dataset.__getitem__()\n\
%(lvar)s.cdmsfile = %(rvar)s.dataset\n%(lvar)s.id=%(index)s\n",
                           }
        #this other dictionary assumes that the modules were already
        #created and will just change their parameters
        convert_mapping_update = {'cdms2.dataset.CdmsFile': "%(lvar)s.id=%(index)s\n"}
        
        params = {'lvar':lvar, 'rvar':rvar, 'index':index}
        
        res = ""
        if not self.obj_map.has_key(lvar):
            try:
                # rvar could a variable used before, so we translate 
                # according to type
                res = convert_mapping[self.obj_map[rvar]]%(params)
                self.add_dependency(rvar, lvar)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping[rvar]%(params)
                self.add_dependency(rvar, lvar)
        else:
            #this means that lvar was used before so we just have to change 
            # its parameters
            try:
                res = convert_mapping_update[self.obj_map[rvar]]%(params)
                self.add_dependency(rvar, lvar)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping_update[rvar]%(params)
                self.add_dependency(rvar, lvar)
        return res.split("\n")
    
    def _convert_assign_vector_access_member(self, lvar, rvar, index, rfunc, args):
        res = ""    
        if rvar == 'vcs_canvas':
            if rfunc == 'getboxfill':
                if self.obj_map.has_key(lvar):
                    res+= "del %s\n"%lvar
                res += "%s = cdat.cdat.Gfb()\n"%lvar
                res += "plotcell.%s = %s\n"%(lvar, lvar)
                res += "%s.name = %s\n"%(lvar,args)
                
                self.obj_map[lvar] = 'cdat.cdat.Gfb'
        return res.split("\n")
    