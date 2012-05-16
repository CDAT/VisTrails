import core.modules.module_registry
import core.requirements
import core.modules.vistrails_module
import vtk
from core.modules.vistrails_module import Module, ModuleError

# Our own constant
import pvvariable

# Need paraview
import paraview.simple as pvsp

class PVClimateSource(Module):
    """PVClimateSource is a module that reads the file and creates reader,
    and variable name."""

    # This constructor is strictly unnecessary. However, some modules
    # might want to initialize per-object data. When implementing your
    # own constructor, remember that it must not take any extra
    # parameters.
    def __init__(self):
        Module.__init__(self)

    # This is the method you should implement in every module that
    # will be executed directly. VisTrails does not use the return
    # value of this method.
    def compute(self):
        # getInputFromPort is a method defined in Module that returns
        # the value stored at an input port. If there's no value
        # stored on the port, the method will return None.
        fileName = self.getInputFromPort("fileName")
        variableName = self.getInputFromPort("variableName")
        #variableType = self.getInputFromPort("variableType")
        reader = pvsp.NetCDFPOPreader(FileName=fileName)
        pvvarInstance = pvvariable.PVVariable()
        pvvarInstance.set_reader(reader)
        pvvarInstance.set_variable_name(variableName);
        pvvarInstance.set_variable_type("POINTS");
        self.setResult("variable", pvvarInstance)
        #self.setResult("outputVariable", inputVariable)
        #self.setResult("fileName", fileName)
        
    def package_dependencies():
        return ['edu.utah.sci.vistrails.vtk']
    

###############################################################################
# the function initialize is called for each package, after all
# packages have been loaded. It is used to register the module with
# the VisTrails runtime.

def initialize():

    # We'll first create a local alias for the module_registry so that
    # we can refer to it in a shorter way.
    reg = core.modules.module_registry.get_module_registry()

    # VisTrails cannot currently automatically detect your derived
    # classes, and the ports that they support as input and
    # output. Because of this, you as a module developer need to let
    # VisTrails know that you created a new module. This is done by calling
    # function addModule:
    reg.add_module(PVClimateSource)

    # In a similar way, you need to report the ports the module wants
    # to make available. This is done by calling addInputPort and
    # addOutputPort appropriately. These calls only show how to set upL
    # one-parameter ports. We'll see in later tutorials how to set up
    # multiple-parameter plots.
    reg.add_input_port(PVClimateSource, "fileName",
                     (core.modules.basic_modules.String, 'File name'))
    reg.add_input_port(PVClimateSource, "variableName",
                     (core.modules.basic_modules.String, 'Input variable name'))
    # @NOTE: Commented out for now
    #reg.add_input_port(PVClimateSource, "variableType",
    #                 (core.modules.basic_modules.String, 'Input variable type'))    
    reg.add_output_port(PVClimateSource, "variable", pvvariable.PVVariableConstant)
    
    # @NOTE (Aashish): Had this for testing
    #reg.add_output_port(PVClimateSource, "outputVariable",
    #                 (core.modules.basic_modules.String, 'Output variable'))
    #reg.add_output_port(PVClimateSource, "fileName",
    #                 (core.modules.basic_modules.String, 'File name'))
