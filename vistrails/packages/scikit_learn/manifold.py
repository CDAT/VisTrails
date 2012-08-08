from core.modules.vistrails_module import Module
from core.modules.basic_modules import Integer, Float, String, Boolean
from packages.NumSciPy.Array import NDArray
from sklearn import manifold, decomposition, lda
from sklearn.utils.fixes import qr_economic
import numpy as np

class RandomProjection(Module):
    """
    Random 2D projection using a random unitary matrix
    """
    my_namespace = 'projections'
    name         = 'Random Projection'
    
    _input_ports = [('X',                   NDArray, False),
                    ('n_components',        Integer, False),
                    ]
    _output_ports = [('Y',                    NDArray, False)]
    
    def compute(self):
        X            = self.getInputFromPort('X')
        n_components = self.forceGetInputFromPort('n_components', 2)
        n_features   = X.shape(1)
        Y            = NDArray()
        
        rng = np.random.RandomState(42)
        Q, _ = qr_economic(rng.normal(size=(n_features, n_components)))
        Y.array = np.dot(Q.T, X.array.T).T
        
        self.setResult('Y', Y)

class RandomizedPCA(Module):
    """
    Principal component analysis (PCA) using randomized SVD
    Linear dimensionality reduction using approximated Singular Value Decomposition 
    of the data and keeping only the most significant singular vectors to project 
    the data to a lower dimensional space.
    This implementation uses a randomized SVD implementation and can handle both 
    scipy.sparse and numpy dense arrays as input.
    """
    my_namespace = 'projections'
    name         = 'Randomized PCA'
    
    _input_ports = [('X',                   NDArray, False),
                    ('n_components',        Integer, False),
                    ('copy',                Boolean, True),
                    ('iterated_power',      Integer, True),
                    ('whiten',              Boolean, True),
                    ('random_state',        Integer, True)
                    ]
    _output_ports = [('Y',                    NDArray, False)]
    
    def compute(self):
        X = self.getInputFromPort('X')
        Y = NDArray()
         
        pca = decomposition.RandomizedPCA(
            n_components   = self.forceGetInputFromPort('n_components', 2),
            copy           = self.forceGetInputFromPort('copy', True),
            iterated_power = self.forceGetInputFromPort('iterated_power', 3),
            whiten         = self.forceGetInputFromPort('whiten', False),
            random_state   = self.forceGetInputFromPort('random_state', None)
            )
        Y.array = pca.fit_transform(X.array)
        
        self.setResult('Y', Y)

#class LDA(Module):
#    """
#    Linear Discriminant Analysis (LDA)
#    """
#    my_namespace = 'projections'
#    name         = 'LDA'
#    
#    _input_ports = [('X',                   NDArray, False),
#                    ('n_components',        Integer, False),
#                    ('priors',              Boolean, True)
#                    ]
#    _output_ports = [('Y',                    NDArray, False)]
#    
#    def compute(self):
#        X = self.getInputFromPort('X')
#        Y = NDArray()
#        
#        X2 = X.array.copy()
#        X2.flat[::X.array.shape[1] + 1] += 0.01  # Make X invertible
#        ldaProj = lda.LDA(
#            n_components = self.forceGetInputFromPort('n_components', 2),
#            priors       = self.forceGetInputFromPort('priors', None),
#            )
#        Y.array = ldaProj.fit_transform(X2)
#
#        self.setResult('Y', Y)

class Isomap(Module):
    """
    One of the earliest approaches to manifold learning is the Isomap algorithm, 
    short for Isometric Mapping. Isomap can be viewed as an extension of 
    Multi-dimensional Scaling (MDS) or Kernel PCA. Isomap seeks a lower-dimensional 
    embedding which maintains geodesic distances between all points. Isomap can 
    be performed with the object Isomap.
    """
    my_namespace = 'projections'
    name         = 'Isomap'

    _input_ports = [('X',                   NDArray, False),
                    ('n_neighbors',         Integer, False),
                    ('n_components',        Integer, False),
                    ('eigen_solver',        String,  True),
                    ('tol',                 Float,   True),
                    ('max_iter',            Integer, True),
                    ('path_method',         String,  True),
                    ('neighbors_algorithm', String,  True),
                    ('out_dim',             Integer, False)
                    ]
    _output_ports = [('Y',                    NDArray, False),
                     ('reconstruction_error', Float,   False)]


    def compute(self):
        isomap = manifold.Isomap(
            n_neighbors         = self.forceGetInputFromPort('n_neighbors', 5),
            n_components        = self.forceGetInputFromPort('n_components', 2),
            eigen_solver        = self.forceGetInputFromPort('eigen_solver', 'auto'),
            tol                 = self.forceGetInputFromPort('tol', 0),
            max_iter            = self.forceGetInputFromPort('max_iter', None),
            path_method         = self.forceGetInputFromPort('path_method', 'auto'),
            neighbors_algorithm = self.forceGetInputFromPort('neighbors_algorithm', 'auto'),
            out_dim             = self.forceGetInputFromPort('out_dim', None)
        )
        
        Y = NDArray()
        Y.array = isomap.fit_transform(self.getInputFromPort('X').get_array())
        reconstruction_error = isomap.reconstruction_error()
             
        self.setResult('Y', Y)
        self.setResult('reconstruction_error', reconstruction_error)

    
