from PyQt4 import Qt, QtCore
from PyQt4.QtNetwork import QTcpSocket, QTcpServer, QHostAddress
from core.vistrail.module_param import ModuleParam
from core.vistrail.module_function import ModuleFunction
from core.modules.module_registry import registry
from core.db.action import create_action

from core.db.io import serialize, unserialize
from core.vistrail.pipeline import Pipeline
from vtDV3D.vtUtilities import *
import copy

from core import system
import core
ElementTree = core.system.get_elementtree_library()

def get_cell_address_from_coords( row, col ):
    return "%s%d" % ( chr( ord('A') + col ), row+1 )

################################################################################
# Copied from medleys/web/server/application_server.py
# 03/09/2010

class XMLObject(object):
    @staticmethod
    def convert_from_str(value, type):
        def bool_conv(x):
            s = str(x).upper()
            if s == 'TRUE':
                return True
            if s == 'FALSE':
                return False

        if value is not None:
            if type == 'str':
                return str(value)
            elif value.strip() != '':
                if type == 'long':
                    return long(value)
                elif type == 'float':
                    return float(value)
                elif type == 'int':
                    return int(value)
                elif type == 'bool':
                    return bool_conv(value)
                elif type == 'date':
                    return date(*strptime(value, '%Y-%m-%d')[0:3])
                elif type == 'datetime':
                    return datetime(*strptime(value, '%Y-%m-%d %H:%M:%S')[0:6])
        return None

    @staticmethod
    def convert_to_str(value,type):
        if value is not None:
            if type == 'date':
                return value.isoformat()
            elif type == 'datetime':
                return value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return str(value)
        return ''

################################################################################

class AliasSimpleGUI(XMLObject):
    def __init__(self, id, name, component=None):
        self._id = id
        self._name = name
        self._component = component

    def to_xml(self, node=None):
        """to_xml(node: ElementTree.Element) -> ElementTree.Element
            writes itself to xml
        """
        if node is None:
            node = ElementTree.Element('alias')

        #set attributes
        node.set('id', self.convert_to_str(self._id,'long'))
        node.set('name', self.convert_to_str(self._name,'str'))
        child_ = ElementTree.SubElement(node, 'component')
        self._component.to_xml(child_)

        return node

    @staticmethod
    def from_xml(node):
        if node.tag != 'alias':
            return None

        #read attributes
        data = node.get('id', None)
        id = AliasSimpleGUI.convert_from_str(data, 'long')
        data = node.get('name', None)
        name = AliasSimpleGUI.convert_from_str(data, 'str')
        for child in node.getchildren():
            if child.tag == "component":
                component = ComponentSimpleGUI.from_xml(child)
        alias = AliasSimpleGUI(id,name,component)
        return alias

################################################################################

