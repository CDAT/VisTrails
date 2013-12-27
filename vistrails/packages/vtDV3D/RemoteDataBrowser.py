import urllib2, sys, os, copy, time, httplib
from HTMLParser import HTMLParser
from urlparse import *
from PyQt4 import QtCore, QtGui
from vtUtilities import isList
#useWebKit = False
    
#        split_url = urlsplit(catalog_url) urlunsplit(split_url)

#class HTMLState:
#    HTML = 0
#    Header = 1
#    Body = 2
#    Table = 3
#    TableRow = 4
#    Anchor = 5

def url_exists(site, path ):
    conn = httplib.HTTPConnection(site)
    conn.request('HEAD', path)
    response = conn.getresponse()
    conn.close()
    return response.status == 200

def displayMessage( msg ):
    msgBox = QtGui.QMessageBox()
    msgBox.setText( msg )
    msgBox.exec_()
       
class ServerType:
    THREDDS = QtGui.QTreeWidgetItem.UserType + 1
    DODS = QtGui.QTreeWidgetItem.UserType + 2
    HYDRAX = QtGui.QTreeWidgetItem.UserType + 3

    @classmethod    
    def getType( cls, url ):
        tokens = url.split('/')
        for token in tokens:
            if token.upper() == 'THREDDS': return cls.THREDDS
            if token.lower() == 'dods': return cls.DODS
            if token.lower() == 'opendap': return cls.HYDRAX
        return QtGui.QTreeWidgetItem.UserType
    
class CatalogNode( QtGui.QTreeWidgetItem ):
    Directory = 0
    DataObject = 1
    Style = None
    
    def __init__( self, url, widget = None ):
         self.parser = None
         self.server_type = ServerType.getType( url )
         self.url = url
         if widget: 
            QtGui.QTreeWidgetItem.__init__( self, widget, self.server_type  )
            CatalogNode.Style = widget.style() 
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DriveNetIcon ) ) 
            self.setText( 0, "%s Catalog (%s)" % ( self.getCatalogType(), self.url ) )
            self.node_type = self.Directory
         else: 
             QtGui.QTreeWidgetItem.__init__( self, self.server_type  ) 
             
    def isTopLevel(self): 
        return ( self.parent() == None )
         
    def setLabel( self, text ):
        if text.endswith( '/' ) or text.endswith( '/:' ):     
            self.node_type = self.Directory
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DirIcon) )
        else:                   
            self.node_type = self.DataObject
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_FileIcon) )
        self.setText( 0, text.strip('/') )
        
    def getNodeType(self):
        if self.node_type == self.Directory: return "Directory"
        if self.node_type == self.DataObject: return "DataObject"
        return "None"

    def getCatalogType(self):
        if self.type() == ServerType.THREDDS: return "THREDDS"
        if self.type() == ServerType.DODS: return "DODS"
        if self.type() == ServerType.HYDRAX: return "HYDRAX"
        return "Undefined"
                    
    def retrieveContent(self): 
        if self.parser == None:
            if self.node_type == self.Directory: 
                if     self.type() == ServerType.THREDDS:   self.parser = ThreddsDirectoryParser( self ) 
                elif   self.type() == ServerType.DODS:      self.parser = DodsDirectoryParser( self ) 
                elif   self.type() == ServerType.HYDRAX:    self.parser = HydraxDirectoryParser( self ) 
                else:  displayMessage( "Error, unrecognized or unimplemented Server type."  )
            else:
                if     self.type() == ServerType.THREDDS:   self.parser = ThreddsDataElementParser( self.url ) 
                elif   self.type() == ServerType.DODS:      self.parser = DodsDataElementParser( self.url ) 
                elif   self.type() == ServerType.HYDRAX:      self.parser = HydraxDataElementParser( self.url ) 
                else:  displayMessage( "Error, unrecognized or unimplemented Server type."  )      
            if self.parser:
                self.parser.execute() 
                return ( self.parser.data_url, self.parser.metadata ) 
        return ( None, None ) if ( self.node_type == self.Directory ) else ( self.parser.data_url, self.parser.metadata )
       
    def __repr__(self): 
        return " %s Node: '%s' <%s>" % ( self.getNodeType(), str(self.text(0)), self.url )

