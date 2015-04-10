identifier = 'com.kitware.pvclimate'
name = 'PVClimate'
version = '0.1.4'

def package_dependencies():
    import core.packagemanager
    dependencies = ["gov.llnl.uvcdat", "gov.llnl.uvcdat.cdms"]
    manager = core.packagemanager.get_package_manager()    
    if manager.has_package('edu.utah.sci.vistrails.spreadsheet'):
        dependencies.append('edu.utah.sci.vistrails.spreadsheet')
    return dependencies

def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('vtk'):
        raise core.requirements.MissingRequirement('vtk')
    if not core.requirements.python_module_exists('paraview'):
        raise core.requirements.MissingRequirement('paraview')
    if not core.requirements.python_module_exists('PyQt4'):
        from core import debug
        debug.warning('PyQt4 is not available. There will be no interaction '
                      'between VTK and the spreadsheet.')    
