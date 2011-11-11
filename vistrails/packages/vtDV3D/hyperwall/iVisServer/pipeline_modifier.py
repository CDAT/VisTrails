import copy

from core.db.io import serialize
from core.vistrail.pipeline import Pipeline
from core.vistrail.module import Module
from core.vistrail.module_param import ModuleParam
from core.vistrail.module_function import ModuleFunction
from core.vistrail.port import Port
from core.vistrail.connection import Connection
from core.modules.module_registry import registry
from core.packagemanager import get_package_manager
from core.db.action import create_action

import packages

screenX = 25.5
screenY = 15.75
mullionX = 1.875
mullionY = 1.875

class PipelineModifier:
    def __init__(self):
        pass

    def getModuleClassByName(self,package,moduleName,namespace=""):
        """getModuleClassByName(package: Str, moduleName: Str) -> Class
        Returns the actual python class of a module; this is done by accessing
        the registry to get the descriptor, and then getting the 'module'
        attribute of the descriptor, which returns the class of that module.
        Notice that it returns a *CLASS*, and not an instance of that class"""
        return registry.get_descriptor_by_name(package,moduleName,namespace).module

    def getModuleClassByModule(self,module):
        """getModuleClassByModule(module: Module) -> Class
        Does the same thing as the above, only it returns the class from a given module
        instead of its name and package"""
        return registry.get_descriptor_by_name(module.package, module.name, module.namespace).module

    def getUpstreamIds(self, module, pipeline):
        """getUpstreamIds(module: Module, pipeline: Pipeline) -> List[Int]
        getUpstreamIds returns the list of ids corresponding to the modules entering
        module"""
        pipelineGraph = pipeline.graph
        return [x[0] for x in pipelineGraph.edges_to(module.id)]

    def findUpstreamModuleByClass(self,module,klass,pipeline):
        """findUpstreamModuleByClass(module: Module, klass: Class, pipeline: Pipeline) -> Module or None
        This method searches the connections directly upstream of module
        for a module that is a subclass of class and returns that module"""
        upstreamIds = self.getUpstreamIds(module, pipeline)
        for upstreamId in upstreamIds:
            upstreamModule = pipeline.get_module_by_id(upstreamId)
            upstreamModuleClass = self.getModuleClassByModule(upstreamModule)
            if issubclass(upstreamModuleClass, klass):
                return upstreamModule
        return None

    def getPackageVersion(self, identifier):
        """getPackageVersion(identifier: str) -> str
        This will return the current version loaded of the package identified
        by identifier 
        """
        pm = get_package_manager()
        return pm.get_package_by_identifier(identifier).version
        
    def deleteModule(self,module,pipeline):
        """deleteModule(module: Module, pipeline: Pipeline) -> None
        deletes the module from the current pipeline in the proper way, taking
        care to also delete all connections. This is done to make sure that the
        modified pipelines we send to the clients are not broken"""
        graph = pipeline.graph
        connect_ids = [x[1] for x in graph.edges_to(module.id)]
        connect_ids += [x[1] for x in graph.edges_from(module.id)]
        action_list = []
        for c_id in connect_ids:
            action_list.append(('delete',pipeline.connections[c_id]))
        action_list.append(('delete',pipeline.modules[module.id]))
        
        action = create_action(action_list)
        pipeline.perform_action(action)

    def getCellLocationModule(self,cell,pipeline):
        """getCellLocationModule(cell: Module, pipeline: Pipeline) -> Module or None
        Returns the CellLocation module attached to the current cell or None if non existent"""
        cellLocationClass = self.getModuleClassByName('edu.utah.sci.vistrails.spreadsheet','CellLocation')
        return self.findUpstreamModuleByClass(cell, cellLocationClass, pipeline)

    def getVTKRendererModule(self, module, pipeline):
        """getVTKRendererModule(module: Module, pipeline: Pipeline) -> Module or None
        Returns the VTKRenderer attached to the module or Non if nonexistent"""
        VTKRendererClass = self.getModuleClassByName("edu.utah.sci.vistrails.vtk","vtkRenderer")
        return self.findUpstreamModuleByClass(module, VTKRendererClass, pipeline)

    def addCellLocation(self, vtkCell, pipeline, position, dimensions, deviceDimensions):
        """addCellLocation(vtkCell: Module, pipeline: Pipeline, position: (Int, Int)) -> None
        This method adds a CellLocation module to the vtkCell to ensure that it is
        sent to the right spreadsheet cell in the display wall. This is done
        according to the tuple in position"""

        print "Device Dimensions", deviceDimensions
        ### Adds the CellLocation Module
        # We need to make sure we create the Cell Location Module using 
        # the current spreadsheet version 
        version = self.getPackageVersion("edu.utah.sci.vistrails.spreadsheet")
        cellLocation = Module(id=pipeline.fresh_module_id(), name="CellLocation", 
                              package="edu.utah.sci.vistrails.spreadsheet",
                              version=version)
        
        action = create_action([('add',cellLocation)])
        pipeline.perform_action(action)
        cellLocation = pipeline.get_module_by_id(cellLocation.id)
        vtkCell = pipeline.get_module_by_id(vtkCell.id)
        
        src = registry.get_port_spec('edu.utah.sci.vistrails.spreadsheet','CellLocation', None, 'self','output')
        dst = registry.get_port_spec('edu.utah.sci.vistrails.vtk','VTKCell', None, 'Location','input')            
        
        ### Connects the CellLocation module to the vtkCell
        inputPort = Port(id=pipeline.get_tmp_id(Port.vtType), spec=dst, moduleId=vtkCell.id, moduleName=vtkCell.name)
        outputPort = Port(id=pipeline.get_tmp_id(Port.vtType), spec=src, moduleId=cellLocation.id, moduleName=cellLocation.name)
        connection = Connection(id=pipeline.fresh_connection_id(), ports=[inputPort,outputPort])
        action = create_action([('add',connection)])
        pipeline.perform_action(action)
        
        action_list = []

        ### Creates the Column function
        spec = registry.get_port_spec('edu.utah.sci.vistrails.spreadsheet','CellLocation',None, 'Column','input')
        columnFunction = spec.create_module_function()
        columnFunction.real_id = pipeline.get_tmp_id(ModuleFunction.vtType)
        columnFunction.db_parameters[0].db_id = pipeline.get_tmp_id(ModuleParam.vtType)
        columnFunction.db_parameters_id_index[columnFunction.db_parameters[0].db_id] = columnFunction.db_parameters[0]
        action_list.append(('add',columnFunction, cellLocation.vtType, cellLocation.id))
        
        ### Creates the Row function
        spec = registry.get_port_spec('edu.utah.sci.vistrails.spreadsheet','CellLocation',None, 'Row','input')
        rowFunction = spec.create_module_function()
        rowFunction.real_id = pipeline.get_tmp_id(ModuleFunction.vtType)
        rowFunction.db_parameters[0].db_id = pipeline.get_tmp_id(ModuleParam.vtType)
        rowFunction.db_parameters_id_index[rowFunction.db_parameters[0].db_id] = rowFunction.db_parameters[0]
        action_list.append(('add',rowFunction, cellLocation.vtType, cellLocation.id))
        
        action = create_action(action_list)
        pipeline.perform_action(action)
        cellLocation = pipeline.get_module_by_id(cellLocation.id)
        
        columnFunction = [x for x in cellLocation._get_functions() if x.name == "Column"][0]
        rowFunction = [x for x in cellLocation._get_functions() if x.name == "Row"][0]
        
        ### Sets the value of columnFunction and rowFunction
        paramList = []
 
