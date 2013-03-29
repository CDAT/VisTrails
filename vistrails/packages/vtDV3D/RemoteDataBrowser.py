
import urllib2, sys, os
from HTMLParser import HTMLParser
from urlparse import *
from PyQt4 import QtCore, QtGui
#        split_url = urlsplit(catalog_url) urlunsplit(split_url)

#class HTMLState:
#    HTML = 0
#    Header = 1
#    Body = 2
#    Table = 3
#    TableRow = 4
#    Anchor = 5
    
class CatalogNodeType:
    THREDDS = QtGui.QTreeWidgetItem.UserType + 1

    @classmethod    
    def getType( cls, url ):
        if ( url.upper().find('THREDDS') >= 0 ): return cls.THREDDS
        return QtGui.QTreeWidgetItem.UserType
    
class CatalogNode( QtGui.QTreeWidgetItem ):
    Directory = 0
    DataObject = 1
    Style = None
    
    def __init__( self, url, widget = None ):
         self.parser = None
         self.node_type = CatalogNodeType.getType( url )
         self.url = url
         if widget: 
            QtGui.QTreeWidgetItem.__init__( self, widget, self.node_type  )
            CatalogNode.Style = widget.style() 
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DriveNetIcon ) ) 
            self.setText( 0, "%s Catalog (%s)" % ( self.getCatalogType(), self.url ) )
            self.node_type = self.Directory
         else: 
             QtGui.QTreeWidgetItem.__init__( self, self.node_type  )  
         
    def setLabel( self, text ):
        if text[-1] == '/':     
            self.node_type = self.Directory
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DirIcon) )
        else:                   
            self.node_type = self.DataObject
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_FileIcon) )
        self.setText( 0, text.strip('/') )
        
    def getType(self):
        if self.node_type == self.Directory: return "Directory"
        if self.node_type == self.DataObject: return "DataObject"
        return "None"

    def getCatalogType(self):
        if self.type() == CatalogNodeType.THREDDS: return "THREDDS"
        return "Undefined"
                    
    def retrieveContent(self): 
        if self.parser == None:
            if self.node_type == self.Directory: 
                if self.type() == CatalogNodeType.THREDDS: self.parser = ThreddsDirectoryParser( self ) 
                else: print>>sys.stderr, "Error, unimplemented Catalog type: %d " % self.type()
            else:
                if self.type() == CatalogNodeType.THREDDS: self.parser = ThreddsDataElementParser( self.url ) 
                else: print>>sys.stderr, "Error, unimplemented Catalog type: %d " % self.type()
            
            if self.parser: return self.parser.execute()
            return None
       
    def __repr__(self): 
        return " %s Node: '%s' <%s>" % ( self.getType(), str(self.text(0)), self.url )

class HTMLCatalogParser(HTMLParser):
    
    def __init__( self ):
        HTMLParser.__init__( self )    
        self.debug_mode = False
        self.state_stack = [ 'root' ]
        
    def execute(self):
        return None

    def dump(self):
        pass
        
    def state(self,frame=0):
        return self.state_stack[ -1-frame ]
    
    def has_state( self, state ):
        return state in self.state_stack        
            
    def handle_starttag(self, tag, attrs):
        self.state_stack.append( tag )
        if self.debug_mode:
            print " Start Tag %s: %s " % ( tag, str( attrs ) )
        else: 
            self.process_start_tag( tag, attrs )           
    
    @staticmethod           
    def get_attribute( tag, attrs ):
        for item in attrs:
            if tag == item[0]: return item[1]
        return None
        
    def handle_endtag(self, tag):
        while True: 
            frame = self.state_stack.pop()
            if frame == tag: break
        if self.debug_mode:
            print " End Tag %s " % ( tag )
        else:
            self.process_end_tag( tag )              
        
    def handle_data( self, data ):
        if self.debug_mode:
            print " State: %s, Data: %s " % ( str(self.state_stack), data )           
        else:
            self.process_data( data )
            
    def process_start_tag( self, tag, attrs ):
        pass   

    def process_end_tag( self, tag ):
        pass   

    def process_data( self, data ):
        pass   

class ThreddsDirectoryParser(HTMLCatalogParser):
    
    def __init__( self, base_node ):
        HTMLCatalogParser.__init__( self )    
        self.child_node = None
        self.root_node = base_node

    def execute(self):
        response = urllib2.urlopen( self.root_node.url )
        self.feed( response.read() )
        return None

    def dump(self):
        print "Retreiving response from: ", self.root_node.url
        response = urllib2.urlopen( self.root_node.url )
        self.debug_mode = True
        data = response.read()
        print data
        self.feed( data ) 
        self.debug_mode = False
            
    def inCatalogEntry(self):
       return self.has_state( 'a' ) and self.has_state( 'tr' )
        
    def process_start_tag( self, tag, attrs ):          
        if ( tag == 'a' ) and self.has_state( 'tr' ):
            url = self.get_attribute( 'href', attrs )
            self.child_node = CatalogNode( urljoin( self.root_node.url, url ) )

    def process_data( self,  data ): 
        if self.child_node and self.inCatalogEntry() and data:         
            self.child_node.setLabel( data.strip() )
            self.root_node.addChild ( self.child_node )
#            print "Adding Child:", str( self.child_node )
            self.child_node = None

