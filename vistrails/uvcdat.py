from PyQt4 import QtGui
#PATH_TO_VISTRAILS_DIR = '/Users/emanuele/src/cdat/git/cmake/source/vistrails/vistrails'
import sys
#sys.path.append(PATH_TO_VISTRAILS_DIR)

from uvcdat.gui.mainwindow import UVCDATMainWindow

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    mainWin = UVCDATMainWindow()
    mainWin.show()
    sys.exit(app.exec_())