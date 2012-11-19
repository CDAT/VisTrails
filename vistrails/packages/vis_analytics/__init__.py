"""Visual Analytics package for VisTrails.

This package ...

"""

identifier = 'edu.poly.vis_analytics'
name = 'Visual Analytics'
version = '0.0.1'

def package_dependencies():
    return ['edu.utah.sci.vistrails.spreadsheet',
            'gov.llnl.uvcdat.cdms']
    
def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('matplotlib'):
        raise core.requirements.MissingRequirement('matplotlib')
    if not core.requirements.python_module_exists('pylab'):
        raise core.requirements.MissingRequirement('pylab')
