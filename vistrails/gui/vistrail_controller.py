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
from PyQt4 import QtCore, QtGui
from core.common import *
from core.configuration import get_vistrails_configuration
from core import debug
import core.db.action
import core.db.locator
import core.modules.vistrails_module
from core.data_structures.graph import Graph
from core.utils import VistrailsInternalError, InvalidPipeline
from core.log.opm_graph import OpmGraph
from core.modules.abstraction import identifier as abstraction_pkg
from core.modules.module_registry import get_module_registry, MissingPort
from core.modules.package import Package
from core.packagemanager import PackageManager
from core.query.version import TrueSearch
from core.query.visual import VisualQuery
import core.system
from core.system import vistrails_default_file_type
from core.vistrail.annotation import Annotation
from core.vistrail.controller import VistrailController as BaseController, \
    vt_action
from core.vistrail.location import Location
from core.vistrail.module import Module
from core.vistrail.module_function import ModuleFunction
from core.vistrail.module_param import ModuleParam
from core.vistrail.pipeline import Pipeline
from core.vistrail.port_spec import PortSpec
from core.vistrail.vistrail import Vistrail, TagExists
from core.vistrails_tree_layout_lw import VistrailsTreeLayoutLW
from gui.utils import show_warning, show_question, YES_BUTTON, NO_BUTTON

import core.analogy
import copy
import os.path
import math

################################################################################

