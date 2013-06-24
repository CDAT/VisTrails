'''
Created on May 28, 2013

@author: tpmaxwel
'''
import sys, os, cdms2
from packages.vtDV3D.RemoteDataBrowser import ServerClass
NcGetVarOut_MS_T = "NcGetVarOut_PI"
ClientVaultPath = os.environ.get("IRODS_CLIENT_VAULT","UNKNOWN")

class RemoteDataset():
    
    def __init__(self, file_path, data_service_type, **args):
        self.file_path = file_path
        self.file_type = RemoteDataset.getFileType( file_path )
        self.data_service_type = data_service_type
        self.cdms_metadata = cdms2.open(file_path)
        self.catalog_path = args.get( 'catalog_path', None )
        self.vars = {}
     
    @staticmethod   
    def getFileType( file_path ):
         return os.path.splitext( file_path )[1].lstrip('.')
        
    @property
    def variables(self):
        return self.cdms_metadata.variables 

    @property
    def id(self):
        return self.catalog_path

    @property
    def axes(self):
        return self.cdms_metadata.axes 
        
    def __getitem__( self, varName ):
        var = self.vars.get( varName, None )
        if var == None:
            var_metadata = self.cdms_metadata[varName]
            if self.data_service_type == ServerClass.IRODS:
                var = iRODS_RemoteVariable( var_metadata, self.catalog_path )
            self.vars[ varName ] = var
        return var


class RemoteVariable():
    
    def __init__(self, var_metadata, dset_catalog_path, **args):
        self.cdms_metadata = var_metadata
        self.dataset_catalog_path = dset_catalog_path
        
    def getAxisList(self):
        return self.cdms_metadata.getAxisList()

    def getGrid(self):
        return self.cdms_metadata.getGrid()

    def listall(self):
        return self.cdms_metadata.listall()
    
    def __call__( self, **args ):
        raise Exception( " Can't access data for '%s' with unspecified remote service type." % self.cdms_metadata.id ) 

class iRODS_RemoteVariable( RemoteVariable ):
    
    def __init__(self, var_metadata, dset_catalog_path, **args):
        RemoteVariable.__init__( self, var_metadata, dset_catalog_path, **args)
    
    def __call__result( self, **args ):
        import irods
        from packages.vtDV3D.RemoteDataBrowser import iRodsCatalogNode
        print "Processing Remote Data on server and retreiving:\n ----> args = ", str(args)
        
        execMyRuleInp = irods.execMyRuleInp_t()
        msParamArray = irods.msParamArray_t()
        
        execMyRuleInp.getCondInput().setLen(0)
        execMyRuleInp.setInpParamArray(msParamArray)
        
        execMyRuleInp.setOutParamDesc("*result")        
        execMyRuleInp.setMyRule("cdmsGetVariable(*ds,*var,*roi,*result)")
        
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*ds",  irods.STR_MS_T, self.dataset_catalog_path )
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*var", irods.STR_MS_T, self.cdms_metadata.id )
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*roi", irods.STR_MS_T, str(args) )
#        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*result", NcGetVarOut_MS_T, None )
                
        outParamArray = irods.rcExecMyRule( iRodsCatalogNode.ServerConnection, execMyRuleInp )
        
        mP = outParamArray.getMsParamByLabel("*result")
        
        if mP:
            result = mP.getExecCmdOut().getStdoutBuf()
            print result
            sys.stdout.flush()

        return self.cdms_metadata( **args )
    
    def getFilePath( self, irods_path ):
#         import irCdmsClient as irUtil
#         phys_path = irUtil.getPhysPath( irods_path )
        irods_path_elems = irods_path.strip(" /").split('/')
        irods_path_elems[0] = ClientVaultPath
        return '/'.join( irods_path_elems )
    
    def __call__( self, **args ):
        import irods
        from packages.vtDV3D.RemoteDataBrowser import iRodsCatalogNode
        print "Processing Remote Data on server and retreiving:\n ----> args = ", str(args)
        
        execMyRuleInp = irods.execMyRuleInp_t()
        msParamArray = irods.msParamArray_t()
        
        execMyRuleInp.getCondInput().setLen(0)
        execMyRuleInp.setInpParamArray(msParamArray)
        
        execMyRuleInp.setOutParamDesc("*objPath")        
