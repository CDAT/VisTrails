"""ORNL-Climate package for VisTrails.

This package ...

"""

identifier = 'gov.ornl.climate'
name = 'ORNL-Climate'
version = '0.0.1'

def package_dependencies():
    import core.packagemanager
    manager = core.packagemanager.get_package_manager()
    if manager.has_package('edu.utah.sci.vistrails.spreadsheet'):
        return ['edu.utah.sci.vistrails.spreadsheet',
                'gov.llnl.uvcdat.cdms']
    else:
        return ['gov.llnl.uvcdat.cdms']

def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('matplotlib'):
        raise core.requirements.MissingRequirement('matplotlib')
    if not core.requirements.python_module_exists('pylab'):
        raise core.requirements.MissingRequirement('pylab')
