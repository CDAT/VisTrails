"""
This module describes a theme structure for UVCDAT GUI. It
specifies icons to be used on the GUI.

"""
from PyQt4 import QtCore, QtGui
from core.configuration import get_vistrails_configuration
import gui.uvcdat.uvcdat_rc

class UVCDATDefaultTheme(object):
    """
    This is the default theme with the colored icons. Other themes can be 
    created by deriving this class.
    
    """
    def __init__(self):
        """ UVCDATDefaultTheme() -> UVCDATDefaultTheme
        This is for initializing all Qt objects
        
        """
        ######################################
        #### ICONS ###########################
        # Workspace
        self.WORKSPACE_NEW_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/new.png')
        self.WORKSPACE_OPEN_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/open.png')
        self.WORKSPACE_CLOSE_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/close.png')
        self.WORKSPACE_SAVE_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/file_save.png')
        self.WORKSPACE_FOLDER_OPEN_PIXMAP = QtGui.QPixmap(
            ':/icons/resources/icons/folder_blue_open.png')
        self.WORKSPACE_FOLDER_CLOSED_PIXMAP = QtGui.QPixmap(
            ':/icons/resources/icons/folder_blue.png')
        self.WORKSPACE_PIPELINE_ICON = QtGui.QIcon(
            ':/icons/resources/icons/pipeline.png')
        # Variables widget
        self.VARIABLE_ADD_ICON = QtGui.QIcon(
            ':/icons/resources/icons/edit_add.png')
        self.VARIABLE_DELETE_ICON = QtGui.QIcon(
            ':/icons/resources/icons/delete.png')
        self.VARIABLE_SELECT_ALL_ICON = QtGui.QIcon(
            ':/icons/resources/icons/checked.png')
        self.VARIABLE_INFO_ICON = QtGui.QIcon(
            ':/icons/resources/icons/info.png')
        self.VARIABLE_EDIT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/edit.png')
        self.VARIABLE_SAVE_ICON = QtGui.QIcon(
            ':/icons/resources/icons/file_save.png')
        
        # Spreadsheet Icons
        self.PREFERENCES_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/preferences.png')
        self.DELETE_CELL_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/delete.png')
        self.EXECUTE_CELL_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/execute.png')
        
        #VCS Plots Icons
        self.PLOT_VIEW_SOURCE_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/source_code.png')
        self.PLOT_EDIT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/edit.png')
        self.PLOT_PREVIOUS_ICON = QtGui.QIcon(
            ':/icons/resources/icons/previous.png')
        self.PLOT_NEXT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/next.png')
        self.PLOT_EXPORT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/file_export.png')
        self.PLOT_COLORMAP_ICON = QtGui.QIcon(
            ':/icons/resources/icons/colormap.png')
        self.PLOT_ANIMATION_ICON = QtGui.QIcon(
            ':/icons/resources/icons/animation.png')
        
class UVCDATMinimalTheme(UVCDATDefaultTheme):
    def __init__(self):
        UVCDATDefaultTheme.__init__(self)
        ######################################
        #### ICONS ###########################
        # Workspace
        self.WORKSPACE_NEW_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/new.png')
        self.WORKSPACE_OPEN_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/open.png')
        self.WORKSPACE_CLOSE_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/close.png')
        self.WORKSPACE_SAVE_PROJECT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/file_save.png')
        
        # Variables widget
        self.VARIABLE_ADD_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/edit_add.png')
        self.VARIABLE_DELETE_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/delete.png')
        self.VARIABLE_SELECT_ALL_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/checked.png')
        self.VARIABLE_INFO_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/info.png')
        self.VARIABLE_EDIT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/edit.png')
        self.VARIABLE_SAVE_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/file_save.png')
        
        # Spreadsheet Icons
        self.PREFERENCES_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/minimal/preferences.png')
        self.DELETE_CELL_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/minimal/delete.png')
        self.EXECUTE_CELL_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/minimal/execute.png')
        
        #VCS Plots Icons
        self.PLOT_VIEW_SOURCE_ICON =  QtGui.QIcon(
            ':/icons/resources/icons/minimal/source_code.png')
        self.PLOT_EDIT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/edit.png')
        self.PLOT_PREVIOUS_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/previous.png')
        self.PLOT_NEXT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/next.png')
        self.PLOT_EXPORT_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/file_export.png')
        self.PLOT_COLORMAP_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/colormap.png')
        self.PLOT_ANIMATION_ICON = QtGui.QIcon(
            ':/icons/resources/icons/minimal/animation.png')
        
class ThemeHolder(object):
    """
    ThemeHolder is a class holding a theme and exposed that theme
    attributes as attributes of itself. This is useful for global
    import of the CurrentTheme variable
    
    """
    def __init__(self):
        object.__init__(self)
        self.theme = None

    def setTheme(self, theme):
        """ setTheme(theme: subclass of DefaultTheme) -> None
        Set the current theme to theme
        
        """
        # This way, the lookups into the theme are much faster, since
        # there's no function calls involved
        self.__dict__.update(theme.__dict__)
        
def get_current_theme():
    """get_current_theme() -> subclass of DefaultTheme
    Instantiates the theme according to the current platform """
    theme = get_vistrails_configuration().uvcdat.theme
    if theme == 'Minimal':
        return UVCDATMinimalTheme()
    else:
        return UVCDATDefaultTheme()

def initializeUVCDATTheme():
    """ initializeCurrentTheme() -> None
    Assign the current theme to the default theme
    
    """
    global UVCDATTheme
    
    UVCDATTheme.setTheme(get_current_theme())

global UVCDATTheme
UVCDATTheme = ThemeHolder()