class ComponentSimpleGUI(XMLObject):
    def __init__(self, id, pos, ctype, spec, val=None, minVal=None, maxVal=None,
                 stepSize=None, strvalueList="", parent=None, seq=False, 
                 widget="text"):
        """ComponentSimpleGUI() 
        widget can be: text, slider, combobox, numericstepper, checkbox

        """
        self._id = id
        self._pos = pos
        self._spec = spec
        self._ctype = ctype
        self._val = val
        self._minVal = minVal
        self._maxVal = maxVal
        self._stepSize = stepSize
        self._strvaluelist = strvalueList
        self._parent = parent
        self._seq = seq
        self._widget = widget

    def _get_valuelist(self):
        data = self._strvaluelist.split(',')
        result = []
        for d in data:
            result.append(urllib.unquote_plus(d))
        return result
    def _set_valuelist(self, valuelist):
        q = []
        for v in valuelist:
            q.append(urllib.quote_plus(v))
        self._strvaluelist = ",".join(q)

    _valueList = property(_get_valuelist,_set_valuelist)

    def to_xml(self, node=None):
        """to_xml(node: ElementTree.Element) -> ElementTree.Element
             writes itself to xml
        """
        if node is None:
            node = ElementTree.Element('component')

        #set attributes
        node.set('id', self.convert_to_str(self._id,'long'))
        node.set('pos', self.convert_to_str(self._pos,'long'))
        node.set('spec', self.convert_to_str(self._spec,'str'))
        node.set('ctype', self.convert_to_str(self._ctype,'str'))
        node.set('val', self.convert_to_str(self._val, 'str'))
        node.set('minVal', self.convert_to_str(self._minVal,'str'))
        node.set('maxVal', self.convert_to_str(self._maxVal,'str'))
        node.set('stepSize', self.convert_to_str(self._stepSize,'str'))
        node.set('valueList',self.convert_to_str(self._strvaluelist,'str'))
        node.set('parent', self.convert_to_str(self._parent,'str'))
        node.set('seq', self.convert_to_str(self._seq,'bool'))
        node.set('widget',self.convert_to_str(self._widget,'str'))
        return node

    @staticmethod
    def from_xml(node):
        if node.tag != 'component':
            return None

        #read attributes
        data = node.get('id', None)
        id = ComponentSimpleGUI.convert_from_str(data, 'long')
        data = node.get('pos', None)
        pos = ComponentSimpleGUI.convert_from_str(data, 'long')
        data = node.get('ctype', None)
        ctype = ComponentSimpleGUI.convert_from_str(data, 'str')
        data = node.get('spec', None)
        spec = ComponentSimpleGUI.convert_from_str(data, 'str')
        data = node.get('val', None)
        val = ComponentSimpleGUI.convert_from_str(data, 'str')
        val = val.replace("&lt;", "<")
        val = val.replace("&gt;", ">")
        val = val.replace("&amp;","&")
        data = node.get('minVal', None)
        minVal = ComponentSimpleGUI.convert_from_str(data, 'str')
        data = node.get('maxVal', None)
        maxVal = ComponentSimpleGUI.convert_from_str(data, 'str')
        data = node.get('stepSize', None)
        stepSize = ComponentSimpleGUI.convert_from_str(data, 'str')
        data = node.get('valueList', None)
        values = ComponentSimpleGUI.convert_from_str(data, 'str')
        values = val.replace("&lt;", "<")
        values = val.replace("&gt;", ">")
        values = val.replace("&amp;","&")
        data = node.get('parent', None)
        parent = ComponentSimpleGUI.convert_from_str(data, 'str')
        data = node.get('seq', None)
        seq = ComponentSimpleGUI.convert_from_str(data, 'bool')
        data = node.get('widget', None)
        widget = ComponentSimpleGUI.convert_from_str(data, 'str')
        component = ComponentSimpleGUI(id=id,
                                       pos=pos,
                                       ctype=ctype,
                                       spec=spec,
                                       val=val,
                                       minVal=minVal,
                                       maxVal=maxVal,
                                       stepSize=stepSize,
                                       strvalueList=values,
                                       parent=parent,
                                       seq=seq,
                                       widget=widget)
        return component

################################################################################

