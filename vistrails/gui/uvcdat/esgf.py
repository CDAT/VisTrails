###############################################################################
#                                                                             #
# Authors:      PCMDI Software Team                                           #
#               Lawrence Livermore National Laboratory:                       #
#                                                                             #
###############################################################################
from PyQt4 import QtCore, QtGui
import cdms2
import uvcdatCommons
import customizeUVCDAT
import os
#import bz2
import xml
import myproxy_logon
import subprocess
import time
from gui.uvcdat.cdmsCache import CdmsCache
from gui.common_widgets import QDockPushButton

"""
class QEsgfGateway(cdms2.esgfConnection):
    def __init__(self,gateway = customizeUVCDAT.defaultEsgfNode,port=80,limit=10,offset=0,mapping=None,datasetids=None,fileids=None):
        cdms2.esgfConnection.__init__(self,gateway,port,limit,offset,mapping,datasetids,fileids)                
"""

if hasattr( cdms2, "esgfDataset" ):
    class QEsgfGateway(cdms2.esgfDataset):
        def __init__(self,gateway = customizeUVCDAT.defaultEsgfNode,port=80,limit=10,offset=0,mapping=None,datasetids=None,fileids=None):
            cdms2.esgfDataset.__init__(self,gateway,port,limit,offset,mapping,datasetids,fileids)                

class QEsgfIndex(QtGui.QListWidget):
    def __init__(self,parent=None):
        QtGui.QListWidget.__init__(self,parent)
        self.parent=parent
            
    def addIndex(self,text):
        self.addItem(text)
        
    def clean(self,index=None):
        if index is None:
            for i in self.count():
                self.removeItemWidget(self.item(0))
                self.parent.index.pop(0)
        else:
            self.removeItemWidget(self.item(index))
            self.parent.index.pop(index)

class QDownloadProgressBar(QtGui.QWidget):
    def __init__(self,parent=None,url="",target="",pipe=None):
        QtGui.QWidget.__init__(self,parent)
        hbox=QtGui.QHBoxLayout()
        self.setLayout(hbox)
        self.pipe=pipe
        b=QtGui.QPushButton("Cancel")
        hbox.addWidget(b)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.cancel)
        lbl=QtGui.QLabel(target.split("/")[-1])
        hbox.addWidget(lbl)
        self.p=QtGui.QProgressBar()
        self.p.setRange(0,100)
        self.p.setValue(0)
        self.setFont(QtGui.QFont("Courier"))
        hbox.addWidget(self.p)
        self.time=QtGui.QLabel("0%")
        hbox.addWidget(self.time)
        self.line=""
        self.done=0
        self.tmaxchars=0
        self.lmaxchars=0
        self.isCanceled=False
    def cancel(self):
        self.isCanceled=True
        self.pipe.terminate()
        self.time.setText("Canceled")
    def update(self):
        if self.isCanceled:
            self.p.setValue(100)
            self.time.setText("Canceled")
            return
        char = self.pipe.stderr.read(1)
        if char == "\n":
            try:
                self.done = int(self.line.split("%")[0].split()[-1])
                self.p.setValue(self.done)
                t = self.line.split()
                if len(t)!=0:
                    t=t[-1]
                    if len(t)>self.tmaxchars:
                        self.tmaxchars=len(t)
                    t=t.rjust(self.tmaxchars)
                    lbl = "%i%% Done, Estimated Time Left: " % (self.done)
                    if len(lbl)>self.lmaxchars:
                        self.lmaxchars=len(lbl)
                    lbl=lbl.ljust(self.lmaxchars)
                    lbl+=t
                    self.time.setText(lbl)

            except Exception,err:
                pass
            self.line=""
            QtGui.QApplication.processEvents()
        else:
            self.line+=char
        
class QMultiDownloadProgressBar(QtGui.QDialog):
    def __init__(self,parent=None):
        QtGui.QDialog.__init__(self,parent)
        pol = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed)
        self.setWindowModality(QtCore.Qt.NonModal)
        vbox=QtGui.QVBoxLayout()
        self.setLayout(vbox)
        self.lbl = QtGui.QLabel("Downloading")
        vbox.addWidget(self.lbl)
        b=QtGui.QPushButton("Cancel ALL")
        vbox.addWidget(b)
        scrollArea = QtGui.QScrollArea()
        scrollArea.setWidgetResizable(True)
        vbox.addWidget(scrollArea)
        f=QtGui.QFrame()
        self.downloads=QtGui.QVBoxLayout()
        f.setLayout(self.downloads)
        scrollArea.setWidget(f)
        self.connect(b,QtCore.SIGNAL("clicked()"),self.cancel)
        self.connect(self,QtCore.SIGNAL("finished(int)"),self.cancel)
    def addDownload(self,url,target,pipe):
        self.downloads.addWidget(QDownloadProgressBar(parent=self,url=url,target=target,pipe=pipe))
    def cancel(self):
        N =self.downloads.count()
        for i in range(N):
            w = self.downloads.itemAt(i).widget() # Gets us the DownloadProgressBar
            w.cancel()

    def exec_(self):
        self.show()
        N =self.downloads.count()
        count=1
        j=0
        while count!=0:
            count=0
            for i in range(N):
                w = self.downloads.itemAt(i).widget() # Gets us the DownloadProgressBar
                w.update()
                if w.pipe.poll() is None:
                    count+=1
            j+=1
            self.lbl.setText("Downloading: %i Files (%i left)" % (N,count))
        #self.hide()

        
class QEsgfCredentials(QtGui.QDialog):
    def __init__(self,parent=None):
        QtGui.QDialog.__init__(self,parent)
        pol = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed)
        vbox=QtGui.QVBoxLayout()
        self.setLayout(vbox)

        lbl = QtGui.QLabel("Please enter your credentials for OpenId on ESGF")
        vbox.addWidget(lbl)
        self.host = uvcdatCommons.QLabeledWidgetContainer(QtGui.QLineEdit(),label="OpenID URL:",widgetSizePolicy=pol,labelSizePolicy=pol)
        self.parent=parent
        self.host.widget.setText("pcmdi9.llnl.gov")
        self.port = uvcdatCommons.QLabeledWidgetContainer(QtGui.QLineEdit(),label="Port:",widgetSizePolicy=pol,labelSizePolicy=pol)
        self.port.widget.setText("7512")
        self.user = uvcdatCommons.QLabeledWidgetContainer(QtGui.QLineEdit(),label="User:",widgetSizePolicy=pol,labelSizePolicy=pol)
        self.user.widget.setText(os.environ.get("USER",""))
        self.password = uvcdatCommons.QLabeledWidgetContainer(QtGui.QLineEdit(),label="Password:",widgetSizePolicy=pol,labelSizePolicy=pol)
        self.password.widget.setEchoMode(QtGui.QLineEdit.Password)
        self.lifetime = uvcdatCommons.QLabeledWidgetContainer(QtGui.QLineEdit(),label="Lifetime:",widgetSizePolicy=pol,labelSizePolicy=pol)
        self.lifetime.widget.setText("43200")
        vbox.addWidget(self.host)
        vbox.addWidget(self.port)
        vbox.addWidget(self.user)
        vbox.addWidget(self.password)

        h=QtGui.QHBoxLayout()
        vbox.addLayout(h)
        ok = QtGui.QPushButton("Ok")
        h.addWidget(ok)
        cancel = QtGui.QPushButton("Cancel")
        h.addWidget(cancel)
        self.connect(cancel,QtCore.SIGNAL("clicked()"),self.hide)
        self.connect(ok,QtCore.SIGNAL("clicked()"),self.acquireCredentials)
        self.cert_file=None
        self.key_file=None
        try:
            f=open(os.path.join(os.environ["HOME"],".dodsrc"))
            for l in f.xreadlines():
                if l[:20]=="CURL.SSL.CERTIFICATE":
                    self.cert_file == l.split("=")[1].strip()
                if l[:12]=="CURL.SSL.KEY":
                    self.key_file == l.split("=")[1].strip()
            f.close()
        except:
            try:
                dodsrc_cache_root=os.path.join(os.environ["HOME"],".dods_cache")
                dodsrc_curl_ssl_certificate=os.path.join(os.environ["HOME"],".esg","credentials.pem")
                dodsrc_curl_ssl_key=os.path.join(os.environ["HOME"],".esg","credentials.pem")
                dodsrc_curl_ssl_capath=os.path.join(os.environ["HOME"],".esg","certificates")
                dodsrc_text=""
                dodsrc_text+="USE_CACHE=0\n"
                dodsrc_text+="MAX_CACHE_SIZE=20\n"
                dodsrc_text+="MAX_CACHED_OBJ=5\n"
                dodsrc_text+="IGNORE_EXPIRES=0\n"
                dodsrc_text+="CACHE_ROOT=%s/\n"%dodsrc_cache_root
                dodsrc_text+="DEFAULT_EXPIRES=86400\n"
                dodsrc_text+="ALWAYS_VALIDATE=0\n"
                dodsrc_text+="DEFLATE=0\n"
                dodsrc_text+="VALIDATE_SSL=1\n"
                dodsrc_text+="CURL.COOKIEJAR=.dods_cookies\n"
                dodsrc_text+="CURL.SSL.VALIDATE=1\n"
                dodsrc_text+="CURL.SSL.CERTIFICATE=%s\n"%dodsrc_curl_ssl_certificate
                dodsrc_text+="CURL.SSL.KEY=%s\n"%dodsrc_curl_ssl_key
                dodsrc_text+="CURL.SSL.CAPATH=%s\n"%dodsrc_curl_ssl_capath
                
                f=open(os.path.join(os.environ["HOME"],".dodsrc"),'w')
                f.write(dodsrc_text)
                f.close()
            except Exception, err:
                m = QtGui.QMessageBox()
                m.setText(str(err))
                m.exec_()

        if self.cert_file is None:
            self.cert_file=os.path.join(os.environ["HOME"],".esg","credentials.pem")
        if self.key_file is None:
            self.key_file=os.path.join(os.environ["HOME"],".esg","credentials.pem")

    def acquireCredentials(self):
        try:
            username= str(self.user.widget.text())
            host= str(self.host.widget.text())
            host=host.split("://")[-1]
            port = int(str(self.port.widget.text()))
            passphrase=str(self.password.widget.text())
            lifetime=int(str(self.lifetime.widget.text()))
            cert_path=os.path.dirname(self.cert_file)
            if not os.path.exists(cert_path):
                try:
                    os.makedirs(cert_path)
                except:
                    pass
                
            myproxy_logon.myproxy_logon(host,username,passphrase,self.cert_file,lifetime=lifetime,port=port)
            
            if self.key_file!=self.cert_file:
                key_path=os.path.dirname(self.key_file)
                
                if not os.path.exists(key_path):
                    try:
                        os.makedirs(key_path)
                    except:
                        pass
                myproxy_logon.myproxy_logon(host,username,passphrase,self.key_file,lifetime=lifetime,port=port)
                
            self.hide()
        except Exception,err:
            m = QtGui.QMessageBox()
            m.setText(str(err))
            m.exec_()
            
class QFacetTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self,text,parent=None,datalist=None):
        QtGui.QTreeWidgetItem.__init__(self,parent)
        self.parent=parent
        self.text=text
        self.datalist=datalist

    def text_to_key(self):
        return self.parent.remake_facet_name(self.text)

    def update_facet_selection(self):
        self.parent.update_facet_selection(self.text_to_key())
 
class QScrollArea2(QtGui.QScrollArea):
    def __init(self,parent=None):
        QtGui.QScrollArea.__init__(self,parent)

    def resizeEvent(*args):
        args[0].F1.setMinimumWidth(args[0].size().width())
        args[0].F1.setMaximumWidth(args[0].size().width())
        args[0].F1.setMinimumHeight(args[0].size().height())
        args[0].F1.setMaximumHeight(args[0].size().height())
        QtGui.QScrollArea.resizeEvent(*args)

class QEsgfBrowser(QtGui.QFrame):
    def __init__(self,parent=None,mapping=None):
        QtGui.QFrame.__init__(self,parent)
        pol = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed)
        ## Decorations
        self.opendapIcon = QtGui.QIcon(customizeUVCDAT.esgfOpenDapIcon)
        self.foldersIcon = QtGui.QIcon(customizeUVCDAT.esgfFolderIcon)
        self.lasIcon = QtGui.QIcon(customizeUVCDAT.esgfLasIcon)
        self.gridftpIcon = QtGui.QIcon(customizeUVCDAT.esgfGridFtpIcon)
        self.httpIcon = QtGui.QIcon(customizeUVCDAT.esgfHttpIcon)
        self.unknownIcon = QtGui.QIcon(customizeUVCDAT.esgfUnknownIcon)
        self.fileIcon = QtGui.QIcon(customizeUVCDAT.esgfFileIcon)
        self.searchIcon = QtGui.QIcon(customizeUVCDAT.esgfSearchIcon)
        self.loginIcon = QtGui.QIcon(customizeUVCDAT.esgfLoginIcon)

        vbox=QtGui.QVBoxLayout()
        self.mapping=mapping
        self.setLayout(vbox)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding) 
        self.toolBar = QtGui.QToolBar()
        try:
            self.root=parent.root
        except:
            self.root=None
        self.toolBar.setIconSize(QtCore.QSize(customizeUVCDAT.iconsize, customizeUVCDAT.iconsize))
        actionInfo = [
            #(self.searchIcon, 'Run Search',self.clickedSearch,True),
            #(':/icons/resources/icons/db_add_256.ico', 'Add Gateway',self.userAddsGateway,True),
            (':/icons/resources/icons/binary-tree-icon.png', 'Edit Mapping',self.editMapping,True),
            (':/icons/resources/icons/floppy_disk_blue.ico', 'Save cache',self.userSaveCache,True),
            (':/icons/resources/icons/login.ico', 'Get Credentials',self.clickedCredentials,True),
            ]
        for info in actionInfo:
            if isinstance(info[0],str):
                icon = QtGui.QIcon(info[0])
            else:
                icon=info[0]
            action = self.toolBar.addAction(icon, 'help')
            action.setToolTip(info[1])
            self.connect(action,QtCore.SIGNAL("triggered()"),info[2])
            action.setEnabled(info[3])

        self.credentials=QEsgfCredentials(parent=self)
        self.credentials.hide()
        
        vbox.addWidget(self.toolBar)
        
        self.facet_search_btn=QDockPushButton("Search",self)
        self.facet_search_btn.setStyleSheet("background-color:lightblue")
        self.facet_search_btn.setMaximumHeight(100)
        self.facet_search_btn.setMaximumWidth(200)
        self.facet_search_btn.setSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Maximum)
        self.facet_search_btn.connect(self.facet_search_btn,QtCore.SIGNAL("clicked(bool)"),self.facet_search_button_pressed)

        search_example_string="Enter your search terms (examples: temperature, \"surface temperature\", climate AND project:CMIP5 AND variable:hus)."
        self.searchLine=QtGui.QLineEdit()
        self.searchLine.setText("")
        self.connect(self.searchLine,QtCore.SIGNAL("returnPressed()"),self.entered_search_line)
        self.searchLine.setToolTip(search_example_string)
        self.searchLine.setStyleSheet("font-size:16px")
        self.searchLine.setMinimumHeight(30)
        search_groupbox=QtGui.QGroupBox("Text Search")
        text_search_vbox=QtGui.QVBoxLayout()
        text_search_vbox.addWidget(self.searchLine)
        search_groupbox.setToolTip(search_example_string)
        search_groupbox.setLayout(text_search_vbox)
        
        #vbox.addWidget(search_groupbox) 
        frame1=QtGui.QFrame()
        frame1_hbox=QtGui.QHBoxLayout()
        #frame1_hbox.addWidget(self.facet_search_btn)
        frame1_hbox.addWidget(search_groupbox)
        frame1.setLayout(frame1_hbox)
        vbox.addWidget(frame1)

        #faceth=QtGui.QHBoxLayout()
        #l=QtGui.QLabel("Current Selection(s):")
        #l.setSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        #faceth.addWidget(l)
        #self.selected_facet_combobox=QtGui.QComboBox()
        #self.selected_facet_combobox.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Fixed)
        #faceth.addWidget(self.selected_facet_combobox)

        self.facet_obj=cdms2.FacetConnection(host=str(self.root.preferences.host_url.currentText()))
        facet_xmlelement=self.facet_obj.get_xmlelement("replica=false")
        self.facet_dict_of_dict={}
        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        self.data_nodelist=self.get_data_nodelist()

        search_frame = QtGui.QFrame()
        search_option_layout=QtGui.QHBoxLayout()
        search_frame.setMaximumHeight(200)
        search_frame.setLayout(search_option_layout)
        
        current_selection_layout=QtGui.QVBoxLayout()
        current_selection_groupbox=QtGui.QGroupBox("Current Selection(s)")
        current_selection_btn_layout=QtGui.QHBoxLayout()
        self.current_selection_btn=QtGui.QPushButton("Hide",self)
        self.current_selection_remove_btn=QtGui.QPushButton("Remove",self)
        self.current_selection_removeAll_btn=QtGui.QPushButton("Reset",self)
        current_selection_btn_layout.addWidget(self.current_selection_btn)
        current_selection_btn_layout.addWidget(self.current_selection_remove_btn)
        current_selection_btn_layout.addWidget(self.current_selection_removeAll_btn)
        self.current_selection_btn.connect(self.current_selection_btn,QtCore.SIGNAL("clicked(bool)"),self.display_current_selection_button_pressed)
        self.current_selection_remove_btn.connect(self.current_selection_remove_btn,QtCore.SIGNAL("clicked(bool)"),self.facet_remove_button_pressed)
        self.current_selection_removeAll_btn.connect(self.current_selection_removeAll_btn,QtCore.SIGNAL("clicked(bool)"),self.facet_removeAll_button_pressed)
        
 
        self.current_selection_listwidget=QtGui.QListWidget()
        self.current_selection_listwidget.addItem(QtGui.QListWidgetItem("replica:false"))
        current_selection_layout.addLayout(current_selection_btn_layout)
        current_selection_layout.addWidget(self.current_selection_listwidget)
        current_selection_groupbox.setLayout(current_selection_layout)
        search_option_layout.addWidget(current_selection_groupbox)

        datanode_groupbox=QtGui.QGroupBox("Data Node Selection(s)")
        datanode_layout=QtGui.QVBoxLayout()
        datanode_btn_layout=QtGui.QHBoxLayout()
        self.datanode_display_btn=QtGui.QPushButton("Show Data Nodes",self)
        self.datanode_display_btn.connect(self.datanode_display_btn,QtCore.SIGNAL("clicked(bool)"),self.display_datanode_button_pressed)
        self.datanode_display_btn.setDisabled(False)
        self.selection_display_btn=QtGui.QPushButton("Select All",self)
        self.selection_display_btn.connect(self.selection_display_btn,QtCore.SIGNAL("clicked(bool)"),self.selectAll_datanode_button_pressed)
        self.selection_display_btn.setDisabled(False)
        datanode_btn_layout.addWidget(self.datanode_display_btn)
        datanode_btn_layout.addWidget(self.selection_display_btn)
        self.datanode_listwidget=QtGui.QListWidget()
        self.datanode_listwidget.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.datanode_listwidget.connect(self.datanode_listwidget,QtCore.SIGNAL("clicked(const QModelIndex &)"),self.datanode_listwidget_clicked)
        for item in self.data_nodelist:
            new_item = QtGui.QListWidgetItem(item.strip())
            self.datanode_listwidget.addItem(new_item)
        datanode_layout.addLayout(datanode_btn_layout)
        datanode_layout.addWidget(self.datanode_listwidget)
        datanode_groupbox.setLayout(datanode_layout)
        self.datanode_listwidget.hide()
        self.selection_display_btn.hide() 
        
        datanode_layout3=QtGui.QVBoxLayout()
        datanode_layout3.addWidget(datanode_groupbox)
        self.show_all_replicas_checkbox=QtGui.QCheckBox("Show All Replicas")
        self.show_all_replicas_checkbox.connect(self.show_all_replicas_checkbox,QtCore.SIGNAL("clicked()"),self.show_all_replicas_checkbox_checked)
        #datanode_layout2=QtGui.QHBoxLayout()
        #datanode_layout2.addWidget(self.show_all_replicas_checkbox)
        #datanode_layout2.addWidget(self.facet_search_btn)
        #datanode_layout3.addLayout(datanode_layout2)
        datanode_layout3.addWidget(self.show_all_replicas_checkbox)
        search_option_layout.addLayout(datanode_layout3)
        vbox.addWidget(search_frame)

        #self.node_tree_widget=QtGui.QTreeWidget() 
        #self.node_tree_widget.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        #self.node_tree_widget.setHeaderLabel("Node Selection(s)")
        #for data_node in self.data_nodelist:
        #    tree_item=QtGui.QTreeWidgetItem(self.node_tree_widget)
        #    tree_item.setText(0,data_node)
        #site_option_layout.addWidget(self.node_tree_widget)       


        self.facet_order_list=['project','institute','model','submodel','instrument','experiment_family','experiment','subexperiment','time_frequency','product','realm','variable','variable_long_name','cmor_table','cf_standard_name','ensemble']

        scroll = QScrollArea2()
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        scroll.F1 = F1 = QtGui.QFrame()
        QS=scroll.size()
        F1.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        H1 = QtGui.QHBoxLayout()
        F1.setLayout(H1)

        self.facet_tree=QtGui.QTreeWidget()
        self.facet_tree.setColumnCount(1)
        self.facet_tree.setHeaderLabel(QtCore.QString("Search Categories"))
        self.facet_tree.setMaximumWidth(200)
        self.facet_tree.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        #self.facet_tree.connect(self.facet_tree,QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *,int)"),self.update_facet_selection)
        self.facet_tree.connect(self.facet_tree,QtCore.SIGNAL("clicked(const QModelIndex &)"),self.facet_item_selected)
        H1.addWidget(self.facet_tree)

        """

        self.vfacet_layout=QtGui.QVBoxLayout()
        self.facet_frame=QtGui.QFrame()
        self.facet_frame.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        self.facet_frame.setLayout(self.vfacet_layout)
        H1.addWidget(self.facet_frame)

        """

        self.add_facet_list_to_dict_of_dict(self.facet_order_list)
        self.disable_unneeded_facet()

        V2=QtGui.QVBoxLayout() 
        #H1.addLayout(V2)
        F2=QtGui.QFrame()
        F2.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        F2.setLayout(V2)
        H1.addWidget(F2)

        self.page_hbox=QtGui.QFrame() # Page, next, collapes,orignally named H2
        self.page_hbox.setContentsMargins(QtCore.QMargins(0,0,0,0))
        self.page_hlayout=QtGui.QHBoxLayout()
        self.page_hbox.setLayout(self.page_hlayout)
        l=QtGui.QLabel("Page: ")
        l.setAlignment(QtCore.Qt.AlignRight)
        self.page_hlayout.addWidget(l)
        self.page_input=QtGui.QLineEdit()
        #self.page_input.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        #self.page_input.setMaximumHeight(25)
        self.page_input.setText("1")
        self.page_input.connect(self.page_input,QtCore.SIGNAL("returnPressed()"),self.page_input_return_pressed)
        self.page_input.setToolTip("Enter a page number.")
        self.page_input.setAlignment(QtCore.Qt.AlignRight)
        self.page_label=""
        self.page_label_dict={}
        self.page_hlayout.addWidget(self.page_input)
        self.l2=QtGui.QLabel("")
        self.page_hlayout.addWidget(self.l2)
        self.next_page_btn=QtGui.QPushButton("Next",self)
        self.next_page_btn.connect(self.next_page_btn,QtCore.SIGNAL("clicked(bool)"),self.next_page_button_pressed)
        self.page_hlayout.addWidget(self.next_page_btn)
        self.page_hbox.hide()
        self.tree_btn_hbox=QtGui.QFrame()
        self.tree_btn_hbox.setContentsMargins(QtCore.QMargins(0,0,0,0))
        self.tree_btn_layout=QtGui.QHBoxLayout()
        self.tree_btn_hbox.setLayout(self.tree_btn_layout)
        self.remove_tree_node_btn=QDockPushButton("Delete",self)
        self.remove_tree_node_btn.setToolTip("Remove the highlighted top level node in the search result tree")
        self.remove_tree_node_btn.connect(self.remove_tree_node_btn,QtCore.SIGNAL("clicked(bool)"),self.remove_tree_node_btn_pressed)
        self.removeAll_tree_node_btn=QDockPushButton("Delete All",self)
        self.removeAll_tree_node_btn.setToolTip("Remove all the nodes in the tree")
        self.removeAll_tree_node_btn.connect(self.removeAll_tree_node_btn,QtCore.SIGNAL("clicked(bool)"),self.removeAll_tree_node_btn_pressed)
        self.collapseAll_tree_node_btn=QDockPushButton("Collapse All", self)
        self.collapseAll_tree_node_btn.setToolTip("Collapse all the nodes in the tree")
        self.collapseAll_tree_node_btn.connect(self.collapseAll_tree_node_btn,QtCore.SIGNAL("clicked(bool)"),self.collapseAll_tree_node_btn_pressed)
        self.tree_btn_layout.addWidget(self.remove_tree_node_btn)
        self.tree_btn_layout.addWidget(self.removeAll_tree_node_btn)
        self.tree_btn_layout.addWidget(self.collapseAll_tree_node_btn)
        self.tree_btn_hbox.hide()
        V2.addWidget(self.page_hbox)
        V2.addWidget(self.tree_btn_hbox) 
        V2.setSpacing(0)
        self.tree = QtGui.QTreeWidget()
        self.tree.setSelectionMode(QtGui.QTreeWidget.ExtendedSelection)
        self.tree.setIconSize(QtCore.QSize(customizeUVCDAT.esgfTreeIconSize,customizeUVCDAT.esgfTreeIconSize))
        self.tree.connect(self.tree,QtCore.SIGNAL("itemSelectionChanged()"),self.tree_current_item_changed)

        V2.addWidget(self.tree)
        scroll.setWidget(F1)
        vbox.addWidget(scroll)
        vbox.addWidget(self.facet_search_btn)

        self.index=[]
        self.nsearches=0
        self.cacheDir=os.path.join(os.environ["HOME"],"PCMDI_GRAPHICS")
        self.cache={}
        self.loadCache(self.cacheDir)
              
        self.itemMenu = QtGui.QMenu(self)
        menuVbox = QtGui.QVBoxLayout()
        menuVbox.setMargin(2)
        self.itemMenu.setLayout(menuVbox)
        downloadDirAction = self.itemMenu.addAction('&Download Directory')
        self.connect(downloadDirAction,QtCore.SIGNAL("triggered()"),self.downloadDirectory)
        self.multiItemsMenu = QtGui.QMenu(self)
        menuVbox = QtGui.QVBoxLayout()
        menuVbox.setMargin(2)
        self.multiItemsMenu.setLayout(menuVbox)
        downloadMultiAction = self.multiItemsMenu.addAction('&Download Selected Files and Directories')
        self.connect(downloadMultiAction,QtCore.SIGNAL("triggered()"),self.downloadMulti)
        self.connect(self.root.preferences.host_url,QtCore.SIGNAL('currentIndexChanged(int)'),self.get_host_url)
    
    def facet_item_selected(self,idx):
        k=self.facet_order_list[idx.row()]
        if not idx.parent().model():
            #Handle the case when the category is clicked and in this case, clicking = toggle
            if self.facet_dict_of_dict[k]['tree'].isExpanded():
                self.facet_dict_of_dict[k]['tree'].setExpanded(False)
            else:
                self.facet_dict_of_dict[k]['tree'].setExpanded(True)
            self.facet_dict_of_dict[k]['tree'].setSelected(False)
        else:
            #Handle the case when a facet is clicked (items under the facet categories)
            facet_selected_key=None
            parent_idx=idx.parent().row()
            if parent_idx < len(self.facet_order_list):
                facet_selected_key=self.facet_order_list[parent_idx]
            self.update_facet_selection(facet_selected_key)
            self.facet_dict_of_dict[k]['tree'].setExpanded(False)

    def get_host_url(self, index):
        cur_text=self.root.preferences.host_url.currentText()
        if not cur_text:
            cur_text="pcmdi9.llnl.gov"
        else:
            cur_text=str(cur_text)
        if len(self.index )>0:
            self.index.pop(0)
        self.addGateway(cur_text)
        #update data_nodelist and facets
        self.facet_obj=cdms2.FacetConnection(host=cur_text)
        self.setCursor(QtCore.Qt.WaitCursor)
 
        search_text1=self.make_search_text_from_facet_combobox()
        search_text2=None
        if search_text1 and search_text2:
            search_text='&'.join([search_text1,search_text2])
        elif search_text1 and not search_text2:
            search_text=search_text1
        elif not search_text1 and search_text2:
            search_text=search_text2
        else:
            search_text=None
        if search_text:
            search_text=search_text.replace('"','')
            search_text=search_text.replace(' ', '%20')
            found,limit,search_text=self.remove_limit_from_search_text(search_text)
            facet_xmlelement=self.facet_obj.get_xmlelement(search_text)
            # update self.facet_dict and call make facet_dict_of_dict to update self.facet_dict_of_dict
        else:
            facet_xmlelement=self.facet_obj.get_xmlelement()
        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        #add new facet to facet_dict_of_dict
        self.add_facet_item_to_dict_of_dict()
        #update facet buttons
        self.update_dict_of_dict([])

        self.setCursor(QtCore.Qt.ArrowCursor)
        self.data_nodelist=self.get_data_nodelist()
        self.datanode_listwidget.clear()
        for item in self.data_nodelist:
            new_item = QtGui.QListWidgetItem(item.strip())
            self.datanode_listwidget.addItem(new_item)
         

    def update_data_nodelist(self,updated_nodelist):
        self.data_nodelist=updated_nodelist
        self.datanode_listwidget.clear()
        #self.datanode_listwidget.addItem(QtGui.QListWidgetItem("*****"))

        for item in updated_nodelist:
            new_item = QtGui.QListWidgetItem(item.strip())
            self.datanode_listwidget.addItem(new_item)
        
    def next_page_button_pressed(self, pressed):
        page_input=str(self.page_input.text() )
        if len(page_input)==0 or (not page_input.isdigit()):
            m=QtGui.QMessageBox()
            m.setText("Please enter a page number.")
            m.exec_()
        else:
            page_num=int(page_input)+1
            max_page=int(str(self.l2.text()).split(' ')[2].strip())
            if max_page<=1:
                m=QtGui.QMessageBox()
                m.setText("All results are retrieved in your current search.  There is no additional page to return to user.")
                m.exec_()
                return
            if page_num < 1:
                page_num=1
            elif page_num > max_page:
                page_num=max_page
               
        self.setCursor(QtCore.Qt.WaitCursor)
        current_limit=int(self.root.preferences.file_retrieval_limit.text())
        offset=(page_num-1)*current_limit

        idx=self.get_current_top_tree_level_idx()
        top_node_label=str(self.tree.topLevelItem(idx).text(0))
        search_text=top_node_label.split(' ')[-1]
        if search_text.startswith('?'):
            search_text=search_text[1:]
        if search_text:
            search_text=search_text+'&offset=%d'%(offset)
        else:
            search_text='offset=%d'%(offset)
        keys=self.parseQuery(search_text)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setExpanded(False)
        page_label_template=self.tree_current_item_changed()
        page_label_tokens=page_label_template.split(" ") 
        page_label_tokens[1]=str(page_num)
        self.page_label=" ".join(page_label_tokens)
        self.search(**keys)
        self.tree.topLevelItem(self.tree.topLevelItemCount()-1).setExpanded(True)

        self.setCursor(QtCore.Qt.ArrowCursor)
        
   
    def datanode_listwidget_clicked(self, index):
        self.setCursor(QtCore.Qt.WaitCursor)
 
        search_text1=self.make_search_text_from_facet_combobox()
        search_text2=self.make_search_text_from_node_tree_widget()
        if search_text1 and search_text2:
            search_text='&'.join([search_text1,search_text2])
        elif search_text1 and not search_text2:
            search_text=search_text1
        elif not search_text1 and search_text2:
            search_text=search_text2
        else:
            search_text=None
        if search_text:
            search_text=search_text.replace('"','')
            search_text=search_text.replace(' ', '%20')
            found,limit,search_text=self.remove_limit_from_search_text(search_text)
            facet_xmlelement=self.facet_obj.get_xmlelement(search_text)
            # update self.facet_dict and call make facet_dict_of_dict to update self.facet_dict_of_dict
        else:
            facet_xmlelement=self.facet_obj.get_xmlelement()
        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        #add new facet to facet_dict_of_dict
        self.add_facet_item_to_dict_of_dict()
        #update facet buttons
        self.update_dict_of_dict([])

        self.setCursor(QtCore.Qt.ArrowCursor)
        
    def get_facet_label_without_count(self,facet_label_with_count):
        facet_label_tokens=facet_label_with_count.split(" ")
        return facet_label_tokens[0]

    def display_current_selection_button_pressed(self):
        if self.current_selection_listwidget.isHidden():
            self.current_selection_listwidget.show()
            self.current_selection_remove_btn.show()
            self.current_selection_removeAll_btn.show()
            self.current_selection_btn.setText("Hide")
        else:
            self.current_selection_listwidget.hide()
            self.current_selection_remove_btn.hide()
            self.current_selection_removeAll_btn.hide()
            self.current_selection_btn.setText("Show")

    def display_datanode_button_pressed(self):
        if self.datanode_listwidget.isHidden():
            self.datanode_listwidget.show()
            self.selection_display_btn.show() 
            self.datanode_display_btn.setText("Hide")
        else:
            self.datanode_listwidget.hide()
            self.selection_display_btn.hide() 
            self.datanode_display_btn.setText("Show Data Nodes")

    def selectAll_datanode_button_pressed(self):
        label=str(self.selection_display_btn.text())
        if label.strip()=="Select All":
            self.datanode_listwidget.selectAll()
            self.selection_display_btn.setText(str("Deselect All"))
        else:
            self.datanode_listwidget.clearSelection()
            self.selection_display_btn.setText(str("Select All"))
        self.datanode_listwidget_clicked(None)
    
    def get_current_top_tree_level_idx(self):
        tree_item=self.tree.currentItem()
        if not tree_item:
            m=QtGui.QMessageBox()
            m.setText("Please select a node on the search result tree")
            m.exec_()
        idx=self.tree.indexOfTopLevelItem(tree_item)
        found=True
        if idx==-1:
            #self.page_input.setEnabled(False)
            count=500
            cur_count=0
            while (idx==-1):
                parent=tree_item.parent()
                idx=self.tree.indexOfTopLevelItem(parent)
                cur_count=cur_count+1
                if cur_count > count:
                    break
                tree_item=parent
            if idx == -1:
                self.page_input.setEnabled(False)
                found=False
            else:
                found=True
        return idx
            
    def tree_current_item_changed(self):
        tree_item=self.tree.currentItem()
        idx=self.tree.indexOfTopLevelItem(tree_item)
        found=True
        if idx==-1:
            #self.page_input.setEnabled(False)
            count=500
            cur_count=0
            while (idx==-1):
                parent=tree_item.parent()
                idx=self.tree.indexOfTopLevelItem(parent)
                cur_count=cur_count+1
                if cur_count > count:
                    break
                tree_item=parent
            if idx == -1:
                self.page_input.setEnabled(False)
                found=False
            else:
                found=True
        if found:
            self.page_input.setEnabled(True)
            #update page displag area 
            query_offset=0
            search_text=None
            try:
                current_search_number_label=str(self.tree.topLevelItem(idx).text(0))
                current_search_number_label_tokens=current_search_number_label.split(" ")
                current_search_number=int(current_search_number_label_tokens[1])
                if current_search_number in self.page_label_dict:
                    node_label_items=self.page_label_dict[current_search_number].split(" ")
                    cur_page = node_label_items[1]
                    total_page=node_label_items[3]
                    total_file=node_label_items[-1][:-1] 
                #node_label=self.tree.topLevelItem(idx).text(0)
                #node_label_items=node_label.split(" ")
                #if node_label_items[2]=="Page":
                #    cur_page=node_label_items[3]
                #    total_page=node_label_items[5]
                else:
                    try:
                        query = str(self.tree.topLevelItem(idx).text(0)).split("?")[1]
                        search_text=query
                        #find offset
                        query_items=query.split('&')
                        for item in query_items:
                            if item.startswith('offset='):
                                query_offset=int(item[7:].strip())
                    except:    
                        query_offset=0
                        search_text=None
                    limit_found=False
                    if search_text:
                        limit_found,limit,search_text=self.remove_limit_from_search_text(search_text)
                        #search_text=self.remove_replica_from_search_text(search_text)
                        facet_xmlelement_count=self.facet_obj.get_xmlelement_count(search_text)
                    else:
                        facet_xmlelement_count=self.facet_obj.get_xmlelement_count()
          
                    total_file=self.facet_obj.make_facet_dict_count(facet_xmlelement_count)
                    if limit_found:
                        self.root.preferences.file_retrieval_limit.setText(limit)
                    current_limit=int(self.root.preferences.file_retrieval_limit.text())
                    remainder=total_file%current_limit
                    if remainder > 0:
                        remainder=1
                    else: 
                        remainder=0
                    total_page=(total_file/current_limit)+remainder
                    cur_page=(query_offset/current_limit)+1
            except:
                try:
                    query = str(self.tree.topLevelItem(idx).text(0)).split("?")[1]
                    search_text=query
                    #find offset
                    query_items=query.split('&')
                    for item in query_items:
                        if item.startswith('offset='):
                            query_offset=int(item[7:].strip())
                except:    
                    query_offset=0
                    search_text=None
                limit_found=False
                if search_text:
                    limit_found,limit,search_text=self.remove_limit_from_search_text(search_text)
                    #search_text=self.remove_replica_from_search_text(search_text)
                    facet_xmlelement_count=self.facet_obj.get_xmlelement_count(search_text)
                else:
                    facet_xmlelement_count=self.facet_obj.get_xmlelement_count()
          
                total_file=self.facet_obj.make_facet_dict_count(facet_xmlelement_count)
                if limit_found:
                    self.root.preferences.file_retrieval_limit.setText(limit)
                current_limit=int(self.root.preferences.file_retrieval_limit.text())
                remainder=total_file%current_limit
                if remainder > 0:
                    remainder=1
                else: 
                    remainder=0
                total_page=(total_file/current_limit)+remainder
                cur_page=(query_offset/current_limit)+1

            self.page_input.setText(str(cur_page))
            self.l2.setText(" of %s (Total Files: %s)"%(str(total_page),str(total_file)))
            #self.page_label="Page %s of %s (Total Files: %s)"%(str(cur_page),str(total_page),str(total_file))
            self.page_hbox.show()
            self.tree_btn_hbox.show()
            if total_page <= 1:
                self.next_page_btn.setDisabled(True)
            else:
                self.next_page_btn.setDisabled(False)
        return "Page %s of %s (Total Files: %s)"%(str(cur_page),str(total_page),str(total_file))

    def remove_tree_node_btn_pressed(self):
        selected_idx_list=self.tree.selectedIndexes()
        for item in selected_idx_list:
            self.tree.takeTopLevelItem(item.row())

    def removeAll_tree_node_btn_pressed(self):
        self.page_hbox.hide()
        self.tree_btn_hbox.hide()
        self.tree.clear()

    def collapseAll_tree_node_btn_pressed(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setExpanded(False)
   
    def page_input_return_pressed(self):
        self.setCursor(QtCore.Qt.WaitCursor)
        page_input=str(self.page_input.text() )
        if len(page_input)==0 or (not page_input.isdigit()):
            m=QtGui.QMessageBox()
            m.setText("Please enter a page number.")
            m.exec_()
        else:
           page_num=int(page_input)
           max_page=int(str(self.l2.text()).split(' ')[2].strip())
           if page_num < 1:
               page_num=1
           elif page_num > max_page:
               page_num=max_page
        current_limit=int(self.root.preferences.file_retrieval_limit.text())
        offset=(page_num-1)*current_limit

        idx=self.get_current_top_tree_level_idx()
        top_node_label=str(self.tree.topLevelItem(idx).text(0))
        search_text=top_node_label.split(' ')[-1]
        if search_text.startswith('?'):
            search_text=search_text[1:]
        if search_text:
            search_text=search_text+'&offset=%d'%(offset)
        else:
            search_text='offset=%d'%(offset)
        keys=self.parseQuery(search_text)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setExpanded(False)
        page_label_template=self.tree_current_item_changed()
        page_label_tokens=page_label_template.split(" ") 
        page_label_tokens[1]=str(page_num)
        self.page_label=" ".join(page_label_tokens)
        self.search(**keys)
        self.tree.topLevelItem(self.tree.topLevelItemCount()-1).setExpanded(True)
        self.setCursor(QtCore.Qt.ArrowCursor)

    def make_facet_label(self,facet_name):
        facet_tokens=facet_name.split('_')
        converted_list=[]
        for facet_item in facet_tokens:
            facet_item=facet_item.upper()
            converted_list.append(facet_item)
        return " ".join(converted_list)

    def remake_facet_name(self,facet_label):
        facet_tokens=facet_label.split(" ")
        converted_list=[]
        for facet_item in facet_tokens:
            facet_item=facet_item.lower()
            converted_list.append(facet_item)
        return "_".join(converted_list)

    def make_search_text_from_facet_combobox(self):
        selected_list=[]
        for i in range(self.current_selection_listwidget.count()):
            selected_list.append(str(self.current_selection_listwidget.item(i).text()))
        search_text='&'.join(selected_list)
        search_text=search_text.replace(':','=')
        return search_text
    
    def make_search_text_from_node_tree_widget(self):
        selected_list=self.datanode_listwidget.selectedItems()
        selected_data_nodelist=[]
        if len(selected_list)>0 and len(selected_list)<len(self.data_nodelist): 
            for item in selected_list:
                selected_data_nodelist.append('data_node='+str(item.text()))
        if selected_data_nodelist != []:
            search_text='&'.join(selected_data_nodelist)
        else:
            search_text=None
        return search_text

    def facet_remove_button_pressed(self):
        idx_list=self.current_selection_listwidget.selectedIndexes()
        idx_list.reverse()
        for cur_idx in idx_list:
            item=self.current_selection_listwidget.takeItem(cur_idx.row())
            if str(item.text())=='replica:false':
                self.show_all_replicas_checkbox.setChecked(True)
            

        #cur_idx=self.selected_facet_combobox.currentIndex()
        #cur_text=self.selected_facet_combobox.itemText(cur_idx)
        #facet_name=cur_text.split(':')[0]
        #self.remove_selected_facet(cur_idx)


        self.setCursor(QtCore.Qt.WaitCursor)
        search_text1=self.make_search_text_from_facet_combobox()
        search_text2=self.make_search_text_from_node_tree_widget()
        if search_text1 and search_text2:
            search_text='&'.join([search_text1,search_text2])
        elif search_text1 and not search_text2:
            search_text=search_text1
        elif not search_text1 and search_text2:
            search_text=search_text2
        else:
            search_text=None
        if search_text:
            search_text=search_text.replace('"','')
            search_text=search_text.replace(' ', '%20')
            found,limit,search_text=self.remove_limit_from_search_text(search_text)
            facet_xmlelement=self.facet_obj.get_xmlelement(search_text)
            # update self.facet_dict and call make facet_dict_of_dict to update self.facet_dict_of_dict
        else:
            facet_xmlelement=self.facet_obj.get_xmlelement()
        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        #add new facet to facet_dict_of_dict
        self.add_facet_item_to_dict_of_dict()
        #update facet buttons
        self.update_dict_of_dict([])
        self.setCursor(QtCore.Qt.ArrowCursor)
       
    def facet_removeAll_button_pressed(self):
        self.setCursor(QtCore.Qt.WaitCursor)
        self.show_all_replicas_checkbox.setChecked(False)

        self.current_selection_listwidget.clear()
        self.current_selection_listwidget.addItem(QtGui.QListWidgetItem("replica:false"))
        facet_xmlelement=self.facet_obj.get_xmlelement("replica=false")
        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        self.update_dict_of_dict([])
        self.setCursor(QtCore.Qt.ArrowCursor)

    def facet_search_button_pressed(self):
        current_text=self.searchLine.text()
        self.searchLine.clear()
        try:
            current_text=str(current_text)
            if len(current_text.strip())>0:
                current_text_tokens=current_text.split(" ")
                current_text_token_list=[]
                for t in current_text_tokens:
                    if t.strip().upper()=='AND':
                        current_text_token_list.append(t.strip().upper())
                    else:
                        current_text_token_list.append(t)
                current_text=" ".join(current_text_token_list)

                search_text_list=[]
                cur_list_combobox=self.get_current_list_from_facet_combobox()

                current_text_tokens=current_text.split('AND')
                for token in current_text_tokens:
                    token=str(token)
                    params=token.split(':')
                    if len(params)==2:
                        if token.strip() not in cur_list_combobox:
                            search_text_list.append(token.strip())
                    elif len(params)==1:
                        new_item='query:'+token.strip()
                        if len(token.strip())>0 and new_item not in cur_list_combobox:
                            search_text_list.append(new_item)
                for item in search_text_list:
                    new_item = QtGui.QListWidgetItem(item.strip())
                    self.current_selection_listwidget.addItem(new_item)
        except Exception, e:
            pass
        search_text1=self.make_search_text_from_facet_combobox()
        search_text2=self.make_search_text_from_node_tree_widget()
        if search_text1 and search_text2:
            search_text='&'.join([search_text1,search_text2])
        elif search_text1 and not search_text2:
            search_text=search_text1
        elif not search_text1 and search_text2:
            search_text=search_text2
        else:
            search_text=None
        self.search_using_facet_selection(search_text)

    def remove_replica_from_search_text(self, search_text):
        tokens=search_text.split('&')
        new_list=[]
        target="replica=false"
        if self.show_all_replicas_checkbox.isChecked():
            target="replica=true"
        for token in tokens:
            if not token.startswith('replica'):
                new_list.append(token)
        new_list.append(target)
        return '&'.join(new_list)

    def remove_limit_from_search_text(self, search_text):
        tokens=search_text.split('&')
        new_list=[]
        found=False
        limit=int(self.root.preferences.file_retrieval_limit.text())
        
        for token in tokens:
            if not token.startswith('limit'):
                new_list.append(token)
            else:
                limit=token.split('=')[1]
                if not limit.isdigit():
                    found=False
                else:
                    found=True
        return found,limit,'&'.join(new_list)

    def search_using_facet_selection(self,search_text):
        if search_text=='':
            m=QtGui.QMessageBox()
            m.setText("Invalid input.  Unable to perform search.")
            m.exec_()
        search_text=search_text.replace('"','')
        search_text=search_text.replace(' ', '%20')
        self.setCursor(QtCore.Qt.WaitCursor)
        limit_found=False
        if search_text:
            limit_found,limit,search_text=self.remove_limit_from_search_text(search_text)
            #search_text=self.remove_replica_from_search_text(search_text)
            keys = self.parseQuery(search_text)
            facet_xmlelement_count=self.facet_obj.get_xmlelement_count(search_text)
        else:
            facet_xmlelement_count=self.facet_obj.get_xmlelement_count()
          
        total_file=self.facet_obj.make_facet_dict_count(facet_xmlelement_count)
        if limit_found:
            self.root.preferences.file_retrieval_limit.setText(limit)
        current_limit=int(self.root.preferences.file_retrieval_limit.text())
        remainder=total_file%current_limit
        if remainder > 0:
            remainder=1
        else: 
            remainder=0
        total_pages=(total_file/current_limit)+remainder
        self.l2.setText(" of %d (Total Files: %d)"%(total_pages,total_file))
        self.page_label="Page 1 of %d (Total Files: %d)"%(total_pages,total_file)
        self.page_hbox.show()
        self.tree_btn_hbox.show()
        if total_pages <= 1:
            self.next_page_btn.setDisabled(True)
        else:
            self.next_page_btn.setDisabled(False)
        #if total_file and total_file > current_limit:
        #    m=QtGui.QMessageBox()
        #    m.setText("Please refine your current selection(s).  Your total number of requested files (%d) exceeds the current limit (%d).  Only the top %d files are displayed."%(total_file, current_limit, current_limit))
        #    m.exec_()
        if search_text:
            search_text=search_text+'&limit='+str(current_limit)
        else:
            search_text='limit='+str(current_limit)
        keys=self.parseQuery(search_text)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setExpanded(False)
        self.search(**keys)
        self.tree.topLevelItem(self.tree.topLevelItemCount()-1).setExpanded(True)
        self.setCursor(QtCore.Qt.ArrowCursor)

    def remove_selected_facet(self,selected_index):
        #self.selected_facet_combobox.removeItem(selected_index)
        item=self.current_selection_listwidget.takeItem(selected_index)
        if str(item.text())=='replica:false':
            self.show_all_replicas_checkbox.setChecked(True)

    def get_data_nodelist(self):
        if "data_node" not in self.facet_dict:
            return []
        nodelist=self.facet_dict["data_node"]
        found_pcmdi9=False
        for node in nodelist:
            node=self.get_facet_label_without_count(node)
            if node=="pcmdi9.llnl.gov":
                found_pcmdi9=True
        new_nodelist=[]
        for node in nodelist:
            node=self.get_facet_label_without_count(node)
            new_nodelist.append(node)
        if found_pcmdi9:
            for node in nodelist:
                node=self.get_facet_label_without_count(node)
                if node.startswith('pcmdi') and node != 'pcmdi9.llnl.gov':
                    new_nodelist.remove(node)
        return new_nodelist        
    
    def get_current_list_from_facet_combobox(self):
        cur_list_combobox=[]
        for i in range(self.current_selection_listwidget.count()):
            item=self.current_selection_listwidget.item(i).text()
            cur_list_combobox.append(str(item))
        return cur_list_combobox

    def update_facet_combobox_from_facet_changes(self):
        # get list of current items in combobox
        cur_list_combobox=self.get_current_list_from_facet_combobox()
        # add new items to combobox 
        search_text_list=[]
        for widgetitem in self.facet_tree.selectedItems():
            widgetitemtext=widgetitem.text(0)
            myitem=str(widgetitemtext)
            target=myitem.split(" ")[0]
            itemparent = widgetitem.parent()
            new_item=self.remake_facet_name(str(itemparent.text(0)))+':'+target
            if new_item not in cur_list_combobox:
                search_text_list.append(new_item)
        for item in search_text_list:
            new_item = QtGui.QListWidgetItem(item.strip())
            self.current_selection_listwidget.addItem(new_item)
        #self.selected_facet_combobox.addItems(search_text_list)

    def show_all_replicas_checkbox_checked(self):
        target="replica:true"
        target2="replica:false"
        cur_list_combobox=self.get_current_list_from_facet_combobox()
        if self.show_all_replicas_checkbox.isChecked(): 
            idx=0
            found=False
            for item in cur_list_combobox:
                if item == target2:
                    found=True
                    break
                idx=idx+1
            if found:
                self.remove_selected_facet(idx) 
        else:
            if target2 not in cur_list_combobox:
                self.current_selection_listwidget.addItem(QtGui.QListWidgetItem(target2))

        self.setCursor(QtCore.Qt.WaitCursor)
        search_text1=self.make_search_text_from_facet_combobox()
        search_text2=self.make_search_text_from_node_tree_widget()
        if search_text1 and search_text2:
            search_text='&'.join([search_text1,search_text2])
        elif search_text1 and not search_text2:
            search_text=search_text1
        elif not search_text1 and search_text2:
            search_text=search_text2
        else:
            search_text=None
        if search_text:
            search_text=search_text.replace('"','')
            search_text=search_text.replace(' ', '%20')
            found,limit,search_text=self.remove_limit_from_search_text(search_text)
            facet_xmlelement=self.facet_obj.get_xmlelement(search_text)
            # update self.facet_dict and call make facet_dict_of_dict to update self.facet_dict_of_dict
        else:
            facet_xmlelement=self.facet_obj.get_xmlelement()
        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        #add new facet to facet_dict_of_dict
        self.add_facet_item_to_dict_of_dict()
        #update facet buttons
        self.update_dict_of_dict([])
        self.setCursor(QtCore.Qt.ArrowCursor)

    def entered_search_line(self):
        current_text=self.searchLine.text()
        self.searchLine.clear()
        try:
            current_text=str(current_text)
            if len(current_text.strip())>0:
                current_text_tokens=current_text.split(" ")
                current_text_token_list=[]
                for t in current_text_tokens:
                    if t.strip().upper()=='AND':
                        current_text_token_list.append(t.strip().upper())
                    else:
                        current_text_token_list.append(t)
                current_text=" ".join(current_text_token_list)

                search_text_list=[]
                cur_list_combobox=self.get_current_list_from_facet_combobox()

                current_text_tokens=current_text.split('AND')
                for token in current_text_tokens:
                    token=str(token)
                    params=token.split(':')
                    if len(params)==2:
                        if token.strip() not in cur_list_combobox:
                            search_text_list.append(token.strip())
                    elif len(params)==1:
                        new_item='query:'+token.strip()
                        if len(token.strip())>0 and new_item not in cur_list_combobox:
                            search_text_list.append(new_item)
                for item in search_text_list:
                    new_item = QtGui.QListWidgetItem(item.strip())
                    self.current_selection_listwidget.addItem(new_item)
                #self.selected_facet_combobox.addItems(search_text_list)

                search_text1=self.make_search_text_from_facet_combobox()
                search_text2=self.make_search_text_from_node_tree_widget()
                if search_text1 and search_text2:
                    search_text='&'.join([search_text1,search_text2])
                elif search_text1 and not search_text2:
                    search_text=search_text1
                elif not search_text1 and search_text2:
                    search_text=search_text2
                else:
                    search_text=None
                self.search_using_facet_selection(search_text)
            else:
                m=QtGui.QMessageBox()
                m.setText("Error: Your search field is empty. Please try again.")
                m.exec_()
        except Exception, e:
            if search_text_list:
                cur_list_combobox=self.get_current_list_from_facet_combobox()
                idx=0
                idx_list=[]
                for item in cur_list_combobox:
                    for target in search_text_list:
                        if item == target:
                            idx_list.append(idx)
                    idx=idx+1
                if idx_list:
                    idx_list.reverse()
                    for item in idx_list:
                        self.remove_selected_facet(item) 
            m=QtGui.QMessageBox()
            m.setText("Error: Your search entry is invalid. Please try again.")
            m.exec_()
            self.setCursor(QtCore.Qt.ArrowCursor)
        
        """
        for token in current_text_tokens:
            token=str(token)
            params=token.split(':')
            if len(params)==2:
                if token.strip() not in cur_list_combobox:
                    search_text_list.append(token.strip())
            elif len(params)==1:
                new_item='query:'+token.strip()
                if new_item not in cur_list_combobox:
                    search_text_list.append(new_item)
        self.selected_facet_combobox.addItems(search_text_list)
        """
    def update_facet_selection(self,selected_facet_key):
        self.setCursor(QtCore.Qt.WaitCursor)
        self.update_facet_combobox_from_facet_changes()
        search_text1=self.make_search_text_from_facet_combobox()
        search_text2=self.make_search_text_from_node_tree_widget()
        if search_text1 and search_text2:
            search_text='&'.join([search_text1,search_text2])
        elif search_text1 and not search_text2:
            search_text=search_text1
        elif not search_text1 and search_text2:
            search_text=search_text2
        else:
            search_text=None

        if search_text:
            search_text=search_text.replace('"','')
            search_text=search_text.replace(' ', '%20')
            found,limit,search_text=self.remove_limit_from_search_text(search_text)
            facet_xmlelement=self.facet_obj.get_xmlelement(search_text)
            # update self.facet_dict and call make facet_dict_of_dict to update self.facet_dict_of_dict
        else:
            facet_xmlelement=self.facet_obj.get_xmlelement()

        self.facet_dict=self.facet_obj.make_facet_dict(facet_xmlelement)
        #add new facet to facet_dict_of_dict
        self.add_facet_item_to_dict_of_dict()
        #update facet buttons
        if selected_facet_key:
            nonupdated_list=self.make_facet_nonupdated_list(selected_facet_key)
            self.update_dict_of_dict(nonupdated_list) 
        else:
            self.update_dict_of_dict([])
        self.setCursor(QtCore.Qt.ArrowCursor)

    def add_key_to_dict_of_dict(self,k):
        self.facet_dict_of_dict[k]={}
        datalist=None
        if k in self.facet_dict:
            datalist=self.facet_dict[k]
        self.facet_dict_of_dict[k]['tree']=QtGui.QTreeWidgetItem()
        self.facet_dict_of_dict[k]['tree'].setText(0,QtCore.QString(self.make_facet_label(k)))
        self.facet_dict_of_dict[k]['tree'].setDisabled(False)
        self.facet_tree.addTopLevelItem(self.facet_dict_of_dict[k]['tree'])
        if k in self.facet_dict:
            for item in self.facet_dict[k]:
                new_item = QtGui.QTreeWidgetItem()
                new_item.setText(0,QtCore.QString(item.strip()))
                self.facet_dict_of_dict[k]['tree'].addChild(new_item)
                
        """
        self.facet_dict_of_dict[k]['btn']=QFacetButton(self.make_facet_label(k),self,datalist)
        self.facet_dict_of_dict[k]['btn'].connect(self.facet_dict_of_dict[k]['btn'],QtCore.SIGNAL("clicked(bool)"),self.facet_dict_of_dict[k]['btn'].facet_button_pressed)
        self.facet_dict_of_dict[k]['btn'].setDisabled(False)
        self.vsp.addWidget(self.facet_dict_of_dict[k]['btn'])
        self.facet_dict_of_dict[k]['ListWidget']=QtGui.QListWidget()
        self.facet_dict_of_dict[k]['ListWidget'].setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.facet_dict_of_dict[k]['ListWidget'].setMinimumHeight(100)
         
        
        if k in self.facet_dict:
            for item in self.facet_dict[k]:
                new_item = QtGui.QListWidgetItem(item.strip())
                self.facet_dict_of_dict[k]['ListWidget'].addItem(new_item)
        self.vsp.addWidget(self.facet_dict_of_dict[k]['ListWidget'])
        self.facet_dict_of_dict[k]['ListWidget'].hide()        
        self.facet_dict_of_dict[k]['ListWidget'].connect(self.facet_dict_of_dict[k]['ListWidget'],QtCore.SIGNAL("itemSelectionChanged()"),self.facet_dict_of_dict[k]['btn'].update_facet_selection)
        """

    def add_facet_list_to_dict_of_dict(self, add_list):
        for k in add_list:
            self.add_key_to_dict_of_dict(k)
 
    def add_facet_item_to_dict_of_dict(self):
        keylist=self.facet_dict.keys()
        keylist.sort()
        for k in keylist:
            if k != 'data_node' and k not in self.facet_dict_of_dict:
                self.add_key_to_dict_of_dict(k)            

    def make_facet_nonupdated_list(self, selected_facet_key):
        #get a facet list that need not be updated
        nonupdated_list=[]
        for k in self.facet_order_list:
            if k != selected_facet_key:
                nonupdated_list.append(k)
            else: 
                nonupdated_list.append(k)
                break
        return nonupdated_list

    def disable_unneeded_facet(self):
        new_key_list=self.facet_dict.keys()
        for k in self.facet_dict_of_dict:
            if k not in new_key_list or len(self.facet_dict[k])==0:
                self.facet_dict_of_dict[k]['tree'].setDisabled(True)

    def update_dict_of_dict(self,nonupdated_list):
        self.facet_tree.disconnect(self.facet_tree,QtCore.SIGNAL("clicked(const QModelIndex &)"),self.facet_item_selected)
        for k in self.facet_dict_of_dict:
            if k not in self.facet_dict or len(self.facet_dict[k])==0:
                self.facet_dict_of_dict[k]['tree'].setDisabled(True)
            elif k not in nonupdated_list:
                children=self.facet_dict_of_dict[k]['tree'].takeChildren()
                for item in self.facet_dict[k]:    
                    new_item = QtGui.QTreeWidgetItem()
                    new_item.setText(0,QtCore.QString(item.strip()))
                    self.facet_dict_of_dict[k]['tree'].addChild(new_item)
        self.facet_tree.collapseAll()
        self.facet_tree.connect(self.facet_tree,QtCore.SIGNAL("clicked(const QModelIndex &)"),self.facet_item_selected)

    def userSaveCache(self):
        self.saveCache(self.cacheDir)
        
    def loadCache(self,source):
        if os.path.isdir(source):
            source = os.path.join(source,"esgfDatasetsCache.pckl")
        if not os.path.exists(source):
            return
        f=open(source)
        #self.cache=eval(bz2.decompress(f.read()))
        self.cache = eval(f.read())
        f.close()

    def saveCache(self,target):
        if os.path.isdir(target):
            target = os.path.join(target,"esgfDatasetsCache.pckl")
        f=open(target,"w")
        #f.write(bz2.compress(repr(self.cache)))
        f.write(repr(self.cache))
        f.close()

    def clearCache(self):
        self.cache={}
        
    def userAddsGateway(self):
        url,ok = QtGui.QInputDialog.getText(self,"Adding A Gateway","URL",text=customizeUVCDAT.defaultEsgfNode)
        if ok is False:
            return
        self.addGateway(gateway=url,mapping=self.mapping)#,datasetids="%(project).%(product).%(valid_institute).%(model).%(experiment).%(time_frequency)s.%(realm).%(cmor_table).%(ensemble)")

    def editMapping(self):
        if self.mapping is not None:
            mapping = self.mapping
        else:
            mapping="None"
        mapping,ok = QtGui.QInputDialog.getText(self,"Edit Mapping","Your mapping",text=mapping)
        if ok is False:
            return
        self.mapping = str(mapping)
        if self.mapping in ["","None","none"]:
            self.mapping=None
        for i in self.index:
            i.mapping=self.mapping

    def doubleClickedItem(self,item,column):
        if item.type()==3:
            txt=str(item.text(0)).split("@")
            service = txt[0].strip()
            url = txt[1].split()[0].strip()
            if service=="OPENDAP":
                try:
                    if url[:-5] in CdmsCache.d:
                        #print "Using cache1 for %s" % url[:5]
                        f = CdmsCache.d[url[:-5]]
                    else:
                        #print "Loading file1 %s" % url[:-5]
                        f = CdmsCache.d[url[:-5]] = cdms2.open(url[:-5])
                    fvars = f.variables.keys()
                    for v in f.variables.keys():
                        V=f[v]
                        for ax in V.getAxisList():
                            if hasattr(ax,"bounds"):
                                sp = ax.bounds.split()
                                for b in sp:
                                    if b in fvars:
                                        fvars.remove(b)
                        for d in V.listdimnames():
                            if d in fvars:
                                fvars.remove(d)
                            
                    #f.close()
                    index=-1
                    if self.root is not None:
                        self.root.varProp.fileEdit.setText(url[:-5])
                        self.root.varProp.fileEdit.emit(QtCore.SIGNAL('returnPressed()'))
                        self.root.varProp.originTabWidget.setCurrentIndex(0)
                        #self.root.tabView.widget(0).fileWidget.widget.fileNameEdit.emit(QtCore.SIGNAL('returnPressed()'))
                        #for i in range(self.root.tabView.widget(0).fileWidget.widget.varCombo.count()):
                        #    t = self.root.tabView.widget(0).fileWidget.widget.varCombo.itemText(i)
                        #    if str(t).split()[0] == fvars[0]:
                        #        index = i
                        #        break
                        #if index!=-1:
                        #    self.root.tabView.widget(0).fileWidget.widget.varCombo.setCurrentIndex(index)
                        #self.hide()
                except Exception,err:
                    m=QtGui.QMessageBox()
                    m.setText("Couldn't open URL: %s (error: %s).Check credentials"%(url[:-5],err))
                    m.exec_()
            elif service == "HTTPServer":
                fnm = QtGui.QFileDialog.getSaveFileName(self,"NetCDF File",url,filter="NetCDF Files (*.nc *.cdg *.NC *.CDF *.nc4 *.NC4) ;; All Files (*.*)",options=QtGui.QFileDialog.DontConfirmOverwrite)
                if len(str(fnm))==0:
                    return
                pipe = self.httpDownloadFile(url,fnm)
                p=QMultiDownloadProgressBar(self)
                p.addDownload(url,fnm,pipe)
                p.exec_()
            elif service == "GridFTP":
                m=QtGui.QMessageBox()
                m.setText("Not Implemented")
                m.exec_() 

    def httpDownloadFile(self,url,fnm):
        cmd = "wget --certificate %s -t 2 -T 10 --private-key %s -O %s %s" % (self.credentials.cert_file,self.credentials.key_file,fnm,url)
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        time.sleep(.1)
        return pipe
        
                #i,o,e = os.popen3("wget --certificate %s --private-key %s %s %s" % (self.credentials.cert_file,self.credentials.key_file,url,fnm))
                #print "Out:",o.readlines()
                #print "Err:",e.readlines()
    def clickedItem(self,item,column):
        if item.type()==3:
            pass
            #txt=str(item.text(0)).split("@")
        else: # ok not a file we need to exapnd/contract
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)

    def addTreeItems(self,Item,dict,mapping,textColor):
        keys = dict.keys()
        if "files" in keys:
            keys.remove("files")
            keys.append("files")
        for k in keys:
            if k == "files":
                for f in dict["files"]:
                    item=QtGui.QTreeWidgetItem(Item,2)
                    item.setIcon(0,self.fileIcon)
                    item.setText(0,f.id)
                    for s in f.services:
                        if textColor=="red":
                            cache=" (cached and needs to be updated)"
                        else:
                            cache = ""
                        txt = "%s @ %s%s" % (s,getattr(f,s),cache)
                        it=QtGui.QTreeWidgetItem(item,3)
                        it.setData(0, QtCore.Qt.TextColorRole, QtGui.QColor(textColor));
                        if s=="OPENDAP":
                            it.setIcon(0,self.opendapIcon)
                            it.setToolTip(0,"You can open me in this GUI")
                        elif s=="LAS":
                            it.setIcon(0,self.lasIcon)
                            it.setToolTip(0,"You can open me in a web browser")
                        elif s=="HTTPServer":
                            it.setIcon(0,self.httpIcon)
                            it.setToolTip(0,"You can download me")
                        elif s=="GridFTP":
                            it.setIcon(0,self.gridftpIcon)
                            it.setToolTip(0,"Not Implemented")
                        else:
                            it.setIcon(0,self.unknownIcon)
                            it.setToolTip(0,"You can see me with an application that know about: %s" % s)
                        it.setText(0,txt)
                        item.addChild(it)
                    if Item.type()==0:
                        for i in range(Item.childCount()):
                            if str(Item.child(i).text(0)) == "Unmapped Files":
                                Item.child(i).addChild(item)
                                break
                    else:
                        Item.addChild(item)
            else:
                found = False
                for i in range(Item.childCount()):
                    item = Item.child(i)
                    if str(item.text(0)) == k:
                        found = True
                        break
                if found is False:
                    item=QtGui.QTreeWidgetItem(Item,1)
                    item.setIcon(0,self.foldersIcon)
                    item.setText(0,str(k))
                    if len(mapping)>0:
                        item.setToolTip(0,mapping[0])
                        item.setWhatsThis(0,mapping[0])
                    Item.addChild(item)
                self.addTreeItems(item,dict[k],mapping[1:],textColor)
        ## for i in range(Item.columnCount()):
        ##     Item.sortChildren(i,0)
        return
            
            
    def addGateway(self,gateway = customizeUVCDAT.defaultEsgfNode,port=80,limit=1000,offset=0,mapping=None,datasetids=None,fileids=None,restPath=None):
        if hasattr(cdms2, "esgfDataset"):
            if mapping is None:
                mapping=self.mapping
            try:
                #print "Actual mapping:",self.mapping
                self.index.append(cdms2.esgfDataset(gateway,port=port,limit=limit,offset=offset,mapping=mapping,datasetids=datasetids,fileids=fileids,restPath=restPath))
                #self.QIndex.addIndex("%s:%i" % (gateway,port))
            except Exception,err:
                import traceback
                traceback.print_last() #writes to session log or console
                m = QtGui.QMessageBox()
                m.setText("%s\n\nSee session log" % str(err))
                m.exec_()
                return            

    def parseQuery(self,query):
        query=query.replace(";","---^^^---")
        query=query.replace("?","---^^^---")
        query=query.replace("&","---^^^---")
        sp=query.split("---^^^---")
        keys={}
        if len(query.strip())>0:
            for s in query.split("---^^^---"):
                try:
                    sp=s.split("=")
                    query_key=sp[0].strip()
                    if query_key not in keys:
                        keys[query_key]=[sp[1].strip()]
                    else:
                        keys[query_key].append(sp[1].strip())
                    #keys[sp[0].strip()]=sp[1].strip()
                except:
                    pass
        return keys

    def clickedCredentials(self):
        self.credentials.show()
        
    def clickedSearch(self):
        query = str(self.searchLine.text())
        keys = self.parseQuery(query)
        self.search(**keys)
        
    def search(self,**keys):
        if len(self.index)==0:
            m = QtGui.QMessageBox()
            m.setText("You need to add at least one gateway before you can search")
            m.exec_()
            return
        
        for i in range(self.tree.topLevelItemCount()):
            if self.tree.topLevelItem(i).isSelected():
                ## Ok we are subsearching
                try:
                    query = str(self.tree.topLevelItem(i).text(0)).split("?")[1]
                except:
                    # expetion means we searched the whole thingy
                    query = str(self.tree.topLevelItem(i).text(0))
                subkeys = self.parseQuery(query)
                for k in subkeys.keys():
                    if not k in keys.keys():
                        keys[k]=subkeys[k]
                
        files = []
        try:
            for i in self.index:
                #d = i.searchDatasets(**keys)
                f = i.search(**keys)
                #print "i mapping is:",i.mapping.template
                files.append(f)
        except Exception,err:
            m = QtGui.QDialog()
            l=QtGui.QVBoxLayout()
            te=QtGui.QTextEdit()
            te.insertPlainText(str(err))
            l.addWidget(te)
            m.setLayout(l)
            m.exec_()
            return
        query=""
        #for i in keys.items():
        #    query+="&%s=%s" % (i[0],i[1])
        for k in keys.keys():
            for v in keys[k]:
                query+="&%s=%s"%(k,v)   
        if query!="":
            query="?"+query[1:]
        
        self.nsearches+=1
        if self.page_label:
            self.page_label_dict[self.nsearches]=self.page_label
        self.createTreeSearchItem(files,"Search %i %s" % (self.nsearches,query))
        self.tree.setCurrentItem(self.tree.topLevelItem(self.tree.topLevelItemCount()-1))

    def createTreeSearchItem(self,searchResults,name):
        ## First the top Item
        Item = QtGui.QTreeWidgetItem(0)
        Item.setText(0,name)
        Item.setIcon(0,self.searchIcon)
        item=QtGui.QTreeWidgetItem(1)
        item.setIcon(0,self.foldersIcon)
        item.setText(0,"Unmapped Files")
        Item.addChild(item)
        indexlist=[]
        n = len(searchResults)
        p = QtGui.QProgressDialog()
        p.setLabelText("Searching...")
        p.show()
        p.setWindowModality(QtCore.Qt.WindowModal)
        p.setRange(0,n)
        failed=[]
        for i in range(n):
            files = searchResults[i]
            p.setValue(i)
            ## first we figure where this comes from
            #nm = "%s:%i" % (d.host,d.port)
            #commenting cache part for now
            """if d.id in self.cache.keys():
                d.resp=xml.etree.ElementTree.fromstring(self.cache[d.id][1])
                ts = self.cache[d.id][0]
            else:
                ts=d["timestamp"]
            try:
                files = d.search()
                #print "Dataset:%s found: %i file, okeys: %s" % (d.id,len(files),repr(d.originalKeys))
            except:
                failed.append(d.id)
                continue
            self.cache[d.id]=[ts,xml.etree.ElementTree.tostring(d.resp),d.originalKeys]
            if not nm in indexlist:
                indexlist.append(nm)
            if ts!=d["timestamp"]:
                textColor="red"
            else:
                textColor="black"
            """
            textColor='black'
            self.addTreeItems(Item,files.mapped,files.mapping.keys(),textColor)
            if p.wasCanceled():
                return
        #Item.datasets = searchResults
        Item.setToolTip(0,"\n".join(indexlist))
        self.tree.addTopLevelItem(Item)
