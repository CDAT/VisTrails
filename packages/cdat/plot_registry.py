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
import ConfigParser
import os, os.path
from PyQt4 import QtCore, QtGui

# vistrails imports
import api
import core.db.action
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
                try:
                    self.plots[p].load()
                except Exception, e:
                    print "Error when loading plot %s"%p, str(e)
                    import traceback
                    traceback.print_exc()
    
    def registerPlots(self):
        for name, plot in self.plots.iteritems():
            if plot.loaded == True:
                self.cdatwindow.registerPlotType(name, plot)
                self.registered.append(name)
    
    @staticmethod    
    def getPlotsDependencies():
        parser = ConfigParser.ConfigParser()
        dependencies = []
        if parser.read(os.path.join(PLOT_FILES_PATH, 'registry.cfg')):
            for p in parser.sections():
                config_file = os.path.join(PLOT_FILES_PATH, 
                                           parser.get(p,'config_file'))
                vt_file = os.path.join(PLOT_FILES_PATH, 
                                       parser.get(p, 'vt_file'))
                plot = Plot(p, config_file, vt_file)
                plot.load(loadwidget=False)
                #print plot.dependencies
                dependencies.extend(plot.dependencies)
        return list(set(dependencies))
    
    def __del__(self):
        plots = self.plots.keys()
        while len(plots) > 0:
            del self.plots[plots[-1]]
            plots.pop()
        
class Plot(object):
    def __init__(self, name, config_file, vt_file):
        self.name = name
        self.config_file = config_file
        self.vt_file = vt_file
        self.locator = FileLocator(os.path.abspath(self.vt_file))
        self.cellnum = 1
        self.filenum = 1
        self.varnum = 0
        self.workflow_tag = None
        self.workflow = None
        self.filetypes = {}
        self.qt_filter = None
        self.files = []
        self.cells = []
        self.vars = []
        self.axes = []
        self.widget = None
        self.alias_widgets = {}
        self.alias_values = {}
        self.dependencies = []
        self.unsatisfied_deps = []
        self.loaded = False
        self.plot_vistrail = None
        self.current_parent_version = 0L
        self.current_controller = None
            
    def load(self, loadwidget=True):
        config = ConfigParser.ConfigParser()
        if config.read(self.config_file):
            if config.has_section('global'):
                if config.has_option('global', 'cellnum'):
                    self.cellnum = config.getint('global', 'cellnum')
                if config.has_option('global', 'filenum'):
                    self.filenum = config.getint('global', 'filenum')
                if config.has_option('global', 'varnum'):
                    self.varnum = config.getint('global', 'varnum')
                if config.has_option('global', 'workflow_tag'):
                    self.workflow_tag = config.get('global', 'workflow_tag')
                else:
                    debug.warning("CDAT Package: file %s does not contain a required option 'workflow_tag'. Widget will not be loaded."%self.config_file)
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
                        
                for v in range(self.varnum):
                    option_name = 'varname_alias' + str(v+1)
                    if config.has_option('global', option_name):
                        self.vars.append(config.get('global', option_name))
                    axes_name = 'axes_alias' + str(v+1)
                    if config.has_option('global', axes_name):
                        self.axes.append(config.get('global', axes_name))
                        
                for x in range(self.cellnum):
                    section_name = 'cell' + str(x+1)
                    if (config.has_section(section_name) and
                        config.has_option(section_name, 'celltype') and
                        config.has_option(section_name, 'row_alias') and
                        config.has_option(section_name, 'col_alias')):
                        self.cells.append(Cell(config.get(section_name, 'celltype'),
                                               config.get(section_name, 'row_alias'),
                                               config.get(section_name, 'col_alias')))
                
                if loadwidget:
                    #load workflow in vistrail
                    #only if dependencies are enabled
                    manager = get_package_manager()
                    self.unsatisfied_deps = []
                    for dep in self.dependencies:
                        if not manager.has_package(dep):
                            self.unsatisfied_deps.append(dep)
                    if len(self.unsatisfied_deps) == 0:
                        (self.plot_vistrail, abstractions , thumbnails) = load_vistrail(self.locator)
                        controller = VistrailController()
                        controller.set_vistrail(self.plot_vistrail, self.locator, 
                                                abstractions, thumbnails) 

                        version = self.plot_vistrail.get_version_number(self.workflow_tag) if self.workflow_tag else controller.get_latest_version_in_graph()
                        controller.change_selected_version(version)
                        self.workflow = controller.current_pipeline
                        self.loadWidget()
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
            
    def loadWidget(self):
        aliases = self.workflow.aliases
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        hidden_aliases = self.computeHiddenAliases()
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
    
    def computeHiddenAliases(self):
        result = []
        result.extend(self.files)
        result.extend(self.vars)
        result.extend(self.axes)
        for c in self.cells:
            result.append(c.row_name)
            result.append(c.col_name)
        return result
    
    def writePipelineToCurrentVistrail(self, aliases):
        """writePipelineToVistrail(aliases: dict) -> None 
        It will compute necessary actions and add to the current vistrail, 
        starting at self.parent_version. In the case self.parent_version
        does not contain a valid workflow, we will start from the root with
        a new pipeline.
        
        """
        #print self.current_controller
        if self.current_controller is None:
            self.current_controller = api.get_current_controller()
            self.current_parent_version = 0L
        else:
            if self.current_parent_version > 0L:
                pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
                if len(pipeline.aliases) >= len(self.workflow.aliases):
                    paliases = set(pipeline.aliases.keys())
                    waliases = set(self.workflow.aliases.keys())
                    if len(waliases - paliases) != 0:
                        self.current_parent_version = 0
        #print "controller ", self.current_controller
        #print "version ", self.current_parent_version 
        if self.current_parent_version == 0L:
            #create actions and paste them in current vistrail
            vistrail = self.current_controller.vistrail
            if vistrail:
                newid = self.addPipelineAction(self.workflow,
                                               self.current_controller,
                                               vistrail, 
                                               self.current_parent_version)
                newtag = self.name
                count = 1
                while vistrail.hasTag(newtag):
                    newtag = "%s %s"%(self.name, count)
                    count += 1 
                vistrail.addTag(newtag, newid)
                self.current_parent_version = newid
                
        #now we update pipeline with current parameter values
        pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