class HTMLCatalogParser(HTMLParser):
   
    def __init__( self, **args ):
        HTMLParser.__init__( self )    
        self.IgnoredTags = [ 'br', 'hr', 'p' ]
        self.debug_mode = args.get( 'debug', False)
        self.state_stack = [ 'root' ]
        self.data_url = None
        self.metadata = None
        
    def execute(self):
        pass

    def dump(self):
        pass
        
    def state(self,frame=0):
        return self.state_stack[ -1-frame ]
    
    def has_state( self, state ):
        return state in self.state_stack        
            
    def handle_starttag(self, tag, attrs):
        if tag not in self.IgnoredTags:
            self.state_stack.append( tag )
            if self.debug_mode: 
                print " Start Tag %s: %s " % ( tag, str( attrs ) ) 
            self.process_start_tag( tag, attrs )           
    
    @staticmethod           
    def get_attribute( tag, attrs ):
        for item in attrs:
            if tag == item[0]: return item[1]
        return None
        
    def handle_endtag(self, tag):
        stack_backup = copy.deepcopy( self.state_stack )
        if tag not in self.IgnoredTags:
            while True: 
                try:
                    frame = self.state_stack.pop()
                except Exception, err:
                    print " <<<<<<<<<<<<<<<<<<< Parse error processing end tag: %s, state stack: %s >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>" % ( tag, str(stack_backup) )
                    self.state_stack = stack_backup
                    return
                if frame == tag: break
            if self.debug_mode: print " End Tag %s " % ( tag )
            self.process_end_tag( tag )              
        
    def handle_data( self, data ):
        sdata = data.strip()
        if self.debug_mode: print "                      State: %s, Data: %s " % ( str(self.state_stack), sdata )           
        self.process_data( sdata )
            
    def process_start_tag( self, tag, attrs ):
        pass   

    def process_end_tag( self, tag ):
        pass   

    def process_data( self, data ):
        pass   

class ThreddsDirectoryParser(HTMLCatalogParser):
    
    def __init__( self, base_node, **args ):
        HTMLCatalogParser.__init__( self, **args )    
        self.child_node = None
        self.root_node = base_node

    def execute(self):
        try:
            response = urllib2.urlopen( self.root_node.url )
            self.feed( response.read() )
        except Exception, err:
            displayMessage( "Error connecting to server:\n%s"  % str(err) )

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


class DodsDirectoryParser(HTMLCatalogParser):
    
    def __init__( self, base_node, **args ):
        HTMLCatalogParser.__init__( self, **args )    
        self.root_node = base_node
        self.row_index = 1
        self.current_data = None

    def execute(self):
        try:
            response = urllib2.urlopen( self.root_node.url )
            self.feed( response.read() )
        except Exception, err:
            displayMessage( "Error connecting to server:\n%s"  % str(err) )
                    
    def process_start_tag( self, tag, attrs ):       
        if ( tag == 'a' ) :
            url = self.get_attribute( 'href', attrs )
            if url and self.current_data: 
                child_node = CatalogNode( urljoin( self.root_node.url, url ) )
                child_node.setLabel( ' '.join( self.current_data ) )
                self.root_node.addChild ( child_node )
#                print "Adding Child:", str( child_node )
                self.current_data = None
                self.row_index = self.row_index + 1

    def process_data( self,  data ): 
#        print " ----> Data: %s, state = %s " % ( data, str( self.state_stack ) )
        data = data.strip().replace( '\n', ' ' )
        if self.has_state( 'body' ) and data.startswith( "%d:" % self.row_index ): 
            self.current_data = [ data ]
        elif data and self.current_data: self.current_data.append( data )

