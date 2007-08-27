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

import copy
from db.versions.v0_7_0.domain import DBVistrail, DBAction, DBTag, DBModule, \
    DBConnection, DBPortSpec, DBFunction, DBParameter, DBLocation, DBAdd, \
    DBChange, DBDelete, DBAnnotation, DBPort

def translateVistrail(_vistrail):
    vistrail = DBVistrail()

    for _action in _vistrail.db_actions.itervalues():
        ops = []
        for op in _action.db_operations:
            if op.vtType == 'add':
                data = convert_data(op.db_data)
                ops.append(DBAdd(id=op.db_id,
                                 what=op.db_what, 
                                 objectId=op.db_objectId, 
                                 parentObjId=op.db_parentObjId, 
                                 parentObjType=op.db_parentObjType, 
                                 data=data))
            elif op.vtType == 'change':
                data = convert_data(op.db_data)
                ops.append(DBChange(id=op.db_id,
                                    what=op.db_what, 
                                    oldObjId=op.db_oldObjId, 
                                    newObjId=op.db_newObjId,
                                    parentObjId=op.db_parentObjId, 
                                    parentObjType=op.db_parentObjType, 
                                    data=data))
            elif op.vtType == 'delete':
                ops.append(DBDelete(id=op.db_id,
                                    what=op.db_what, 
                                    objectId=op.db_objectId, 
                                    parentObjId=op.db_parentObjId, 
                                    parentObjType=op.db_parentObjType))
        action = DBAction(id=_action.db_id,
                          prevId=_action.db_prevId, 
                          date=_action.db_date, 
                          user=_action.db_user, 
                          operations=ops,
                          annotations=_action.db_annotations.values())
        vistrail.db_add_action(action)

    for _tag in _vistrail.db_tags.itervalues():
        tag = DBTag(id=_tag.db_id,
                    name=_tag.db_name)
        vistrail.db_add_tag(tag)

    vistrail.db_version = '0.7.0'
    return vistrail

def convert_data(child):
    # FIXME don't like using core in here...
    from core.modules.module_registry import registry, PortSpec
    if child.vtType == 'module':
        descriptor = registry.get_descriptor_from_name_only(child.db_name)
        package = descriptor.identifier
        return DBModule(id=child.db_id,
                        cache=child.db_cache, 
                        abstraction=0, 
                        name=child.db_name,
                        package=package)
    elif child.vtType == 'connection':
        return DBConnection(id=child.db_id)
    elif child.vtType == 'portSpec':
        return DBPortSpec(id=child.db_id,
                          name=child.db_name, 
                          type=child.db_type, 
                          spec=child.db_spec)
    elif child.vtType == 'function':
        return DBFunction(id=child.db_id,
                          pos=child.db_pos, 
                          name=child.db_name)
    elif child.vtType == 'parameter':
        return DBParameter(id=child.db_id,
                           pos=child.db_pos,
                           name=child.db_name, 
                           type=child.db_type, 
                           val=child.db_val, 
                           alias=child.db_alias)
    elif child.vtType == 'location':
        return DBLocation(id=child.db_id,
                          x=child.db_x,
                          y=child.db_y)
    elif child.vtType == 'annotation':
        return DBAnnotation(id=child.db_id,
                            key=child.db_key,
                            value=child.db_value)
    elif child.vtType == 'port':
        sig = child.db_sig
        if sig == 'SetColor(vtkPiecewiseFunction)':
            sig = 'SetColor_2(vtkPiecewiseFunction)'
        elif sig == 'SetScalarOpacity(vtkPiecewiseFunction)':
            sig = 'SetScalarOpacity_2(vtkPiecewiseFunction)'
        elif sig == 'SetGradientOpacity(vtkPiecewiseFunction)':
            sig = 'SetGradientOpacity_2(vtkPiecewiseFunction)'
        if '(' in sig:
            name = sig[:sig.find('(')]
            specs = sig[sig.find('(')+1:sig.find(')')]
            new_specs = []
            for spec_name in specs.split(','):
                descriptor = registry.get_descriptor_from_name_only(spec_name)
                spec_str = descriptor.identifier + ':' + spec_name
                new_specs.append(spec_str)
            spec = '(' + ','.join(new_specs) + ')'
        else:
            name = sig
            spec = ''
        return DBPort(id=child.db_id,
                      type=child.db_type, 
                      moduleId=child.db_moduleId, 
                      moduleName=child.db_moduleName, 
                      name=name,
                      spec=spec)
