'''
Created on Nov 30, 2011

@author: emanuele
'''

class PlotPipelineHelper(object):
    '''
    This will take care of pipeline manipulation for plots.
    '''


    def __init__(self):
        '''
        Constructor
        '''
        
    @staticmethod
    def find_module_by_name(pipeline, module_name):
        for module in pipeline.module_list:
            if module.name == module_name:
                return module
    
    @staticmethod
    def find_modules_by_type(pipeline, moduletype):
        result = []
        for module in pipeline.module_list:
            desc = module.module_descriptor
            if issubclass(desc.module, moduletype):
                result.append(module)
        return result