###############################################################################
##
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: contact@vistrails.org
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################
""" The file describes the parameter tree view

QParameterView
"""
from PyQt4 import QtCore, QtGui
from core.inspector import PipelineInspector
from core.vistrail.module_param import ModuleParam
from gui.common_widgets import QSearchTreeWindow, QSearchTreeWidget
from gui.paramexplore.virtual_cell import QVirtualCellWindow
from gui.paramexplore.pe_pipeline import QAnnotatedPipelineView
from gui.vistrails_palette import QVistrailsPaletteInterface
import operator
from core.utils import InstanceObject

################################################################################

class ParameterInfo(InstanceObject):
    #     ParameterInfo(type=,
    #                   identifier=,
    #                   namespace=,
    #                   value=,
    #                   id=,
    #                   dbtype=,
    #                   parent_dbtype=,
    #                   parent_id=,
    #                   is_alias=)
    pass

################################################################################


class QParameterView(QSearchTreeWindow, QVistrailsPaletteInterface):
    """
    QParameterView is a special widget for displaying aliases and
    parameters inside a pipeline
    
    """
    def createTreeWidget(self):
        """ createTreeWidget() -> QModuleTreeWidget
        Return the search tree widget for this window
        
        """
        self.setWindowTitle('Set Methods')
        return QParameterTreeWidget(self)

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline
        self.treeWidget.updateFromPipeline(pipeline)

class QParameterTreeWidget(QSearchTreeWidget):
    """
    QParameterTreeWidget is a subclass of QSearchTreeWidget to display all
    Vistrails Module
    
    """
    def __init__(self, parent=None):
        """ QParameterTreeWidget(parent: QWidget) -> QParameterTreeWidget
        Set up size policy and header

        """
        QSearchTreeWidget.__init__(self, parent)
        self.header().hide()
        self.setRootIsDecorated(False)
        self.delegate = QParameterTreeWidgetItemDelegate(self, self)
        self.setItemDelegate(self.delegate)

    def updateFromPipeline(self, pipeline):
        """ updateFromPipeline(pipeline: Pipeline) -> None
        Read the list of aliases and parameters from the pipeline
        
        """
        self.clear()
        if not pipeline:
            return

        # Update the aliases
        if len(pipeline.aliases)>0:
            aliasRoot = QParameterTreeWidgetItem(None, self,
                                                 QtCore.QStringList('Aliases'))
            aliasRoot.setFlags(QtCore.Qt.ItemIsEnabled,
                               )
            for (alias, info) in pipeline.aliases.iteritems():
                ptype, pId, parentType, parentId, _ = info
                parameter = pipeline.db_get_object(ptype, pId)
                v = parameter.strValue
                aType = parameter.type
                aIdentifier = parameter.identifier
                aNamespace = parameter.namespace
                label = QtCore.QStringList('%s = %s' % (alias, v))
                pInfo = ParameterInfo(type=aType,
                                      identifier=aIdentifier,
                                      namespace=aNamespace,
                                      value=v,
                                      id=pId,
                                      dbtype=ptype,
                                      parent_dbtype=parentType,
                                      parent_id=parentId,
                                      is_alias=True)
                aliasItem = QParameterTreeWidgetItem((alias, [pInfo]),
                                                     aliasRoot, label)
            aliasRoot.setExpanded(True)
            
        # Now go through all modules and functions

        inspector = PipelineInspector()
        inspector.inspect_ambiguous_modules(pipeline)
        sortedModules = sorted(pipeline.modules.iteritems(),
                               key=lambda item: item[1].name)
        for mId, module in sortedModules:
            if len(module.functions)>0:
                mLabel = QtCore.QStringList(module.name)
                moduleItem = None
                for fId in xrange(len(module.functions)):
                    function = module.functions[fId]
                    if len(function.params)==0: continue
                    if moduleItem==None:
                        if inspector.annotated_modules.has_key(mId):
                            annotatedId = inspector.annotated_modules[mId]
                            moduleItem = QParameterTreeWidgetItem(annotatedId,
                                                                  self, mLabel)
                        else:
                            moduleItem = QParameterTreeWidgetItem(None,
                                                                  self, mLabel)
                    v = ', '.join([p.strValue for p in function.params])
                    label = QtCore.QStringList('%s(%s)' % (function.name, v))
                    
                    pList = [ParameterInfo(type=function.params[pId].type,
                                           identifier=function.params[pId].identifier,
                                           namespace=function.params[pId].namespace,
                                           value=function.params[pId].strValue,
                                           id=function.params[pId].real_id,
                                           dbtype=ModuleParam.vtType,
                                           parent_dbtype=function.vtType,
                                           parent_id=function.real_id,
                                           is_alias=False)
                             for pId in xrange(len(function.params))]
                    mName = module.name
                    if moduleItem.parameter!=None:
                        mName += '(%d)' % moduleItem.parameter
                    fName = '%s :: %s' % (mName, function.name)
                    mItem = QParameterTreeWidgetItem((fName, pList),
                                                     moduleItem,
                                                     label)
                if moduleItem:
                    moduleItem.setExpanded(True)
                    
            
            