#        execMyRuleInp.setMyRule("cdmsTransferVariable(*dsetPath,*varName,*roi,*clientResc)")
        execMyRuleInp.setMyRule("cdmsTransferVariable||msiPythonInitialize##msiTransferCDMSVariable( *dsetPath, *varName, *roi, *svrResc, *physPath, *objPath )##msiPhyPathReg(*objPath,*svrResc,*physPath,null,*Status)##msiDataObjPhymv(*objPath,*clientResc,*svrResc,\"0\",null,*Status)##msiPythonFinalize|nop")        
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*dsetPath",  irods.STR_MS_T, self.dataset_catalog_path )
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*varName", irods.STR_MS_T, self.cdms_metadata.id )
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*roi", irods.STR_MS_T, str(args) )
        irods.addMsParamToArray( execMyRuleInp.getInpParamArray(), "*clientResc", irods.STR_MS_T, "clientResc" )
                
        outParamArray = irods.rcExecMyRule( iRodsCatalogNode.ServerConnection, execMyRuleInp )
        
        mP = outParamArray.getMsParamByLabel("*objPath")
        
        if mP:
            result_obj_path = mP.parseForStr()      # getExecCmdOut().getStdoutBuf( )
            dataObjInp = irods.dataObjInp_t()
            dataObjInp.setObjPath( result_obj_path )
            ( rodsObjStatOut, status ) = irods.rcObjStat( iRodsCatalogNode.ServerConnection, dataObjInp )
            stat_methods = dir( rodsObjStatOut )
            filePath = self.getFilePath(  result_obj_path )
            print " GetRemoteVariable result: %s (%s) " % ( result_obj_path, filePath )
            ds = cdms2.open( filePath )
            result_variable = ds( self.cdms_metadata.id )
            sys.stdout.flush()
            return result_variable

        return None

       
# irods Dataset attributes:  'Conventions', 'Generating_Process_or_Model', 'Originating_center', 'Product_Type', '___cdms_internals__', '__call__', '__cdms_internals__', '__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__getitem__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 
# '__weakref__', '_convention_', '_filemap_', '_getSections', '_getinternals', '_gridmap_', '_isEmptyNode', '_listatts', '_makeOptParser', '_node_', '_processXmlValue', '_setatts', '_setinternals', '_status_', '_toDOMElement', '_toDOMElements', '_v', '_xmlpath_', 'attributes', 'autoApiInfo', 'axes', 'calendar', 'cdm_data_type', 'cdms_filemap', 'cleardefault', 'close', 'createAxis', 'createRectGrid', 'createVariable', 'creator_name', 'datapath', 'default_variable', 'default_variable_name', 'dictdict', 'dimensionarray', 'dimensionobject', 'directory', 'dump', 'file_format', 'fromXml', 'getAxis', 'getConvention', 'getDictionary', 'getGrid', 'getLogicalCollectionDN', 'getPaths', 'getVariable', 'getVariables', 'getattribute', 'getdimensionunits', 'getglobal', 'getslab', 'go', 'grids', 'history', 
# 'id', 'listall', 'listattribute', 'listdimension', 'listglobal', 'listvariable', 'listvariables', 'location', 'matchPattern', 'matchone', 'mode', 'openFile', 'parent', 'printXml', 'readScripGrid', 'scanDocString', 'searchPattern', 'searchPredicate', 'searchone', 'showall', 'showattribute', 'showdimension', 'showglobal', 'showvariable', 'stripSectionsFromDoc', 'sync', 'toDOM', 'toXml', 'uri', 'variables', 'xlinks']        
        
        