#        self.tree.setColumnCount(6)
        self.connect(self.tree,QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),self.doubleClickedItem)
        self.connect(self.tree,QtCore.SIGNAL("itemClicked(QTreeWidgetItem *,int)"),self.clickedItem)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self.tree,QtCore.SIGNAL("customContextMenuRequested(QPoint)"),self.popupmenu)
        def sortItems(Item):
            ncols = Item.columnCount()
            for i in range(ncols):
                Item.sortChildren(i,0)
            for i in range(Item.childCount()):
                sortItems(Item.child(i))
        sortItems(Item)
        
        if failed!=[]:
            m = QtGui.QMessageBox()
            m.setText("The following datasets could not be mapped to your schema:%s and therefore have been skipped: %s" % (self.mapping,"; ".join(failed)))
            m.exec_()
            

    def popupmenu(self,pos):
        nSelected = len(self.tree.selectedItems())
        item = self.tree.itemAt(pos)
        if nSelected == 1:
            if item and item.type()==1: # Only popup for directories!
                self.itemMenu.popup(self.tree.mapToGlobal(pos))
        else:
            self.multiItemsMenu.popup(self.tree.mapToGlobal(pos))

    def downloadMulti(self):
        dialog=QMultiDownloadProgressBar(self)
        dirnm = str(QtGui.QFileDialog.getExistingDirectory(self))
        if len(dirnm)==0:
            return
        items = self.tree.selectedItems()
        for item in items:
            if item.type()==1: #Directory
                self.downloadDirectory(directory=dirnm,item=item,dialog=dialog)
            elif item.type()==2: #Generic File (with multiple services)
                for j in range(item.childCount()):
                    txt = str(item.child(j).text(0))
                    sp = txt.split("@")
                    service=sp[0].strip()
                    url=sp[1].split()[0]
                    nm=url.split("/")[-1]
                    if service == "HTTPServer":
                        dialog.addDownload("",nm,self.httpDownloadFile(url,os.path.join(dirnm,nm)))
            elif item.type()==3: #Service selected
                txt=str(item.text(0))
                sp=txt.split("@")
                service=sp[0].strip()
                url=sp[1].split()[0]
                nm=url.split("/")[-1]
                if service == "HTTPServer":
                    dialog.addDownload("",nm,self.httpDownloadFile(url,os.path.join(dirnm,nm)))
        dialog.exec_()
                
                
            
    def downloadDirectory(self,directory=None,item=None,dialog=None):
        show = False
        if dialog is None:
            dialog=QMultiDownloadProgressBar(self)
            show=True
        if directory is None:
            item = self.tree.currentItem()
            dirnm = str(QtGui.QFileDialog.getExistingDirectory(self))
            if len(dirnm)==0:
                return
        else:
            dirnm = directory
        for i in range(item.childCount()):
            child = item.child(i)
            if child.type()==1:
                newdirnm=os.path.join(dirnm,str(child.text(0)))
                try:
                    os.makedirs(newdirnm)
                except:
                    pass
                self.downloadDirectory(newdirnm,child,dialog)
            elif child.type()==2:
                for j in range(child.childCount()):
                    txt = str(child.child(j).text(0))
                    sp = txt.split("@")
                    service=sp[0].strip()
                    url=sp[1].split()[0]
                    nm=url.split("/")[-1]
                    if service == "HTTPServer":
                        dialog.addDownload("",nm,self.httpDownloadFile(url,os.path.join(dirnm,nm)))
        if show:
            dialog.exec_()