class ThreddsDataElementParser(HTMLCatalogParser):
    
    def __init__( self, url ):
        HTMLCatalogParser.__init__( self ) 
        self.base_url = url 
        self.data_element_address = None
        self.processHref = False  

    def execute(self):
        response = urllib2.urlopen( self.base_url )
        data = response.read()
        self.feed( data )
        return self.data_element_address
                    
    def process_data( self,  data ): 
        if ( data.upper().find('OPENDAP') >= 0 ) and self.has_state( 'li' ):
            self.processHref = True  
#            print " >>>> Data Parser Data Tag: data=%s, state=%s  " % ( str( data.strip() ), str( self.state_stack ) )
        elif self.processHref: 
#            print " >>>> Data Parser Data Tag: %s" % ( data )
            if self.has_state( 'a' ):
                self.data_element_address =  urljoin( self.base_url, data )     
#                print " >>>> Data Parser URL: %s " % ( self.data_element_address )
                self.processHref = False
                    
class RemoteDataBrowser(QtGui.QWidget):
    new_data_element = QtCore.SIGNAL("new_data_element")
    server_file_path = os.path.expanduser( '~/.vistrails/remote_server_list' )

    def __init__( self, parent = None, **args ):
        QtGui.QFrame.__init__( self, parent )
        self.inSync = True
        self.inputDialog = QtGui.QInputDialog()
#        self.inputDialog.setMinimumWidth( 500 )
        self.treeWidget = QtGui.QTreeWidget()
        self.treeWidget.setColumnCount(1)
        self.treeWidget.connect( self.treeWidget, QtCore.SIGNAL("itemClicked(QTreeWidgetItem *,int)"), self.retrieveItem ) 
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
                
        layout.addWidget( self.treeWidget )
        self.setWindowTitle( "Remote Data Browser" )
        self.treeWidget.setHeaderLabel ( "Data Servers" )
                
        button_list_layout = QtGui.QHBoxLayout()
        
        new_server_button = QtGui.QPushButton( "New Server" )  
        new_server_button.setToolTip( "Add new OpenDAP server")  
        self.connect( new_server_button, QtCore.SIGNAL('clicked(bool)'), self.addNewServer )
        button_list_layout.addWidget( new_server_button )
             
        self.discard_server_button = QtGui.QPushButton( "Remove Server"  )   
        self.discard_server_button.setToolTip( "Remove selected OpenDAP server")        
        self.connect( self.discard_server_button, QtCore.SIGNAL('clicked(bool)'), self.removeSelectedServer )
        button_list_layout.addWidget( self.discard_server_button )
        self.discard_server_button.setEnabled ( False )

        useCloseButton = args.get( 'closeButton', False )
        if useCloseButton:
            close_button = QtGui.QPushButton( "Close"  )       
            button_list_layout.addWidget( close_button )       
            self.connect( close_button, QtCore.SIGNAL('clicked(bool)'), self.close)
        
        layout.addLayout( button_list_layout )
        self.readServerList()
     
    def readServerList( self ):
        try:    server_file = open( self.server_file_path )
        except: return
        while True:
            address = server_file.readline().strip()
            if not address: break
            base_node = CatalogNode( str(address), self.treeWidget ) 
            base_node.retrieveContent() 
        server_file.close()               

    def updateServerList( self ):
        try:    server_file = open( self.server_file_path, "w" )
        except: return
        nservers = self.treeWidget.topLevelItemCount() 
        for si in range( nservers ):
            serverItem = self.treeWidget.topLevelItem( si )
            server_file.write( serverItem.url + "\n" )
        server_file.close()
        self.inSync = True 
        
    def close(self): 
        if not self.inSync: self.updateServerList()
        QtGui.QDialog.close( self ) 
                               
    def addNewServer(self): 
        url, ok = self.inputDialog.getText( self, 'Add OpenDap Server', 'Enter new server url:')     
        if ok and url:
            base_node = CatalogNode( str(url), self.treeWidget ) 
            base_node.retrieveContent() 
            self.inSync = False
    
    @staticmethod          
    def notify( msg ):
            QtGui.QMessageBox.information( self, "RemoteDataBrowser", msg )
        
    def removeSelectedServer(self): 
        currentItem = self.treeWidget.currentItem()
#        treeWidget = currentItem.treeWidget()
        if currentItem: 
            removed_item = self.treeWidget.takeTopLevelItem( self.treeWidget.indexOfTopLevelItem( currentItem ) )
            del removed_item
            self.inSync = False
        else:
            self.notify( "Must select a server." )
            self.discard_server_button.setEnabled ( False )
                
    def retrieveItem( self, item, index ):
        treeWidget = item.treeWidget()
        self.discard_server_button.setEnabled ( treeWidget <> None )
        data_element_address = item.retrieveContent()
        if data_element_address: 
            self.emit(  self.new_data_element, data_element_address )
            print "Emit new_data_element signal: ", data_element_address
            self.close()

class RemoteDataBrowserDialog(QtGui.QDialog):

    def __init__( self, parent = None ):
        QtGui.QDialog.__init__( self, parent )
        self.browser = RemoteDataBrowser( self, closeButton = True )
        self.browser.setFixedSize( 500, 500 )
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget( self.browser )
                     
if __name__ == '__main__':   
    app = QtGui.QApplication(sys.argv)
    browser = RemoteDataBrowserDialog( ) # "http://dp6.nccs.nasa.gov/thredds/", CatalogNodeType.THREDDS )
    browser.show()
    app.exec_()