#        columnValue = (dimensions[0] + position[0]) % 2 + 1
#        rowValue = (dimensions[1] + position[1]) % 2 + 1
        gPos = (dimensions[0] + position[0], dimensions[1] + position[1])
        columnValue = (gPos[0]-deviceDimensions[0]) % deviceDimensions[2] + 1
        rowValue = (gPos[1]-deviceDimensions[1]) % deviceDimensions[3] + 1

        print (columnValue, rowValue)
        ### changes the Column function
        paramList.append((str(columnValue), columnFunction.params[0].type, columnFunction.params[0].namespace, columnFunction.params[0].identifier, None))

        ### changes the Row function
        paramList.append((str(rowValue), rowFunction.params[0].type, rowFunction.params[0].namespace, rowFunction.params[0].identifier, None))
        
        action_list = []                    
        for i in xrange(len(paramList)):
            (p_val, p_type, p_namespace, p_identifier, p_alias) = paramList[i]
            function = columnFunction if i == 0 else rowFunction
            old_param = function.params[0]
            param_id = pipeline.get_tmp_id(ModuleParam.vtType)
            new_param = ModuleParam(id=param_id, pos=i, name='<no description>', alias=p_alias, val=p_val, type=p_type, identifier=p_identifier, namespace=p_namespace, )
            action_list.append(('change', old_param, new_param, 
                                function.vtType, function.real_id))
            
        action = create_action(action_list)
        pipeline.perform_action(action)

    def addVTKCameraToRenderer(self, vtkRenderer, pipeline):
        """addVTKCameraToRenderer(renderer: Module, pipeline: Pipeline) -> Module
        Adds a vtkCamera module to the received vtkRenderer. If a camera already exists, it
        returns this camera"""
        vtkCamera = self.findUpstreamModuleByClass(vtkRenderer, self.getModuleClassByName('edu.utah.sci.vistrails.vtk','vtkCamera'), pipeline)
        if not vtkCamera is None:
            ### If a camera is already connected to the renderer, just return it
            return vtkCamera
        # Making sure we create the vtkCamera module using the current version of
        # the vtk package
        version = self.getPackageVersion("edu.utah.sci.vistrails.vtk")
        vtkCamera = Module(id=pipeline.fresh_module_id(), name="vtkCamera", 
                           package="edu.utah.sci.vistrails.vtk", version=version)
        action = create_action([('add',vtkCamera)])
        pipeline.perform_action(action)
                
        src = registry.get_port_spec('edu.utah.sci.vistrails.vtk','vtkCamera', None, 'self','output')
        dst = registry.get_port_spec('edu.utah.sci.vistrails.vtk','vtkRenderer', None, 'SetActiveCamera','input')
        inputPort = Port(id=pipeline.get_tmp_id(Port.vtType), spec=dst, moduleId=vtkRenderer.id, moduleName=vtkRenderer.name)
        outputPort = Port(id=pipeline.get_tmp_id(Port.vtType), spec=src, moduleId=vtkCamera.id, moduleName=vtkCamera.name)
        connection = Connection(id=pipeline.fresh_connection_id(), ports=[inputPort,outputPort])
        action = create_action([('add',connection)])
        pipeline.perform_action(action)
        return vtkCamera

    def setCamera(self, vtkCell, camera, pipeline, position, dimensions, doZoom):
        """
        setCamera(vtkCell: Module, camera: Module, pipeline: Pipeline, position: (Int, Int), dimensions: (Int, Int), doZoom: Bool) -> Pipeline
        This method modifies the received camera in the received pipeline to have it match the requirements for the display wall
        """

        functionList = camera._get_functions()
        windowCenterFunction = None
        zoomFunction = None

        for function in functionList:
            if function.name == "SetWindowCenter":
                windowCenterFunction = function
            if function.name == "Zoom":
                zoomFunction = function            

        action_list = []
                    
        if windowCenterFunction is None:
            spec = registry.get_port_spec('edu.utah.sci.vistrails.vtk','vtkCamera', None, 'SetWindowCenter','input')
            windowCenterFunction = spec.create_module_function()    
            windowCenterFunction.real_id = pipeline.get_tmp_id(ModuleFunction.vtType)
            windowCenterFunction.db_parameters[0].db_id = pipeline.get_tmp_id(ModuleParam.vtType)
            windowCenterFunction.db_parameters[1].db_id = pipeline.get_tmp_id(ModuleParam.vtType)
            windowCenterFunction.db_parameters_id_index[windowCenterFunction.db_parameters[0].db_id] = windowCenterFunction.db_parameters[0]
            windowCenterFunction.db_parameters_id_index[windowCenterFunction.db_parameters[1].db_id] = windowCenterFunction.db_parameters[1]
            action_list.append(('add', windowCenterFunction, camera.vtType, camera.id))
            
        if zoomFunction is None:
            spec = registry.get_port_spec('edu.utah.sci.vistrails.vtk','vtkCamera', None, 'Zoom','input')
            zoomFunction = spec.create_module_function()
            zoomFunction.real_id = pipeline.get_tmp_id(ModuleFunction.vtType)
            zoomFunction.db_parameters[0].db_id = pipeline.get_tmp_id(ModuleParam.vtType)
            zoomFunction.db_parameters_id_index[zoomFunction.db_parameters[0].db_id] = zoomFunction.db_parameters[0]            
            action_list.append(('add', zoomFunction, camera.vtType, camera.id))
            
        action = create_action(action_list)
        pipeline.perform_action(action)

        camera = pipeline.get_module_by_id(camera.id)
        functionList = camera._get_functions()
        windowCenterFunction = [x for x in camera._get_functions() if x.name == "SetWindowCenter"][0]

        if doZoom:
            zoomFunction = [x for x in camera._get_functions() if x.name == "Zoom"][0]

        columnCenter = - dimensions[2] + (position[0]*2+1);
        rowCenter = dimensions[3] - (position[1]*2+1);


        zoom = min(dimensions[2], dimensions[3])
