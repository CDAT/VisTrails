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
import ConfigParser
import os, os.path
from PyQt4 import QtCore, QtGui

# vistrails imports
from core.db.io import load_vistrail
from core.db.locator import FileLocator
from core.modules.constant_configuration import StandardConstantWidget
from core.modules.module_registry import get_module_registry
from core.vistrail.controller import VistrailController

#assuming vistrail files and config files for plots are in ./plots
PLOT_FILES_PATH = os.path.join(os.path.dirname(__file__),
                             'plots')

class PlotRegistry(object):
    def __init__(self, cdatwindow):
        self.cdatwindow = cdatwindow
        self.plots = {}
        
    def loadPlots(self):
        parser = ConfigParser.ConfigParser()
        if parser.read(os.path.join(PLOT_FILES_PATH, 'registry.cfg')):
            for p in parser.sections():
                config_file = os.path.join(PLOT_FILES_PATH, 
                                           parser.get(p,'config_file'))
                vt_file = os.path.join(PLOT_FILES_PATH, 
                                       parser.get(p, 'vt_file'))
                self.plots[p] = Plot(p, config_file, vt_file)
    
    def registerPlots(self):
        for name, plot in self.plots.iteritems():
            self.cdatwindow.registerPlotType(name, plot)
        
class Plot(object):
    def __init__(self, name, config_file, vt_file):
        self.name = name
        self.config_file = config_file
        self.vt_file = vt_file
        self.cellnum = 1
        self.filenum = 1
        self.workflow_tag = None
        self.workflow = None
        self.filetype = None
        self.files = []
        self.cells = []
        self.widget = None
        self.alias_widgets = {}
        self.alias_values = {}
        try:
            self.load()
        except Exception, e:
            print "Error when loading plot", str(e)
            import traceback
            traceback.print_exc()
            
    def load(self):
        config = ConfigParser.ConfigParser()
        if config.read(self.config_file):
            self.cellnum = config.getint('global', 'cellnum')
            self.filenum = config.getint('global', 'filenum')
            self.workflow_tag = config.get('global', 'workflow_tag') 
            self.filetype = config.get('global', 'filetype')
            for y in range(self.filenum):
                option_name = 'filename_alias' + str(y+1)
                self.files.append(config.get('global', option_name))
            for x in range(self.cellnum):
                section_name = 'cell' + str(x+1)
                self.cells.append(Cell(config.get(section_name, 'celltype'),
                                       config.get(section_name, 'row_alias'),
                                       config.get(section_name, 'col_alias')))
            #load workflow in vistrail
            locator = FileLocator(os.path.abspath(self.vt_file))
            (v, abstractions , thumbnails) = load_vistrail(locator)
            controller = VistrailController()
            controller.set_vistrail(v, locator, abstractions, thumbnails)
            version = v.get_version_number(self.workflow_tag)
            controller.change_selected_version(version)
            self.workflow = controller.current_pipeline
            self.load_widget()
            
    def load_widget(self):
        aliases = self.workflow.aliases
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        hidden_aliases = self.compute_hidden_aliases()
        for name, (type, oId, parentType, parentId, mId) in aliases.iteritems():
            if name not in hidden_aliases:
                p = self.workflow.db_get_object(type, oId)
                if p.identifier == '':
                    idn = 'edu.utah.sci.vistrails.basic'
                else:
                    idn = p.identifier
                reg = get_module_registry()
                p_module = reg.get_module_by_name(idn, p.type, p.namespace)
                if p_module is not None:
                    widget_type = p_module.get_widget_class()
                else:
                    widget_type = StandardConstantWidget
                p_widget = widget_type(p, None)
                a_layout = QtGui.QHBoxLayout()
                label = QtGui.QLabel(name)
                a_layout.addWidget(label)
                a_layout.addWidget(p_widget)
                
                layout.addLayout(a_layout)
                self.alias_widgets[name] = p_widget
                
        widget.setLayout(layout)
        self.widget = widget
    
    def compute_hidden_aliases(self):
        result = []
        result.extend(self.files)
        for c in self.cells:
            result.append(c.row_name)
            result.append(c.col_name)
        return result
    
    def applyChanges(self):
        print "applyChanges"
        
    def previewChanges(self, aliases):
        #print "previewChanges", aliases
        # we will just execute the pipeline with the given alias dictionary
        locator = FileLocator(os.path.abspath(self.vt_file))
        (v, abstractions , thumbnails) = load_vistrail(locator)
        controller = VistrailController()
        controller.set_vistrail(v, locator, abstractions, thumbnails)
        version = v.get_version_number(self.workflow_tag)
        controller.change_selected_version(version)
        (results, _) = controller.execute_current_workflow(aliases)
        #print results[0]
        
    def discardChanges(self):
        print "discardChanges"
        
class Cell(object):
    def __init__(self, type=None, row_name=None, col_name=None):
        self.type = type
        self.row_name = row_name
        self.col_name = col_name 