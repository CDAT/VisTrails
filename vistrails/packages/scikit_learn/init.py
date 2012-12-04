from generators import SCurveGenerator, SwissRollGenerator
from manifold import RandomProjection, RandomizedPCA, Isomap, LLE, MLLE, HLLE, LTSA
from views import ProjectionView

_modules = [(SCurveGenerator,     {'namespace':SCurveGenerator.my_namespace}),
            (SwissRollGenerator,  {'namespace':SwissRollGenerator.my_namespace}),
            (RandomProjection,    {'namespace':RandomProjection.my_namespace,    'name':RandomProjection.name}),
            (RandomizedPCA,       {'namespace':RandomizedPCA.my_namespace,       'name':RandomizedPCA.name}),
            (Isomap,              {'namespace':Isomap.my_namespace,              'name':Isomap.name}),
            (LLE,                 {'namespace':LLE.my_namespace,                 'name':LLE.name}),
            (MLLE,                {'namespace':MLLE.my_namespace,                'name':MLLE.name}),
            (HLLE,                {'namespace':HLLE.my_namespace,                'name':HLLE.name}),
            (LTSA,                {'namespace':LTSA.my_namespace,                'name':LTSA.name}),
            (ProjectionView,      {'namespace':ProjectionView.my_namespace,      'name':ProjectionView.name}),
            ]

