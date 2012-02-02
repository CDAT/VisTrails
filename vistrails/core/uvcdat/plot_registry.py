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

from PyQt4 import QtCore
# vistrails imports
import api
import core.db.action
from core.db.io import load_vistrail, get_workflow_diff
from core.db.locator import FileLocator
from gui.modules import get_widget_class
from gui.modules.constant_configuration import StandardConstantWidget
from core.modules.module_registry import get_module_registry
from core.vistrail.controller import VistrailController
from core.uvcdat.utils import UVCDATInternalError
from core.packagemanager import get_package_manager
from core import debug

#assuming vistrail files and config files for plots are in ./plots
PLOT_FILES_PATH = os.path.join(os.path.dirname(__file__),
                             'plots')

#do not use registry directly. Use get_plot_registry() to get the registry
global registry
registry = None

class PlotRegistry():
    def __init__(self):
        self.signals = PlotRegistrySignals()
        self.plots = {}
        self.registered = []
    
    def add_plot(self, name, plot_package, config_file, vt_file, parent=None):
        plot = None
        if not plot_package in self.plots:
            self.plots[plot_package] = {}
        if parent is not None:
            if parent not in self.plots[plot_package]:
                self.plots[plot_package][parent] = {}
            plot = Plot(name, plot_package,config_file, vt_file,parent)
            self.plots[plot_package][parent][name] = plot
            self.signals.emit_new_plot_type(self.plots[plot_package][parent][name])
        else:
            plot = Plot(name, plot_package, config_file, vt_file)
            self.plots[plot_package][name] = plot
        return plot 
            
        
    def load_plot_package(self, plot_package):
        if plot_package in self.plots:
            self.signals.emit_new_plot_package(plot_package)
            for plot in self.plots[plot_package].itervalues():
                plot.load()     
                if plot.loaded:
                    self.signals.emit_new_plot_type(self.plots[plot_package][plot.name])   
                
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
            
    def set_global(self):
        global registry

        if registry is not None:
            raise UVCDATInternalError("Global plot registry already set.")

        registry                 = self
        
