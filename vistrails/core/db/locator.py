############################################################################
##
## Copyright (C) 2006-2007 University of Utah. All rights reserved.
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

from core.vistrail.vistrail import Vistrail
from db.services.locator import XMLFileLocator as _XMLFileLocator, \
    DBLocator as _DBLocator

class CoreLocator(object):

    @staticmethod
    def load_from_gui(parent_widget):
        pass # Opens a dialog that the user will be able to use to
             # show the right values, and returns a locator suitable
             # for loading a file

    @staticmethod
    def save_from_gui(parent_widget, locator):
        pass # Opens a dialog that the user will be able to use to
             # show the right values, and returns a locator suitable
             # for saving a file

class XMLFileLocator(_XMLFileLocator, CoreLocator):

    def __init__(self, filename):
        _XMLFileLocator.__init__(self, filename)

    def load(self):
        vistrail = _XMLFileLocator.load(self)
        Vistrail.convert(vistrail)
        vistrail.locator = self
        return vistrail

    def save(self, vistrail):
        _XMLFileLocator.save(self, vistrail)
        vistrail.locator = self

    ##########################################################################

    def __eq__(self, other):
        if type(other) != XMLFileLocator:
            return False
        return self._name == other._name

    ##########################################################################

    @staticmethod
    def load_from_gui(parent_widget):
        import gui.extras.core.db.locator as db_gui
        return db_gui.get_load_xml_file_locator_from_gui(parent_widget)

    @staticmethod
    def save_from_gui(parent_widget, locator=None):
        import gui.extras.core.db.locator as db_gui
        return db_gui.get_save_xml_file_locator_from_gui(parent_widget, 
                                                         locator)

class DBLocator(_DBLocator, CoreLocator):

    def __init__(self, host, port, database, user, passwd, name=None,
                 vistrail_id=None, connection_id=None):
        _DBLocator.__init__(self, host, port, database, user, passwd, name,
                            vistrail_id, connection_id)

    def load(self):
        vistrail = _DBLocator.load(self)
        Vistrail.convert(vistrail)
        vistrail.locator = self
        return vistrail

    def save(self, vistrail):
        _DBLocator.save(self, vistrail)
        vistrail.locator = self

    ##########################################################################

    def __eq__(self, other):
        if type(other) != DBLocator:
            return False
        return (self._host == other._host and
                self._port == other._port and
                self._db == other._db and
                self._user == other._user and
                self._vt_name == other._vt_name and
                self._vt_id == other._vt_id)

    ##########################################################################
        
    @staticmethod
    def load_from_gui(parent_widget):
        import gui.extras.core.db.locator as db_gui
        return db_gui.get_load_db_locator_from_gui(parent_widget)

    @staticmethod
    def save_from_gui(parent_widget, locator=None):
        import gui.extras.core.db.locator as db_gui
        return db_gui.get_save_db_locator_from_gui(parent_widget, locator)