class MedleySimpleGUI(XMLObject):
    def __init__(self, id, name, vtid=None, version=None, alias_list=None, 
                 t='vistrail', has_seq=None):
        self._id = id
        self._name = name
        self._version = version
        self._alias_list = alias_list
        self._vtid = vtid
        self._type = t

        if has_seq == None:
            self._has_seq = False
            if type(self._alias_list) == type({}):
                for v in self._alias_list.itervalues():
                    if v._component._seq == True:
                        self._has_seq = True
        else:
            self._has_seq = has_seq

    @staticmethod
    def type_to_widget(wtype=None):
        """__type_to_widget(wtype: String) -> String
           According to its type, return the widget to be used
        """
        #widgets
        #text, slider, combobox, numericstepper, checkbox
        #types
        #edu.utah.sci.vistrails.basic:Integer, edu.utah.sci.vistrails.basic:Float, edu.utah.sci.vistrails.basic:String
        #Integer, Float, String

        if wtype == None:
            return None
 
        if wtype == "Integer":
            return "text"
        elif wtype == "Float":
            return "text"
        elif wtype == "String":
            return "text"
        elif wtype == "Bool":
            return "checkbox"
        elif wtype == "edu.utah.sci.vistrails.basic:Integer":
            return "text"
        elif wtype == "edu.utah.sci.vistrails.basic:Float":
            return "text"
        elif wtype == "edu.utah.sci.vistrails.basic:String":
            return "text"
        else:
            return "text"
        

    def to_xml(self, node=None):
        """to_xml(node: ElementTree.Element) -> ElementTree.Element
           writes itself to xml
        """

        if node is None:
            node = ElementTree.Element('medley_simple_gui')

        #set attributes
        node.set('id', self.convert_to_str(self._id,'long'))
        node.set('version', self.convert_to_str(self._version,'long'))
        node.set('vtid', self.convert_to_str(self._vtid,'long'))
        node.set('name', self.convert_to_str(self._name,'str'))
        node.set('type', self.convert_to_str(self._type,'str'))
        node.set('has_seq', self.convert_to_str(self._has_seq,'bool'))
        for (k,v) in self._alias_list.iteritems():
            child_ = ElementTree.SubElement(node, 'alias')
            v.to_xml(child_)
        return node

    @staticmethod
    def from_xml(node):
        if node.tag == 'medley_simple_gui':
            #read attributes
            data = node.get('id', None)
            id = MedleySimpleGUI.convert_from_str(data, 'long')
            data = node.get('name', None)
            name = MedleySimpleGUI.convert_from_str(data, 'str')
            data = node.get('version', None)
            version = MedleySimpleGUI.convert_from_str(data, 'long')
            data = node.get('vtid', None)
            vtid = MedleySimpleGUI.convert_from_str(data, 'long')
            data = node.get('type', None)
            type = MedleySimpleGUI.convert_from_str(data, 'str')
            data = node.get('has_seq', None)
            seq = ComponentSimpleGUI.convert_from_str(data, 'bool')
            alias_list = {}
            for child in node.getchildren():
                if child.tag == "alias":
                    alias = AliasSimpleGUI.from_xml(child)
                    alias_list[alias._name] = alias
            return MedleySimpleGUI(id=id, name=name, vtid=vtid, version=version, 
                                   alias_list=alias_list, t=type, has_seq=seq)
        elif node.tag == 'workflow':
            data = node.get('id', None)
            wid = MedleySimpleGUI.convert_from_str(data, 'long')
            data = node.get('name', None)
            name = MedleySimpleGUI.convert_from_str(data, 'str')
            data = node.get('version', None)
            version = MedleySimpleGUI.convert_from_str(data, 'long')
            data = node.get('vistrail_id', None)
            vtid = MedleySimpleGUI.convert_from_str(data, 'long')

            type = 'vistrail'
            seq = False

            alias_list = {}
            rpos = 1
            for child in node.getchildren():
                if child.tag == "module":
                    modulename = child.get('name', None)
                    for function in child.getchildren():
                        if function.tag == "function":
                            functioname = function.get('name', None)
                            fid = function.get('id', None)
                            for parameter in function.getchildren():
                                if parameter.tag == "parameter":
                                    ppos = parameter.get('pos', None)
                                    ptype = parameter.get('type', None)
                                    pname = parameter.get('name', None)
                                    pvalue = parameter.get('val', None)
                                    palias = parameter.get('alias', None)
                                    pid = parameter.get('id', None)
                                    widget = MedleySimpleGUI.type_to_widget(ptype)

                                    if pname == "<no description>":
                                        pname = functioname + "_" + ppos

                                    component = ComponentSimpleGUI(pid, rpos, "Parameter", "String", val=pvalue, widget=widget)
                                    rpos += 1

                                    #we cannot use only alias._name, since more than one alias can have the same name       
                                    alias = AliasSimpleGUI(pid, pname, component=component)
                                    aliasname = alias._name + "_" + pid
                                    alias_list[aliasname] = alias                                    
                                    
            if alias_list != {}:
                medley = MedleySimpleGUI(wid, name=name, vtid=vtid, version=version, 
                                       alias_list=alias_list, t=type, has_seq=seq)
                return medley
            else:
                return None

################################################################################

def cellCoordsInList( row, col, cells ):
    if cells == None: return True
    for cell in cells:
        if ( cell[0] == row ) and ( cell[1] == col ):
            return True
    return False