class VistrailController(QtCore.QObject, BaseController):
    """
    VistrailController is the class handling all action control in
    VisTrails. It updates pipeline, vistrail and emit signals to
    update the view

    Signals emitted:

    vistrailChanged(): emitted when the version tree needs to be
    recreated (for example, a node was added/deleted or the layout
    changed).

    versionWasChanged(): emitted when the current version (the one
    being displayed by the pipeline view) has changed.

    searchChanged(): emitted when the search statement from the
    version view has changed.

    stateChanged(): stateChanged is called when a vistrail goes from
    unsaved to saved or vice-versa.
    
    notesChanged(): notesChanged is called when the version notes have
    been updated

    """

    def __init__(self, vis=None, auto_save=True, name=''):
        """ VistrailController(vis: Vistrail, name: str) -> VistrailController
        Create a controller for a vistrail.

        """
        QtCore.QObject.__init__(self)
        BaseController.__init__(self, vis)
        self.name = ''
        self.file_name = None
        self.set_file_name(name)
        # FIXME: self.current_pipeline_view currently stores the SCENE, not the VIEW
        self.current_pipeline_view = None
        self.vistrail_view = None
        self.reset_pipeline_view = False
        self.reset_version_view = True
        self.quiet = False
        # if self.search is True, vistrail is currently being searched
        self.search = None
        self.search_str = None
        # If self.refine is True, search mismatches are hidden instead
        # of ghosted
        self.refine = False
        self.full_tree = False
        self.analogy = {}
        # if self._auto_save is True, an auto_saving timer will save a temporary
        # file every 2 minutes
        self._auto_save = auto_save
        self.timer = QtCore.QTimer(self)
        self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.write_temporary)
        self.timer.start(1000 * 60 * 2) # Save every two minutes

        self._previous_graph_layout = None
        self._current_graph_layout = VistrailsTreeLayoutLW()
        self.animate_layout = False
        self.num_versions_always_shown = 1

    ##########################################################################
    # Signal vistrail relayout / redraw

    def replace_unnamed_node_in_version_tree(self, old_version, new_version):
        """method analogous to invalidate_version_tree but when only
        a single unnamed node and links need to be updated. Much faster."""
        self.reset_version_view = False
        try:
            self.emit(QtCore.SIGNAL('invalidateSingleNodeInVersionTree'),
                                    old_version, new_version)
        finally:
            self.reset_version_view = True

    def invalidate_version_tree(self, reset_version_view=True, animate_layout=False):
        """ invalidate_version_tree(reset_version_tree: bool, animate_layout: bool) -> None
        
        """
        self.reset_version_view = reset_version_view
        self.animate_layout = animate_layout
        #FIXME: in the future, rename the signal
        try:
            self.emit(QtCore.SIGNAL('vistrailChanged()'))
        finally:
            self.reset_version_view = True

    def has_move_actions(self):
        return self.current_pipeline_view.hasMoveActions()

    def flush_move_actions(self):
        return self.current_pipeline_view.flushMoveActions()

    ##########################################################################
    # Autosave

    def enable_autosave(self):
        self._auto_save = True

    def disable_autosave(self):
        self._auto_save = False

    def get_locator(self):
        from gui.application import VistrailsApplication
        if (self._auto_save and 
            VistrailsApplication.configuration.check('autosave')):
            return self.locator or core.db.locator.untitled_locator()
        else:
            return None

    def cleanup(self):
        locator = self.get_locator()
        if locator:
            locator.clean_temporaries()
        self.disconnect(self.timer, QtCore.SIGNAL("timeout()"), self.write_temporary)
        self.timer.stop()

    def set_vistrail(self, vistrail, locator, abstractions=None, thumbnails=None):
        """ set_vistrail(vistrail: Vistrail, locator: VistrailLocator) -> None
        Start controlling a vistrail
        
        """
        # self.vistrail = vistrail
        BaseController.set_vistrail(self, vistrail, locator, abstractions,
                                    thumbnails)
        if locator != None:
            self.set_file_name(locator.name)
        else:
            self.set_file_name('')
        if locator and locator.has_temporaries():
            self.set_changed(True)

    ##########################################################################
    # Actions, etc
    
    def perform_action(self, action, quiet=None):
        """ performAction(action: Action, quiet=None) -> timestep

        performs given action on current pipeline.

        quiet and self.quiet control invalidation of version
        tree. If quiet is set to any value, it overrides the field
        value self.quiet.

        If the value is True, then no invalidation happens (gui is not
        updated.)
        
        """
        if action is not None:
            BaseController.perform_action(self,action)

            if quiet is None:
                if not self.quiet:
                    self.invalidate_version_tree(False)
            else:
                if not quiet:
                    self.invalidate_version_tree(False)
            return action.db_id
        return None

    def add_new_action(self, action):
        """add_new_action(action) -> None

        Call this function to add a new action to the vistrail being
        controlled by the vistrailcontroller.

        FIXME: In the future, this function should watch the vistrail
        and get notified of the change.

        """
        if action is not None:
            BaseController.add_new_action(self, action)
            self.emit(QtCore.SIGNAL("new_action"), action)
            self.recompute_terse_graph()

    ##########################################################################

    @vt_action
    def add_module_action(self, module):
        if not self.current_pipeline:
            raise Exception("No version is selected")
        action = core.db.action.create_action([('add', module)])
        return action

    def add_module_from_descriptor(self, descriptor, x=0.0, y=0.0, 
                                   internal_version=-1):
        module = self.create_module_from_descriptor(descriptor, x, y, 
                                                    internal_version)
        action = self.add_module_action(module)
        return module


    def add_module(self, x, y, identifier, name, namespace='', 
                   internal_version=-1):
        """ addModule(x: int, y: int, identifier, name: str, namespace='') 
               -> Module
        Add a new module into the current pipeline
        
        """
        module = self.create_module(identifier, name, namespace, x, y,
                                    internal_version)
        action = self.add_module_action(module)
        return module
            
    def delete_module(self, module_id):
        """ delete_module(module_id: int) -> version id
        Delete a module from the current pipeline
        
        """
        return self.delete_module_list([module_id])

    def create_module_list_deletion_action(self, pipeline, module_ids):
        """ create_module_list_deletion_action(
               pipeline: Pipeline,
               module_ids: [int]) -> Action
        Create action that will delete multiple modules from the given pipeline.

        """
        ops = BaseController.delete_module_list_ops(self, pipeline, module_ids)
        return core.db.action.create_action(ops)

    @vt_action
    def delete_module_list(self, module_ids):
        """ delete_module_list(module_ids: [int]) -> [version id]
        Delete multiple modules from the current pipeline
        
        """
        action = self.create_module_list_deletion_action(self.current_pipeline,
                                                         module_ids)
        return action

    def move_module_list(self, move_list):
        """ move_module_list(move_list: [(id,x,y)]) -> [version id]        
        Move all modules to a new location. No flushMoveActions is
        allowed to to emit to avoid recursive actions
        
        """
        action_list = []
        for (id, x, y) in move_list:
            module = self.current_pipeline.get_module_by_id(id)
            loc_id = self.vistrail.idScope.getNewId(Location.vtType)
            location = Location(id=loc_id,
                                x=x, 
                                y=y,
                                )
            if module.location and module.location.id != -1:
                old_location = module.location
                action_list.append(('change', old_location, location,
                                    module.vtType, module.id))
            else:
                # probably should be an error
                action_list.append(('add', location, module.vtType, module.id))
        action = core.db.action.create_action(action_list)
        self.add_new_action(action)
        return self.perform_action(action)

    @vt_action
    def add_connection_action(self, connection):
        action = core.db.action.create_action([('add', connection)])
        return action

    def add_connection(self, output_id, output_port_spec, 
                       input_id, input_port_spec):
        """ add_connection(output_id: long,
                           output_port_spec: PortSpec | str,
                           input_id: long,
                           input_port_spec: PortSpec | str) -> Connection
        Add a new connection into Vistrail
        
        """
        connection = \
            self.create_connection_from_ids(output_id, output_port_spec, 
                                            input_id, input_port_spec)
        action = self.add_connection_action(connection)
        return connection
    
    def delete_connection(self, id):
        """ delete_connection(id: int) -> version id
        Delete a connection with id 'id'
        
        """
        return self.delete_connection_list([id])

    @vt_action
    def delete_connection_list(self, connect_ids):
        """ delete_connection_list(connect_ids: list) -> version id
        Delete a list of connections
        
        """
        action_list = []
        for c_id in connect_ids:
            action_list.append(('delete', 
                                self.current_pipeline.connections[c_id]))
        action = core.db.action.create_action(action_list)
        return action

    @vt_action
    def add_function_action(self, module, function):
        action = core.db.action.create_action([('add', function, 
                                                module.vtType, module.id)])
        return action

    def add_function(self, module, function_name):
        function = self.create_function(module, function_name)
        action = self.add_function_action(module, function)
        return function

    @vt_action
    def update_function(self, module, function_name, param_values, old_id=-1L,
                        aliases=[]):
        op_list = self.update_function_ops(module, function_name, param_values,
                                           old_id, aliases=aliases)
        action = core.db.action.create_action(op_list)
        return action

    @vt_action
    def update_parameter(self, function, old_param_id, new_value):
        old_param = function.parameter_idx[old_param_id]
        new_param = BaseController.update_parameter(self, old_param, new_value)
        if new_param is None:
            return None
        op = ('change', old_param, new_param, 
              function.vtType, function.real_id)
        action = core.db.action.create_action([op])
        return action

    @vt_action
    def delete_method(self, function_pos, module_id):
        """ delete_method(function_pos: int, module_id: int) -> version id
        Delete a method with function_pos from module module_id

        """

        module = self.current_pipeline.get_module_by_id(module_id)
        function = module.functions[function_pos]
        action = core.db.action.create_action([('delete', function,
                                                module.vtType, module.id)])
        return action

    @vt_action
    def delete_annotation(self, key, module_id):
        """ delete_annotation(key: str, module_id: long) -> version_id
        Deletes an annotation from a module
        
        """
        module = self.current_pipeline.get_module_by_id(module_id)
        annotation = module.get_annotation_by_key(key)
        action = core.db.action.create_action([('delete', annotation,
                                                module.vtType, module.id)])
        return action

    @vt_action
    def add_annotation(self, pair, module_id):
        """ add_annotation(pair: (str, str), moduleId: int)        
        Add/Update a key/value pair annotation into the module of
        moduleId
        
        """
        assert type(pair[0]) == type('')
        assert type(pair[1]) == type('')
        if pair[0].strip()=='':
            return

        module = self.current_pipeline.get_module_by_id(module_id)
        a_id = self.vistrail.idScope.getNewId(Annotation.vtType)
        annotation = Annotation(id=a_id,
                                key=pair[0], 
                                value=pair[1],
                                )
        if module.has_annotation_with_key(pair[0]):
            old_annotation = module.get_annotation_by_key(pair[0])
            action = \
                core.db.action.create_action([('change', old_annotation,
                                                   annotation,
                                                   module.vtType, module.id)])
        else:
            action = core.db.action.create_action([('add', annotation,
                                                        module.vtType, 
                                                        module.id)])
        return action

    def update_functions_ops_from_ids(self, module_id, functions):
        module = self.current_pipeline.modules[module_id]
        return self.update_functions_ops(module, functions)

    def update_port_spec_ops_from_ids(self, module_id, deleted_ports, 
                                      added_ports):
        module = self.current_pipeline.modules[module_id]
        return self.update_port_spec_ops(module, deleted_ports, added_ports)

    @vt_action
    def update_functions(self, module, functions):
        op_list = self.update_functions_ops(module, functions)
        action = core.db.action.create_action(op_list)
        return action

    @vt_action
    def update_ports_and_functions(self, module_id, deleted_ports, added_ports,
                                   functions):
        op_list = self.update_port_spec_ops_from_ids(module_id, deleted_ports, 
                                                     added_ports)
        op_list.extend(self.update_functions_ops_from_ids(module_id, functions))
        action = core.db.action.create_action(op_list)
        return action

    @vt_action
    def update_ports(self, module_id, deleted_ports, added_ports):
        op_list = self.update_port_spec_ops_from_ids(module_id, deleted_ports, 
                                                     added_ports)
        action = core.db.action.create_action(op_list)
        return action

    def has_module_port(self, module_id, port_tuple):
        """ has_module_port(module_id: int, port_tuple: (str, str)): bool
        Parameters
        ----------
        
        - module_id : 'int'        
        - port_tuple : (portType, portName)

        Returns true if there exists a module port in this module with given params

        """
        (type, name) = port_tuple
        module = self.current_pipeline.get_module_by_id(module_id)
        return len([x for x in module.db_portSpecs
                    if x.name == name and x.type == type]) > 0

    @vt_action
    def add_module_port(self, module_id, port_tuple):
        """ add_module_port(module_id: int, port_tuple: (str, str, list)
        Parameters
        ----------
        
        - module_id : 'int'        
        - port_tuple : (portType, portName, portSpec)
        
        """
        module = self.current_pipeline.get_module_by_id(module_id)
        p_id = self.vistrail.idScope.getNewId(PortSpec.vtType)
        port_spec = PortSpec(id=p_id,
                             type=port_tuple[0],
                             name=port_tuple[1],
                             sigstring=port_tuple[2],
                             )
        action = core.db.action.create_action([('add', port_spec,
                                                module.vtType, module.id)])
        return action

    @vt_action
    def delete_module_port(self, module_id, port_tuple):
        """
        Parameters
        ----------
        
        - module_id : 'int'
        - port_tuple : (portType, portName, portSpec)
        
        """
        spec_id = -1
        module = self.current_pipeline.get_module_by_id(module_id)
        port_spec = module.get_portSpec_by_name((port_tuple[1], port_tuple[0]))
        action_list = [('delete', port_spec, module.vtType, module.id)]
        for function in module.functions:
            if function.name == port_spec.name:
                action_list.append(('delete', function, 
                                    module.vtType, module.id))
        action = core.db.action.create_action(action_list)
        return action

    def create_group(self, module_ids, connection_ids):
        self.flush_move_actions()
        (group, connections) = \
            BaseController.create_group(self, self.current_pipeline, 
                                        module_ids, connection_ids)
        op_list = []
        op_list.extend(('delete', self.current_pipeline.connections[c_id])
                       for c_id in connection_ids)
        op_list.extend(('delete', self.current_pipeline.modules[m_id]) 
                       for m_id in module_ids)
        op_list.append(('add', group))
        op_list.extend(('add', c) for c in connections)
        action = core.db.action.create_action(op_list)
        self.add_new_action(action)
