from core.modules.vistrails_module import Module
from core.modules.basic_modules import Integer, Float
from packages.vis_analytics.matrix import Matrix

from sklearn import datasets


################################################################################

class Generator(object):
    my_namespace = 'generator'
    
class SCurveGenerator(Module, Generator):
    """" Sample Generator is a component to create some testing data. """
    
    _input_ports = [('n_samples', [(Integer, 'The number of sample points on the S curve.')]),
                    ('noise', [(Float, 'The standard deviation of the gaussian noise.')]),
                    ('random_state', [(Integer, 'RandomState instance or None')])]
    _output_ports = [('matrix', [(Matrix, '')])]
                     
    def compute(self):
        n_samples = self.forceGetInputFromPort('n_samples', 100)
        noise = self.forceGetInputFromPort('noise', 0.0)
        random_state = self.forceGetInputFromPort('random_state', None)
        
        X, t = datasets.samples_generator.make_s_curve(n_samples, noise, random_state)
        
        # Creating matrix with values, ids, labels and attributes
        matrix = Matrix()
        matrix.values     = X
        matrix.ids        = range(X.shape[1])
        matrix.labels     = [str(_id) for _id in matrix.ids]
        matrix.attributes = [str(attr) for attr in range(X.shape[1])]
         
        self.setResult('matrix', matrix)
        
class SwissRollGenerator(Module, Generator):
    """"  Generate a swiss roll dataset. """
    
    _input_ports = [('n_samples', [(Integer, 'The number of sample points on the S curve.')]),
                    ('noise', [(Float, 'The standard deviation of the gaussian noise.')]),
                    ('random_state', [(Integer, 'RandomState instance or None')])]
    _output_ports = [('matrix', [(Matrix, '')])]
    
    def compute(self):
        n_samples = self.forceGetInputFromPort('n_samples', 100)
        noise = self.forceGetInputFromPort('noise', 0.0)
        random_state = self.forceGetInputFromPort('random_state', None)
        
        X, t = datasets.samples_generator.make_swiss_roll(n_samples, noise, random_state)
        
        # Creating matrix with values, ids, labels and attributes
        matrix = Matrix()
        matrix.values     = X
        matrix.ids        = range(X.shape[1])
        matrix.labels     = [str(_id) for _id in matrix.ids]
        matrix.attributes = [str(attr) for attr in range(X.shape[1])]
         
        self.setResult('matrix', matrix)
    