class Device:
    def __init__(self,name="unnamed_device",dimensions=(1,1)):
        self.name = name
        self.dimensions = dimensions
        self.addresses = {}
        self.clientDimensions = {}
        self.cellModuleNames = [ "DV3DCell", "SlicePlotCell" ]

        self.semaphoredCells = {}
        self.semaphoredGrid = {}
        self.idCounter = 0

        self.pipelineForKey = {}
        self.dimensionsForKey = {}
        self.namesForKey = {}
        self.moduleIdsForKey = {}
        self.usersForKey = {}
        self.localIdForPosition = {}

    def addClient(self, dimensions, socket):
        for x in range(dimensions[0], dimensions[0]+dimensions[2]):
            for y in range(dimensions[1], dimensions[1]+dimensions[3]):
                print self.name,"added client for location", (x, y)
                self.addresses[(x,y)] = socket
                self.clientDimensions[(x,y)] = dimensions
                self.semaphoredGrid[(x,y)] = False

    def preparePipelineForLocation( self, pipeline, module_id, dimensions ):
        """
        preparePipelineForLocation(pipeline: Pipeline, module_id: Int, position: (Int, Int)) -> [((Int, Int), Pipeline)]
        Returns a list with tuples that contain the location of a pipeline, along with the pipeline itself
        """
        print " preparePipelineForLocation: module=%s, dims=%s " % ( str(module_id), str(dimensions) )
        result = []
        for row in range(dimensions[3]):
            for column in range(dimensions[2]):
                localPipeline = copy.copy(pipeline)
                currentModule = localPipeline.get_module_by_id(module_id)

                for module in localPipeline.module_list:
                    if ( module.name in self.cellModuleNames ):
                        if ( module.id <> module_id ):
                            delete_module( module, localPipeline )
                      
                serializedPipeline = serialize(localPipeline)
#                print " Serialized pipeline: %s " % str( serializedPipeline )
                result.append( ((dimensions[0]+column, dimensions[1]+row), serializedPipeline) )
        
        return result
    