#         for op in action.operations:
#             print op.vtType, op.what, op.old_obj_id, op.new_obj_id
        result = self.perform_action(action)
        return group
    
    def create_abstraction(self, module_ids, connection_ids, name):
        self.flush_move_actions()
        (abstraction, connections) = \
            BaseController.create_abstraction(self, self.current_pipeline, 
                                              module_ids, connection_ids, name)
        op_list = []
        op_list.extend(('delete', self.current_pipeline.connections[c_id])
                       for c_id in connection_ids)
        op_list.extend(('delete', self.current_pipeline.modules[m_id]) 
                       for m_id in module_ids)
        op_list.append(('add', abstraction))
        op_list.extend(('add', c) for c in connections)
        action = core.db.action.create_action(op_list)
        self.add_new_action(action)
        result = self.perform_action(action)
        return abstraction

    def create_abstractions_from_groups(self, group_ids):
        for group_id in group_ids:
            self.create_abstraction_from_group(group_id)

    def create_abstraction_from_group(self, group_id, name=""):
        self.flush_move_actions()
        name = self.get_abstraction_name(name)
        
        (abstraction, connections) = \
            BaseController.create_abstraction_from_group(self, 
                                                         self.current_pipeline, 
                                                         group_id, name)

        op_list = []
        getter = self.get_connections_to_and_from
        op_list.extend(('delete', c)
                       for c in getter(self.current_pipeline, [group_id]))
        op_list.append(('delete', self.current_pipeline.modules[group_id]))
        op_list.append(('add', abstraction))
        op_list.extend(('add', c) for c in connections)
        action = core.db.action.create_action(op_list)
        self.add_new_action(action)
        result = self.perform_action(action)
        return abstraction


    def ungroup_set(self, module_ids):
        self.flush_move_actions()
        for m_id in module_ids:
            self.create_ungroup(m_id)

    def create_ungroup(self, module_id):
        (modules, connections) = \
            BaseController.create_ungroup(self, self.current_pipeline, 
                                          module_id)
        pipeline = self.current_pipeline
        old_conn_ids = self.get_module_connection_ids([module_id], 
                                                      pipeline.graph)
        op_list = []
        op_list.extend(('delete', pipeline.connections[c_id]) 
                       for c_id in old_conn_ids)
        op_list.append(('delete', pipeline.modules[module_id]))
        op_list.extend(('add', m) for m in modules)
        op_list.extend(('add', c) for c in connections)
        action = core.db.action.create_action(op_list)
        self.add_new_action(action)
        res = self.perform_action(action)
        self.current_pipeline.validate(False)
        return res

    def create_abstraction_with_prompt(self, module_ids, connection_ids, 
                                       name=""):
        name = self.get_abstraction_name(name)
        if name is None:
            return
        return self.create_abstraction(module_ids, connection_ids, name)

    def update_notes(self, notes):
        """
        Parameters
        ----------

        - notes : 'QtCore.QString'
        
        """
        self.flush_move_actions()
        
        if self.vistrail.set_notes(self.current_version, str(notes)):
            self.emit(QtCore.SIGNAL('notesChanged()'))

    ##########################################################################
    # Workflow Execution
    
    def execute_workflow_list(self, vistrails):
        old_quiet = self.quiet
        self.quiet = True
        (results, changed) = BaseController.execute_workflow_list(self, 
                                                                  vistrails)        
        self.quiet = old_quiet
        if changed:
            self.invalidate_version_tree(False)

    def execute_current_workflow(self, custom_aliases=None):
        """ execute_current_workflow() -> None
        Execute the current workflow (if exists)
        
        """
        self.flush_move_actions()
        if self.current_pipeline:
            locator = self.get_locator()
            if locator:
                locator.clean_temporaries()
                locator.save_temporary(self.vistrail)
            self.execute_workflow_list([(self.locator,
                                         self.current_version,
                                         self.current_pipeline,
                                         self.current_pipeline_view,
                                         custom_aliases,
                                         None)])

    def enable_missing_package(self, identifier, deps):
        from gui.application import VistrailsApplication
        msg = "VisTrails needs to enable package '%s'." % identifier
        if len(deps) > 0:
            msg += (" This will also enable the dependencies: %s." 
                    " Do you want to enable these packages?") % str(deps)
        else:
            msg += " Do you want to enable this package?"
        res = show_question('Enable package?',
                            msg,
                            [YES_BUTTON, NO_BUTTON], 
                            YES_BUTTON)
        if res == NO_BUTTON:
