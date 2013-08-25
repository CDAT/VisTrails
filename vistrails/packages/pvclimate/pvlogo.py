import sys

from core import system

splashPath = (system.vistrails_root_directory() +
                          "/gui/uvcdat/resources/images/splash.png")


from PyQt4.QtCore import Qt
from PyQt4.QtGui import *

class PVLogo(QWidget):
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.image = QImage()
        logoPath = (system.vistrails_root_directory() +
                    "/gui/uvcdat/resources/images/splash.png")
        self.image.load(logoPath)
        self.image = self.image.scaledToWidth(100)
 
    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(0, 0, self.image)
        painter.end()
 
 
#class MainWindow(QMainWindow):
# 
#    def __init__(self, parent = None):
# 
#        QMainWindow.__init__(self, parent)
# 
#        widget = QWidget(self)
#        self.editor = QTextEdit()
#        layout = QGridLayout(widget)
#        layout.addWidget(self.editor, 0, 0, 1, 2)
#        layout.addWidget(QPushButton("Refresh"), 1, 0)
#        layout.addWidget(QPushButton("Cancel"), 1, 1)
# 
#        self.setCentralWidget(widget)
#        self.overlay = PVLogo(self.centralWidget())
# 
#    def resizeEvent(self, event):
# 
#        self.overlay.resize(event.size())
#        event.accept()
# 
# 
#if __name__ == "__main__":
# 
#    app = QApplication(sys.argv)
#    window = MainWindow()
#    window.show()
#    sys.exit(app.exec_())