class HydraxDirectoryParser(HTMLCatalogParser):
    
    def __init__( self, base_node, **args ):
        HTMLCatalogParser.__init__( self, **args )    
        self.root_node = base_node
        self.current_url = None
        self.excluded_links = [ 'ddx', 'dds', 'das', 'info', 'html', 'viewers', 'parent directory/', 'rdf', 'doc', 'thredds catalog', 'xml', 'nsf', 'nasa', 'noaa' ]

    def execute(self):
        try:
            response = urllib2.urlopen( self.root_node.url )
            self.feed( response.read() )
        except Exception, err:
            displayMessage( "Error connecting to server:\n%s"  % str(err) )
                    
    def process_start_tag( self, tag, attrs ): 
        if ( tag == 'a' ) and self.has_state( 'td' ) and not self.has_state( 'div' ):
#            print " Anchor start tag: %s, state: %s "  % ( str( attrs ), str( self.state_stack ) )    
            self.current_url = self.get_attribute( 'href', attrs )

    def process_data( self,  data ):
        data = data.strip().replace( '\n', ' ' )
        if self.current_url and data:
            if ( data.lower() not in self.excluded_links ): 
                child_node = CatalogNode( urljoin( self.root_node.url, self.current_url ) )
                child_node.setLabel( data )
                self.root_node.addChild( child_node )
            self.current_url = None

