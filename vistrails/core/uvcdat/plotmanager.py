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
        self._plot_versions = {}
        self._registry = None
        self._userplots = None
        self._plots = None
        
    def init_registry(self):
        self._registry = PlotRegistry()
        self._registry.set_global()

    def initialize_plots(self):
        self.load_plots() 
            
    def load_plots(self):
        if not self._registry:
            raise UVCDATInternalError("Plot Registry must have been initialized")
        
        pkg_parser = ConfigParser.ConfigParser()
        if pkg_parser.read(os.path.join(PLOT_FILES_PATH, 'registry.cfg')):
            for p in pkg_parser.sections():
                plot_package_folder = os.path.join(PLOT_FILES_PATH,
                                                   pkg_parser.get(p,'codepath'))
                plot_package_config_file = os.path.join(plot_package_folder, 
                                           pkg_parser.get(p,'config_file'))
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
                    print "Error when loading %s plot"%p, str(e)
                    import traceback
                    traceback.print_exc()