#        zoom = min(dimensions[2] - dimensions[0]+1, dimensions[3] - dimensions[1]+1)

        paramList = []

        ### changes the setWindowCenter function
        paramList.append((str(columnCenter), windowCenterFunction.params[0].type, windowCenterFunction.params[0].namespace, windowCenterFunction.params[0].identifier, None))
        paramList.append((str(rowCenter), windowCenterFunction.params[1].type, windowCenterFunction.params[1].namespace, windowCenterFunction.params[1].identifier, None))
        
        if doZoom:
        ### changes the zoom function
            paramList.append((str(zoom), zoomFunction.params[0].type, zoomFunction.params[0].namespace, zoomFunction.params[0].identifier, None))

        action_list = []                    
        for i in xrange(len(paramList)):
            (p_val, p_type, p_namespace, p_identifier, p_alias) = paramList[i]
            function = windowCenterFunction if i == 0 or i == 1 else zoomFunction
            old_param = function.params[i] if i == 0 or i == 1 else function.params[0]
            param_id = pipeline.get_tmp_id(ModuleParam.vtType)
            new_param = ModuleParam(id=param_id, pos=i, name='<no description>', alias=p_alias, val=p_val, type=p_type, identifier=p_identifier, namespace=p_namespace,)
            action_list.append(('change', old_param, new_param, function.vtType, function.real_id))
            
        action = create_action(action_list)
        pipeline.perform_action(action)
 
        serializedPipeline = serialize(pipeline)
        result = ((dimensions[0]+position[0], dimensions[1]+position[1]), serializedPipeline)
        return result

    def setViSUSRange(self, pipeline, module, dimensions, position):
        functionList = module._get_functions()

        rangeFunction = None

        for function in functionList:
            if function.name == "Range":
                rangeFunction = function

        fullRange = (rangeFunction.params[0].value(),
                     rangeFunction.params[1].value(),
                     rangeFunction.params[2].value(),
                     rangeFunction.params[3].value())
        print 'in range', fullRange

        rw = fullRange[1]-fullRange[0]
        rh = fullRange[3]-fullRange[2]
        aspectRatio = float(rw) / rh #
        aspectRatio = (dimensions[2]-dimensions[0])*2560.0/((dimensions[3]-dimensions[1])*1600)
        nw = int(rh*aspectRatio)
        
        fullRange = (fullRange[0]-(nw-rw)/2,
                     fullRange[1]+(nw-rw)/2,
                     fullRange[2], fullRange[3])
        print 'out range', fullRange
        
        incX = screenX / (screenX + mullionX)
        incY = screenY / (screenY + mullionY)

        localRange = (fullRange[0] + ((fullRange[1] - fullRange[0]) / (dimensions[2]-dimensions[0])) * position[0],
                      int(fullRange[0] + ((fullRange[1] - fullRange[0]) / (dimensions[2]-dimensions[0])) * (position[0] + incX)),
                      fullRange[2] + ((fullRange[3] - fullRange[2]) / (dimensions[3]-dimensions[1])) * position[1],
                      int(fullRange[2] + ((fullRange[3] - fullRange[2]) / (dimensions[3]-dimensions[1])) * (position[1] + incY)))
