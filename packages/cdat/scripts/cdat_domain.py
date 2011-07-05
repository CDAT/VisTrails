#!/usr/bin/env python
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
def convert_to_vt_type(t):
    vt_type_dict = {'str':'core.modules.basic_modules.String',
                    'float': 'core.modules.basic_modules.Float',
                    'int':'core.modules.basic_modules.Integer',
                    'bool':'core.modules.basic_modules.Boolean',
                    'list': 'core.modules.basic_modules.List',
                    'None': 'core.modules.basic_modules.Null',
                    'file': 'core.modules.basic_modules.File',
                    'dict': 'core.modules.basic_modules.Dictionary',
                    'tuple': 'core.modules.basic_modules.Tuple',
                    'True' : 'core.modules.basic_modules.Boolean',
                    'False': 'core.modules.basic_modules.Boolean',
                    'vcs.boxfill.Gfb' : 'Gfb',
                    #'numpy.ndarray':'reg.get_module_by_name("edu.utah.sci.vistrails.numpyscipy", "Numpy Array", namespace="numpy|array")',
                    }
    if vt_type_dict.has_key(t):
        return vt_type_dict[t]
    else:
        print "Type %s not found!" % t
        return None

do_not_cache_me = ['png','plot','isofill','isoline','boxfill']
class CDATModule:
    _extra_modules = []
    _extra_vistrails_modules = {}
    def __init__(self, author=None, language=None, type=None, url=None,
                 codepath=None, version=None, actions=None):
        self._author = author
        self._language = language
        self._type = type
        self._url = url
        self._codepath = codepath
        self._version = version
        self._actions = actions
        (self._namespace, self._name) = self.split(codepath)

    @staticmethod
    def split(codepath):
        dot = codepath.rfind('.')
        if dot != -1:
            name = codepath[dot+1:]
            data = codepath[:dot]
            namespace = data.replace('.','|')
        else:
            name = codepath
            namespace = codepath
        return (namespace,name)

    def write_extra_module_definition(self, lines, name):
        lines.append("%s = new_module(Module,'%s')\n"%(name,name))

    @staticmethod
    def write_extra_module_definitions_init(lines):
        lines.append("vt_type_dict = {}\n")
        lines.append("def get_late_type(type):\n")
        lines.append("    return vt_type_dict[type]\n\n")

    @staticmethod
    def write_extra_module_definitions(lines):
        for t in CDATModule._extra_modules:
            e = convert_to_vt_type(t)
            if e == None:
                namespace,name = CDATModule.split(t)
                lines.append("%s = new_module(Module,'%s')\n"%(name,name))
                lines.append("vt_type_dict['%s'] = %s\n"%(t,name))
                CDATModule._extra_vistrails_modules[name] = namespace
        lines.append("\n\n")

    @staticmethod
    def register_extra_vistrails_modules(lines, ident=''):
        for (name,namespace) in CDATModule._extra_vistrails_modules.iteritems():
            lines.append(ident + "    reg.add_module(%s,namespace='%s')\n"%(name,
                                                                      namespace))

    def register_extra_vistrails_module(self, lines, name, ident=''):
        lines.append(ident + "    reg.add_module(%s,namespace='%s')\n"%(name,
                                                                        self._namespace))

    def write_module_definitions(self, lines):
        for a in self._actions:
            a.write_module_definition(lines)

    def register_vistrails_modules(self, lines):
        for a in self._actions:
            a.register_itself(lines,self._namespace)

    def build_vistrails_modules_dict(self):
        for a in self._actions:
            types = a.check_extra_types()
            for t in types:
                if t not in CDATModule._extra_modules:
                    CDATModule._extra_modules.append(t)

    def add_extra_input_port_to_all_modules(self, lines, port_name, port_type,
                                            doc, optional = False):
        lines.append("\n    #extra input ports not available in the xml file\n")
        for a in self._actions:
            a.register_extra_input_port(port_name, port_type, lines, doc,
                                        optional)

    def add_extra_output_port_to_all_modules(self, lines, port_name, port_type,
                                            doc, optional = False):
        lines.append("\n    #extra output ports not available in the xml file\n")
        for a in self._actions:
            a.register_extra_output_port(port_name, port_type, lines, doc,
                                         optional)