class Plot(object):
    def __init__(self, name, package, config_file=None, vt_file=None, parent=None):
        self.name = name
        self.package = package
        self.parent = parent
        self.config_file = config_file
        self.serializedConfigAlias = None
        self.vt_file = vt_file
        self.locator = None
        if self.vt_file:
            self.locator = FileLocator(os.path.abspath(self.vt_file))
        self.cellnum = 1
        self.filenum = 1
        self.varnum = 0
        self.workflow_tag = None
        self.workflow = None
        self.workflow_version = -1
        self.filetypes = {}
        self.qt_filter = None
        self.files = []
        self.cells = []
        self.vars = []
        self.axes = []
        self._widget = None
        self.alias_widgets = {}
        self.alias_values = {}
        self.dependencies = []
        self.unsatisfied_deps = []
        self.loaded = False
        self.plot_vistrail = None
        self.current_parent_version = 0L
        self.current_controller = None
            
    def load(self, loadworkflow=True):
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
#                else:
#                    debug.warning("CDAT Package: file %s does not contain a required option 'workflow_tag'. Widget will not be loaded."%self.config_file)
#                    self.loaded = False
#                    return
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
            
                if config.has_option('global', 'serialized_config_alias'):
                    self.serializedConfigAlias = config.get('global', 'serialized_config_alias')

                    for y in range(self.filenum):
                        self.files.append( 'Filename' + str(y+1) )
                            
                    for v in range(self.varnum):
                        self.vars.append( 'VariableName' + str(v+1) )
                        self.axes.append( 'Axes' + str(v+1) )

                    for x in range(self.cellnum):
                        section_name = 'cell' + str(x+1)
                        if config.has_section(section_name):
                            cellType = config.get(section_name, 'celltype')
                            if config.has_option(section_name, 'address_alias'):
                                self.cells.append( Cell( cellType, None, None,
                                                     config.get(section_name, 'address_alias') ) )
                            else:
                                self.cells.append(Cell( cellType,"Row"+str(x+1), "Column"+str(x+1) ) )                                                              
                else:
                    
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
                
                if loadworkflow:
                    #load workflow in vistrail
                    #only if dependencies are enabled
                    manager = get_package_manager()
                    self.unsatisfied_deps = []
                    for dep in self.dependencies:
                        if not manager.has_package(dep):
                            self.unsatisfied_deps.append(dep)
                    if len(self.unsatisfied_deps) == 0:
                        try:
                            (self.plot_vistrail, abstractions , thumbnails, mashups) = load_vistrail(self.locator)
                            controller = VistrailController()
                            controller.set_vistrail(self.plot_vistrail, self.locator, 
                                                    abstractions, thumbnails,
                                                    mashups) 
    
                            self.workflow_version = self.plot_vistrail.get_version_number(self.workflow_tag) if self.workflow_tag else controller.get_latest_version_in_graph()
                            print " Loaded %s version: %s" % (  self.name, str( self.workflow_version ) )
                            controller.change_selected_version(self.workflow_version)
                            self.workflow = controller.current_pipeline
                            self.loaded = True
                        except Exception, err:
                            debug.warning( "Error loading workflow %s: %s" % ( self.name, err ) )
                            self.loaded = False
                    else:
                        debug.warning("UV-CDAT: %s widget could not be loaded \
    because it depends on packages that are not loaded:"%self.name)
                        debug.warning("  %s"%", ".join(self.unsatisfied_deps))
                        self.loaded = False
            else:
                debug.warning("UV-CDAT: file %s does not contain a 'global'\
 section. Widget will not be loaded."%self.config_file)
                self.loaded = False
            
    def getWidget(self, refresh=False):
        if self._widget == None or refresh:
            self.loadWidget()
        return self._widget
    def setWidget(self, widget):
        self._widget = widget
    widget = property(getWidget, setWidget)
    
    def loadWidget(self):
        from PyQt4 import QtGui
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
                    widget_type = get_widget_class(p_module)
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
        self._widget = widget
    
    def computeHiddenAliases(self):
        result = []
        result.extend(self.files)
        result.extend(self.vars)
        result.extend(self.axes)
        if self.serializedConfigAlias: 
            result.extend( self.serializedConfigAlias )
        for c in self.cells:
            result.append(c.row_name)
            result.append(c.col_name)
        return result
    
    @staticmethod
    def are_workflows_equal(vistrail_a, vistrail_b, version_a, version_b):
        diff_versions = ((vistrail_a, version_a), (vistrail_b, version_b))
        diff = get_workflow_diff(*diff_versions)
        (p1, p2, v1Andv2, heuristicMatch, v1Only, v2Only, paramChanged) = diff
        if len(v1Only) == 0 and len(v2Only)==0:
            return True
        return False
    
    def checkIfWorkflowsAreCompatible(self):
        vistrail_a = self.current_controller.vistrail
        vistrail_b = self.plot_vistrail
        version_a = self.current_parent_version
        version_b = self.workflow_version
        return self.are_workflows_equal(vistrail_a, vistrail_b,
                                        version_a, version_b)
    
    def resetWorkflow(self):
        pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
        self.current_controller.change_selected_version(self.current_parent_version)
        ids = []
        for module in pipeline.module_list:
            ids.append(module.id)
        action = self.current_controller.delete_module_list(ids)
        self.current_parent_version = action.id
        return action
        
    def writePipelineToCurrentVistrail(self, aliases):
        """writePipelineToVistrail(aliases: dict) -> list of actions
        It will compute necessary actions and add to the current vistrail, 
        starting at self.parent_version. In the case self.parent_version
        does not contain a valid workflow, we will start from the root with
        a new pipeline.
        
        """
        actions = []
        #print self.current_controller
        if self.current_controller is None:
            self.current_controller = api.get_current_controller()
            self.current_parent_version = 0L
        else:
            if self.current_parent_version > 0L:
                pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
                if (len(pipeline.aliases) >= len(self.workflow.aliases) and
                    self.checkIfWorkflowsAreCompatible()):
                    paliases = set(pipeline.aliases.keys())
                    waliases = set(self.workflow.aliases.keys())
                    if len(waliases - paliases) != 0:
                        actions.append(self.resetWorkflow())
        # print "writePipelineToCurrentVistrail: controller ", self.current_controller
        #print "version ", self.current_parent_version 
        pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
        if len(pipeline.module_list) == 0:
            #create actions and paste them in current vistrail
            vistrail = self.current_controller.vistrail
            if vistrail:
                action = self.addPipelineAction(self.workflow,
                                               self.current_controller,
                                               vistrail, 
                                               self.current_parent_version)
                actions.append(action)
                newid = action.id
                #no tagging for now
#                newtag = self.name
#                count = 1
#                while vistrail.hasTag(newtag):
#                    newtag = "%s %s"%(self.name, count)
#                    count += 1 
#                vistrail.addTag(newtag, newid)
                self.current_parent_version = newid
                
        #now we update pipeline with current parameter values
        pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
        self.addMergedAliases( aliases, pipeline )
        action = self.addParameterChangesFromAliasesAction(pipeline, 
                                        self.current_controller, 
                                        self.current_controller.vistrail, 
                                        self.current_parent_version, aliases)
        actions.append(action)
        if action:
            self.current_parent_version = action.id
        return actions
                
    def applyChanges(self, aliases):