#         localRange = (fullRange[0] + ((fullRange[1] - fullRange[0]) / dimensions[2]) * position[0],
#                       int(fullRange[0] + ((fullRange[1] - fullRange[0]) / dimensions[2]) * (position[0] + incX)),
#                       fullRange[0] + ((fullRange[3] - fullRange[2]) / dimensions[3]) * position[1],
#                       int(fullRange[0] + ((fullRange[3] - fullRange[2]) / dimensions[3]) * (position[1] + incY)))

        print position, localRange

        action_list = []

        paramList = []
        paramList.append((str(localRange[0]), rangeFunction.params[0].type, rangeFunction.params[0].namespace, rangeFunction.params[0].identifier, None))
        paramList.append((str(localRange[1]), rangeFunction.params[1].type, rangeFunction.params[1].namespace, rangeFunction.params[1].identifier, None))
        paramList.append((str(localRange[2]), rangeFunction.params[2].type, rangeFunction.params[2].namespace, rangeFunction.params[2].identifier, None))
        paramList.append((str(localRange[3]), rangeFunction.params[3].type, rangeFunction.params[3].namespace, rangeFunction.params[3].identifier, None))

        for i in range(len(paramList)):
            (p_val, p_type, p_namespace, p_identifier, p_alias) = paramList[i]
            function = rangeFunction
            old_param = function.params[i]
            param_id = pipeline.get_tmp_id(ModuleParam.vtType)
            new_param = ModuleParam(id=param_id, pos=i, name='<no description>', alias=p_alias, val=p_val, type=p_type, identifier=p_identifier, namespace=p_namespace,)
            action_list.append(('change', old_param, new_param, function.vtType, function.real_id))

        action = create_action(action_list)
        pipeline.perform_action(action)

        serializedPipeline = serialize(pipeline)
        result = ((dimensions[0]+position[0], dimensions[1]+position[1]), serializedPipeline)
        return result

    def setMistViewport(self, pipeline, module, dimensions, position):
        functionList = module._get_functions()

        viewportFunction = None

        for function in functionList:
            if function.name == "Viewport":
                viewportFunction = function

        fullRange = (viewportFunction.params[0].value(),
                    viewportFunction.params[1].value(),
                    viewportFunction.params[2].value(),
                    viewportFunction.params[3].value())
        print 'in range', fullRange
        print 'dimension:', dimensions

        rw = fullRange[2]-fullRange[0]
        rh = fullRange[3]-fullRange[1]

        centerFunction = None
        for function in functionList:
            if function.name == "GlobalCenter":
                centerFunction = function
	centerX = rw*0.5 + fullRange[0]
	centerY = rh*0.5 + fullRange[1] 

        aspectRatio = float(rw) / rh
        nw = int(rh*aspectRatio)
        
        fullRange = (fullRange[0]-(nw-rw)/2,
                     fullRange[1],
                     fullRange[2]+(nw-rw)/2,
                     fullRange[3])
        print 'out range', fullRange
        print 'position:', position
        
        incX = screenX / (screenX + mullionX)
        incY = screenY / (screenY + mullionY)

        localRange = ( (rw)*position[0],
                       (rh)*position[1],
                       (rw)*(position[0]+1),
                       (rh)*(position[1]+1))

        print position, localRange

        action_list = []
        paramList = []
        paramList.append((viewportFunction, str(localRange[0]), viewportFunction.params[0].type, viewportFunction.params[0].namespace, viewportFunction.params[0].identifier, None, 0))
        paramList.append((viewportFunction, str(localRange[1]), viewportFunction.params[1].type, viewportFunction.params[1].namespace, viewportFunction.params[1].identifier, None, 1))
        paramList.append((viewportFunction, str(localRange[2]), viewportFunction.params[2].type, viewportFunction.params[2].namespace, viewportFunction.params[2].identifier, None, 2))
        paramList.append((viewportFunction, str(localRange[3]), viewportFunction.params[3].type, viewportFunction.params[3].namespace, viewportFunction.params[3].identifier, None, 3))

        paramList.append((centerFunction, str(centerX), centerFunction.params[0].type, centerFunction.params[0].namespace, 
centerFunction.params[0].identifier, None, 0))
        paramList.append((centerFunction, str(centerY), centerFunction.params[1].type, centerFunction.params[1].namespace, 
centerFunction.params[1].identifier, None, 1))
        print "Params: ", paramList


        for i in range(len(paramList)):
            (function, p_val, p_type, p_namespace, p_identifier, p_alias, pos) = paramList[i]
