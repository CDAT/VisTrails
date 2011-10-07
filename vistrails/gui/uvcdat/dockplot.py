from PyQt4 import QtCore, QtGui
import platform
from qtbrowser.vcdatCommons import plotTypes, gmInfos
from gui.uvcdat.ui_dockplot import Ui_DockPlot

class DockPlot(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockPlot, self).__init__(parent)
        self.ui = Ui_DockPlot()
        self.ui.setupUi(self)
        self.plotTree = PlotTreeWidget(self.ui.mainWidget)
        layout = QtGui.QVBoxLayout()
        layout.setMargin(0)
        layout.setSpacing(0)
        layout.addWidget(self.plotTree)
        self.ui.mainWidget.setLayout(layout)
        self.initTree()
        
    def initTree(self):
        customPlots = ['ParaView Simple Plot',
                       'Volume Rendering',
                       'DV3D Volume Isosurfacing',
                       'DV3D Volume Rendering',
                       'DV3D Volume Slicer']
        self.cdat_item = QtGui.QTreeWidgetItem(None, QtCore.QStringList('CDAT'))
        self.custom_item = QtGui.QTreeWidgetItem(None, QtCore.QStringList('Custom Widgets'))
        self.plotTree.addTopLevelItem(self.cdat_item)
        self.plotTree.addTopLevelItem(self.custom_item)
        for plot in plotTypes:
            item = QtGui.QTreeWidgetItem(self.cdat_item, QtCore.QStringList(plot))
        for plot in customPlots:
            item = QtGui.QTreeWidgetItem(self.custom_item, QtCore.QStringList(plot))
        self.plotTree.expandAll()

class PlotTreeWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        super(PlotTreeWidget, self).__init__(parent)
        self.header().hide()
        self.setRootIsDecorated(False)
        self.delegate = PlotTreeWidgetItemDelegate(self, self)
        self.setItemDelegate(self.delegate)
        self.connect(self,
                     QtCore.SIGNAL('itemPressed(QTreeWidgetItem *,int)'),
                     self.onItemPressed)

    def onItemPressed(self, item, column):
        """ onItemPressed(item: QTreeWidgetItem, column: int) -> None
        Expand/Collapse top-level item when the mouse is pressed
        
        """
        if item and item.parent() == None:
            self.setItemExpanded(item, not self.isItemExpanded(item))
        
        
class PlotTreeWidgetItemDelegate(QtGui.QItemDelegate):
    def __init__(self, view, parent):
        """ QModuleTreeWidgetItemDelegate(view: QTreeView,
                                          parent: QWidget)
                                          -> QModuleTreeWidgetItemDelegate
        Create the item delegate given the tree view
        
        """
        QtGui.QItemDelegate.__init__(self, parent)
        self.treeView = view
        self.isMac = platform.system() in ['Darwin']

    def paint(self, painter, option, index):
        """ painter(painter: QPainter, option QStyleOptionViewItem,
                    index: QModelIndex) -> None
        Repaint the top-level item to have a button-look style
        
        """
        model = index.model()
        if not model.parent(index).isValid():
            buttonOption = QtGui.QStyleOptionButton()            
            buttonOption.state = option.state
            if self.isMac:
                buttonOption.state |= QtGui.QStyle.State_Raised
            buttonOption.state &= ~QtGui.QStyle.State_HasFocus

            buttonOption.rect = option.rect
            buttonOption.palette = option.palette
            buttonOption.features = QtGui.QStyleOptionButton.None

            style = self.treeView.style()
            
            style.drawControl(QtGui.QStyle.CE_PushButton,
                              buttonOption,
                              painter,
                              self.treeView)

            branchOption = QtGui.QStyleOption()
            i = 9 ### hardcoded in qcommonstyle.cpp
            r = option.rect
            branchOption.rect = QtCore.QRect(r.left() + i / 2,
                                             r.top() + (r.height() - i) / 2,
                                             i, i)
            branchOption.palette = option.palette
            branchOption.state = QtGui.QStyle.State_Children

            if self.treeView.isExpanded(index):
                branchOption.state |= QtGui.QStyle.State_Open
                
            style.drawPrimitive(QtGui.QStyle.PE_IndicatorBranch,
                                branchOption,
                                painter, self.treeView)

            textrect = QtCore.QRect(r.left() + i * 2,
                                    r.top(),
                                    r.width() - ((5 * i) / 2),
                                    r.height())
            text = option.fontMetrics.elidedText(
                model.data(index,
                           QtCore.Qt.DisplayRole).toString(),
                QtCore.Qt.ElideMiddle,
                textrect.width())
            style.drawItemText(painter,
                               textrect,
                               QtCore.Qt.AlignCenter,
                               option.palette,
                               self.treeView.isEnabled(),
                               text)
        else:
            QtGui.QItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        """ sizeHint(option: QStyleOptionViewItem, index: QModelIndex) -> None
        Take into account the size of the top-level button
        
        """
        return (QtGui.QItemDelegate.sizeHint(self, option, index) + 
                QtCore.QSize(2, 2))