#        self.addMergedAliases( aliases, pipeline )
        newid = self.addParameterChangesFromAliasesAction(pipeline, 
                                        self.current_controller, 
                                        self.current_controller.vistrail, 
                                        self.current_parent_version, aliases)
        self.current_parent_version = newid
            
                
    def applyChanges(self, aliases):
        #print "applyChanges"
        self.writePipelineToCurrentVistrail(aliases)
        pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
        #print "Controller changed ", self.current_controller.changed
        controller = VistrailController()
        controller.set_vistrail(self.current_controller.vistrail,
                                self.current_controller.locator)
        controller.change_selected_version(self.current_parent_version)
        (results, _) = controller.execute_current_workflow()
        #print results[0]
        
#    def addMergedAliases( self, aliases, pipeline ):
#        if 'dvInputSpecs' in pipeline.aliases:
#            fileAliases = ','.join( [ "%s:%s" % ( self.files[i], aliases[self.files[i]] )  for i in range(self.filenum) ] )
#            varAliases = ','.join( [ "%s:%s" % ( self.vars[i], aliases[self.vars[i]] )  for i in range(self.varnum) ] )
#            gridAliases = ','.join( [ "%s:%s" % ( self.axes[i], aliases[self.axes[i]] )  for i in range(self.varnum) ] )
#            aliases[ 'dvInputSpecs' ] = ';'.join( [ fileAliases, varAliases, gridAliases ] )
#            print " dvInputSpecs: ", str( aliases[ 'dvInputSpecs' ] )
#        if 'dvCellSpecs' in pipeline.aliases:
#            aliases[ 'dvCellSpecs' ] = ','.join( [ "%s%s" % ( chr( ord('A') + int(aliases[self.cells[i].col_name]) ), aliases[self.cells[i].row_name] )  for i in range(self.cellnum) ] )
#            print " dvCellSpecs: ", str( aliases[ 'dvCellSpecs' ] )
        
    def previewChanges(self, aliases):
        print "previewChanges", aliases
        # we will just execute the pipeline with the given alias dictionary
        controller = VistrailController()
        controller.set_vistrail(self.plot_vistrail, self.locator)
        version = self.plot_vistrail.get_version_number(self.workflow_tag) if self.workflow_tag else controller.get_latest_version_in_graph()
        controller.change_selected_version(version)
        (results, _) = controller.execute_current_workflow(aliases)
        #print results[0]
        
    def discardChanges(self):
        print "discardChanges"
        print "FIXME"
        
    #functions related to provenance
    # we don't want to use the controller directly because we might be changing
    # a pipeline that is not the current pipeline
    def addPipelineAction(self, pipeline, controller, vistrail, 
                             parent_version):
        """addPipelineAction(pipeline: Pipeline, controller: VistrailController,
                             vistrail: Vistrail, parent_version: long) -> long
        
        """
        #print "addPipelineAction(%s,%s,%s,%s)"%(pipeline, controller, vistrail,
        #                                        parent_version)
        id_remap = {}
        action = core.db.action.create_paste_action(pipeline,
                                                    vistrail.idScope, 
                                                    id_remap)
                
        vistrail.add_action(action, parent_version, 
                            controller.current_session)
        controller.set_changed(True)
        controller.recompute_terse_graph()
        controller.invalidate_version_tree()
        #print "will return ", action.id
        return action.id
        
    def addParameterChangesFromAliasesAction(self, pipeline, controller, vistrail,
                                             parent_version, aliases):
        param_changes = []
        newid = parent_version
#        print "addParameterChangesFromAliasesAction()"
#        print "Aliases: %s " % str( aliases )
#        print "Pipeline Aliases: %s " % str( pipeline.aliases )
        for k,value in aliases.iteritems():
            alias = pipeline.aliases.get(k,None) # alias = (type, oId, parentType, parentId, mId)
            if alias:
                module = pipeline.modules[alias[4]]
                function = module.function_idx[alias[3]]
                old_param = function.parameter_idx[alias[1]]
                #print alias, module, function, old_param
                if old_param.strValue != value:
                    new_param = VistrailController.update_parameter(controller, 
                                                                    old_param, 
                                                                    value)
                    if new_param is not None:
                        op = ('change', old_param, new_param, 
                              function.vtType, function.real_id)
                        param_changes.append(op)
#                        print "Added parameter change for alias=%s, value=%s" % ( k, value  )
                    else:
                        debug.warning("CDAT Package: Change parameter %s in widget %s was not generated"%(k, self.name))
            else:
                debug.warning( "CDAT Package: Alias %s does not exist in pipeline" % (k) )
        if len(param_changes) > 0:
            action = core.db.action.create_action(param_changes)
            vistrail.add_action(action, parent_version, controller.current_session)
            controller.set_changed(True)
            controller.recompute_terse_graph()
            controller.invalidate_version_tree()
            newid = action.id
        return newid
    
class Cell(object):
    def __init__(self, type=None, row_name=None, col_name=None):
        self.type = type
        self.row_name = row_name
        self.col_name = col_name 