#            function = viewportFunction#rangeFunction
            print i, function, p_val, p_type, p_namespace, p_identifier, p_alias, pos
            old_param = function.params[pos]
            param_id = pipeline.get_tmp_id(ModuleParam.vtType)
            new_param = ModuleParam(id=param_id, pos=i, name='<no description>', alias=p_alias, val=p_val, type=p_type, identifier=p_identifier, namespace=p_namespace,)
            action_list.append(('change', old_param, new_param, function.vtType, function.real_id))

        action = create_action(action_list)
        pipeline.perform_action(action)

        serializedPipeline = serialize(pipeline)
        result = ((dimensions[0]+position[0], dimensions[1]+position[1]), serializedPipeline)
        return result

    def setTuvok(self, pipeline, module, dimensions, position):
        functionList = module._get_functions()
        
        frustumFunction = None
        for function in functionList:
            if function.name == "frustum":
                frustumFunction = function

        fullFrustum = (frustumFunction.params[0].value(),
                       frustumFunction.params[1].value(),
                       frustumFunction.params[2].value(),
                       frustumFunction.params[3].value(),
                       frustumFunction.params[4].value(),
                       frustumFunction.params[5].value())

        incX = screenX / (screenX + mullionX)
        incY = screenY / (screenY + mullionY)

        localFrustum = (fullFrustum[0] + ((fullFrustum[1] - fullFrustum[0]) / float(dimensions[2])) * position[0],
                        fullFrustum[0] + ((fullFrustum[1] - fullFrustum[0]) / float(dimensions[2])) * (position[0]+incX),
                        fullFrustum[2] + ((fullFrustum[3] - fullFrustum[2]) / float(dimensions[3])) * position[1],
                        fullFrustum[2] + ((fullFrustum[3] - fullFrustum[2]) / float(dimensions[3])) * (position[1]+incY),
                        fullFrustum[4],
                        fullFrustum[5])

        print position, localFrustum


        action_list = []

        paramList = []
        paramList.append((str(localFrustum[0]), frustumFunction.params[0].type, frustumFunction.params[0].namespace, frustumFunction.params[0].identifier, None))
        paramList.append((str(localFrustum[1]), frustumFunction.params[1].type, frustumFunction.params[1].namespace, frustumFunction.params[1].identifier, None))
        paramList.append((str(localFrustum[2]), frustumFunction.params[2].type, frustumFunction.params[2].namespace, frustumFunction.params[2].identifier, None))
        paramList.append((str(localFrustum[3]), frustumFunction.params[3].type, frustumFunction.params[3].namespace, frustumFunction.params[3].identifier, None))
        paramList.append((str(localFrustum[4]), frustumFunction.params[4].type, frustumFunction.params[4].namespace, frustumFunction.params[4].identifier, None))
        paramList.append((str(localFrustum[5]), frustumFunction.params[5].type, frustumFunction.params[5].namespace, frustumFunction.params[5].identifier, None))

        for i in range(len(paramList)):
            (p_val, p_type, p_namespace, p_identifier, p_alias) = paramList[i]
            function = frustumFunction
            old_param = function.params[i]
            param_id = pipeline.get_tmp_id(ModuleParam.vtType)
            new_param = ModuleParam(id=param_id, pos=i, name='<no description>', alias=p_alias, val=p_val, type=p_type, identifier=p_identifier, namespace=p_namespace,)
            action_list.append(('change', old_param, new_param, function.vtType, function.real_id))

        action = create_action(action_list)
        pipeline.perform_action(action)

        serializedPipeline = serialize(pipeline)
        result = ((dimensions[0]+position[0], dimensions[1]+position[1]), serializedPipeline)
        return result
        pass


    def preparePipelineForStereo(self, pipeline, module_id, dimensions, deviceDimensions):
        result = []

        serializedPipeline = serialize(pipeline)
        p1 = ((dimensions[0], dimensions[1]), serializedPipeline)
        serializedPipeline = serialize(pipeline)
        p2 = ((dimensions[0]+1, dimensions[1]), serializedPipeline)

        result.append(p1)
        result.append(p2)
        return result

    def preparePipelineForLocation(self, pipeline, module_id, dimensions, clientDimensions):
        """
        preparePipelineForLocation(pipeline: Pipeline, module_id: Int, position: (Int, Int)) -> [((Int, Int), Pipeline)]
        Returns a list with tuples that contain the location of a pipeline, along with the pipeline itself
        """

        result = []
        for row in range(dimensions[3]):
            for column in range(dimensions[2]):
                localPipeline = copy.copy(pipeline)
                currentModule = localPipeline.get_module_by_id(module_id)

                VTKCells = [module for module in localPipeline.module_list if module.name == "VTKCell" and module.id != module_id]
                for cell in VTKCells:
                    self.deleteModule(cell, localPipeline)

                cellLocation = self.getCellLocationModule(currentModule, localPipeline)
                if not cellLocation is None:
                    self.deleteModule(cellLocation, localPipeline)

                dim = clientDimensions[(column+dimensions[0], row+dimensions[1])]
                self.addCellLocation(currentModule, localPipeline, (column, row), dimensions, dim)

                print currentModule.name
                if currentModule.name == "StreamingImageCell":
                    ### Mist Streaming Image stuff
                    result.append(self.setMistViewport(localPipeline, currentModule, dimensions, (column, row)))
                elif currentModule.name == "ViSUSCell":
                    ### ViSUS stuff
                    result.append(self.setViSUSRange(localPipeline, currentModule, dimensions, (column, row)))
                elif currentModule.name == "TuvokCell":
                    ### Tuvok stuff
                    result.append(self.setTuvok(localPipeline, currentModule, dimensions, (column, row)))
                else:
                    ### VTK stuff
                    vtkRenderer = self.getVTKRendererModule(currentModule, localPipeline)
                    if vtkRenderer is None:
                        print "No vtkRenderer found"
                        return []
                    vtkCamera = self.addVTKCameraToRenderer(vtkRenderer, localPipeline)                