#    def setCellLocation( self, module, pipeline, dimensions ):
#        spec = registry.get_port_spec('gov.nasa.nccs.vtdv3d','spreadsheet.DV3DCell', None, 'cell_location','input')
#        cellLocFunction = spec.create_module_function()
#        cellLocFunction.real_id = pipeline.get_tmp_id( ModuleFunction.vtType )
#        cellLocFunction.db_parameters[0].db_id = pipeline.get_tmp_id( ModuleParam.vtType )
#        cellLocFunction.db_parameters_id_index[cellLocFunction.db_parameters[0].db_id] = cellLocFunction.db_parameters[0]
#        action_list.append(('add', cellLocFunction, module.vtType, module.id))
#
#        cellLoc = get_cell_address_from_coords( dimensions[0], dimensions[1] )   
#        print " Set Client Cell Location: %s, %s " % ( str(cellLoc), str(dimensions) )
#        module_functions = module._get_functions()
#        cellLocFunction = [x for x in module_functions if x.name == "cell_location"][0]                          
#        (p_val, p_type, p_namespace, p_identifier, p_alias) = (str(cellLoc), cellLocFunction.params[0].type, cellLocFunction.params[0].namespace, cellLocFunction.params[0].identifier, None)
#        old_param = cellLocFunction.params[0]
#        param_id = pipeline.get_tmp_id(ModuleParam.vtType)
#        new_param = ModuleParam(id=param_id, pos=0, name='<no description>', alias=p_alias, val=p_val, type=p_type, identifier=p_identifier, namespace=p_namespace, )
#        action_list = [ ('change', old_param, new_param, cellLocFunction.vtType, cellLocFunction.real_id) ]          
#        action = create_action(action_list)
#        pipeline.perform_action(action)
               
    def dispatchPipeline(self, pipeline, vistrailName, versionName, moduleId, dimensions):        
        pipelineList = self.preparePipelineForLocation( pipeline,  moduleId, dimensions )
        serializedPipelinesDict = {}
        for (socketAddress, pipeline) in pipelineList:
            message = "server-displayClient-"
            pipelineString = "pipeline,"
            pipelineString+=str(pipeline)
            message += str(len(pipelineString))+":"+pipelineString

            if self.addresses.has_key(socketAddress):
                if serializedPipelinesDict.has_key(self.addresses[socketAddress]):
                    serializedPipelinesDict[self.addresses[socketAddress]] += message
                else:
                    serializedPipelinesDict[self.addresses[socketAddress]] = message
            else: 
                print self.name, "found no receiver for ", socketAddress
                print self.addresses.keys(), self.addresses.values()

        for socketKey in serializedPipelinesDict:
            socketKey.write(serializedPipelinesDict[socketKey])

        self.pipelineForKey[self.idCounter] = copy.copy(pipeline)
        self.dimensionsForKey[self.idCounter] = dimensions
        self.namesForKey[self.idCounter] = (vistrailName, versionName)
        self.moduleIdsForKey[self.idCounter] = moduleId

        for row in range(dimensions[3]):
            for column in range(dimensions[2]):
                self.localIdForPosition[(dimensions[0]+column, dimensions[1]+row)] = self.idCounter
                self.semaphoredGrid[(dimensions[0]+column, dimensions[1]+row)] = True
        self.semaphoredCells[self.idCounter] = True
        self.idCounter += 1
        return self.idCounter-1

    def queryProperties(self, localId):
        #Get the xml of the pipeline
        root = ElementTree.fromstring(self.pipelineForKey[int(localId)])
        #Transform the XML in Medley GUI
        medley = MedleySimpleGUI.from_xml(root)
        return ElementTree.tostring(medley.to_xml())

    def updatePipeline(self, localId, medleyXml):
        root = ElementTree.fromstring(self.pipelineForKey[int(localId)])
        changed, root2 = self.update_xml(localId, ElementTree.fromstring(medleyXml))
      
        if not changed: return localId

        ppipe = ElementTree.tostring(root2)
        pdimm = self.dimensionsForKey[int(localId)]
        pmid = self.moduleIdsForKey[int(localId)]
        pnames = self.namesForKey[int(localId)]
		
        pinstance = unserialize(ppipe, Pipeline)

        self.deleteCell(localId)
        newId = self.dispatchPipeline(pinstance, pnames[0], pnames[1], pmid, pdimm)   

        return str(newId)

    def deleteCell(self, tokens):
        if not self.pipelineForKey.has_key(int(tokens[0])): return "cellDeleted"
        localId = int(tokens[0])
        dimensions = self.dimensionsForKey[localId]

        pipelineList = self.pipelineModifier.getClearPipelines(dimensions, self.clientDimensions)

        serializedPipelinesDict = {}
        for (socketAddress, pipeline) in pipelineList:
            message = "server-displayClient-"
            pipelineString = "pipeline,"
            pipelineString+=str(pipeline)
            message += str(len(pipelineString))+":"+pipelineString

            if self.addresses.has_key(socketAddress):
                if serializedPipelinesDict.has_key(self.addresses[socketAddress]):
                    serializedPipelinesDict[self.addresses[socketAddress]] += message
                else:
                    serializedPipelinesDict[self.addresses[socketAddress]] = message
            else: 
                print self.name, "found no receiver for ", socketAddress

        for socketKey in serializedPipelinesDict:
            socketKey.write(serializedPipelinesDict[socketKey])

        dicts = [self.pipelineForKey, self.dimensionsForKey, self.namesForKey, self.moduleIdsForKey]
        for d in dicts:
            if d.has_key(localId): del d[localId]

        return "cellDeleted"

    def lockCell(self, tokens):
        self.usersForKey[int(tokens[0])] = (float(tokens[1]), float(tokens[2]), float(tokens[3]))
        return "cellLocked,"+self.name+","+tokens[0]+","+tokens[1]+","+tokens[2]+","+tokens[3]

    def unlockCell(self, tokens):
        try:
            self.usersForKey                            #Check if this variable exists    
            if (tokens[0] in self.usersForKey):
                del self.usersForKey[int(tokens[0])]
        except NameError:
            print "Theres no cell locked or the cell you want to unlock isnt locked"
        return "cellUnlocked,"+self.name+","+tokens[0]
    
    def processInteractionMessage( self, tokens, selected_cells, msgType="interaction" ):
        eventType = tokens[0]
        event_data=','.join(  [ str(tokens[i]) for i in range( len(tokens) ) ]  )
#        print "         --- processInteractionMessage --- "
        for dimensions in self.dimensionsForKey.values():
            x = dimensions[0]
            y = dimensions[1]
            isSelectedCell = cellCoordsInList( y, x, selected_cells )
#            print " Device server -> sendMouseInteractionMessage[%s]: %s " % ( str(isSelectedCell), str( (x,y) ) )
            if isSelectedCell:
                columnValue = x + 1
                rowValue = y + 1
                message = "server-displayClient-"
                tokensString = msgType
                tokensString += "," + str(rowValue)+","+str(columnValue)+","+event_data
                message += str(len(tokensString))+":"+tokensString
                if self.addresses.has_key((x,y)): self.addresses[(x,y)].write(message)


    def sendMesageToClient( self, msg ):
        message = "server-displayClient-"
        message += str(len(msg)) + ":" + msg
        for address in self.addresses.values():
            address.write(message)
                
