############################################################################
##
## Copyright (C) 2006-2010 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################
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
            if not command.endswith("\n"):
                command += "\n"
            qcommands.append(QtCore.QString(command))
        self.shell.write_and_exec(qcommands)
        
    def commandsReceived(self, commands):
        self._commands.append(commands)
        #print commands
        if self.parser is not None:
            if not self.shell_package_loaded:
                # we have to delay the initialization to the first command
                # received because VisTrails shell must be already visible or
                # else the shell will not load the package
                self.initSession()
            newcommands = self.parser.translate(commands)
            self.writeCommands(newcommands)
        else:
            core.debug.log("CDAT Package received commands and they were not parsed")
            
class CDATParser(object):
    def __init__(self):
        self.parser = None
        self.modules = []
        self.load_modules()
        self.initialize()
        self.obj_map = {}
        
    def initialize(self):
        #building grammar to identify cdat python commands
        #modules
        cdms2_ = Literal('cdms2')
        cdms2_open = ("cdms2.open")
        vcs_ = Literal('vcs')
        comma = Drop(',') 
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
        access_vec = rvar & index
        
        with DroppedSpace():
            cmd = (comment |
                   var & Drop('=') & func_call |
                   func_call |
                   var & Drop('=') & access_vec ) > Node
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
            if hasattr(node, 'lvar') and hasattr(node, 'rfunc'):
                result.extend(self._convert_attrib_call(node.rfunc[0], 
                                                        node.lvar[0], 
                                                        node.args[0]))
                self.obj_map[node.lvar[0]] = self.get_outputtype(node.rfunc[0])
            elif hasattr(node, 'rfunc') and hasattr(node, 'args'):
                result.extend(self._convert_call(node.rfunc[0], node.args[0]))
            elif hasattr(node, 'lvar') and hasattr(node, 'rvar'):
                result.extend(self._convert_attrib_vector_access(node.lvar[0],
                                                                 node.rvar[0],
                                                                 node.index[0]))
                self.obj_map[node.lvar[0]] = self.get_outputtype(node.rvar[0])
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
                
    def _convert_attrib_call(self, funcname, var, args):
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
        if not self.obj_map.has_key(var):
            try:
                res = convert_mapping[funcname]%(params)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping[self.obj_map[funcname]]%(params)
        else:
            try:
                res = convert_mapping_update[funcname]%(params)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping_update[self.obj_map[funcname]]%(params)
        
        return res.split("\n")
                
    def _convert_call(self, funcname, args):
        args = args.split(",")
        res = ""
        if funcname == 'plot':
            if not self.obj_map.has_key('plotcell'):
                res = "plotcell = cdat.cdat.CDATCell()\n"
            res += "plotcell.slab1=%s.variable\n"%args[0]
            args.pop(0)
            if not args[0].startswith("'") and not args[0].startswith('"'):
                res += "plotcell.slab2=%s.variable\n"%args[0]
                args.pop(0)  
            col= args[-1].split("=")[1]
            res+= "plotcell.col=%s\n"%col
            args.pop()
            row = args[-1].split("=")[1]
            res+= "plotcell.row=%s\n"%row
            args.pop()
            if len(args) >= 3:
                res+="plotcell.template=%s\n"%args[2]
                args.pop(2)
            if len(args) >= 2:
                res+="plotcell.plotType=%s\n"%args[1]
                args.pop(1)
            if len(args) > 1:
                res+="plotcell.gmName=%s\n"%args[0]
                args.pop(0)
            if len(args) > 1:
                print "args left in plot: %s"%args
            res += "run_pipeline()\n"
            self.obj_map['plotcell'] = 'cdat.CDATCell'
        return res.split("\n")
    
    def _convert_attrib_vector_access(self, lvar, rvar, index):
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
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping[rvar]%(params)
        else:
            #this means that lvar was used before so we just have to change 
            # its parameters
            try:
                res = convert_mapping_update[self.obj_map[rvar]]%(params)
            except KeyError:
                # funcname might be a variable used before, so we translate according to type
                res = convert_mapping_update[rvar]%(params)
        return res.split("\n")
    