import logging
import os

# decorator
def UVCDATTest(func):
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    wrapped.isUVCDATTest = True
    return wrapped

class UVCDATTestManager:
    """
    All functions on this class should not take any parameters, and
    are called by run_tests(). Test functions should raise exceptions
    to signify failure.
    """
    
    def __init__(self, cdat_source_dir, uvcdat_window):
        self.cdat_source_dir = cdat_source_dir
        
        test_nc_file = 'libcdms/src/cdunif/test/testnc.nc'
        self.test_nc_file_path = os.path.join(cdat_source_dir, test_nc_file)
        
        self.uvcdat_window = uvcdat_window
    
    @UVCDATTest
    def test_save_close_load_vcs_project(self):
        #open load variable widget
        definedVariableWidget = self.uvcdat_window.dockVariable.widget()
        definedVariableWidget.newVariable()
        
        #set the file path
        loadVariableWidget = self.uvcdat_window.varProp
        loadVariableWidget.fileEdit.setText(self.test_nc_file_path)
        loadVariableWidget.updateFile()
        
        #just load the first variable and close load widget
        loadVariableWidget.defineVarCloseClicked()
        
        #simulate variable drag and drop
        variableItems = definedVariableWidget.getItems()
        variableName = variableItems[0].getVarName()
        dropInfo = (variableName, 'Sheet 1', 1, 1)
        
        projectController = self.uvcdat_window.get_current_project_controller()
        projectController.variable_was_dropped(dropInfo)
    
    def run_tests(self):
        """
        Executes all functions defined on self as tests, prints
        exceptions, and returns number of fails.
        """
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
                
        