class ThreddsDataElementParser(HTMLCatalogParser):
    
    def __init__( self, url, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_url = url 
        self.processHref = False  

    def execute(self):
        response = urllib2.urlopen( self.base_url )
        data = response.read()
        self.feed( data )

    def process_start_tag( self, tag, attrs ): 
        if self.processHref and (tag == 'a'):
           url = self.get_attribute( 'href', attrs )
           metadata_url = urljoin( self.base_url, url )
           md_parser = ThreddsMetadataParser( metadata_url )
           md_parser.execute()
           self.metadata = md_parser.getMetadata()
                               
    def process_data( self,  data ): 
        if ( data.find('OPENDAP:') >= 0 ) and self.has_state( 'li' ):
            self.processHref = True  
        elif self.processHref and self.has_state( 'li' ): 
            if self.has_state( 'a' ):
                self.data_url =  urljoin( self.base_url, data )     
                self.processHref = False

class ThreddsMetadataParser(HTMLCatalogParser):

    
    def __init__( self, url, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_url = url
        self.metadata = [ "<html><head><title>Metadata</title></head><body><p><h1>Metadata</h1><p><hr><p>" ] 
        self.md_decl = False
        self.md_text = False

    def execute(self):
        response = urllib2.urlopen( self.base_url )
        data = response.read()
        self.metadata.append( '</body></html>')
        self.feed( data )

    def getMetadata(self):
        return ' '.join( self.metadata )

    def process_start_tag( self, tag, attrs ): 
        if (tag == 'input'):
           input_type = self.get_attribute( 'type', attrs )
           if input_type == 'checkbox': 
               self.md_decl = True
               self.metadata.append( '<p>') 
        if (tag == 'textarea'):
            self.md_text = True       
            self.metadata.append( '<p>') 

    def process_end_tag( self, tag ):
        if (tag == 'textarea'):
            self.md_text = False
            self.md_decl = False
            self.metadata.append( '<p><hr><p>') 
                               
    def process_data( self,  data ): 
        if self.md_text:       
            self.metadata.append( "<pre>%s</pre>" % data ) 
        elif self.md_decl: 
            if self.has_state('font'):  self.metadata.append( '<strong>%s</strong>' % data )     
            else:                       self.metadata.append( data )

class HydraxMetadataParser(HTMLCatalogParser):
    
    def __init__( self, html_form_data, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.raw_html = html_form_data
        self.metadata = [ "<html><head><title>Metadata</title></head><body><p><h1>Metadata</h1><p><hr><p>" ] 
        self.md_decl = False
        self.md_text = False

    def execute(self):
        self.feed( self.raw_html )
        self.metadata.append( '</body></html>')

    def getMetadata(self):
        return ' '.join( self.metadata )

    def process_start_tag( self, tag, attrs ): 
        if (tag == 'input'):
           input_type = self.get_attribute( 'type', attrs )
           if input_type == 'checkbox': 
               self.md_decl = True
               self.metadata.append( '<p>') 
        if (tag == 'textarea'):
            self.md_text = True       
            self.metadata.append( '<p>') 

    def process_end_tag( self, tag ):
        if (tag == 'textarea'):
            self.md_text = False
            self.md_decl = False
            self.metadata.append( '<p><hr><p>') 
                               
    def process_data( self,  data ): 
        if self.md_text:       
            self.metadata.append( "<pre>%s</pre>" % data ) 
        elif self.md_decl: 
            if self.has_state('font'):  self.metadata.append( '<strong>%s</strong>' % data )     
            else:                       self.metadata.append( data )

class DodsDataElementParser(HTMLCatalogParser):
    
    def __init__( self, url, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_url = url 
        self.data_element_address = None
        self.processHref = False 
        self.completeListing = args.get( 'complete', False ) 

#    def process_start_tag( self, tag, attrs ):       
#        print "Start Tag %s: %s" % ( tag, str(attrs) )
        
    def execute(self):
        response = urllib2.urlopen( self.base_url )
        self.metadata = response.read()
        self.feed( self.metadata )
                    
    def process_data( self,  data ): 
#        print "Data: %s" % ( data )
        if ( data.find('Data URL') >= 0 ) and self.has_state( 'td' ):
            self.processHref = True  
        elif self.processHref and self.has_state( 'td' ): 
            if data.startswith("http:"):
                self.data_url =  urljoin( self.base_url, data )     
                self.processHref = False

class HydraxDataElementParser(HTMLCatalogParser):
    
    def __init__( self, url, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_url = url 
        self.processHref = False 

    def process_start_tag( self, tag, attrs ): 
        if self.processHref and tag == 'input':
            url = self.get_attribute( 'value', attrs )
            if url:     
                self.data_url =  urljoin( self.base_url, url )     
                self.processHref = False
        
    def execute(self):
        link = urllib2.urlopen( self.base_url )
        response = link.read()
        mdparser = HydraxMetadataParser( response )
        mdparser.execute()
        self.metadata = mdparser.getMetadata()
        self.feed( response )
                    
    def process_data( self,  data ): 
        if ( data.find('Data URL') >= 0 ) and self.has_state( 'td' ):
            self.processHref = True  
                    
class RemoteDataBrowser(QtGui.QFrame):
    new_data_element = QtCore.SIGNAL("new_data_element")
    server_file_path = os.path.expanduser( '~/.vistrails/remote_server_list' )
    default_server_list = [ 'http://nomads.ncep.noaa.gov:80/dods/' ]

    def __init__( self, parent = None, **args ):
        QtGui.QFrame.__init__( self, parent )
        self.inputDialog = QtGui.QInputDialog()
        self.autoRetrieveBaseCatalogs = args.get("autoretrieve",False)
        self.data_element_address = None
        self.metadata = None
        self.treeWidget = QtGui.QTreeWidget()
        self.treeWidget.setColumnCount(1)
        self.treeWidget.setMinimumHeight( 250 )
        self.treeWidget.connect( self.treeWidget, QtCore.SIGNAL("itemClicked(QTreeWidgetItem *,int)"), self.retrieveItem ) 
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
                
        layout.addWidget( self.treeWidget )
        self.setWindowTitle( "Remote Data Browser" )
        self.treeWidget.setHeaderLabel ( "Data Servers" )

#         if useWebKit: 
#             from PyQt4 import QtWebKit  
#             self.view = QtWebKit.QWebView( self ) 
#             self.textFrame = self.view 
          
        self.view = QtGui.QTextDocument( self )
        self.textFrame = QtGui.QTextEdit()
        self.textFrame.setDocument ( self.view )
       
        f = QtGui.QFrame( self )
        f.setFrameStyle( QtGui.QFrame.StyledPanel | QtGui.QFrame.Raised )
        f.setLineWidth(2)
        f_layout = QtGui.QVBoxLayout(f)
        f.setLayout( f_layout )
        f_layout.addWidget( self.textFrame )
        layout.addWidget( f )
                
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

        self.useCloseButton = args.get( 'closeButton', False )
        if self.useCloseButton:
            close_button = QtGui.QPushButton( "Close"  )       
            button_list_layout.addWidget( close_button )       
            self.connect( close_button, QtCore.SIGNAL('clicked(bool)'), self.close)

        self.load_mdata_button = QtGui.QPushButton( "Show Metadata"  )   
        self.load_mdata_button.setToolTip( "Display complete metadata listing")        
        self.connect( self.load_mdata_button, QtCore.SIGNAL('clicked(bool)'), self.loadMetadata )
#        button_list_layout.addWidget( self.load_mdata_button )
        self.load_mdata_button.setEnabled ( False )

        self.load_data_button = QtGui.QPushButton( "Open"  )   
        self.load_data_button.setToolTip( "Open Selected Dataset in UVCDAT")        
        self.connect( self.load_data_button, QtCore.SIGNAL('clicked(bool)'), self.loadData )
        button_list_layout.addWidget( self.load_data_button )
        self.load_data_button.setEnabled ( False )
        
        layout.addLayout( button_list_layout )
        self.initServerFile()
        self.readServerList()
     
    def readServerList( self ):
        try:    server_file = open( self.server_file_path )
        except: return
        while True:
            input_line = server_file.readline()
            if not input_line: break
            address_rec = input_line.strip().split(',')
            address = address_rec[-1] 
            base_node = CatalogNode( str(address), self.treeWidget ) 
            if self.autoRetrieveBaseCatalogs: base_node.retrieveContent() 
        server_file.close()               

    def updateServerList( self ):
        try:    server_file = open( self.server_file_path, "w" )
        except: return
        nservers = self.treeWidget.topLevelItemCount() 
        for si in range( nservers ):
            serverItem = self.treeWidget.topLevelItem( si )
            server_file.write( serverItem.url + "\n" )
        server_file.close()

    def initServerFile( self ):
        if not os.path.isfile( self.server_file_path ):
            try:    server_file = open( self.server_file_path, "w" )
            except: return
            for server in self.default_server_list:
                server_file.write( server + "\n" )
            server_file.close()
                                       
    def addNewServer(self): 
        url, ok = self.inputDialog.getText( self, 'Add OpenDap Server', 'Enter new server url:')     
        if ok and url:
            base_node = CatalogNode( str(url), self.treeWidget ) 
            if self.autoRetrieveBaseCatalogs: base_node.retrieveContent() 
            self.updateServerList()
    
    @staticmethod          
    def notify( msg ):
            QtGui.QMessageBox.information( self, "RemoteDataBrowser", msg )
        
    def removeSelectedServer(self): 
        currentItem = self.treeWidget.currentItem()
        if currentItem and currentItem.isTopLevel(): 
            removed_item = self.treeWidget.takeTopLevelItem( self.treeWidget.indexOfTopLevelItem( currentItem ) )
            del removed_item
            self.updateServerList()
        else:
            self.notify( "Must select a server." )
            self.discard_server_button.setEnabled ( False )
                
    def retrieveItem( self, item, index ):
        self.discard_server_button.setEnabled( item.isTopLevel() )
        try:
            (self.data_element_address, self.metadata) = item.retrieveContent()
            if self.metadata:
                self.view.setHtml( self.metadata )
        except Exception, err:
            print>>sys.stderr, "Error retrieving data item: %s\n Item: %s" % ( str(err), str(item) )
            (self.data_element_address, self.metadata) = ( None, None )
        self.load_data_button.setEnabled ( self.data_element_address <> None ) 
#        self.load_mdata_button.setEnabled( self.data_element_address <> None ) 
           
    def loadData( self ):
        self.emit(  self.new_data_element, self.data_element_address )
        print "Loading URL: ", self.data_element_address

    def loadMetadata( self ):
        pass

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
