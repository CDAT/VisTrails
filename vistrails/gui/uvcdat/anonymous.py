import cdat_info, os
from PyQt4 import QtGui,QtCore
class QAnonymousMessageBox(QtGui.QDialog):
    def __init__(self,parent=None):
        QtGui.QDialog.__init__(self,parent)
        #self.setText("Do you want to allow UV-CDAT to collect anonymous usage information?")
        self.setModal(QtCore.Qt.ApplicationModal)
        self.setWindowTitle("Anonymous Usage")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.WindowTitleHint)
        V=QtGui.QVBoxLayout()
        l=QtGui.QLabel("do you want to allow UV-CDAT to collect anonymous usage informations?")
        V.addWidget(l)
        H=QtGui.QHBoxLayout()
        y = QtGui.QPushButton("Yes")
        n = QtGui.QPushButton("No")
        H.addWidget(y)
        H.addWidget(n)
        V.addLayout(H)
        self.setLayout(V)
        self.setVisible(True)
        self.connect(y,QtCore.SIGNAL("clicked()"),self.yes)
        self.connect(n,QtCore.SIGNAL("clicked()"),self.no)
    def yes(self,*args):
        cdat_info.ping = True
        self.storeAnonymous()
    def no(self,*args):
        cdat_info.ping = False
        self.storeAnonymous()
    def storeAnonymous(self):
        fanom = os.path.join(os.environ["HOME"],"PCMDI_GRAPHICS",".anonymouslog")
        try:
            f=open(fanom,"w")
            print >>f, "#Store information about allowing UVCDAT anonymous logging"
            print >>f, "# Need sto be True or False"
            print >>f, "UVCDAT_ANONYMOUS_LOG: %s" % cdat_info.ping
            f.close()
        except Exception,err:
            print err
            pass
        cdat_info.ping_checked = True
        self.close()


def check():
    if hasattr(cdat_info,"ping_checked") and cdat_info.ping_checked is False:
        val = cdat_info.runCheck()
        if not val in [True,False]:
            d = QAnonymousMessageBox()
            d.show()
            d.raise_()
            d.exec_()