class QParameterTreeWidgetItemDelegate(QtGui.QItemDelegate):
    """    
    QParameterTreeWidgetItemDelegate will override the original
    QTreeWidget paint function to draw buttons for top-level item
    similar to QtDesigner. This mimics
    Qt/tools/designer/src/lib/shared/sheet_delegate, which is only a
    private class from QtDesigned.
    
    """
    def __init__(self, view, parent):
        """ QParameterTreeWidgetItemDelegate(view: QTreeView,
                                          parent: QWidget)
                                          -> QParameterTreeWidgetItemDelegate
        Create the item delegate given the tree view
        
        """
        QtGui.QItemDelegate.__init__(self, parent)
        self.treeView = view

    def paint(self, painter, option, index):
        """ painter(painter: QPainter, option QStyleOptionViewItem,
                    index: QModelIndex) -> None
        Repaint the top-level item to have a button-look style
        
        """
        model = index.model()
        if model.parent(index).isValid()==False:
            style = self.treeView.style()
            r = option.rect
            textrect = QtCore.QRect(r.left() + 10,
                                    r.top(),
                                    r.width() - 10,
                                    r.height())
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            text = option.fontMetrics.elidedText(
                model.data(index, QtCore.Qt.DisplayRole).toString(),
                QtCore.Qt.ElideMiddle, 
                textrect.width()-10)
            style.drawItemText(painter,
                               textrect,
                               QtCore.Qt.AlignLeft,
                               option.palette,
                               self.treeView.isEnabled(),
                               text)
            painter.setPen(QtGui.QPen(QtCore.Qt.black))
            fm = QtGui.QFontMetrics(font)
            size = fm.size(QtCore.Qt.TextSingleLine, text)
            painter.drawLine(textrect.left()-5,
                             textrect.bottom()-1,
                             textrect.left()+size.width()+5,
                             textrect.bottom()-1)

            annotatedId = model.data(index, QtCore.Qt.UserRole+1)            
            if annotatedId.isValid():
                idRect = QtCore.QRect(
                    QtCore.QPoint(textrect.left()+size.width()+5,
                                  textrect.top()),
                    textrect.bottomRight())
                QAnnotatedPipelineView.drawId(painter, idRect,
                                              annotatedId.toInt()[0],
                                              QtCore.Qt.AlignLeft |
                                              QtCore.Qt.AlignVCenter)
        else:
            QtGui.QItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        """ sizeHint(option: QStyleOptionViewItem, index: QModelIndex) -> None
        Take into account the size of the top-level button
        
        """
        return (QtGui.QItemDelegate.sizeHint(self, option, index) +
                QtCore.QSize(2, 2))
            

class QParameterTreeWidgetItem(QtGui.QTreeWidgetItem):
    """
    QParameterTreeWidgetItem represents module on QParameterTreeWidget
    
    """
    def __init__(self, info, parent, labelList):
        """ QParameterTreeWidgetItem(info: (str, []),
                                     parent: QTreeWidgetItem
                                     labelList: QStringList)
                                     -> QParameterTreeWidget
                                     
        Create a new tree widget item with a specific parent and
        labels. info describing a set of paramters as follow:
        (name, [ParameterInfo]):
           name  = Name of the parameter set (alias or function)
        If this item is a top-level item, info can either be None or
        an integer specifying the annotated id of this module

        """
        self.parameter = info
        QtGui.QTreeWidgetItem.__init__(self, parent, labelList)
        if type(self.parameter)==int:
            self.setData(0, QtCore.Qt.UserRole+1,
                         QtCore.QVariant(self.parameter))
