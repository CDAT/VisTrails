import logging
import os
import sys
import tempfile
import traceback

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
        
    def simulate_load_variable(self, path_or_url=None, varname_or_index=1):
        """
        @param path_or_url: If ommited or None, uses testnc.nc from libcdms
        @param varname_or_index: Name of variable, or the index in the 
          variable combobox. If ommited, the first variable is used
        """
        
        #open load variable widget
        definedVariableWidget = self.uvcdat_window.dockVariable.widget()
        definedVariableWidget.newVariable()
        
        #set the file path
        if path_or_url is None: path_or_url = self.test_nc_file_path
        loadVariableWidget = self.uvcdat_window.varProp
        loadVariableWidget.fileEdit.setText(path_or_url)
        loadVariableWidget.updateFile()
        
        if isinstance(varname_or_index, basestring):
            for i in range(loadVariableWidget.varCombo.count()):
                itemText = loadVariableWidget.varCombo.itemText(i)
                if varname_or_index == str(itemText).split()[0]:
                    loadVariableWidget.varCombo.setCurrentIndex(i)
                    loadVariableWidget.variableSelected(itemText)
                    break
        elif isinstance(varname_or_index, (int, long)):
            itemText = loadVariableWidget.varCombo.itemText(varname_or_index)
            loadVariableWidget.varCombo.setCurrentIndex(varname_or_index)
            loadVariableWidget.variableSelected(itemText)
        else:
            msg = "Invalid varname_or_index: %s" % str(varname_or_index)
            raise Exception(msg)
            
        loadVariableWidget.defineVarCloseClicked()
        
    def varname_from_index(self, index):
        """Variable name based on it's index in the defined variables widget
        """
        definedVariableWidget = self.uvcdat_window.dockVariable.widget()
        variableItems = definedVariableWidget.getItems()
        return variableItems[index].getVarName()
    
    def selectVariable(self, varname):
        definedVariableWidget = self.uvcdat_window.dockVariable.widget()
        definedVariableWidget.selectVariableFromName(varname)
        
    def simulate_variable_drag_and_drop(self, varname_or_index=0, 
                                        sheet="Sheet 1", col=0, row=0, 
                                        projectController=None):
        if isinstance( varname_or_index, ( int, long ) ):
            varname_or_index = self.varname_from_index(varname_or_index)
        dropInfo = (varname_or_index, sheet, col, row)
        
        if projectController is None:
            projectController = self.get_project_controller()
        projectController.variable_was_dropped(dropInfo)
        
    def simulate_plot_drag_and_drop(self, package="VCS", name="Boxfill", 
                                    method="default", sheet="Sheet 1", col=0, 
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
        
    def simulate_calculator_command(self, command):
        self.uvcdat_window.dockCalculator.widget().le.setText(command)
        self.uvcdat_window.dockCalculator.widget().run_command()

    def simulate_set_monthly_bounds(self, varname):
        self.selectVariable(varname)
        
        class dummyAction:
            def text(self):
                return "Set Bounds For Monthly Data"
            
        self.uvcdat_window.mainMenu.setBounds(dummyAction())
        
    def simulate_mean_operation(self, varname):
        
        
    def close_project(self):
        from gui.vistrails_window import _app
        _app.close_vistrail(None, True)
    
    @UVCDATTest
    def test_save_open_close_vcs_project(self):
        
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
        self.simulate_default_vcs_boxfill()
        
        #undock sheet
        spreadSheetWindow = self.uvcdat_window.centralWidget()
        tabController = spreadSheetWindow.get_current_tab_controller()
        tabController.splitTab(0)
        
        #show plot properties
        tabWidget = tabController.floatingTabWidgets[0].widget()
        tabWidget.requestPlotConfigure(0, 0)
        
        #hide plot properties
        self.uvcdat_window.plotProp.hide()
        
        #close floating sheet, placing it back in main window
        tabWidget.close()
        
    @UVCDATTest
    def test_1D_isofill_plot(self):

        self.simulate_load_variable(varname_or_index='longitude')
        self.simulate_plot_drag_and_drop(name="Isofill")
        self.simulate_variable_drag_and_drop()
        
        #ensure that the variable wasn't added to the plot
        projectController = self.get_project_controller()
        cellController = projectController.sheet_map['Sheet 1'][(0,0)]
        if len(cellController.plots[0].variables) > 0:
            raise Exception("1D variable longitude should have been prevented "
                            "from being added to Isofill plot")
            
    @UVCDATTest
    def test_time_bounds_computed_vars(self):
        
        self.simulate_load_variable()
        varname = self.varname_from_index(0)
        self.simulate_calculator_command("computed_var=%s*2" % varname)
        self.simulate_set_monthly_bounds("computed_var")
        self.simulate_mean_operation("computed_var")
        
    innerFail = False
        
    def run_tests(self):
        """
        Executes all @UVCDATTest decorated functions defined on self, prints
        exceptions, and returns number of fails.
        """
        import datetime
        print "RUNNING TESTS. Timestamp: %s" % str(datetime.datetime.now())
        
        #setup special exception hook due to some exceptions not being thrown
        def test_exception_hook(exctype, value, tb):
            UVCDATTestManager.innerFail = True
            print "FAILED TEST"
            print ''.join(traceback.format_exception(exctype, value, tb))
            
        sys.excepthook = test_exception_hook
            
        failCount = 0
        for attribute in dir(self):
            if not hasattr(self, attribute): continue
            testFunction = getattr(self, attribute)
            
            if not hasattr(testFunction, '__call__'): continue
            if not hasattr(testFunction, 'isUVCDATTest'): continue
            if not testFunction.isUVCDATTest: continue

            print "RUNNING TEST %s" % attribute

            self.disable_autosave()
            
            try:
                testFunction()
            except Exception, e:
                failCount += 1
                print "FAILED TEST %s" % attribute
                logging.exception(e)
            else:
                if UVCDATTestManager.innerFail:
                    failCount +=1
                    UVCDATTestManager.innerFail = False
                      
            #close all open projects so each test starts with clean slate
            for _ in range(self.uvcdat_window.workspace.numProjects):
                self.close_project()
                    
                    
        #restore default exception hook
        sys.excepthook = sys.__excepthook__
            
        plural = "s"
        if failCount == 1:
            plural = ""
        print "TEST RESULTS: %d test%s failed." % (failCount, plural)
        return failCount
                
        