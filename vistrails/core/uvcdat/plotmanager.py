###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: contact@vistrails.org
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

import os
import ConfigParser
from PyQt4 import QtCore
from core.uvcdat.plot_registry import PlotRegistry
from core.uvcdat.utils import UVCDATInternalError
from core.uvcdat.plot_pipeline_helper import PlotPipelineHelper

#assuming vistrail files and config files for plots are in ./plots
PLOT_FILES_PATH = os.path.join(os.path.dirname(__file__),
                             'plots')

global _plot_manager
_plot_manager = None

class PlotManager(QtCore.QObject):
    def __init__(self):
        """__init__() -> PlotManager
        
        """
        global _plot_manager
        if _plot_manager:
            m = "Plot manager can only be constructed once."
            raise UVCDATInternalError(m)
        QtCore.QObject.__init__(self)
        _plot_manager = self
        self._plot_list = {}
        self._plot_helpers = {}
        self._plot_versions = {}
        self._registry = None
        self._userplots = None
        self._plots = None
        
    def init_registry(self):
        self._registry = PlotRegistry()
        self._registry.set_global()

    def initialize_plots(self):
        self.load_plots() 
            
    def parse_helper_type_str(self, text):
        last_dot = text.rfind(".")
        if last_dot > -1:
            path = text[0:last_dot]
            klass_name = text[last_dot+1:]
            module = __import__(path, globals(), locals(), [klass_name])
            klass = getattr(module, klass_name)
        else:
            try:
                klass = globals()[klass_name]
            except:
                klass =None
        return klass
    
    def load_plots(self):
        self.load_vcs_plots()
        if not self._registry:
            raise UVCDATInternalError("Plot Registry must have been initialized")
        
        pkg_parser = ConfigParser.ConfigParser()
        if pkg_parser.read(os.path.join(PLOT_FILES_PATH, 'registry.cfg')):
            for p in pkg_parser.sections():
                #BAB for future, should check to make sure package successfully loaded before we load it's plot here
                # for now doing specific check for visit
                if p == 'VisIt':
                    from packages.VisIt.info import package_requirements as visit_requirements
                    try:
                        visit_requirements()
                    except Exception:
                        continue
                try:
                    plot_package_folder = os.path.join(PLOT_FILES_PATH,
                                                       pkg_parser.get(p,'codepath'))
                    plot_package_config_file = os.path.join(plot_package_folder, 
                                               pkg_parser.get(p,'config_file'))
                    
                    helper = PlotPipelineHelper
                    if pkg_parser.has_option(p, 'helper') :
                        helper = self.parse_helper_type_str(pkg_parser.get(p, 'helper'))
                    self._plot_helpers[p] = helper
                        
                    pl_parser = ConfigParser.ConfigParser()
                    if pl_parser.read(plot_package_config_file):
                        for pl in pl_parser.sections():
                            config_file = os.path.join(plot_package_folder, 
                                                       pl_parser.get(pl,'config_file'))
                            vt_file = os.path.join(plot_package_folder, 
                                                   pl_parser.get(pl, 'vt_file'))
                            if p not in self._plot_list:
                                self._plot_list[p] = {}
                            self._plot_list[p][pl] = self._registry.add_plot(pl,p,
                                                                        config_file, 
                                                                        vt_file)
                    try:
                        self._registry.load_plot_package(p)
                    except Exception, e:
                        print "Error when loading %s plot --> "%p, str(e)
                        import traceback
                        traceback.print_exc()
                        
                except Exception, e:
                    print "Error when loading package_config_file: %s" % plot_package_config_file, str(e)
                    import traceback
                    traceback.print_exc()
                    
    def load_vcs_plots(self):
        from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper
        from gui.uvcdat.uvcdatCommons import plotTypes, gmInfos
        from packages.uvcdat_cdms.init import get_canvas
        if not self._registry:
            raise UVCDATInternalError("Plot Registry must have been initialized")
        
        for p in sorted(plotTypes.keys()): 
            #kitem = self.addPlotBar(k)
            if p not in self._plot_list:
                self._plot_list[p] = {}
                self._plot_helpers[p] = CDMSPipelineHelper
            for pl in plotTypes[p]:
                ## Special section here for VCS GMs they have one more layer
                self._plot_list[p][pl] = {}
                for m in get_canvas().listelements(str(pl).lower()):
                    self._plot_list[p][pl][m] = self._registry.add_plot(m,p,
                                                                        None, 
                                                                        None,
                                                                        pl)
                    #FIXME: get the var num from somewhere
                    self._plot_list[p][pl][m].varnum = int(gmInfos[pl]["nSlabs"])
            #vcs packages do not need to be loaded
            
    def get_plot_helper(self, plot_package):
        if plot_package in self._plot_helpers:
            return self._plot_helpers[plot_package]
            
    def get_plot_by_name(self, plot_type, plot_name=None):
        for pkg in self._plot_list:
            for pl in self._plot_list[pkg]:
                if plot_name is not None and type(self._plot_list[pkg][pl]) == type({}):
                    if pl == plot_type:
                        for m in self._plot_list[pkg][pl]:
                            if m == plot_name:
                                return self._plot_list[pkg][pl][m]
                elif plot_name is None and type(self._plot_list[pkg][pl]) != type({}):
                    if plot_type == pl:
                        return self._plot_list[pkg][pl]
        return None
    
    def get_plot(self, plot_package, plot_type, plot_name=None):
        if plot_name is not None:
            try:
                return self._plot_list[plot_package][plot_type][plot_name]
            except KeyError:
                return None
        else:
            try:
                return self._plot_list[plot_package][plot_type]
            except KeyError:
                return None
            
    def get_plot_by_vistrail_version(self, plot_package, vistrail, version):
        plots = self._plot_list[plot_package]
        vistrail_a = vistrail
        version_a = version
        pipeline = vistrail.getPipeline(version)
        for pl in plots.itervalues():
            vistrail_b = pl.plot_vistrail
            version_b = pl.workflow_version
            if (pl.are_workflows_equal(vistrail_a, vistrail_b, 
                                        version_a, version_b) and
                len(pipeline.aliases) == len(pl.workflow.aliases)):
                return pl
        
def get_plot_manager():
    global _plot_manager
    if not _plot_manager:
        raise UVCDATInternalError("plot manager not constructed yet.")
    return _plot_manager