"""ORNL-Climate package for VisTrails.

This package ...

"""

identifier = 'gov.ornl.climate'
name = 'ORNL-Climate'
version = '0.0.1'

def package_dependencies():
    return ['edu.utah.sci.vistrails.spreadsheet',
           'gov.llnl.uvcdat.cdms', 
           'edu.utah.sci.vistrails.numpyscipy']
    
def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('matplotlib'):
        raise core.requirements.MissingRequirement('matplotlib')
    if not core.requirements.python_module_exists('pylab'):
        raise core.requirements.MissingRequirement('pylab')
