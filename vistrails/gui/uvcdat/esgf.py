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
            
        
class QEsgfBrowser(QtGui.QDialog):
    def __init__(self,parent=None,mapping=None):
        QtGui.QDialog.__init__(self,parent)
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
        self.toolBar = QtGui.QToolBar()
        try:
            self.root=parent.root
        except:
            self.root=None
        self.toolBar.setIconSize(QtCore.QSize(customizeUVCDAT.iconsize, customizeUVCDAT.iconsize))
        actionInfo = [
            (self.searchIcon, 'Run Search',self.clickedSearch,True),
            (':/icons/resources/icons/db_add_256.ico', 'Add Gateway',self.userAddsGateway,True),
            (':/icons/resources/icons/binary-tree-icon.png', 'Edit Mapping',self.editMapping,True),
            (':/icons/resources/icons/floppy_disk_blue.ico', 'Save cache',self.userSaveCache,True),
            (self.loginIcon, 'Get Credentials',self.clickedCredentials,True),
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

        self.searchLine = uvcdatCommons.QLabeledWidgetContainer(QtGui.QLineEdit(),label="Search:",widgetSizePolicy=pol,labelSizePolicy=pol)
        self.searchLine.widget.setText("project=CMIP5&limit=100&experiment=historical")
        self.connect(self.searchLine.widget,QtCore.SIGNAL("returnPressed()"),self.clickedSearch)
        self.searchLine.widget.setToolTip("search fields must be separated by ; or &\nkeyword/value are separated by =\nexample: variable=ta&project=cmip5")
        vbox.addWidget(self.searchLine)

        hsp = QtGui.QSplitter(QtCore.Qt.Horizontal)

        self.QIndex = QEsgfIndex()
        hsp.addWidget(self.QIndex)
        
        self.tree = QtGui.QTreeWidget()
        self.tree.setSelectionMode(QtGui.QTreeWidget.ExtendedSelection)
        self.tree.setIconSize(QtCore.QSize(customizeUVCDAT.esgfTreeIconSize,customizeUVCDAT.esgfTreeIconSize))
        hsp.addWidget(self.tree)
        hsp.setSizes([200,600])
        self.index=[]
        self.nsearches=0
        self.cacheDir=os.path.join(os.environ["HOME"],"PCMDI_GRAPHICS")
        self.cache={}
        self.loadCache(self.cacheDir)
        vbox.addWidget(hsp)
        
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
                    f=cdms2.open(url[:-5])
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
                            
                    f.close()
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
                fnm = QtGui.QFileDialog.getSaveFileName(self,"NetCDF File",filter="NetCDF Files (*.nc *.cdg *.NC *.CDF *.nc4 *.NC4) ;; All Files (*.*)",options=QtGui.QFileDialog.DontConfirmOverwrite)
                if len(str(fnm))==0:
                    return
                pipe = self.httpDownloadFile(url,fnm)
                p=QMultiDownloadProgressBar(self)
                p.addDownload(url,fnm,pipe)
                p.exec_()

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
                            it.setToolTip(0,"You can download me")
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
        if mapping is None:
            mapping=self.mapping
        try:
            #print "Actual mapping:",self.mapping
            self.index.append(cdms2.esgfDataset(gateway,port=port,limit=limit,offset=offset,mapping=mapping,datasetids=datasetids,fileids=fileids,restPath=restPath))
            self.QIndex.addIndex("%s:%i" % (gateway,port))
        except Exception,err:
            m = QtGui.QMessageBox()
            m.setText(str(err))
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
                    keys[sp[0].strip()]=sp[1].strip()
                except:
                    pass
        return keys

    def clickedCredentials(self):
        self.credentials.show()
        
    def clickedSearch(self):
        query = str(self.searchLine.widget.text())
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
        for i in keys.items():
            query+="&%s=%s" % (i[0],i[1])
        if query!="":
            query="?"+query[1:]
        
        self.nsearches+=1
        self.createTreeSearchItem(files,"Search %i %s" % (self.nsearches,query))
        
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
        
