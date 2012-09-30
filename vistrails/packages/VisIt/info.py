identifier = 'gov.lbl.visit'
version = '0.0.1'
name = "VisIt"

def package_dependencies():
    import core.packagemanager
    dependencies = []
    manager = core.packagemanager.get_package_manager()
    if manager.has_package('edu.utah.sci.vistrails.spreadsheet'):
        dependencies.append('edu.utah.sci.vistrails.spreadsheet')
    dependencies.append('gov.llnl.uvcdat')
    dependencies.append('gov.llnl.uvcdat.cdms')
    return dependencies

def package_requirements():
    import core.requirements
    if not core.requirements.python_module_exists('visit'):
        raise core.requirements.MissingRequirement('visit')
    if not core.requirements.python_module_exists('visit.pyqt_gui'):
        raise core.requirements.MissingRequirement('visit.pyqt_gui')
    # Figure out how to check on pvvariable
    if not core.requirements.python_module_exists('PyQt4'):
        from core import debug
        debug.warning('PyQt4 is not available. There will be no interaction '
                      'between VisIt and the spreadsheet.')
    import visit.pyqt_gui
    import visit