#             QtGui.QMessageBox.warning(VistrailsApplication.builderWindow,
#                                       'Missing modules',
#                                       'Some necessary modules will be missing.')
            return False
        return True

    def install_missing_package(self, identifier):
        res = show_question('Install package?',
                            "This pipeline contains a module"
                            " in package '%s', which"
                            " is not installed. Do you want to"
                            " install and enable that package?" % \
                                identifier, [YES_BUTTON, NO_BUTTON],
                            YES_BUTTON)
        return res == YES_BUTTON

    def change_selected_version(self, new_version, report_all_errors=True,
                                do_validate=True, from_root=False):
        """change_selected_version(new_version: int,
                                   report_all_errors: boolean,
                                   do_validate: boolean,
                                   from_root: boolean)

        Change the current vistrail version into new_version and emit a
        notification signal.

        NB: in most situations, the following post-condition holds:

        >>> controller.change_selected_version(v)
        >>> assert v == controller.current_version

        In some occasions, however, the controller will not be able to
        switch to the desired version. One example where this can
        happen is when the selected version has obsolete modules (that
        is, the currently installed package for those modules has
        module upgrades). In these cases, change_selected_version will
        return a new version which corresponds to a workflow that was
        created by the upgrading mechanism that packages can provide.
        
        """

        try:
            self.do_version_switch(new_version, report_all_errors,
                                   do_validate, from_root)
        except InvalidPipeline, e:
            from gui.application import VistrailsApplication


#             def process_err(err):
#                 if isinstance(err, Package.InitializationFailed):
#                     QtGui.QMessageBox.critical(
#                         VistrailsApplication.builderWindow,
#                         'Package load failed',
#                         'Package "%s" failed during initialization. '
#                         'Please contact the developer of that package '
#                         'and report a bug.' % err.package.name)
#                 elif isinstance(err, PackageManager.MissingPackage):
#                     QtGui.QMessageBox.critical(
#                         VistrailsApplication.builderWindow,
#                         'Unavailable package',
#                         'Cannot find package "%s" in\n'
#                         'list of available packages. \n'
#                         'Please install it first.' % err._identifier)
#                 elif issubclass(err.__class__, MissingPort):
#                     msg = ('Cannot find %s port "%s" for module "%s" '
#                            'in loaded package "%s". A different package '
#                            'version might be necessary.') % \
#                            (err._port_type, err._port_name, 
#                             err._module_name, err._package_name)
#                     QtGui.QMessageBox.critical(
#                         VistrailsApplication.builderWindow, 'Missing port',
#                         msg)
#                 else:
#                     QtGui.QMessageBox.critical(
#                         VistrailsApplication.builderWindow,
#                         'Invalid Pipeline', str(err))

            # VisTrails will not raise upgrade exceptions unless
            # configured to do so. To get the upgrade requests,
            # configuration option upgradeModules must be set to True.

            exception_set = e.get_exception_set()
            if len(exception_set) > 0:
                msg_box = QtGui.QMessageBox(VistrailsApplication.builderWindow)
                msg_box.setIcon(QtGui.QMessageBox.Warning)
                msg_box.setText("The current workflow could not be validated.")
                msg_box.setInformativeText("Errors occurred when trying to "
                                           "construct this workflow.")
                msg_box.setStandardButtons(QtGui.QMessageBox.Ok)
                msg_box.setDefaultButton(QtGui.QMessageBox.Ok)
                msg_box.setDetailedText(str(e))
                msg_box.exec_()