#        for dimensions in self.dimensionsForKey.values():
#            x = dimensions[0]
#            y = dimensions[1]
#            if self.addresses.has_key((x,y)): 
#                self.addresses[(x,y)].write(message)

    def shutdown(self):
        msg = "exit" 
        message = "server-displayClient-"
        message += str(len(msg)) + ":" + msg
        for address in self.addresses.values():
            address.write(message)
            address.flush()
            address.close()
        self.addresses.clear()

    def processSyncMessage(self, tokens):
        return ("", "", "")

    def queryOccupation(self):                
        reply = "occupationReport,"
        reply += self.name+","
        for key in self.pipelineForKey:
            reply += self.namesForKey[key][0]+","+self.namesForKey[key][1]+","
            reply += str(self.moduleIdsForKey[key])+","
            reply += str(key)+","
            reply += str(self.dimensionsForKey[key][0])+","+\
                str(self.dimensionsForKey[key][1])+","+\
                str(self.dimensionsForKey[key][2])+","+\
                str(self.dimensionsForKey[key][3])+","
            if self.usersForKey.has_key(key):
                reply += "locked,"+str(self.usersForKey[key][0])+","+str(self.usersForKey[key][1])+","+str(self.usersForKey[key][2])+","
            else:
                reply += "unlocked,"
        return reply[:-1]
    
    def update_xml(self, localId, medley):
        """ Update the current pipeline with the changes received
            medley = Medley XML
        """
        #getting medley information
        data = medley.get('id', None)
        mid = MedleySimpleGUI.convert_from_str(data, 'long')
        data = medley.get('name', None)
        mname = MedleySimpleGUI.convert_from_str(data, 'str')
        data = medley.get('version', None)
        mversion = MedleySimpleGUI.convert_from_str(data, 'long')
        data = medley.get('vtid', None)
        mvtid = MedleySimpleGUI.convert_from_str(data, 'long')
        data = medley.get('type', None)
        mtype = MedleySimpleGUI.convert_from_str(data, 'str')

        #comparing with the pipeline information
        workflow = ElementTree.fromstring(self.pipelineForKey[int(localId)])   

        data = workflow.get('id', None)
        wid = MedleySimpleGUI.convert_from_str(data, 'long')
        data = workflow.get('name', None)
        wname = MedleySimpleGUI.convert_from_str(data, 'str')
        data = workflow.get('version', None)
        wversion = MedleySimpleGUI.convert_from_str(data, 'long')
        data = workflow.get('vistrail_id', None)
        wvtid = MedleySimpleGUI.convert_from_str(data, 'long')

        if ((mid != wid) or (mname != mname)):
            print "Error: Different Workflow"
            return None

        #alias_list = {}
        #rpos = 1
        changed = False
        for child in workflow.getchildren():
            if child.tag == "module":
                modulename = child.get('name', None)
                for function in child.getchildren():
                    if function.tag == "function":
                        functioname = function.get('name', None)
                        fid = function.get('id', None)
                        for parameter in function.getchildren():
                            if parameter.tag == "parameter":
                                ppos = parameter.get('pos', None)
                                ptype = parameter.get('type', None)
                                pname = parameter.get('name', None)
                                pvalue = parameter.get('val', None)
                                palias = parameter.get('alias', None)
                                pid = parameter.get('id', None)
                                widget = MedleySimpleGUI.type_to_widget(ptype)

                                if pname == "<no description>":
                                    if palias != "":
                                        pname = palias
                                    else:
                                        pname = functioname + "_" + ppos                                
                                
                                #compare with the medley and update its value
                                #isnt the best way to do it... but first I will make it work
                                #for each parameter found in the workflow, I will search all the parameters in the medley

                                for c_alias in medley.getchildren():
                                    aid = c_alias.get('id', None)
                                    aname = c_alias.get('name', None)           

                                    if pname == aname:
                                        for c_param in c_alias.getchildren():
                                            if c_param.get('ctype', None) == "Parameter":
                                                if (parameter.get('id') == aid):
                                                    newvalue = c_param.get('val', None)
                                                    parameter.set('val', newvalue)
                                                    if newvalue != pvalue:
                                                        changed = True
                                        
                                    
        return changed, workflow

