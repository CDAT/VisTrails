import logging
import os
import tempfile

from core.db.locator import FileLocator

# decorator
def UVCDATTest(func):
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    wrapped.isUVCDATTest = True
    return wrapped

class UVCDATTestManager:
    """
    All test functions on this class should be decorated with @UVCDATTest and
    not take any parameters, they are called by run_tests(). 
     
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
        
    def simulate_variable_drag_and_drop(self, varname_or_index=0, 
                                        sheet="Sheet 1", col=0, row=0, 
                                        projectController=None):
        definedVariableWidget = self.uvcdat_window.dockVariable.widget()
        if isinstance( varname_or_index, ( int, long ) ):
            variableItems = definedVariableWidget.getItems()
            varname_or_index = variableItems[0].getVarName()
        dropInfo = (varname_or_index, sheet, col, row)
        
        if projectController is None:
            projectController = self.get_project_controller()
        projectController.variable_was_dropped(dropInfo)
        
    def simulate_plot_drag_and_drop(self, package="VCS", name="Boxfill", 
                                    method="ASD", sheet="Sheet 1", col=0, 
                                    row=0, projectController=None):
        """
        @param method: Only used if package is VCS
        """
        
        if projectController is None:
            projectController = self.get_project_controller()
        
        plot = None
        if package == 'VCS':
            plot = projectController.plot_manager.new_plot(package, name, method)
        else:
            plot = projectController.plot_manager.new_plot(package, name)
            
        dropInfo = (plot, sheet, col, row)
        
        projectController.plot_was_dropped(dropInfo)
        
    def simulate_save_project(self, filepath, projectController=None):
        if projectController is None:
            projectController = self.get_project_controller()
        projectController.vt_controller.locator = FileLocator(filepath)
        #projectController.vt_controller.locator.clean_temporaries()
        self.uvcdat_window.workspace.saveProject(False)
        #projectController.vt_controller.locator.clean_temporaries()
        
    def simulate_open_project(self, filepath):
        locator = FileLocator(filepath)
        locator.clean_temporaries()
        
        from gui.vistrails_window import _app
        _app.open_vistrail_without_prompt(locator)
        
        self.disable_autosave()
        
    def get_project_controller(self):
        return self.uvcdat_window.get_current_project_controller()
    
    def disable_autosave(self, projectController=None):
        if projectController is None:
            projectController = self.get_project_controller()
        projectController.vt_controller.disable_autosave()
    
    def simulate_default_vcs_boxfill(self):
        self.simulate_load_variable()
        self.simulate_plot_drag_and_drop()
        self.simulate_variable_drag_and_drop()
        
    def close_project(self):
        from gui.vistrails_window import _app
        _app.close_vistrail(None, True)
    
    @UVCDATTest
    def test_save_open_close_vcs_project(self):
        
        #all tests should call this very first
        self.disable_autosave()
        
        self.simulate_default_vcs_boxfill()
        
        #is deleted upon closing
        temp_save_file = tempfile.NamedTemporaryFile(suffix=".vt", delete=True)
        
        self.simulate_save_project(temp_save_file.name)
        self.close_project()
        
        self.simulate_open_project(temp_save_file.name)
        self.close_project()
        
        self.simulate_open_project(temp_save_file.name)
        self.close_project()
        
        temp_save_file.close()
        
    @UVCDATTest
    def test_detach_sheet_open_plot_properties(self):
        self.disable_autosave()
        self.simulate_default_vcs_boxfill()
        
        #undock sheet
        spreadSheetWindow = self.uvcdat_window.centralWidget()
        spreadSheetWindow.get_current_tab_controller().splitTab(0)
        
        #show plot properties
        self.uvcdat_window.showPlotProperties()
        self.close_project()
        
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

            print "Running test %s" % attribute
            try:
                function()
            except Exception, e:
                failCount += 1
                print "Failed test %s" % attribute
                logging.exception(e)
            
        plural = "s"
        if failCount == 1:
            plural = ""
        print "%d test%s failed." % (failCount, plural)
        return failCount
                
        