#                 print 'got to exception set'
#                 # Process all errors as usual
#                 if report_all_errors:
#                     for exc in exception_set:
#                         print 'processing', exc
#                         process_err(exc)
#                 else:
#                     process_err(exception_set.__iter__().next())

        except Exception, e:
            from gui.application import VistrailsApplication
            QtGui.QMessageBox.critical(
                VistrailsApplication.builderWindow,
                'Unexpected Exception', str(e))
            raise
        
        if not self._current_terse_graph or \
                new_version not in self._current_terse_graph.vertices:
            self.recompute_terse_graph()

        self.emit(QtCore.SIGNAL('versionWasChanged'), self.current_version)

    def set_search(self, search, text=''):
        """ set_search(search: SearchStmt, text: str) -> None
        Change the currrent version tree search statement
        
        """
        if self.search != search or self.search_str != text:
            self.search = search
            self.search_str = text
            if self.search:
                self.search.run(self.vistrail, '')
                self.invalidate_version_tree(True)
            if self.refine:
                # need to recompute the graph because the refined items might
                # have changed since last time
                self.recompute_terse_graph()
                self.invalidate_version_tree(True)
            else:
                self.invalidate_version_tree(False)
            
            self.emit(QtCore.SIGNAL('searchChanged'))

    def set_refine(self, refine):
        """ set_refine(refine: bool) -> None
        Set the refine state to True or False
        
        """
        if self.refine!=refine:
            self.refine = refine
            # need to recompute the graph because the refined items might
            # have changed since last time
            self.recompute_terse_graph()
            self.invalidate_version_tree(True)

    def set_full_tree(self, full):
        """ set_full_tree(full: bool) -> None        
        Set if Vistrails should show a complete version tree or just a
        terse tree
        
        """
        if full != self.full_tree:
            self.full_tree = full
            self.invalidate_version_tree(True)

    def recompute_terse_graph(self):
        # get full version tree (including pruned nodes)
        # this tree is kept updated all the time. This
        # data is read only and should not be updated!
        fullVersionTree = self.vistrail.tree.getVersionTree()

        # create tersed tree
        x = [(0,None)]
        tersedVersionTree = Graph()

        # cache actionMap and tagMap because they're properties, sort of slow
        am = self.vistrail.actionMap
        tm = self.vistrail.get_tagMap()
        last_n = self.vistrail.getLastActions(self.num_versions_always_shown)

        while 1:
            try:
                (current,parent)=x.pop()
            except IndexError:
                break

            # mount childs list
            if current in am and self.vistrail.is_pruned(current):
                children = []
            else:
                children = \
                    [to for (to, _) in fullVersionTree.adjacency_list[current]
                     if (to in am) and (not self.vistrail.is_pruned(to) or \
                                            to == self.current_version)]

            if (self.full_tree or 
                (current == 0) or  # is root
                (current in tm) or # hasTag:
                (len(children) <> 1) or # not oneChild:
                (current == self.current_version) or # isCurrentVersion
                (am[current].expand) or  # forced expansion
                (current in last_n)): # show latest
                # yes it will!
                # this needs to be here because if we are refining
                # version view receives the graph without the non
                # matching elements
                if( (not self.refine) or
                    (self.refine and not self.search) or
                    (current == 0) or
                    (self.refine and self.search and 
                     self.search.match(self.vistrail,am[current]) or
                     current == self.current_version)):
                    # add vertex...
                    tersedVersionTree.add_vertex(current)
                
                    # ...and the parent
                    if parent is not None:
                        tersedVersionTree.add_edge(parent,current,0)

                    # update the parent info that will 
                    # be used by the childs of this node
                    parentToChildren = current
                else:
                    parentToChildren = parent
            else:
                parentToChildren = parent

            for child in reversed(children):
                x.append((child, parentToChildren))

        self._current_terse_graph = tersedVersionTree
        self._current_full_graph = self.vistrail.tree.getVersionTree()
        self._previous_graph_layout = copy.deepcopy(self._current_graph_layout)
        self._current_graph_layout.layout_from(self.vistrail, 
                                               self._current_terse_graph)

    def refine_graph(self, step=1.0):
        """ refine_graph(step: float in [0,1]) -> (Graph, Graph)        
        Refine the graph of the current vistrail based the search
        status of the controller. It also return the full graph as a
        reference
        
        """
        if not self.animate_layout:
            return (self._current_terse_graph, self._current_full_graph,
                    self._current_graph_layout)

        graph_layout = copy.deepcopy(self._current_graph_layout)
        terse_graph = copy.deepcopy(self._current_terse_graph)
        am = self.vistrail.actionMap
        step = 1.0/(1.0+math.exp(-(step*12-6))) # use a logistic sigmoid function
        
        # Adding nodes to tree
        for (c_id, c_node) in self._current_graph_layout.nodes.iteritems():
            if self._previous_graph_layout.nodes.has_key(c_id):
                p_node = self._previous_graph_layout.nodes[c_id]
            else: 
                p_id = c_id
                # Find closest child of contained in both graphs
                while not self._previous_graph_layout.nodes.has_key(p_id):
                    # Should always have exactly one child
                    p_id = [to for (to, _) in \
                                self._current_full_graph.adjacency_list[p_id]
                            if (to in am) and \
                                not self.vistrail.is_pruned(to)][0]
                p_node = self._previous_graph_layout.nodes[p_id]

            # Interpolate position
            x = p_node.p.x - c_node.p.x
            y = p_node.p.y - c_node.p.y
            graph_layout.move_node(c_id, x*(1.0-step), y*(1.0-step))
            
        # Removing nodes from tree
        for (p_id, p_node) in self._previous_graph_layout.nodes.iteritems():
            if not self._current_graph_layout.nodes.has_key(p_id):
                # Find closest parent contained in both graphs
                shared_parent = p_id
                while (shared_parent > 0 and 
                       shared_parent not in self._current_graph_layout.nodes):
                    shared_parent = \
                        self._current_full_graph.parent(shared_parent)

                # Find closest child contained in both graphs
                c_id = p_id
                while not self._current_graph_layout.nodes.has_key(c_id):
                    # Should always have exactly one child
                    c_id = [to for (to, _) in \
                                self._current_full_graph.adjacency_list[c_id]
                            if (to in am) and \
                                not self.vistrail.is_pruned(to)][0]
                    
                # Don't show edge that skips the disappearing nodes
                if terse_graph.has_edge(shared_parent, c_id):
                    terse_graph.delete_edge(shared_parent, c_id)

                # Add the disappearing node to the graph and layout
                c_node = copy.deepcopy(self._current_graph_layout.nodes[c_id])
                c_node.id = p_id
                graph_layout.add_node(p_id, c_node)
                terse_graph.add_vertex(p_id)
                p_parent = self._current_full_graph.parent(p_id)
                if not terse_graph.has_edge(p_id, p_parent):
                    terse_graph.add_edge(p_parent, p_id)
                p_child = p_id
                while p_child not in self._current_graph_layout.nodes:
                    # Should always have exactly one child
                    p_child = [to for (to, _) in \
                                   self._current_full_graph.adjacency_list[p_child]
                               if (to in am) and \
                                   not self.vistrail.is_pruned(to)][0]
                if not terse_graph.has_edge(p_id, p_child):
                    terse_graph.add_edge(p_id, p_child)

                # Interpolate position
                x = p_node.p.x - c_node.p.x
                y = p_node.p.y - c_node.p.y
                graph_layout.move_node(p_id, x*(1.0-step), y*(1.0-step))

        return (terse_graph, self._current_full_graph,
                graph_layout)

    ##########################################################################
    # undo/redo navigation

    def _change_version_short_hop(self, new_version):
        """_change_version_short_hop is used internally to
        change versions when we're moving exactly one action up or down.
        This allows a few optimizations that improve interactivity."""
        
        if self.current_version <> new_version:
            # Instead of recomputing the terse graph, simply update it

            # There are two variables in play:
            # a) whether or not the destination node is currently on the
            # terse tree (it will certainly be after the move)
            # b) whether or not the current node will be visible (it
            # certainly is now, since it's the current one)

            dest_node_in_terse_tree = new_version in self._current_terse_graph.vertices
            
            current = self.current_version
            tree = self.vistrail.tree.getVersionTree()
            # same logic as recompute_terse_graph except for current
            children_count = len([x for (x, _) in tree.adjacency_list[current]
                                  if (x in self.vistrail.actionMap and
                                      not self.vistrail.is_pruned(x))])
            current_node_will_be_visible = \
                (self.full_tree or
                 self.vistrail.has_tag(self.current_version) or
                 children_count <> 1)

            self.change_selected_version(new_version)
            # case 1:
            if not dest_node_in_terse_tree and \
                    not current_node_will_be_visible and not current == 0:
                # we're going from one boring node to another,
                # so just rename the node on the terse graph
                self._current_terse_graph.rename_vertex(current, new_version)
                self.replace_unnamed_node_in_version_tree(current, new_version)
            else:
                # bail, for now
                self.recompute_terse_graph()
                self.invalidate_version_tree(False)
        

    def show_parent_version(self):
        """ show_parent_version() -> None
        Go back one from the current version and display it

        """
        # NOTE cscheid: Slight change in the logic under refined views:
        # before r1185, undo would back up more than one action in the
        # presence of non-matching refined nodes. That seems wrong. Undo
        # should always move one step only.         

        prev = None
        try:
            prev = self._current_full_graph.parent(self.current_version)
        except Graph.VertexHasNoParentError:
            prev = 0

        self._change_version_short_hop(prev)

    def show_child_version(self, which_child):
        """ show_child_version(which_child: int) -> None
        Go forward one version and display it. This is used in redo.

        ONLY CALL THIS FUNCTION IF which_child IS A CHILD OF self.current_version

        """
        self._change_version_short_hop(which_child)
        

    def prune_versions(self, versions):
        """ prune_versions(versions: list of version numbers) -> None
        Prune all versions in 'versions' out of the view
        
        """
        # We need to go up-stream to the highest invisible node
        current = self._current_terse_graph
        if not current:
            (current, full, layout) = self.refine_graph()
        else:
            full = self._current_full_graph
        changed = False
        new_current_version = None
        for v in versions:
            if v!=0: # not root
                highest = v
                while True:
                    p = full.parent(highest)
                    if p==-1:
                        break
                    if p in current.vertices:
                        break
                    highest = p
                if highest!=0:
                    changed = True
                    if highest == self.current_version:
                        new_current_version = full.parent(highest)
                self.vistrail.pruneVersion(highest)
        if changed:
            self.set_changed(True)
        if new_current_version is not None:
            self.change_selected_version(new_current_version)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False)

    def hide_versions_below(self, v):
        """ hide_versions_below(v: int) -> None
        Hide all versions including and below v
        
        """
        full = self.vistrail.getVersionGraph()
        x = [v]

        am = self.vistrail.actionMap

        changed = False

        while 1:
            try:
                current=x.pop()
            except IndexError:
                break

            children = [to for (to, _) in full.adjacency_list[current]
                        if (to in am) and \
                            not self.vistrail.is_pruned(to)]
            self.vistrail.hideVersion(current)
            changed = True

            for child in children:
                x.append(child)

        if changed:
            self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False, False) 

    def show_all_versions(self):
        """ show_all_versions() -> None
        Unprune (graft?) all pruned versions

        """
        full = self.vistrail.getVersionGraph()
        am = self.vistrail.actionMap
        for a in am.iterkeys():
            self.vistrail.showVersion(a)
        self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False, False)

    def expand_versions(self, v1, v2):
        """ expand_versions(v1: int, v2: int) -> None
        Expand all versions between v1 and v2
        
        """
        full = self.vistrail.getVersionGraph()
        changed = False
        p = full.parent(v2)
        while p>v1:
            self.vistrail.expandVersion(p)
            changed = True
            p = full.parent(p)
        if changed:
            self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False, True)

    def collapse_versions(self, v):
        """ collapse_versions(v: int) -> None
        Collapse all versions including and under version v until the next tag or branch
        
        """
        full = self.vistrail.getVersionGraph()
        x = [v]

        am = self.vistrail.actionMap
        tm = self.vistrail.get_tagMap()

        changed = False

        while 1:
            try:
                current=x.pop()
            except IndexError:
                break

            children = [to for (to, _) in full.adjacency_list[current]
                        if (to in am) and not self.vistrail.is_pruned(to)]
            if len(children) > 1:
                break;
            self.vistrail.collapseVersion(current)
            changed = True

            for child in children:
                if (not child in tm and  # has no Tag
                    child != self.current_version): # not selected
                    x.append(child)

        if changed:
            self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False, True) 

    def expand_or_collapse_all_versions_below(self, v, expand=True):
        """ expand_or_collapse_all_versions_below(v: int) -> None
        Expand/Collapse all versions including and under version v
        
        """
        full = self.vistrail.getVersionGraph()
        x = [v]
        
        am = self.vistrail.actionMap

        changed = False

        while 1:
            try:
                current=x.pop()
            except IndexError:
                break

            children = [to for (to, _) in full.adjacency_list[current]
                        if (to in am) and not self.vistrail.is_pruned(to)]
            if expand:
                self.vistrail.expandVersion(current)
            else:
                self.vistrail.collapseVersion(current)
            changed = True

            for child in children:
                x.append(child)

        if changed:
            self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False, True) 

    def collapse_all_versions(self):
        """ collapse_all_versions() -> None
        Collapse all expanded versions

        """
        am = self.vistrail.actionMap
        for a in am.iterkeys():
            self.vistrail.collapseVersion(a)
        self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False, True)

    def set_num_versions_always_shown(self, num):
        """ set_num_versions_always_shown(num: int) -> None

        """
        if num <> self.num_versions_always_shown:
            self.num_versions_always_shown = num
            self.set_changed(True)
            self.recompute_terse_graph()
            self.invalidate_version_tree(False)

    def setSavedQueries(self, queries):
        """ setSavedQueries(queries: list of (str, str, str)) -> None
        Set the saved queries of a vistail
        
        """
        self.vistrail.setSavedQueries(queries)
        self.set_changed(True)
        
    def update_current_tag(self,tag):
        """ update_current_tag(tag: str) -> Bool
        Update the current vistrail tag and return success predicate
        
        """
        self.flush_move_actions()
        try:
            if self.vistrail.hasTag(self.current_version):
                self.vistrail.changeTag(tag, self.current_version)
            else:
                self.vistrail.addTag(tag, self.current_version)
        except TagExists:
            show_warning('Name Exists',
                         "There is already another version named '%s'.\n"
                         "Please enter a different one." % tag)
            return False
        self.set_changed(True)
        self.recompute_terse_graph()
        self.invalidate_version_tree(False)
        return True

    def perform_param_changes(self, actions):
        """perform_param_changes(actions) -> None

        Performs a series of parameter change actions to the current version.

        FIXME: this function seems to be called from a single place in
        the spreadsheet cell code. Do we need it?
        """
        if len(actions) == 0:
            return
        for action in actions:
            for operation in action.operations:
                if operation.vtType == 'add' or operation.vtType == 'change':
                    if operation.new_obj_id < 0:
                        data = operation.data
                        new_id = self.vistrail.idScope.getNewId(data.vtType)
                        data.real_id = new_id
                        operation.new_obj_id = new_id
            self.add_new_action(action)
            self.perform_action(action, quiet=True)
        self.set_changed(True)
        self.invalidate_version_tree(False)

    ################################################################################
    # Clipboard, copy/paste

    def get_selected_item_ids(self):
        return self.current_pipeline_view.get_selected_item_ids()

    def copy_modules_and_connections(self, module_ids, connection_ids):
        """copy_modules_and_connections(module_ids: [long],
                                     connection_ids: [long]) -> str
        Serializes a list of modules and connections
        """
        self.flush_move_actions()

        def process_group(group):
            # reset pipeline id for db
            group.pipeline.id = None
            # recurse
            for module in group.pipeline.module_list:
                if module.is_group():
                    process_group(module)

        pipeline = Pipeline()
        sum_x = 0.0
        sum_y = 0.0
        for module_id in module_ids:
            module = self.current_pipeline.modules[module_id]
            sum_x += module.location.x
            sum_y += module.location.y
            if module.is_group():
                process_group(module)

        center_x = sum_x / len(module_ids)
        center_y = sum_y / len(module_ids)
        for module_id in module_ids:
            module = self.current_pipeline.modules[module_id]
            module = module.do_copy()
            module.location.x -= center_x
            module.location.y -= center_y
            pipeline.add_module(module)
        for connection_id in connection_ids:
            connection = self.current_pipeline.connections[connection_id]
            pipeline.add_connection(connection)
        return core.db.io.serialize(pipeline)
        
    def paste_modules_and_connections(self, str, center):
        """ paste_modules_and_connections(str,
                                          center: (float, float)) -> [id list]
        Paste a list of modules and connections into the current pipeline.

        Returns the list of module ids of added modules

        """
        self.flush_move_actions()

        pipeline = core.db.io.unserialize(str, Pipeline)
        modules = []
        connections = []
        if pipeline:
            def process_group(group):
                # reset pipeline id for db
                group.pipeline.id = None
                # recurse
                for module in group.pipeline.module_list:
                    if module.is_group():
                        process_group(module)

            for module in pipeline.module_list:
                module.location.x += center[0]
                module.location.y += center[1]
                if module.is_group():
                    process_group(module)

            id_remap = {}
            action = core.db.action.create_paste_action(pipeline, 
                                                        self.vistrail.idScope,
                                                        id_remap)

            modules = [op.objectId
                       for op in action.operations
                       if (op.what == 'module' or 
                           op.what == 'abstraction' or
                           op.what == 'group')]
            connections = [op.objectId
                           for op in action.operations
                           if op.what == 'connection']
                
            self.add_new_action(action)
            self.vistrail.change_description("Paste", action.id)
            self.perform_action(action)
            self.current_pipeline.validate(False)
        return modules

    def get_abstraction_name(self, name="", check_exists=True):
        name = self.do_abstraction_prompt(name)
        if name is None:
            return None
        while name == "" or (check_exists and self.abstraction_exists(name)):
            name = self.do_abstraction_prompt(name, name != "")
            if name is None:
                return None
        return name

    def do_abstraction_prompt(self, name="", exists=False):
        if exists:
            prompt = "'%s' already exists.  Enter a new subworkflow name" % \
                name
        else:
            prompt = 'Enter subworkflow name'
            
        (text, ok) = QtGui.QInputDialog.getText(None, 
                                                'Set SubWorkflow Name',
                                                prompt,
                                                QtGui.QLineEdit.Normal,
                                                name)
        if ok and not text.isEmpty():
            return str(text).strip().rstrip()
        if not ok:
            return None
        return ""

    def import_abstractions(self, abstraction_ids):
        for abstraction_id in abstraction_ids:
            abstraction = self.current_pipeline.modules[abstraction_id]
            new_name = self.get_abstraction_name(abstraction.name)
            if new_name:
                self.import_abstraction(new_name,
                                        abstraction.name, 
                                        abstraction.namespace,
                                        abstraction.internal_version)
        
    def do_export_prompt(self, title, prompt):
        (text, ok) = QtGui.QInputDialog.getText(None,
                                                title,
                                                prompt,
                                                QtGui.QLineEdit.Normal,
                                                '')
        if ok and not text.isEmpty():
            return str(text).strip().rstrip()
        return ''
            
    def do_save_dir_prompt(self):
        dialog = QtGui.QFileDialog.getExistingDirectory
        dir_name = dialog(None, "Save Subworkflows...",
                          core.system.vistrails_file_directory())
        if dir_name.isEmpty():
            return None
        dir_name = os.path.abspath(str(dir_name))
        setattr(get_vistrails_configuration(), 'fileDirectory', dir_name)
        core.system.set_vistrails_file_directory(dir_name)
        return dir_name
    
    def export_abstractions(self, abstraction_ids):
        save_dir = self.do_save_dir_prompt()
        if not save_dir:
            return 

        def read_init(dir_name):
            import imp
            found_attrs = {}
            found_lists = {}
            attrs = ['identifier', 'name', 'version']
            lists = ['_subworkflows', '_dependencies']
            try:
                (file, pathname, description) = \
                    imp.find_module(os.path.basename(dir_name), 
                                    [os.path.dirname(dir_name)])
                module = imp.load_module(os.path.basename(dir_name), file,
                                         pathname, description)
                for attr in attrs:
                    if hasattr(module, attr):
                        found_attrs[attr] = getattr(module, attr)
                for attr in lists:
                    if hasattr(module, attr):
                        found_lists[attr] = getattr(module, attr)
            except Exception, e:
                debug.critical("Exception: %s" % e)
                pass
            return (found_attrs, found_lists)

        def write_init(save_dir, found_attrs, found_lists, attrs, lists):
            init_file = os.path.join(save_dir, '__init__.py')
            if os.path.exists(init_file):
                f = open(init_file, 'a')
            else:
                f = open(init_file, 'w')
            for attr, val in attrs.iteritems():
                if attr not in found_attrs:
                    print >>f, "%s = '%s'" % (attr, val)
            for attr, val_list in lists.iteritems():
                if attr not in found_lists:
                    print >>f, "%s = %s" % (attr, str(val_list))
                else:
                    diff_list = []
                    for val in val_list:
                        if val not in found_lists[attr]:
                            diff_list.append(val)
                    print >>f, '%s.extend(%s)' % (attr, str(diff_list))
            f.close()

        if os.path.exists(os.path.join(save_dir, '__init__.py')):
            (found_attrs, found_lists) = read_init(save_dir)
        else:
            found_attrs = {}
            found_lists = {}

        if 'name' in found_attrs:
            pkg_name = found_attrs['name']
        else:
            pkg_name = self.do_export_prompt("Target Package Name",
                                             "Enter target package name")
            if not pkg_name:
                return

        if 'identifier' in found_attrs:
            pkg_identifier = found_attrs['identifier']
        else:
            pkg_identifier = self.do_export_prompt("Target Package Identifier",
                                                   "Enter target package "
                                                   "identifier (e.g. "
                                                   "org.place.user.package)")
            if not pkg_identifier:
                return

        abstractions = []
        for abstraction_id in abstraction_ids:
            abstraction = self.current_pipeline.modules[abstraction_id]
            if abstraction.is_abstraction() and \
                    abstraction.package == abstraction_pkg:
                abstractions.append(abstraction)
                [abstractions.extend(v) for v in self.find_abstractions(abstraction.vistrail).itervalues()]
        pkg_subworkflows = []
        pkg_dependencies = set()
        for abstraction in abstractions:
            new_name = self.get_abstraction_name(abstraction.name, False)
            if not new_name:
                break
            (subworkflow, dependencies) = \
                self.export_abstraction(new_name,
                                        pkg_identifier,
                                        save_dir,
                                        abstraction.name, 
                                        abstraction.namespace,
                                        str(abstraction.internal_version))
            pkg_subworkflows.append(subworkflow)
            pkg_dependencies.update(dependencies)

        attrs = {'identifier': pkg_identifier,
                 'name': pkg_name,
                 'version': '0.0.1'}
        lists = {'_subworkflows': pkg_subworkflows,
                 '_dependencies': list(pkg_dependencies)}
        write_init(save_dir, found_attrs, found_lists, attrs, lists)

    def set_changed(self, changed):
        """ set_changed(changed: bool) -> None
        Set the current state of changed and emit signal accordingly
        
        """
        BaseController.set_changed(self, changed)
        # FIXME: emit different signal in the future
        self.emit(QtCore.SIGNAL('stateChanged'))

    def set_file_name(self, file_name):
        """ set_file_name(file_name: str) -> None
        Change the controller file name
        
        """
        if file_name == None:
            file_name = ''
        if self.file_name!=file_name:
            self.file_name = file_name
            self.name = os.path.split(file_name)[1]
            if self.name=='':
                self.name = 'untitled%s'%vistrails_default_file_type()
            self.emit(QtCore.SIGNAL('stateChanged'))

    def write_vistrail(self, locator, version=None):
        need_invalidate = BaseController.write_vistrail(self, locator, version)
        if need_invalidate:
            self.invalidate_version_tree(False)
            #self.set_changed(False)

    def write_opm(self, locator):
        if self.log:
            if self.vistrail.db_log_filename is not None:
                log = core.db.io.merge_logs(self.log, 
                                            self.vistrail.db_log_filename)
            else:
                log = self.log
            opm_graph = OpmGraph(log=log, 
                                 version=self.current_version,
                                 workflow=self.current_pipeline,
                                 registry=get_module_registry())
            locator.save_as(opm_graph)

    def query_by_example(self, pipeline):
        """ query_by_example(pipeline: Pipeline) -> None
        Perform visual query on the current vistrail
        
        """
        if len(pipeline.modules)==0:
            search = TrueSearch()
        else:
            if not self._current_terse_graph:
                self.recompute_terse_graph()
            versions_to_check = \
                set(self._current_terse_graph.vertices.iterkeys())
            search = VisualQuery(pipeline, versions_to_check)

        self.set_search(search, '') # pipeline.dump_to_string())

    ##########################################################################
    # analogies

    def add_analogy(self, analogy_name, version_from, version_to):
        assert type(analogy_name) == str
        assert type(version_from) == int or type(version_from) == long
        assert type(version_to) == int or type(version_to) == long
        if analogy_name in self.analogy:
            raise VistrailsInternalError("duplicated analogy name '%s'" %
                                         analogy_name)
        self.analogy[analogy_name] = (version_from, version_to)

    def remove_analogy(self, analogy_name):
        if analogy_name not in self.analogy:
            raise VistrailsInternalError("missing analogy '%s'" %
                                         analogy_name)
        del self.analogy[analogy_name]

    def perform_analogy(self, analogy_name, analogy_target):
        if analogy_name not in self.analogy:
            raise VistrailsInternalError("missing analogy '%s'" %
                                         analogy_name)

        # remove delayed actions since we're not necessarily using
        # current_version
        self._delayed_actions = []

        (a, b) = self.analogy[analogy_name]
        c = analogy_target

        try:
            pipeline_a = self.vistrail.getPipeline(a)
            pipeline_a.validate()
        except InvalidPipeline, e:
            (_, pipeline_a) = \
                self.handle_invalid_pipeline(e, a, Vistrail())
        try:
            pipeline_c = self.vistrail.getPipeline(c)
            pipeline_c.validate()
        except InvalidPipeline, e:
            (_, pipeline_c) = self.handle_invalid_pipeline(e, a, Vistrail())
                                                     
        action = core.analogy.perform_analogy_on_vistrail(self.vistrail,
                                                          a, b, c, 
                                                          pipeline_a,
                                                          pipeline_c)
        self.add_new_action(action)
        self.vistrail.change_description("Analogy", action.id)
        self.vistrail.change_analogy_info("(%s -> %s)(%s)" % (a, b, c), 
                                          action.id)
        self.perform_action(action)
        self.current_pipeline.validate(False)
        self.current_pipeline_view.setupScene(self.current_pipeline)
    
