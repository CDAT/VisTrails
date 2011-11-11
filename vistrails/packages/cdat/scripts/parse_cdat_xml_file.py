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
from core.system import get_elementtree_library
ElementTree = get_elementtree_library()
from cdat_domain import CDATAction, CDATModule, CDATOption, CDATPort

class XMLNode:
    def __init__(self):
        pass

    def has_attribute(self, node, attr):
        return node.hasAttribute(attr)

    def get_attribute(self, node, attr):
        try:
            attribute = node.attributes.get(attr)
            if attribute is not None:
                return attribute.value
        except KeyError:
            pass
        return None

    @staticmethod
    def convert_from_str(value, type):
        def bool_conv(x):
            s = str(x).upper()
            if s == 'TRUE':
                return True
            if s == 'FALSE':
                return False

        if value is not None:
            if type == 'str':
                return str(value)
            elif value.strip() != '':
                if type == 'long':
                    return long(value)
                elif type == 'float':
                   return float(value)
                elif type == 'int':
                    return int(value)
                elif type == 'bool':
                    return bool_conv(value)
                elif type == 'date':
                    return date(*strptime(value, '%Y-%m-%d')[0:3])
                elif type == 'datetime':
                    return datetime(*strptime(value, '%Y-%m-%d %H:%M:%S')[0:6])
        return None

class CDATOptionNode(XMLNode):
    @staticmethod
    def from_xml(node):
        tag = node.tag
        data = node.get('default', None)
        default = CDATOptionNode.convert_from_str(data, 'str')
        data = node.get('doc', None)
        doc = CDATOptionNode.convert_from_str(data, 'str')
        data = node.get('instance', None)
        instance = CDATOptionNode.convert_from_str(data, 'str')
        return CDATOption(tag=tag, default=default,doc=doc,instance=instance)

class CDATPortNode(XMLNode):
    """Represents Input or Output nodes"""
    @staticmethod
    def from_xml(node):
        tag = node.tag
        data = node.get('doc', None)
        doc = CDATPortNode.convert_from_str(data, 'str')
        data = node.get('instance', None)
        instance = CDATPortNode.convert_from_str(data, 'str')
        data = node.get('position', None)
        position = CDATPortNode.convert_from_str(data, 'int')
        data = node.get('required', None)
        required = CDATPortNode.convert_from_str(data, 'bool')
        return CDATPort(tag=tag, doc=doc, instance=instance,
                        position=position, required=required)

class CDATActionNode(XMLNode):
    @staticmethod
    def from_xml(node):
        data = node.get('name', None)
        name = CDATActionNode.convert_from_str(data,'str')
        data = node.get('type', None)
        type = CDATActionNode.convert_from_str(data,'str')

        options = []
        inputs = []
        outputs = []
        doc = ""
        
        #read children
        for child in node.getchildren():
            if child.tag == 'options':
                for optnode in child.getchildren():
                    option = CDATOptionNode.from_xml(optnode)
                    options.append(option)
            elif child.tag == 'input':
                for inode in child.getchildren():
                    port = CDATPortNode.from_xml(inode)
                    inputs.insert(port._position,port)
            elif child.tag == 'output':
                for onode in child.getchildren():
                    port = CDATPortNode.from_xml(onode)
                    outputs.insert(port._position,port)
            elif child.tag == 'doc':
                doc = child.text
        return CDATAction(name=name, type=type, options=options, inputs=inputs,
                          outputs=outputs, doc=doc)

class CDATModuleNode(XMLNode):
    @staticmethod
    def from_xml(node):
        data = node.get('author',None)
        author = CDATModuleNode.convert_from_str(data,'str')
        data = node.get('programminglanguage', None)
        language = CDATModuleNode.convert_from_str(data,'str')
        data = node.get('type', None)
        type = CDATModuleNode.convert_from_str(data, 'str')
        data = node.get('url', None)
        url = CDATModuleNode.convert_from_str(data, 'str')
        data = node.get('version', None)
        version = CDATModuleNode.convert_from_str(data, 'str')
        data = node.get('codepath', None)
        codepath = CDATModuleNode.convert_from_str(data, 'str')

        actions = []
        #read actions
        for child in node.getchildren():
            if child.tag == 'action':
                action = CDATActionNode.from_xml(child)
                actions.append(action)

        return CDATModule(author=author,
                              language=language,
                              type=type,
                              url=url,
                              codepath=codepath,
                              version=version,
                              actions=actions)

def parse_cdat_xml_file(filename):
    """ parse_cdat_xml_file(filename:str) -> CDATModuleNode
    """
    tree = ElementTree.parse(filename)
    module = CDATModuleNode.from_xml(tree.getroot())
    return module

def parse_cdat_xml_string(text):
    """ parse_cdat_xml_string(text:str) -> CDATModuleNode
    """
    module = CDATModuleNode.from_xml(ElementTree.fromstring(text))
    return module
