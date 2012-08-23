from core.modules.vistrails_module import Module, ModuleError

class CDMSData(Module):
    _input_ports = [("variable", "(gov.llnl.uvcdat.cdms:CDMSVariable)")]
    _output_ports = [("data", "(edu.utah.sci.vistrails.basic:List)")]
    
    def compute(self):
        if not self.hasInputFromPort('variable'):
            raise ModuleError(self, "'variable' is mandatory.")
        self.var = self.getInputFromPort('variable')
        data = self.var.var.data.flatten().tolist()
        self.setResult("data", data)