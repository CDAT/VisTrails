from core.modules.vistrails_module import Module

class Matrix(Module):
    """
    This class represent a generic matrix, each row is an instance, and every 
    instance has values, an id and a label. Every column has an attribute
    """
    my_namespace = 'matrix'
    name         = 'Matrix'
    
    def __init__(self):
        Module.__init__(self)
        
        #       attr1, attr2, attr3, ...
        # lbl1, val11, val12, val13, ...
        # lbl2, val21, val22, val23, ...
        # lbl3, val31, val32, val33, ...
        # ... , ...  , ...  , ...  , ...
        self.values     = None      # numpy.array
        self.ids        = None      # numpy.array
        self.labels     = None      # list<string>
        self.attributes = None      # list<string>
        