import api
import os
from core.modules.vistrails_module import Module, ModuleError
from core.db.io import load_vistrail
from core.vistrail.controller import VistrailController
from core.db.locator import FileLocator

class VistrailServer:
    def __init__(self, resource_path):
        self.viewVistrail = {}
        self.viewController = {}
        if resource_path!=None:
            self.resource_path = resource_path
        else:
            self.resource_path = os.path.dirname(__file__) + '/resources/'

    def queryFiles(self):
        """return list of .vt files in resource_path dir"""
        print "queryFiles"
        files = []
        for f in os.listdir(self.resource_path):
            if f[-3:]==".vt":
                files.append(f)
        files.sort()
        return files

    def querySavedLayouts(self):
        """return list of saved layouts in resource_path dir"""
        print "querySavedLayouts"
        files = []
        for f in os.listdir(self.resource_path):
            if f[-3:]=="lay":
                files.append(f)
        files.sort()
        return files

    def queryTags(self, filename):
        """returns a list of (version.name, version.id) for named versions present in file"""
        print "queryTags"
        tags = []
        try:
            import os
            (vistrail, controller) =  self.loadVistrailFromFile(os.path.join(self.resource_path,filename))
            self.viewVistrail[filename] = vistrail
            self.viewController[filename] = controller
        except:
            raise ModuleError(self, "Error processing queryTags request")

        for tag in sorted(vistrail.get_tagMap().iteritems(), reverse=True):
#            tags.append((tag[1].name, tag[1].id))
            print tag
            #tags.append(tag[1].name)
            tags.append(tag[1])

        return tags

    def openVersion(self, filename, tag_name):
        """returns all VTKCell and ViSUSCell ids in a pipeline"""
        print "openVersion ", tag_name
        cells = []
        pipeline = self.getPipeline(filename, tag_name)
        #from core.db.io import serialize
        #print tag_name, serialize(pipeline)
        for module in pipeline.module_list:
            if module.name == "VTKCell" or module.name == "ViSUSCell" or module.name == "TuvokCell" or module.name == "StreamingImageCell":
                cells.append(module.id)
        return cells

    def getParameters(self, filename, tag_name):
        """return nested dict: {(module.name, module.id):{(fucntion.name,function.id):[(param.type,param.value(),param.id)]}}"""
        print "getParameters"
        modules = {}
        vt = self.viewVistrail[filename]
        #opens pipeline by id if tag_name is an int (assumes no versions are tagged with int values)
        try:
            tag_name = int(tag_name)
        except:
            pass

        pipeline = vt.getPipeline(tag_name)

        for module in pipeline.module_list:
            for function in module.functions:
                for param in function.params:
                    if param.alias[:6] == "iPhone":
                        if (module.name, module.id) not in modules.keys():
                            modules[(module.name, module.id)] = {}
                        if (function.name, function.real_id) not in modules[(module.name, module.id)].keys():
                            modules[(module.name, module.id)][(function.name, function.real_id)] = []
                        modules[(module.name, module.id)][(function.name, function.real_id)].append((param.type, param.value(), param.real_id))
        return modules

    def setParameter(self, filename, pipeline_id, module_id, function_id, param_id, param_value):
        """return (new controller id, new param id)"""
        print "setParameter"

        controller = self.viewController[filename]
        controller.change_selected_version(int(pipeline_id))

        return_id = api.change_parameter_by_id(long(module_id), long(function_id), long(param_id), str(param_value), controller)

        current_vistrail = self.viewVistrail[filename]
        current_vistrail.locator.save([(current_vistrail.vtType, current_vistrail)])
        return (controller.current_version, return_id)

    def setTag(self, filename, pipeline_id, tag_value):
        print "setParameter"

        current_vistrail = self.viewVistrail[filename]
        current_vistrail.addTag(tag_value, pipeline_id)
        current_vistrail.locator.save([(current_vistrail.vtType, current_vistrail)])

    def processMessage(self, message, socket):
        (sender, tokens) = message
        tokens = tokens.split(',')
        if len(tokens) == 0: return

        if tokens[0] == "queryFiles":
            replyTokens = "availableFiles,"
            for n in self.queryFiles():
                replyTokens += n + ","
            replyTokens = replyTokens[:-1]
            return ("vistrailServer", sender, replyTokens)

        if tokens[0] == "queryTags":
            replyTokens = "availableTags,"
            for n in self.queryTags(tokens[1]):
                replyTokens += n+","#n[0] + "," + str(n[1]) + ","
            replyTokens = replyTokens[:-1]
            return ("vistrailServer", sender, replyTokens)

        if tokens[0] == "openVersion":
            replyTokens = "VTKCells,"
            replyTokens += tokens[1]+","+tokens[2]+","
            cells = self.openVersion(tokens[1],tokens[2])
            for n in cells:
                replyTokens += str(n) + ","
            replyTokens = replyTokens[:-1]
            return ("vistrailServer", sender, replyTokens)

        if tokens[0] == "getParameters":
            replyTokens = "Parameters,"

            #               filename, version_name
            replyTokens += tokens[1]+","+tokens[2]+","
            parameters_dict = self.getParameters(tokens[1],tokens[2])

            for m in parameters_dict:
                param_stack = []
                m_count = len(parameters_dict[m].keys())*3
                for func in parameters_dict[m].keys():
                    f_count = len(parameters_dict[m][func])*3
                    for param in parameters_dict[m][func]:
                        param_stack.append(str(param)[1:-1])
                    param_stack.append(",".join([str(func[0]), str(func[1]), str(f_count)]))
                    m_count += f_count

                param_stack.append(",".join([str(m[0]), str(m[1]), str(m_count)]))
                param_stack.reverse()
                replyTokens += ",".join(param_stack)+","
                
            replyTokens = replyTokens[:-1]
            return ("vistrailServer", sender, replyTokens)

        if tokens[0] == "setParameter":
            replyTokens = "Parameter,"

            #add filename
            replyTokens += tokens[1]+","

            #                           filename, pipeline_id, module_id, function_id, param_id, param_value 
            param_id = self.setParameter(tokens[1],tokens[2],tokens[3],tokens[4],tokens[5],tokens[6])

            #              add pipeline_id,        param_id
            replyTokens += str(param_id[0])+","+str(param_id[1])+","
                
            replyTokens = replyTokens[:-1]
            return ("vistrailServer", sender, replyTokens)

        if tokens[0] == "setTag":
            replyTokens = "setTag,"

            self.setTag(tokens[1], int(tokens[2]), tokens[3])
                
            replyTokens = replyTokens[:-1]
            return ("vistrailServer", sender, replyTokens)

        return ""
    
    def loadVistrailFromFile(self, filename):
        locator = FileLocator(filename)
        (v, abstractions , thumbnails)  = load_vistrail(locator)
        controller = VistrailController()
        controller.set_vistrail(v, locator, abstractions, thumbnails)
        return (v, controller)
    
    def getPipeline(self, fileName, versionName):
        
        vt = self.viewVistrail[fileName]
        try:
            versionName = int(versionName)
        except:
            #making sure tag_name is an int
            if type(versionName) == type("string"):
                versionName = vt.get_version_number(versionName)
        #using controller to get pipeline, this will take care of upgrades
        controller = self.viewController[fileName]
        controller.change_selected_version(versionName)
        controller.flush_delayed_actions()
        pipeline = controller.current_pipeline
        #print "getPipeline -> ", controller.current_version
        return pipeline