class StereoDevice(Device):
    def __init__(self,name="unnamed_device",dimensions=(1,1)):
        Device.__init__(self,name,dimensions)

    def dispatchPipeline(self, pipeline, vistrailName, versionName, moduleId, dimensions):
        pipelineList = self.pipelineModifier.preparePipelineForStereo(pipeline, moduleId, dimensions, self.dimensions)
        
        serializedPipelinesDict = {}
        for (socketAddress, pipeline) in pipelineList:
            message = "server-displayClient-"
            pipelineString = "pipeline,"
            pipelineString+=str(pipeline)
            message += str(len(pipelineString))+":"+pipelineString

            if self.addresses.has_key(socketAddress):
                if serializedPipelinesDict.has_key(self.addresses[socketAddress]):
                    serializedPipelinesDict[self.addresses[socketAddress]] += message
                else:
                    serializedPipelinesDict[self.addresses[socketAddress]] = message
            else: 
                print self.name, "found no receiver for ", socketAddress

        for socketKey in serializedPipelinesDict:
            print socketKey.peerAddress().toString()
            socketKey.write(serializedPipelinesDict[socketKey])

        self.pipelineForKey[self.idCounter] = copy.copy(pipeline)
        self.dimensionsForKey[self.idCounter] = dimensions
        self.namesForKey[self.idCounter] = (vistrailName, versionName)
        self.moduleIdsForKey[self.idCounter] = moduleId

        for row in range(dimensions[3]):
            for column in range(dimensions[2]):
                self.localIdForPosition[(dimensions[0]+column, dimensions[1]+row)] = self.idCounter
#                self.semaphoredGrid[(dimensions[0]+column, dimensions[1]+row)] = True
#        self.semaphoredCells[self.idCounter] = True
        self.idCounter += 1
        return self.idCounter-1

    def processInteractionMessage(self, tokens):
#        iPhoneDimensions = (320, 416)
#        displayWallDimensions = (6*2560, 4*1600)

        localID = int(tokens[1])
        eventType = tokens[2]
        button = tokens[3]
        pos = [int(tokens[4]), int(tokens[5])]

        dimensions = self.dimensionsForKey[localID]
        for x in [0, 1]:
            for y in [0]:
                columnValue = x % 2 + 1
                rowValue = y % 2 + 1
                message = "server-displayClient-"
                tokensString = "interaction,"
                tokensString += str(rowValue)+","+str(columnValue)+","+eventType+","+button+","+str(pos[0])+","+str(pos[1])
                message += str(len(tokensString))+":"+tokensString
                if self.addresses.has_key((x,y)):
                    print "sending event to", (x,y)
                    self.addresses[(x, y)].write(message)

### PROCESS_SYNC_MESSAGE

#         column = int(tokens[1])
#         row = int(tokens[2])
#         localId = self.localIdForPosition[(column, row)]
#         self.semaphoredGrid[(column,row)] = False

# ######################################################################
# ### Uncomment this loop to enable framelocking
# ######################################################################
#         for c in range(self.dimensionsForKey[localId][2]):
#             for r in range(self.dimensionsForKey[localId][3]):
#                 localColumn = (self.dimensionsForKey[localId][0] + c)
#                 localRow = (self.dimensionsForKey[localId][1] + r)
#                 ### this means that not everyone is ready for the refresh call
#                 if self.semaphoredGrid[(localColumn,localRow)]: return ("", "", "")
 
#         ### if everyone is not semaphored, we can tell them to 
#         ### swap their buffers

#         self.semaphoredCells[localId] = False
#         for c in range(self.dimensionsForKey[localId][2]):
#             for r in range(self.dimensionsForKey[localId][3]):
#                 localColumn = (self.dimensionsForKey[localId][0] + c)
#                 localRow = (self.dimensionsForKey[localId][1] + r)
#                 tokensString = "refresh,"+str(localColumn%2)+","+str(localRow%2)
#                 message = "server-displayClient-"+str(len(tokensString))+":"+tokensString
# #                self.udpSocket.writeDatagram(message, self.addresses[(localColumn, localRow)].peerAddress(), 50000)
#                 self.addresses[(localColumn, localRow)].write(message)
# #                self.semaphoredGrid[(c,r)] = True

#         return ("", "", "")