#        print "applyChanges"
        return self.writePipelineToCurrentVistrail(aliases)
        #pipeline = self.current_controller.vistrail.getPipeline(self.current_parent_version)
        #print "Controller changed ", self.current_controller.changed
        #controller = VistrailController()
        #controller.set_vistrail(self.current_controller.vistrail,
        #                        self.current_controller.locator)
        #controller.change_selected_version(self.current_parent_version)
        #(results, _) = controller.execute_current_workflow()
        #print results[0]
        
    def addMergedAliases( self, aliases, pipeline ):
        if self.serializedConfigAlias:
            if self.serializedConfigAlias in pipeline.aliases:
                try:
                    fileAliases = '|'.join( [ "%s!%s!%s" % ( self.files[i], aliases[self.files[i]], aliases[".".join([self.files[i],"url"])] )  for i in range(self.filenum) ] )
                    varAliases = '|'.join( [ "%s!%s" % ( self.vars[i], aliases[self.vars[i]] )  for i in range(self.varnum) ] )
                    gridAliases = '|'.join( [ "%s!%s" % ( self.axes[i], aliases[self.axes[i]] )  for i in range(self.varnum) ] )
                    cellAliases = '|'.join( [ "location%d!%s" % ( i, self.cells[i].getAddress( aliases ) ) for i in range( len(self.cells) ) ] )
                    aliases[ self.serializedConfigAlias ] = ';'.join( [ fileAliases, varAliases, gridAliases, cellAliases ] )
                    print " vcdatInputSpecs: ", str( aliases[ self.serializedConfigAlias ] )
                except KeyError, err:
                    # it failed because the other aliases do not exist
                    # it's very likely that the serialized alias is already set.
                    debug.debug("Could not build serialized alias from other aliases. Using current one.")
#                if 'vcdatCellSpecs' in pipeline.aliases:
#                aliases[ 'vcdatCellSpecs' ] = ','.join( [ "%s%s" % ( chr( ord('A') + int(aliases[self.cells[i].col_name]) ), aliases[self.cells[i].row_name] )  for i in range(self.cellnum) ] )
#                print " vcdatCellSpecs: ", str( aliases[ 'vcdatCellSpecs' ] )
        
    def unserializeAliases(self, aliases):
        if self.serializedConfigAlias:
            if self.serializedConfigAlias in aliases:
                (fileAliases, varAliases, gridAliases, cellAliases) = aliases[self.serializedConfigAlias].split(";")
                fileAliases = fileAliases.split("|")
                varAliases = varAliases.split("|")
                gridAliases = gridAliases.split("|")
                cellAliases = cellAliases.split("|")
                for i in range(self.filenum):
                    a, v = fileAliases[i].split("!")
                    aliases[self.files[i]] = v
                for i in range(self.varnum):
                    a,v = varAliases[i].split("!")
                    aliases[self.vars[i]] = v
                for i in range(self.varnum):
                    a,v = gridAliases[i].split("!")
                    aliases[self.axes[i]] = v
                for i in range( len( cellAliases ) ):
                    a,v = cellAliases[i].split("!")
                    aliases[ a ] = v
                    
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
        print "addPipelineAction(%s,%s,%s,%s)"%(pipeline, controller, vistrail, parent_version)
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
        return action
        
    def addParameterChangesFromAliasesAction(self, pipeline, controller, vistrail, parent_version, aliases):
        param_changes = []
        newid = parent_version
        print "addParameterChangesFromAliasesAction()"
        print "Aliases: %s " % str( aliases )
        print "Pipeline Aliases: %s " % str( pipeline.aliases )
        aliasList = aliases.iteritems()
        for k,value in aliasList:
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
                        debug.debug("CDAT Package: Change parameter %s in widget %s was not generated"%(k, self.name))
            else:
                debug.debug( "CDAT Package: Alias %s does not exist in pipeline" % (k) )
        action = None
        if len(param_changes) > 0:
            action = core.db.action.create_action(param_changes)
            controller.change_selected_version(parent_version)
            controller.add_new_action(action)
            controller.perform_action(action)
        return action
    
class Cell(object):
    def __init__(self, type=None, row_name=None, col_name=None, address_name=None):
        self.type = type
        self.row_name = row_name
        self.col_name = col_name
        self.address_name = address_name
        
    def getAddress( self, aliases ):
        srow = aliases[ self.row_name ] 
        icol = int( aliases[ self.col_name ] ) - 1
        colHeader = chr( ord('A') + icol )
        addr = "%c%s" % ( colHeader, srow )
        return addr
        
class PlotRegistrySignals(QtCore.QObject):
    # new_module_signal is emitted with descriptor of new module
    new_plot_type_signal = QtCore.SIGNAL("new_plot_type")
    new_plot_package_signal = QtCore.SIGNAL("new_plot_package")
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        
    def emit_new_plot_type(self, plot):
        self.emit(self.new_plot_type_signal, plot)

    def emit_new_plot_package(self, plot_package_name):
        self.emit(self.new_plot_package_signal, plot_package_name)
        
def get_plot_registry():
    global registry
    if not registry:
        raise UVCDATInternalError("Plot Registry not constructed yet.")
    return registry

def plot_registry_loaded():
    global registry
    return registry is not None

##############################################################################