class CDATAction:
    def __init__(self, name=None, type=None, options=None, inputs=None,
                 outputs=None, doc=None):
        self._name = name
        self._type = type
        self._options = options
        self._inputs = inputs
        self._outputs = outputs
        self._doc = doc

    def write_module_definition(self, lines, ident='', compute_method=None):
        def write_compute_method(self,lines, ident):
            lines.append(ident + "def compute(self):\n")
            lines.append(ident + "    if self.hasInputFromPort('canvas'):\n")
            lines.append(ident + "        canvas = self.getInputFromPort('canvas')\n")
            lines.append(ident + "    else:\n")
            lines.append(ident + "        canvas = vcs.init()\n")
            lines.append(ident + "    args = []\n")
            for inp in self._inputs:
                lines.append(ident + "    %s = None\n"%inp._name)
                for inst in inp._valid_instances:
                    if inp._valid_instances.index(inst) == 0:
                        lines.append(ident + "    if self.hasInputFromPort('%s'):\n" % inst)
                        lines.append(ident + "        %s = self.getInputFromPort('%s')\n" % (inp._name, inst))
                        lines.append(ident + "        args.append(%s)\n"%inp._name)
                    else:
                        lines.append(ident + "    elif self.hasInputFromPort('%s'):\n" % inst)
                        lines.append(ident + "        %s = self.getInputFromPort('%s')\n" % (inp._name, inst))
                        lines.append(ident + "        args.append(%s)\n"%inp._name)
                if inp._required:
                    lines.append("\n"+ ident +"    # %s is a required port\n" % inp._name)
                    lines.append(ident + "    try:\n")
                    lines.append(ident + "        if %s == None:\n" % inp._name)
                    lines.append(ident + "            raise ModuleError(self, \"'%s' is a mandatory port\")\n" % inp._name)
                    lines.append(ident + "    except ValueError:\n")
                    lines.append(ident + "        pass #this means it is an array that we can't compare to None:\n")
                    lines.append(ident + "             #and so there is a value attached to it:\n")
            lines.append("\n"+ident +"    # build up the keyword arguments from the optional inputs.\n")
            lines.append(ident +"    kwargs = {}\n")

            for opt in self._options:
                for inst in opt._valid_instances:
                    if opt._valid_instances.index(inst) == 0:
                        lines.append(ident +"    if self.hasInputFromPort('%s'):\n" % inst)
                        lines.append(ident +"        kwargs['%s'] = self.getInputFromPort('%s')\n" % (opt._name, inst))
                    else:
                        lines.append(ident +"    elif self.hasInputFromPort('%s'):\n" % inst)
                        lines.append(ident +"        kwargs['%s'] = self.getInputFromPort('%s')\n" % (opt._name, inst))

            if len(self._outputs) > 0:
                lines.append(ident + "    #force images to be created in the background\n")
                lines.append(ident + "    kwargs['bg'] = 1\n")
                lines.append(ident + "    res = canvas.%s(*args,**kwargs)\n"%self._name)
                lines.append(ident + "    self.setResult('%s',res)\n"%(self._outputs[0]._name))
                lines.append(ident + "    self.setResult('canvas',canvas)\n")
            lines.append("\n")
        if self._name in do_not_cache_me:
            lines.append(ident + "class %s(Module,NotCacheable):\n" % self._name)
        else:
            lines.append(ident + "class %s(Module):\n" % self._name)
        lines.append(ident + '    """%s\n'%self._doc)
        lines.append(ident + '    """\n')
        if not compute_method:
            write_compute_method(self,lines,ident="    ")
        else:
            lines.extend(compute_method)

    def register_itself(self,lines, namespace):
        lines.append("\n    #Module %s\n" % self._name)
        lines.append("    reg.add_module(%s,namespace='%s')\n" % (self._name,namespace))
        for inp in self._inputs:
            inp.write_input_ports(self._name, lines)
        for opt in self._options:
            opt.write_input_ports(self._name, lines, True, force=False)
        for out in self._outputs:
            out.write_output_ports(self._name, lines, force=True)

    def check_extra_types(self):
        types = []
        for out in self._outputs:
            for o in out._instance:
                if o not in types:
                    types.append(o)
        for inp in self._inputs:
            for r in inp._ref_instance:
                if r not in types:
                    types.append(r)
        return types

    def register_extra_input_port(self, port_name, port_type, lines, doc,
                                  optional=False):
        self._write_port('input', port_name, port_type, lines, doc, optional)

    def register_extra_output_port(self, port_name, port_type, lines, doc,
                                  optional=False):
        self._write_port('output', port_name, port_type, lines, doc, optional)

    #private methods
    def _write_port(self, io_type, port_name, port_type,
                    lines, doc, optional=False):
        lines.append("    reg.add_%s_port(%s, '%s', \n" % (io_type,
                                                           self._name,
                                                           port_name))
        lines.append("                       ")
        lines.append("(%s,\n" % port_type)
        lines.append("                        ")
        if not optional:
            lines.append("\"%s\"))\n" % doc)
        else:
            lines.append("\"%s\"), True)\n" % doc)

