import logging
import os
import tempfile

from db.services.locator import ZIPFileLocator

# decorator
def UVCDATTest(func):
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    wrapped.isUVCDATTest = True
    return wrapped

class UVCDATTestManager:
    """
    All test functions on this class should be decorated with @UVCDATTest and
    not take any parameters they are called by run_tests(). 
     
    Test functions should raise exceptions to signify failure.
    """
    
    def __init__(self, cdat_source_dir, uvcdat_window):
        self.cdat_source_dir = cdat_source_dir
        
        test_nc_file = 'libcdms/src/cdunif/test/testnc.nc'
        self.test_nc_file_path = os.path.join(cdat_source_dir, test_nc_file)
        
        self.uvcdat_window = uvcdat_window
        
    def simulate_load_variable(self, path_or_url=None, varname_or_index=None):
        """
        @param path_or_url: If ommited or None, uses testnc.nc from libcdms
        @param varname_or_index: Name of variable, or the index in the 
          variable combobox. If ommited or None, the first variable is used
        """
        
        #open load variable widget
        definedVariableWidget = self.uvcdat_window.dockVariable.widget()
        definedVariableWidget.newVariable()
        
        #set the file path
        if path_or_url is None: path_or_url = self.test_nc_file_path
        loadVariableWidget = self.uvcdat_window.varProp
        loadVariableWidget.fileEdit.setText(path_or_url)
        loadVariableWidget.updateFile()
        
        #@todo: load variable based on varname or index
        #just load the first variable and close load widget
        loadVariableWidget.defineVarCloseClicked()
        
    def simulate_variable_drag_and_drop(self, varname_or_index=0, sheet="Sheet 1", col=1, row=1):
        if isinstance( varname_or_index, ( int, long ) ):
            variableItems = definedVariableWidget.getItems()
            varname_or_index = variableItems[0].getVarName()
        dropInfo = (varname_or_index, sheet, col, row)
        
        projectController = self.uvcdat_window.get_current_project_controller()
        projectController.variable_was_dropped(dropInfo)
        
    def simulate_plot_drag_and_drop(self, package="VCS", plot="Boxfill", 
                                    method="ASD", sheet="Sheet 1", col=1, 
                                    row=1):
        """
        @param method: Only used if package is VCS
        """
        
        projectController = self.uvcdat_window.get_current_project_controller()
        
        plot = None
        if package == 'VCS':
            plot = projectController.plot_manager.new_plot(package, plot, method)
        else:
            plot = projectController.plot_manager.new_plot(package, plot)
            
        dropInfo = (plot, sheet, col, row)
        projectController.plot_was_dropped(dropInfo)
        
    def simulate_save_project(self, filepath):
        
        projectController = self.uvcdat_window.get_current_project_controller()
        projectController.vt_controller.locator = ZIPFileLocator(filepath)
        self.uvcdat_window.workspace.saveProject(False)
        
    def simulate_open_project(self, filepath):
        locator = ZIPFileLocator(filepath)
        
        from gui.vistrails_window import _app
        _app.open_vistrail_without_prompt(locator)
    
    @UVCDATTest
    def test_save_close_load_vcs_project(self):
        
        self.simulate_load_variable()
        self.simulate_variable_drag_and_drop()
        self.simulate_plot_drag_and_drop()
        
        #is deleted upon closing
        temp_save_file = tempfile.NamedTemporaryFile(suffix=".vt", delete=True)
        
        self.simulate_save_project(temp_save_file.name)
        self.uvcdat_window.workspace.closeProject(False)
        
        self.simulate_open_project(temp_save_file.name)
        self.uvcdat_window.workspace.closeProject(False)
        
        self.simulate_open_project(temp_save_file.name)
        self.uvcdat_window.workspace.closeProject(False)
        
        temp_save_file.close()
        
    def run_tests(self):
        """
        Executes all @UVCDATTest decorated functions defined on self, prints
        exceptions, and returns number of fails.
        """
        import datetime
        print "Running tests. Timestamp: %s" % str(datetime.datetime.now())
        
        failCount = 0
        for attribute in dir(self):
            if not hasattr(self, attribute):continue
            function = getattr(self, attribute)
            
            if not hasattr(function, '__call__'): continue
            if not hasattr(function, 'isUVCDATTest'): continue
            if not function.isUVCDATTest: continue

            try:
                function()
            except Exception, e:
                failCount += 1
                print "Failed test %s" % attribute
                logging.exception(e)
            
        return failCount
                
        