################################################################################
# Testing

import unittest
import gui.utils
import api
import os

class TestVistrailController(gui.utils.TestVisTrailsGUI):

    # def test_add_module(self):
    #     v = api.new_vistrail()
       
    def tearDown(self):
        from core.configuration import get_vistrails_configuration
        gui.utils.TestVisTrailsGUI.tearDown(self)

        config = get_vistrails_configuration()
        filename = os.path.join(config.abstractionsDirectory,
                                '__TestFloatList.xml')
        if os.path.exists(filename):
            os.remove(filename)

    def test_create_functions(self):
        controller = VistrailController(Vistrail(), False)
        controller.change_selected_version(0L)
        module = controller.add_module(0.0,0.0, 'edu.utah.sci.vistrails.basic', 
                                       'ConcatenateString')
        functions = [('str1', ['foo'], -1, True),
                     ('str2', ['bar'], -1, True)]
        controller.update_functions(module, functions)

        self.assertEquals(len(controller.current_pipeline.module_list), 1)
        p_module = controller.current_pipeline.modules[module.id]
        self.assertEquals(len(p_module.functions), 2)
        self.assertEquals(p_module.functions[0].params[0].strValue, 'foo')
        self.assertEquals(p_module.functions[1].params[0].strValue, 'bar')

        # make sure updates work correctly
        # also check that we can add more than one function w/ same name
        # by passing False as should_replace
        new_functions = [('str1', ['baz'], -1, True),
                         ('str2', ['foo'], -1, False),
                         ('str3', ['bar'], -1, False)]
        controller.update_functions(p_module, new_functions)
        self.assertEquals(len(p_module.functions), 4)

    def test_abstraction_create(self):
        from core.db.locator import XMLFileLocator
        import core.db.io
        from core.configuration import get_vistrails_configuration
        config = get_vistrails_configuration()
        filename = os.path.join(config.abstractionsDirectory,
                                '__TestFloatList.xml')
        v = XMLFileLocator(core.system.vistrails_root_directory() +
                           '/tests/resources/test_abstraction.xml').load()

        controller = VistrailController(v, False)
        pipeline = v.getPipeline(9L)
        controller.current_pipeline = pipeline
        controller.current_version = 9L
        
        module_ids = [1, 2, 3]
        connection_ids = [1, 2, 3]
        
        controller.create_abstraction(module_ids, connection_ids, 
                                      '__TestFloatList')
        self.assert_(os.path.exists(filename))
