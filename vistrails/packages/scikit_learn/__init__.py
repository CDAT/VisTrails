"""ORNL-Climate package for VisTrails.

This package ...

"""

identifier = 'edu.poly.scikit_learn'
name = 'Scikit-Learn'
version = '0.0.1'

def package_dependencies():
    return ['edu.utah.sci.vistrails.spreadsheet']

def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('numpy'):
        raise core.requirements.MissingRequirement('numpy')
    if not core.requirements.python_module_exists('scipy'):
        raise core.requirements.MissingRequirement('scipy')
    if not core.requirements.python_module_exists('sklearn'):
        raise core.requirements.MissingRequirement('sklearn')
    if not core.requirements.python_module_exists('matplotlib'):
        raise core.requirements.MissingRequirement('matplotlib')
