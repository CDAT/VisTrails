from PyQt4 import QtCore, QtGui
from packages.spreadsheet.spreadsheet_tab import StandardWidgetSheetTab

################################################################################

class BlankWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)


class DisplayWallSheetTab(StandardWidgetSheetTab):
    """
    MultiHeadDisplayWallSheetTab is a wrapper of StandardWidgetSheetTab that
    has the dimensions to be the number of displays of the
    system. Each time a cell is sent to the sheet, it will bring that
    widget to the corresponding display (and make it fullscreen).
    
    """
    def __init__(self, tabWidget, col, row, columnCount, rowCount, displayWidth, displayHeight, fullScreenEnabled=True ):
        """ DisplayWallSheetTab(tabWidget: QTabWidget)
        Detecting the number of displays and their geometry and create
        a table with that dimensions

        """
        canFullScreen = False
        screenMap = {}
        if displayWidth<0 or displayHeight<0:
            canFullScreen = fullScreenEnabled
            desktop = QtGui.QDesktopWidget() 
            screenMap[(row, col)] = desktop.screenGeometry(0)
        else:
            screenMap[(row, col)] = QtCore.QRect( 0, 0, displayWidth, displayHeight )

        StandardWidgetSheetTab.__init__(self, tabWidget, 1, 1 )
        self.canFullScreen = canFullScreen
        self.screenMap = screenMap
        self.cellWidgets = {}
        self.setCellWidget( row, col, BlankWidget(self) )
        
    def setCellWidget(self, row, col, cellWidget):
        """ setCellWidget(row: int,
                          col: int,                            
                          cellWidget: QWidget) -> None                            
        Replace the current location (row, col) with a cell widget
        
        """
        print " DisplayWallSheetTab.setCellWidget: ( %d, %d ) " % ( row, col )
        if cellWidget:
            if self.cellWidgets.has_key((row, col)):
                oldCellWidget = self.cellWidgets[(row, col)]
                oldCellWidget.hide()
                oldCellWidget.deleteLater()
                self.cellWidgets[(row,col)] = None
            cellWidget.setParent(self)
            cellWidget.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)# | QtCore.Qt.WindowStaysOnTopHint)
            cellWidget.setGeometry(self.screenMap[(row,col)])
            if self.canFullScreen:
                cellWidget.showFullScreen()
            else:
                cellWidget.show()
            self.cellWidgets[(row,col)] = cellWidget
        else:
            self.setCellWidget(row, col, BlankWidget(self))

    def getCellWidget(self, row, col):
        """ getCellWidget(row: int, col: int) -> QWidget
        Get cell at a specific row and column.
        
        """
#        print " DisplayWallSheetTab.getCellWidget "
        if (row, col) in self.cellWidgets:
            return self.cellWidgets[(row, col)]
        return None