#                    result.append(self.setCamera(currentModule, vtkCamera, localPipeline, (column, row), dimensions, False))
                    result.append(self.setCamera(currentModule, vtkCamera, localPipeline, (column, row), dimensions, True))
        
        return result

    def getClearPipelines(self, dimensions, clientDimensions):
        result = []
        for row in range(dimensions[3]):
            for column in range(dimensions[2]):
                localPipeline = Pipeline()
                vtkversion = self.getPackageVersion("edu.utah.sci.vistrails.vtk")
                vtkCell = Module(id=localPipeline.fresh_module_id(), name="VTKCell", 
                                 package="edu.utah.sci.vistrails.vtk",
                                 version=vtkversion)
                action = create_action([('add',vtkCell)])
                localPipeline.perform_action(action) 

                vtkRenderer = Module(id=localPipeline.fresh_module_id(), 
                                     name="vtkRenderer", 
                                     package="edu.utah.sci.vistrails.vtk",
                                     version=vtkversion)
                action = create_action([('add',vtkRenderer)])
                localPipeline.perform_action(action)

                src = registry.get_port_spec('edu.utah.sci.vistrails.vtk','vtkRenderer', None, 'self','output')
                dst = registry.get_port_spec('edu.utah.sci.vistrails.vtk','VTKCell', None, 'AddRenderer','input')
                inputPort = Port(id=localPipeline.get_tmp_id(Port.vtType), spec=dst, moduleId=vtkCell.id, moduleName=vtkCell.name)
                outputPort = Port(id=localPipeline.get_tmp_id(Port.vtType), spec=src, moduleId=vtkRenderer.id, moduleName=vtkRenderer.name)
                connection = Connection(id=localPipeline.fresh_connection_id(), ports=[inputPort,outputPort])
                action = create_action([('add',connection)])
                localPipeline.perform_action(action)        

                cellLocation = self.getCellLocationModule(vtkCell, localPipeline)
                if not cellLocation is None:
                    self.deleteModule(cellLocation, localPipeline)
                dim = clientDimensions[(column+dimensions[0], row+dimensions[1])]
                self.addCellLocation(vtkCell, localPipeline, (column, row), dimensions, dim)

                result.append(((dimensions[0]+column,dimensions[1]+row), serialize(localPipeline)))
        return result
