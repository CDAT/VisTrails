from core.modules.vistrails_module import Module

class Matrix(Module):
    """
    This class represent a generic matrix, each row is an instance, and every 
    instance has values, id and label. Every column has an attribute
    """
    my_namespace = 'matrix'
    name         = 'Matrix'
    
    def __init__(self):
        Module.__init__(self)
        
        self.values     = None      # numpy.array
        self.ids        = None      # numpy.array
        self.labels     = None      # list<string>
        self.attributes = None      # list<string>
        