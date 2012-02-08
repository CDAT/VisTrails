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
from core.system import vistrails_root_directory, execute_cmdline
from core.utils import Chdir
import core.requirements

def uvcdat_version():
    """uvcdat_version() -> string - Returns the current UV-CDAT version."""
    # 1.0 alpha is the first version released
    return '1.0-alpha'

def uvcdat_revision():
    """uvcdat_revision() -> str 
    When run on a working copy, shows the current git hash else
    shows the latest release revision

    """
    git_dir = os.path.join(vistrails_root_directory(), '..')
    with Chdir(git_dir):
        release = "<update_before_release>"
        if core.requirements.executable_file_exists('git'):
            lines = []
            result = execute_cmdline(['git', 'describe', '--always', '--abbrev=12'],
                                     lines)
            if len(lines) == 1:
                if result == 0:
                    release = lines[0].strip(" \n")
    return release

def short_about_string():
    return """UV-CDAT version %s.%s""" % \
            (uvcdat_version(), uvcdat_revision())
    