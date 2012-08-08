from core.modules.vistrails_module import Module
from core.modules.basic_modules import Integer, Float
from packages.NumSciPy.Array import NDArray

from sklearn import manifold, datasets


################################################################################

class Generator(object):
    my_namespace = 'generator'
    
class SCurveGenerator(Module, Generator):
    """" Sample Generator is a component to create some testing data. """
    
    _input_ports = [('n_samples', [(Integer, 'The number of sample points on the S curve.')]),
                    ('noise', [(Float, 'The standard deviation of the gaussian noise.')]),
                    ('random_state', [(Integer, 'RandomState instance or None')])]
    _output_ports = [('X', [(NDArray, 'The points. [n_samples, 3]')]),
                     ('t', [(NDArray, 'The univariate position of the sample. [n_samples]')])]
    
    def compute(self):
        n_samples = self.forceGetInputFromPort('n_samples', 100)
        noise = self.forceGetInputFromPort('noise', 0.0)
        random_state = self.forceGetInputFromPort('random_state', None)
        
        X, t = NDArray(), NDArray()
        X.array, t.array = datasets.samples_generator.make_s_curve(n_samples, noise, random_state)
        
        self.setResult('X', X)
        self.setResult('t', t)
        
class SwissRollGenerator(Module, Generator):
    """"  Generate a swiss roll dataset. """
    
    _input_ports = [('n_samples', [(Integer, 'The number of sample points on the S curve.')]),
                    ('noise', [(Float, 'The standard deviation of the gaussian noise.')]),
                    ('random_state', [(Integer, 'RandomState instance or None')])]
    _output_ports = [('X', [(NDArray, 'The points. [n_samples, 3]')]),
                     ('t', [(NDArray, 'The univariate position of the sample. [n_samples]')])]
    
    def compute(self):
        n_samples = self.forceGetInputFromPort('n_samples', 100)
        noise = self.forceGetInputFromPort('noise', 0.0)
        random_state = self.forceGetInputFromPort('random_state', None)
        
        X, t = NDArray(), NDArray()
        X.array, t.array = datasets.samples_generator.make_swiss_roll(n_samples, noise, random_state)
        
        self.setResult('X', X)
        self.setResult('t', t)