'''
Created on May 28, 2013

@author: tpmaxwel
'''
import sys, os, cdms2
from packages.vtDV3D.RemoteDataBrowser import ServerClass

class RemoteDataset():
    
    def __init__(self, file_path, data_service_type, **args):
        self.file_path = file_path
        self.file_type = file_path.split('.')[-1]
        self.data_service_type = data_service_type
        self.cdms_metadata = cdms2.open(file_path)
        self.server_address = args.get( 'server_address', None )
        self.vars = {}
        
    @property
    def variables(self):
        return self.cdms_metadata.variables 

    @property
    def axes(self):
        return self.cdms_metadata.axes 
        
    def __getitem__( self, varName ):
        var = self.vars.get( varName, None )
        if var == None:
            var_metadata = self.cdms_metadata[varName]
            var = RemoteVariable( var_metadata, self.data_service_type, self.server_address )
            self.vars[ varName ] = var
        return var


class RemoteVariable():
    
    def __init__(self, metadata, data_service_type, server_address, **args):
        self.cdms_metadata = metadata
        self.data_service_type = data_service_type
        self.server_address = server_address
        
    def getAxisList(self):
        return self.cdms_metadata.getAxisList()

    def getGrid(self):
        return self.cdms_metadata.getGrid()

    def listall(self):
        return self.cdms_metadata.listall()
    
    def __call__( self, **args ):
        import irods, inspect
        irods_dir = dir( irods )
        print "Processing Remote Data on server and retreiving:\n ----> args = ", str(args)
        sys.stdout.flush()
        exec_inp = irods.execMyRuleInp_t()
        exec_inp.setAddr( self.server_address )
        exec_inp.setMyRule( 'uvcdatGetVariable' )
        exec_inp.setInpParamArray()
#        exec_inp.setOutParamDesc()
        exec_outp = irods.msParamArray_t()
        irods.rcExecMyRule( exec_inp, exec_outp )
        return self.cdms_metadata

       
# Dataset attributes:  'Conventions', 'Generating_Process_or_Model', 'Originating_center', 'Product_Type', '___cdms_internals__', '__call__', '__cdms_internals__', '__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__getitem__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 
# '__weakref__', '_convention_', '_filemap_', '_getSections', '_getinternals', '_gridmap_', '_isEmptyNode', '_listatts', '_makeOptParser', '_node_', '_processXmlValue', '_setatts', '_setinternals', '_status_', '_toDOMElement', '_toDOMElements', '_v', '_xmlpath_', 'attributes', 'autoApiInfo', 'axes', 'calendar', 'cdm_data_type', 'cdms_filemap', 'cleardefault', 'close', 'createAxis', 'createRectGrid', 'createVariable', 'creator_name', 'datapath', 'default_variable', 'default_variable_name', 'dictdict', 'dimensionarray', 'dimensionobject', 'directory', 'dump', 'file_format', 'fromXml', 'getAxis', 'getConvention', 'getDictionary', 'getGrid', 'getLogicalCollectionDN', 'getPaths', 'getVariable', 'getVariables', 'getattribute', 'getdimensionunits', 'getglobal', 'getslab', 'go', 'grids', 'history', 
# 'id', 'listall', 'listattribute', 'listdimension', 'listglobal', 'listvariable', 'listvariables', 'location', 'matchPattern', 'matchone', 'mode', 'openFile', 'parent', 'printXml', 'readScripGrid', 'scanDocString', 'searchPattern', 'searchPredicate', 'searchone', 'showall', 'showattribute', 'showdimension', 'showglobal', 'showvariable', 'stripSectionsFromDoc', 'sync', 'toDOM', 'toXml', 'uri', 'variables', 'xlinks']        
        
        