class CDATItem:
    def __init__(self, tag=None, doc=None, instance=None, required=False):
        self._name = tag
        self._doc = doc
        self._instance = []
        self._ref_instance = []
        self._parse_instance(instance) 
        self._valid_instances = []
        if required == None:
            self._required = False
        else:
            self._required = required

    def _parse_instance(self, instance):
        #TODO: improve this by making it recursive
        if instance.startswith('[') and instance.endswith(']'):
            self._instance = ['list']
            if instance.rfind('[') == 0:
                #single list
                instance = instance[1:-1]
                instance = instance.strip(" \t\n")
                if instance not in self._ref_instance:
                    self._ref_instance.append(instance)
            else:
                data = [i.strip(" \t\n") for i in instance.split('/')]
                for d in data:
                    if d.startswith('[') and d.endswith(']'):
                        if d not in self._ref_instance:
                            self._ref_instance.append(d[1:-1])
                    else:
                        print "Ignoring %s"%d
        
#        elif instance.startswith('(') and instance.endswith(')'):
#            #tuples can have elements of different types
#            data = set([[i.strip(" \t\n") for i in instance.split('/')]])
#            self._instance = set()
        else:
            data = [i.strip(" \t\n") for i in instance.split('/')]
            for i in data:
                if not i.startswith('['):
                    self._instance.append(i)
                elif i.startswith('[') and i.endswith(']'):
                    self._instance.append('list')
                    i = i[1:-1]
                    i = i.strip(" \t\n")
                    if i not in self._ref_instance:
                        self._ref_instance.append(i)
                                                   
    def write_input_ports(self, module_name, lines, optional=False, force=False):
        self._write_ports('input',module_name, lines, optional, force)

    def write_output_ports(self, module_name, lines, optional=False, force=False):
        self._write_ports('output',module_name, lines, optional, force)

    def _write_ports(self, port_type, module_name, lines, optional=False,
                     force=False):
        if len(self._instance) == 1:
            type = convert_to_vt_type(self._instance[0])
            if type == None and self._instance[0] in CDATModule._extra_modules:
                force = True
            if force and type == None:
                type = "get_late_type('%s')"%self._instance[0]
            if type != None:
                self._valid_instances.append(self._name)
                lines.append("    reg.add_%s_port(%s, '%s', \n" % (port_type,
                                                                   module_name,
                                                                   self._name))
                lines.append("                       ")
                lines.append("(%s,\n" % type)
                lines.append("                        ")
                if not optional:
                    lines.append("\"%s\"))\n" % self._doc)
                else:
                    lines.append("\"%s\"), True)\n" % self._doc)
        else:
            count = 0
            for i in xrange(len(self._instance)):
                type = convert_to_vt_type(self._instance[i])
                new_force = force
                if type == None and self._instance[i] in CDATModule._extra_modules:
                    new_force = True
                if new_force and type == None:
                    type = "get_late_type('%s')"%self._instance[i]
                if type != None:
                    name = "%s_%s"%(self._name,count)
                    self._valid_instances.append(name)
                    count += 1
                    lines.append("    reg.add_input_port(%s, '%s', \n" % (module_name,
                                                                          name))
                    lines.append("                       ")
                    lines.append("(%s,\n" % type)
                    lines.append("                        ")
                    if not optional:
                        lines.append("\"%s\"))\n" % self._doc)
                    else:
                        lines.append("\"%s\"), True)\n" % self._doc)

class CDATOption(CDATItem):
    def __init__(self, tag=None, default=None, doc=None, instance=None):
        CDATItem.__init__(self, tag, doc, instance, False)
        self._default = default

class CDATPort(CDATItem):
    def __init__(self, tag=None, doc=None, instance=None, position=None, required=False):
        CDATItem.__init__(self, tag, doc, instance, required)
        self._position = position