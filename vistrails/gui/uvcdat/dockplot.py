from PyQt4 import QtCore, QtGui
import platform
from uvcdatCommons import plotTypes
from core.uvcdat.plot_registry import get_plot_registry
import graphicsMethodsWidgets

class DockPlot(QtGui.QDockWidget):
    PANEL_ITEM = 0
    VCS_CONTAINER_ITEM = 1
    VCS_ITEM = 2
    CUSTOM_CONTAINER_ITEM = 3
    CUSTOM_ITEM = 4 
    def __init__(self, parent=None):
        super(DockPlot, self).__init__(parent)
        ## self.ui = Ui_DockPlot()
        ## self.ui.setupUi(self)
        self.root=parent.root
        self.setWindowTitle("Plots and Analyses")
        self.plot_bars = {}
        self.plotTree = PlotTreeWidget(self)
        self.setWidget(self.plotTree)
        ## layout = QtGui.QVBoxLayout()
        ## layout.setMargin(0)
        ## layout.setSpacing(0)
        ## layout.addWidget(self.plotTree)
        ## self.ui.mainWidget.setLayout(layout)
        #self.initVCSTree()
        
    def initVCSTree(self):
        for k in sorted(plotTypes.keys()):
            kitem = self.addPlotBar(k)
            for plot in plotTypes[k]:
                item = QtGui.QTreeWidgetItem(kitem, 
                                             QtCore.QStringList(plot),
                                             self.VCS_CONTAINER_ITEM)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsDragEnabled)
                ## Special section here for VCS GMs they have one more layer
                for m in self.plotTree.getMethods(item):
                    item2 = PlotTreeWidgetItem(plot, m, QtCore.QStringList(m),
                                               self.VCS_ITEM, None, item)
        
    def addPlotBar(self, plot_package_name):
        if plot_package_name not in self.plot_bars:
            item = QtGui.QTreeWidgetItem(None, QtCore.QStringList(plot_package_name),
                                          self.PANEL_ITEM)
            item.setFlags(item.flags() &~QtCore.Qt.ItemIsDragEnabled)
            self.plot_bars[plot_package_name] = item
            self.plotTree.addTopLevelItem(item)
            return item
        else:
            return self.plot_bars[plot_package_name]
          
    def addCustomPlotType(self, panel_type, plot_type, plot=None, parent_item=None):
        if parent_item is None:
            parent_item = self.plot_bars[panel_type] 
        item = PlotTreeWidgetItem(plot_type, None, QtCore.QStringList(plot_type),
                                  self.CUSTOM_ITEM, plot, parent_item)
        return item
        
    def newPlotType(self, plot):
        self.addCustomPlotType(plot.package, plot.name, plot)
        
    def link_registry(self):
        self.update_from_plot_registry()
        self.connect_registry_signals()
        
    def update_from_plot_registry(self):
        """ update_from_plot_registry() -> None
        Setup this tree widget to show modules currently inside plot registry
                
        """
        self.plotTree.setSortingEnabled(False)
        registry = get_plot_registry()
        for plot_package in registry.plots:
            baritem = self.addPlotBar(plot_package)
            if plot_package == "VCS":
                for plottype in registry.plots[plot_package]:
                    item = QtGui.QTreeWidgetItem(baritem, 
                                                 QtCore.QStringList(plottype),
                                                 self.VCS_CONTAINER_ITEM)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsDragEnabled)
                    ## Special section here for VCS GMs they have one more layer
                    for plot in registry.plots[plot_package][plottype].itervalues():
                        item2 = PlotTreeWidgetItem(plottype, plot.name, 
                                                   QtCore.QStringList(plot.name),
                                                   self.VCS_ITEM, plot, item)
            else:
                for plot in registry.plots[plot_package].itervalues():
                    self.addCustomPlotType(plot_package, plot.name, plot)
        
        self.plotTree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.plotTree.setSortingEnabled(True)
        
    def connect_registry_signals(self):
        registry = get_plot_registry()
        self.connect(registry.signals, registry.signals.new_plot_package_signal,
                     self.addPlotBar)
        self.connect(registry.signals, registry.signals.new_plot_type_signal,
                     self.newPlotType)
        
class PlotTreeWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        super(PlotTreeWidget, self).__init__(parent)
        self.header().hide()
        self.root=parent.root
        self.setRootIsDecorated(False)
        self.delegate = PlotTreeWidgetItemDelegate(self, self)
        self.setItemDelegate(self.delegate)
        self.setDragEnabled(True)
        self.flags = QtCore.Qt.ItemIsDragEnabled
        self.setAcceptDrops(False)
        self.connect(self,
                     QtCore.SIGNAL('itemPressed(QTreeWidgetItem *,int)'),
                     self.onItemPressed)

        self.connect(self,
                     QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *,int)'),
                     self.popupEditor)

        
    def mimeData(self, itemList):
        """ mimeData(itemList) -> None        
        Setup the mime data to contain itemList because Qt 4.2.2
        implementation doesn't instantiate QTreeWidgetMimeData
        anywhere as it's supposed to. It must have been a bug...
        
        """
        data = QtGui.QTreeWidget.mimeData(self, itemList)
        a = QtCore.QByteArray()
        a.append(self.currentItem().text(0))
        data.setData("plotType", a)
        data.items = itemList
        return data
            
    def onItemPressed(self, item, column):
        """ onItemPressed(item: QTreeWidgetItem, column: int) -> None
        Expand/Collapse top-level item when the mouse is pressed
        
        """
        if item and item.parent() == None:
            self.setItemExpanded(item, not self.isItemExpanded(item))
        
    def getMethods(self,item):
        plotType = item.text(0)
        analyser = item.parent().text(0)
        if analyser == "VCS":
            return self.root.canvas[0].listelements(str(plotType).lower())
        else:
            return ["default",]
        
    def popupEditor(self,item,column):
        if item.type()!= DockPlot.VCS_ITEM:
            return
        name = item.text(0)
        plotType = item.parent().text(0)
        analyser = item.parent().parent().text(0)
        editorDock = QtGui.QDockWidget(self.root)
        editorDock.setWindowTitle("%s-%s-%s Graphics Method Editor" % (analyser,plotType,name))
        ## self.root.addDockWidget(QtCore.Qt.LeftDockWidgetArea,editorDock)
        save=QtGui.QPushButton("Save")
        cancel=QtGui.QPushButton("Cancel")
        w = QtGui.QFrame()
        v=QtGui.QVBoxLayout()
        h=QtGui.QHBoxLayout()
        h.addWidget(save)
        h.addWidget(cancel)
        if analyser == "VCS":
            w.editor=QtGui.QTabWidget()
            w.editor.root=self.root
            v.addWidget(w.editor)
            if editorDock.widget() is not None:
                editorDock.widget().destroy()
            if plotType == "Boxfill":
                widget = graphicsMethodsWidgets.QBoxfillEditor(w.editor,gm = str(name))
            elif plotType == "Isofill":
                widget = graphicsMethodsWidgets.QIsofillEditor(w.editor,gm = str(name))
            elif plotType == "Isoline":
                widget = graphicsMethodsWidgets.QIsolineEditor(w.editor,gm = str(name))
            elif plotType == "Meshfill":
                widget = graphicsMethodsWidgets.QMeshfillEditor(w.editor,gm = str(name))
            elif plotType == "Outfill":
                widget = graphicsMethodsWidgets.QOutfillEditor(w.editor,gm = str(name))
            elif plotType == "Outline":
                widget = graphicsMethodsWidgets.QOutlineEditor(w.editor,gm = str(name))
            elif plotType == "Scatter":
                widget = graphicsMethodsWidgets.QScatterEditor(w.editor,gm = str(name))
            elif plotType == "Taylordiagram":
                widget = graphicsMethodsWidgets.QTaylorDiagramEditor(w.editor,gm = str(name))
            elif plotType == "Vector":
                widget = graphicsMethodsWidgets.QVectorEditor(w.editor,gm = str(name))
            elif plotType == "XvsY":
                widget = graphicsMethodsWidgets.Q1DPlotEditor(w.editor,gm = str(name), type="xvsy")
            elif plotType == "Xyvsy":
                widget = graphicsMethodsWidgets.Q1DPlotEditor(w.editor,gm = str(name), type="xyvsy")
            elif plotType == "Yxvsx":
                widget = graphicsMethodsWidgets.Q1DPlotEditor(w.editor,gm = str(name), type="yxvsx")
            else:
                print "UNKWON TYPE:",plotType
            w.editor.insertTab(0,widget,"Properties")
            w.editor.setCurrentIndex(0)
            if str(name) == "default":
                widget.setEnabled(False)
                try:
                    w.editor.widget(1).widget().setEnabled(False)
                except:
                    pass
            ## Connect Button
            save.clicked.connect(widget.applyChanges)
            cancel.clicked.connect(editorDock.close)
        else:
            print "Put code to popup",analyser,"editor"
            v.addWidget(QtGui.QLabel("Maybe one day?"))
            save.clicked.connect(editorDock.close)
            cancel.clicked.connect(editorDock.close)
        v.addLayout(h)
        w.setLayout(v)
        editorDock.setWidget(w)
        editorDock.setFloating(True)
        editorDock.show()
        
class PlotTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, plot_type, gm, labels, type, plot_obj=None, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent, labels, type)
        self.plot = plot_obj
        self.plot_type = plot_type
        self.gm = gm
                
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