class AbstractLLE(object):
    """
    
    """
    my_namespace = 'projections'

    _input_ports = [('X',            [(NDArray, 'Sample data, shape = (n_samples, n_features).')]),
                    ('n_neighbors',  [(Integer, 'number of neighbors to consider for each point.')]),
                    ('n_components', [(Integer, 'number of coordinates for the manifold.')]),
                    ('reg',          [(Float, 'regularization constant, multiplies the trace of the local covariance matrix of the distances.')]),
                    ('eigen_solver', [(String, '')]),
                    ('tol',          [(Float, 'Tolerance for \'arpack\' method Not used if eigen_solver==\'dense\'.')]),
                    ('max_iter',     [(Integer, 'maximum number of iterations for the arpack solver.')]),
                    ('random_state', [(Integer, 'The generator used to initialize the centers.')]),
                    ]
    
    _output_ports = [('Y',             [(NDArray, 'Embedding vectors. s shape [n_samples, n_components].')]),
                     ('squared_error', [(Float, 'Reconstruction error for the embedding vectors')])
                     ]
    
    def __init__(self):
        self.hessian_tol = 0.0001
        self.modified_tol = 1e-12

    def compute(self):
        Y = NDArray()
        Y.array, squared_error = manifold.locally_linear_embedding(
            X            = self.getInputFromPort('X').get_array(),
            n_neighbors  = self.forceGetInputFromPort('n_neighbors', 10),
            n_components = self.forceGetInputFromPort('n_components', 2),
            reg          = self.forceGetInputFromPort('reg', 0.001),
            eigen_solver = self.forceGetInputFromPort('eigen_solver', 'auto'),
            tol          = self.forceGetInputFromPort('tol', 1e-06),
            max_iter     = self.forceGetInputFromPort('max_iter', 100),
            method       = self.method,
            hessian_tol  = self.hessian_tol,
            modified_tol = self.modified_tol,
            random_state = self.forceGetInputFromPort('random_state', None)
#            out_dim      = self.forceGetInputFromPort('out_dim', None)
        )
        
        self.setResult('Y', Y)
        self.setResult('squared_error', squared_error)

class LLE(Module, AbstractLLE):
    """
    Locally linear embedding (LLE) seeks a lower-dimensional projection of the
    data which preserves distances within local neighborhoods. It can be thought 
    of as a series of local Principal Component Analyses which are globally 
    compared to find the best nonlinear embedding.
    """
    name = 'Locally Linear Embedding'
    
    def __init__(self):
        Module.__init__(self)
        self.method = 'standard'
        

class MLLE(Module, AbstractLLE):
    """
    One well-known issue with LLE is the regularization problem. When the number 
    of neighbors is greater than the number of input dimensions, the matrix 
    defining each local neighborhood is rank-deficient. To address this, standard 
    LLE applies an arbitrary regularization parameter r, which is chosen relative 
    to the trace of the local weight matrix. Though it can be shown formally that 
    as r->0, the solution coverges to the desired embedding, there is no guarantee that 
    the optimal solution will be found for r>0. This problem manifests itself in 
    embeddings which distort the underlying geometry of the manifold.
    """
    name = 'Modified Locally Linear Embedding'
    _input_ports = AbstractLLE._input_ports + \
                   [('modified_tol', [(Float, 'Tolerance for modified LLE method. Only used if method==\'modified\'')])]
    
    def __init__(self):
        Module.__init__(self)
        self.method = 'modified'
    
    def compute(self):
        self.modified_tol = self.forceGetInputFromPort('modified_tol', 1e-12)
        AbstractLLE.compute(self)

class HLLE(Module, AbstractLLE):
    """
    Hessian Eigenmapping (also known as Hessian-based LLE: HLLE) is another method 
    of solving the regularization problem of LLE. It revolves around a hessian-based 
    quadratic form at each neighborhood which is used to recover the locally linear 
    structure. Though other implementations note its poor scaling with data size, 
    sklearn implements some algorithmic improvements which make its cost comparable 
    to that of other LLE variants for small output dimension.
    """
    name = 'Hessian Eigenmapping'
    _input_ports = AbstractLLE._input_ports + \
                   [('hessian_tol',  [(Float, 'Tolerance for Hessian eigenmapping method. Only used if method==\'hessian\'')])]

    def __init__(self):
        Module.__init__(self)
        self.method = 'hessian'

    def compute(self):
        self.hessian_tol = self.forceGetInputFromPort('hessian_tol', 0.0001)
        AbstractLLE.compute(self)

class LTSA(Module, AbstractLLE):
    """
    Though not technically a variant of LLE, Local tangent space alignment (LTSA) 
    is algorithmically similar enough to LLE that it can be put in this category. 
    Rather than focusing on preserving neighborhood distances as in LLE, LTSA seeks 
    to characterize the local geometry at each neighborhood via its tangent space, 
    and performs a global optimization to align these local tangent spaces to learn 
    the embedding.
    """
    name = 'Local Tangent Space Alignment'
    
    def __init__(self):
        Module.__init__(self)
        self.method = 'ltsa'



