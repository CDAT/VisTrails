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
from core.packagemanager import get_package_manager
from core import debug

#assuming vistrail files and config files for plots are in ./plots
PLOT_FILES_PATH = os.path.join(os.path.dirname(__file__),
                             'plots')

class PlotRegistry(object):
    def __init__(self, cdatwindow):
        self.cdatwindow = cdatwindow
        self.plots = {}
        self.registered = []
        
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
            if plot.loaded == True:
                self.cdatwindow.registerPlotType(name, plot)
                self.registered.append(name)
        
class Plot(object):
    def __init__(self, name, config_file, vt_file):
        self.name = name
        self.config_file = config_file
        self.vt_file = vt_file
        self.cellnum = 1
        self.filenum = 1
        self.workflow_tag = None
        self.workflow = None
        self.filetypes = {}
        self.qt_filter = None
        self.files = []
        self.cells = []
        self.widget = None
        self.alias_widgets = {}
        self.alias_values = {}
        self.dependencies = []
        self.unsatisfied_deps = []
        self.loaded = False
        try:
            self.load()
        except Exception, e:
            print "Error when loading plot", str(e)
            import traceback
            traceback.print_exc()
            
    def load(self):
        config = ConfigParser.ConfigParser()
        if config.read(self.config_file):
            if config.has_section('global'):
                if config.has_option('global', 'cellnum'):
                    self.cellnum = config.getint('global', 'cellnum')
                if config.has_option('global', 'filenum'):
                    self.filenum = config.getint('global', 'filenum')
                if config.has_option('global', 'workflow_tag'):
                    self.workflow_tag = config.get('global', 'workflow_tag')
                else:
                    debug.warning("CDAT Package: file %s does not contain a \
required option 'workflow_tag'. Widget will not be loaded."%self.config_file)
                    self.loaded = False
                    return
                if config.has_option('global', 'filetypes'):
                    types = config.get('global', 'filetypes')
                    tlist = [t.strip() for t in types.split(";")]
                    for t in tlist:
                        kv = t.split(":")
                        self.filetypes[kv[0].strip()] = [v.strip() 
                                                         for v in kv[1].split(",")]
                if config.has_option('global', 'qt_filter'):
                    self.qt_filter = config.get('global', 'qt_filter')
                if config.has_option('global', 'dependencies'):
                    deps = config.get('global', 'dependencies')
                    self.dependencies = [d.strip() for d in deps.split(",")]
            
                for y in range(self.filenum):
                    option_name = 'filename_alias' + str(y+1)
                    if config.has_option('global', option_name):
                        self.files.append(config.get('global', option_name))
                        
                for x in range(self.cellnum):
                    section_name = 'cell' + str(x+1)
                    if (config.has_section(section_name) and
                        config.has_option(section_name, 'celltype') and
                        config.has_option(section_name, 'row_alias') and
                        config.has_option(section_name, 'col_alias')):
                        self.cells.append(Cell(config.get(section_name, 'celltype'),
                                               config.get(section_name, 'row_alias'),
                                               config.get(section_name, 'col_alias')))
                
                #load workflow in vistrail
                #only if dependencies are enabled
                manager = get_package_manager()
                self.unsatisfied_deps = []
                for dep in self.dependencies:
                    if not manager.has_package(dep):
                        self.unsatisfied_deps.append(dep)
                if len(self.unsatisfied_deps) == 0:
                    locator = FileLocator(os.path.abspath(self.vt_file))
                    (v, abstractions , thumbnails) = load_vistrail(locator)
                    controller = VistrailController()
                    controller.set_vistrail(v, locator, abstractions, thumbnails)
                    version = v.get_version_number(self.workflow_tag)
                    controller.change_selected_version(version)
                    self.workflow = controller.current_pipeline
                    self.load_widget()
                    self.loaded = True
                else:
                    debug.warning("CDAT Package: %s widget could not be loaded \
because it depends on packages that are not loaded:"%self.name)
                    debug.warning("  %s"%", ".join(self.unsatisfied_deps))
                    self.loaded = False
            else:
                debug.warning("CDAT Package: file %s does not contain a 'global'\
 section. Widget will not be loaded."%self.config_file)
                self.loaded = False
            
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