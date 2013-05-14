
import urllib2, sys, os, copy, time, httplib
from HTMLParser import HTMLParser
from urlparse import *
from PyQt4 import QtCore, QtGui, QtWebKit
from vtUtilities import displayMessage

iRODS_enabled = True
try:    from irods import *
except Exception, err: 
    iRODS_enabled = False

import irods    
print "IRODS API:\n", str( dir(irods) )
sys.stdout.flush()

def getIRodsEnv():
    if not iRODS_enabled: return None
    rvals = getRodsEnv()
    for val in rvals:
        if type(val) <> type(4):
            return val


#        split_url = urlsplit(catalog_url) urlunsplit(split_url)

#class HTMLState:
#    HTML = 0
#    Header = 1
#    Body = 2
#    Table = 3
#    TableRow = 4
#    Anchor = 5

def url_exists2(site, path ):
    conn = httplib.HTTPConnection(site)
    conn.request('HEAD', path)
    response = conn.getresponse()
    conn.close()
    return response.status == 200

def url_exists( url ):
    try: conn = urllib2.urlopen(url)
    except: return False
    code = conn.getcode() 
    conn.close()
    return code == 200
       
class ServerType:
    THREDDS = QtGui.QTreeWidgetItem.UserType + 1
    DODS = QtGui.QTreeWidgetItem.UserType + 2
    HYDRAX = QtGui.QTreeWidgetItem.UserType + 3
    IRODS = QtGui.QTreeWidgetItem.UserType + 4
    REST = QtGui.QTreeWidgetItem.UserType + 5

    @classmethod    
    def getType( cls, address ):
        if address.count(';') >= 3:
           return cls.IRODS
        else: 
            tokens = address.split('/')
            for token in tokens:
                if token.upper() == 'THREDDS': return cls.THREDDS
                if token.lower() == 'dods': return cls.DODS
                if token.lower() == 'opendap': return cls.HYDRAX 
            return QtGui.QTreeWidgetItem.UserType

    @classmethod    
    def getTypeStr( cls, type ):
        if type == cls.THREDDS: return "THREDDS"
        if type == cls.DODS: return "DODS"
        if type == cls.HYDRAX: return "HYDRAX"
        if type == cls.IRODS: return "IRODS"
        if type == cls.REST: return "REST"
        return "Undefined"

class ServerClass:
    OPENDAP = 0
    IRODS = 1
    
    @classmethod    
    def getStr( cls, server_class ):
        if server_class == cls.OPENDAP: return "OPENDAP"
        if server_class == cls.IRODS: return "IRODS"

    @classmethod    
    def getIndex( cls, server_str ):
        if server_str == "OPENDAP": return cls.OPENDAP
        if server_str == "IRODS": return cls.IRODS

class NewServerDialog(QtGui.QDialog):
    UNDEF = -1
    
    def __init__( self, parent ):
        QtGui.QDialog.__init__(self, parent)        
        self.setWindowTitle('Select New Server')
        self.address = None
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        self.serverClass = NewServerDialog.UNDEF

        self.serverTypeTabbedWidget = QtGui.QTabWidget()
        layout.addWidget( self.serverTypeTabbedWidget )

        opendapTab = QtGui.QWidget()  
        opendapTabLayout = QtGui.QHBoxLayout()  
        url_label = QtGui.QLabel( "Server URL:"  )
        opendapTabLayout.addWidget( url_label ) 
        self.OpenDAPServer = QtGui.QLineEdit( self )
        opendapTabLayout.addWidget( self.OpenDAPServer )              
        opendapTab.setLayout( opendapTabLayout )        
        self.serverTypeTabbedWidget.addTab( opendapTab, ServerClass.getStr( ServerClass.OPENDAP ) ) 

        if iRODS_enabled:
            myEnv = getIRodsEnv() 
            iRODSTab = QtGui.QWidget()  
            iRODSTabLayout = QtGui.QGridLayout()        
            rodsHostLabel = QtGui.QLabel("iRods Host:", iRODSTab)
            iRODSTabLayout.addWidget( rodsHostLabel, 0, 0 )
            print " Env methods: ", str( dir(myEnv) ); sys.stdout.flush()
            rhost = myEnv.rodsHost if hasattr(myEnv,'rodsHost') else myEnv.getRodsHost()
            self.RodsHost = QtGui.QLineEdit( rhost, iRODSTab )
            iRODSTabLayout.addWidget( self.RodsHost, 0, 1 )
            
            rodsPortLabel = QtGui.QLabel("iRods Port:", iRODSTab)
            iRODSTabLayout.addWidget( rodsPortLabel, 1, 0 )
            rPort = myEnv.rodsPort if hasattr(myEnv,'rodsPort') else myEnv.getRodsPort()
            self.RodsPort = QtGui.QLineEdit( str (rPort), iRODSTab )
            iRODSTabLayout.addWidget( self.RodsPort, 1, 1 )

            rodsUserNameLabel = QtGui.QLabel("iRods User Name:", iRODSTab)
            iRODSTabLayout.addWidget( rodsUserNameLabel, 2, 0 )
            rUserName = myEnv.rodsUserName if hasattr(myEnv,'rodsUserName') else myEnv.getRodsUserName()
            self.RodsUserName = QtGui.QLineEdit( rUserName, iRODSTab )
            iRODSTabLayout.addWidget( self.RodsUserName, 2, 1 )

            rodsZoneLabel = QtGui.QLabel("iRods Zone:", iRODSTab)
            iRODSTabLayout.addWidget( rodsZoneLabel, 3, 0 )
            rZone = myEnv.rodsZone if hasattr(myEnv,'rodsZone') else myEnv.getRodsZone()
            self.RodsZone = QtGui.QLineEdit( rZone,  iRODSTab )
            iRODSTabLayout.addWidget( self.RodsZone, 3, 1 )            
                   
            iRODSTab.setLayout( iRODSTabLayout )        
            NewServerDialog.IRODS = self.serverTypeTabbedWidget.addTab( iRODSTab, ServerClass.getStr( ServerClass.IRODS ) )         
        
        # Add ok/cancel buttons
        buttonLayout = QtGui.QHBoxLayout()
        buttonLayout.setMargin(5)
        self.okButton = QtGui.QPushButton('&OK', self)
        self.okButton.setAutoDefault(False)
        self.okButton.setFixedWidth(100)
        buttonLayout.addWidget(self.okButton)
        self.cancelButton = QtGui.QPushButton('&Cancel', self)
        self.cancelButton.setAutoDefault(False)
        self.cancelButton.setShortcut('Esc')
        self.cancelButton.setFixedWidth(100)
        buttonLayout.addWidget(self.cancelButton)
        layout.addLayout(buttonLayout)
        self.connect(self.okButton, QtCore.SIGNAL('clicked(bool)'), self.okClicked )
        self.connect(self.cancelButton, QtCore.SIGNAL('clicked(bool)'), self.close ) 
        self.setMinimumWidth ( 500 ) 
        
    def okClicked(self):
        tab_index = self.serverTypeTabbedWidget.currentIndex()
        self.serverClass = ServerClass.getIndex( self.serverTypeTabbedWidget.tabText( tab_index ) )
        if self.serverClass == ServerClass.OPENDAP:
            self.address = str( self.OpenDAPServer.text() )
        elif self.serverTypeTabbedWidget.currentIndex() == ServerClass.IRODS:
            self.address = ';'.join( [ str( self.RodsHost.text() ), str( self.RodsPort.text() ), str( self.RodsUserName.text() ), str( self.RodsZone.text() ) ] )
        self.close()
#            if url_exists( self.address ): self.close()
#            else: displayMessage( "This does not appear to be a valid server address.")

    def getServerAddress(self):
        return self.address
    
    def getServerClass(self):
        return self.serverClass
      
class CatalogNode( QtGui.QTreeWidgetItem ):
    Directory = 0
    DataObject = 1
    Style = None
    
    def __init__( self, **args ):
         self.node_type = args.get( 'node_type', None )
         widget = args.get( 'widget', None )
         if widget: 
            QtGui.QTreeWidgetItem.__init__( self, widget, self.server_type  )
            CatalogNode.Style = widget.style() 
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DriveNetIcon ) ) 
            self.setText( 0, "%s Catalog (%s)" % ( ServerType.getTypeStr( self.type() ), self.getAddressLabel() ) )
         else: 
             QtGui.QTreeWidgetItem.__init__( self, self.server_type  ) 
             
    def loadData(self):
        pass
             
    def isTopLevel(self): 
        return ( self.parent() == None )
         
    def setLabel( self, text ):
        self.setNodeDisplay( text )               
         
    def getNodeType(self):
        if self.node_type == self.Directory: return "Directory"
        if self.node_type == self.DataObject: return "DataObject"
        return "None"

    def setNodeDisplay( self, text ):
        if self.node_type == self.Directory:  self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DirIcon) )
        if self.node_type == self.DataObject: self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_FileIcon) )
        self.setText( 0, text.strip('/') )

    def getCatalogType(self):
        return "Undefined"
                    
    def retrieveContent(self): 
        return ( None, None ) 
    
    def getAddressLabel(self):
        return ""
       
    def __repr__(self): 
        return " %s Node: '%s' <%s>" % ( self.getNodeType(), str(self.text(0)), self.getAddressLabel() )

class OpenDAPCatalogNode( CatalogNode ):
    server_class = None
    
    def __init__( self, **args ):
        self.server_class=ServerClass.OPENDAP
        self.parser = None
        self.address = args.get( "server_address", None )
        self.server_type = args.get( "server_type", ServerType.getType( self.address ) )
        CatalogNode.__init__( self, **args )
                                                  
    def retrieveContent(self): 
        if self.parser == None:
            if self.node_type == self.Directory: 
                if     self.type() == ServerType.THREDDS:   self.parser = ThreddsDirectoryParser( self ) 
                elif   self.type() == ServerType.DODS:      self.parser = DodsDirectoryParser( self ) 
                elif   self.type() == ServerType.HYDRAX:    self.parser = HydraxDirectoryParser( self ) 
                else:  displayMessage( "Error, unrecognized or unimplemented Server type."  )
            else:
                if     self.type() == ServerType.THREDDS:   self.parser = ThreddsDataElementParser( self.address ) 
                elif   self.type() == ServerType.DODS:      self.parser = DodsDataElementParser( self.address ) 
                elif   self.type() == ServerType.HYDRAX:    self.parser = HydraxDataElementParser( self.address ) 
                else:  displayMessage( "Error, unrecognized or unimplemented Server type."  )      
            if self.parser:
                self.parser.execute() 
                return ( self.parser.data_address, self.parser.metadata ) 
        return ( None, None ) if ( self.node_type == self.Directory ) else ( self.parser.data_address, self.parser.metadata )

    def setLabel( self, text ):
        if self.node_type == None: 
            hasDirTxt = ( text.endswith( '/' ) or text.endswith( '/:' ) )
            self.node_type = self.Directory if hasDirTxt else self.DataObject 
        self.setNodeDisplay( text )               
    
    def getAddressLabel(self):
        return self.address

class iRodsCatalogNode( CatalogNode ):
    Directory = 0
    DataObject = 1
    Style = None

    
    def __init__( self, **args ):
        self.server_class=ServerClass.IRODS
        self.server_type = ServerType.IRODS
        self.server_address = args.get('server_address',None)
        CatalogNode.__init__( self, **args )
        self.catalog_path = args.get( 'catalog_path','' )   
        self.download_dir = args.get( 'download_dir','/tmp/' )        
        self.server_conn = args.get('conn',None)
        self.collection = None
        self.metadata = None
        self.localFilePath = None

    def getFileMetadata( self ): 
        if self.metadata == None:
            path = self.getIRodsPath()
            try:    f = irodsOpen( self.server_conn, path, 'r' )
            except: f = iRodsOpen( self.server_conn, path, 'r' )
            if f:
#                print "Reading Metadata for file", path
#                print "File Methods: \n", str( dir(f) )
                strList = [] 
                strList.append( "File Name = %s" % f.getName() )
                strList.append( "File Path = %s" % f.getPath() )
                strList.append( "Owner Name = %s" % f.getOwnerName() )
                strList.append( "Size = %s" % f.getSize() )
                mdataList = getFileUserMetadata( self.server_conn, path ) 
                for mdataItem in mdataList:
                    mdname = mdataItem[0].replace( '_', ' ' ).title()
                    if mdataItem[2]:    strList.append( "%s = %s (%s)" % ( mdname, mdataItem[1], mdataItem[2]) )
                    else:               strList.append( "%s = %s" % ( mdname, mdataItem[1] ) )
                            
                self.metadata = '<p>'.join(strList)
                f.close()
            else: print>>sys.stderr, " Error, Can't open Data Object: ", path
        
    def __del__(self):
        if self.server_conn:
            print "Disconnecting."
            self.server_conn.disconnect()
            self.server_conn = None
                                 
    def retrieveContent(self):
        mdata = None
        data_path = None
        if not self.collection:
            if self.server_conn == None: 
                node_tokens = self.server_address.split(';')
                self.server_conn, errMsg = rcConnect( node_tokens[0], int(node_tokens[1]), node_tokens[2], node_tokens[3] )
                status = clientLogin( self.server_conn )
            if self.node_type == self.Directory:
                self.collection = irodsCollection( self.server_conn )
                path_tokens = self.catalog_path.split('/')
                for subCollection in path_tokens:
                    if subCollection: self.collection.openCollection(subCollection)
                subCollections = self.collection.getSubCollections()
                for subCollection in subCollections:
                    rv = self.collection.openCollection(subCollection)
                    path = '/'.join( [ self.catalog_path, subCollection] )
                    catalogNode = iRodsCatalogNode( conn=self.server_conn, catalog_path=path, node_type=CatalogNode.Directory )
                    catalogNode.setLabel( subCollection )
                    self.addChild ( catalogNode )
                    self.collection.upCollection()
                dataObjRefs = self.collection.getObjects()
                for dataObjRef in dataObjRefs:
                    data_name = dataObjRef[0]
                    resc_name = dataObjRef[1]
                    path = '/'.join( [ self.catalog_path, data_name] )
                    dataObj = self.collection.open( data_name, "r", resc_name )
                    dataObjNode = iRodsCatalogNode( conn=self.server_conn, catalog_path=path, node_type=CatalogNode.DataObject )
                    dataObjNode.setLabel( data_name )
                    self.addChild ( dataObjNode )
                    self.collection.upCollection()
                if self.collection: mdata = self.collection.getUserMetadata() 
            elif self.node_type == self.DataObject:
                self.getLocaPath()
                self.getFileMetadata()    
        return ( self.localFilePath, self.metadata )
    
    def getLocaPath(self):
        irods_path = self.getIRodsPath().strip('/')
        self.localFilePath = os.path.join( self.download_dir, irods_path )
        dirname = os.path.dirname( self.localFilePath )
        try: os.makedirs( dirname )
        except OSError, err: 
            if not os.path.isdir(dirname): print>>sys.stderr, "Error creating directory %s: %s " % ( dirname, str(err) )
                
    def getIRodsPath(self):
        myEnv = getIRodsEnv()
        rHome = myEnv.rodsHome if hasattr(myEnv,'rodsHome') else myEnv.getRodsHome()
        irods_path = rHome + self.catalog_path 
        return irods_path             
          
    def loadData( self ):
        status = -1
        if self.localFilePath and not os.path.exists( self.localFilePath ):
            dataObjInp = dataObjInp_t()
#            print "Data Object Methods: \n", str( dir(dataObjInp) )
            dataObjInp.objPath = self.getIRodsPath() 
            status = rcDataObjGet( self.server_conn, dataObjInp, self.localFilePath ) 
        return status
    
    def getAddressLabel(self):
        if self.server_address:
            address_tokens = self.server_address.split(';')
            return "%s:%s/%s" % ( address_tokens[0], address_tokens[1], address_tokens[3] )
        return self.catalog_path
                    
class HTMLCatalogParser(HTMLParser):
   
    def __init__( self, **args ):
        HTMLParser.__init__( self )    
        self.IgnoredTags = [ 'br', 'hr', 'p' ]
        self.debug_mode = args.get( 'debug', False)
        self.state_stack = [ 'root' ]
        self.data_address = None
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
            response = urllib2.urlopen( self.root_node.address )
            self.feed( response.read() )
        except Exception, err:
            displayMessage( "Error connecting to server:\n%s"  % str(err) )

    def dump(self):
        print "Retreiving response from: ", self.root_node.address
        response = urllib2.urlopen( self.root_node.address )
        self.debug_mode = True
        data = response.read()
        print data
        self.feed( data ) 
        self.debug_mode = False
            
    def inCatalogEntry(self):
       return self.has_state( 'a' ) and self.has_state( 'tr' )
        
    def process_start_tag( self, tag, attrs ):          
        if ( tag == 'a' ) and self.has_state( 'tr' ):
            address = self.get_attribute( 'href', attrs )
            self.child_node = OpenDAPCatalogNode( server_address=urljoin( self.root_node.address, address ) )

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
            response = urllib2.urlopen( self.root_node.address )
            self.feed( response.read() )
        except Exception, err:
            displayMessage( "Error connecting to server:\n%s"  % str(err) )
                    
    def process_start_tag( self, tag, attrs ):       
        if ( tag == 'a' ) :
            address = self.get_attribute( 'href', attrs )
            if address and self.current_data: 
                child_node = OpenDAPCatalogNode( server_address=urljoin( self.root_node.address, address ) )
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
        self.current_address = None
        self.excluded_links = [ 'ddx', 'dds', 'das', 'info', 'html', 'viewers', 'parent directory/', 'rdf', 'doc', 'thredds catalog', 'xml', 'nsf', 'nasa', 'noaa' ]

    def execute(self):
        try:
            response = urllib2.urlopen( self.root_node.address )
            self.feed( response.read() )
        except Exception, err:
            displayMessage( "Error connecting to server:\n%s"  % str(err) )
                    
    def process_start_tag( self, tag, attrs ): 
        if ( tag == 'a' ) and self.has_state( 'td' ) and not self.has_state( 'div' ):
#            print " Anchor start tag: %s, state: %s "  % ( str( attrs ), str( self.state_stack ) )    
            self.current_address = self.get_attribute( 'href', attrs )

    def process_data( self,  data ):
        data = data.strip().replace( '\n', ' ' )
        if self.current_address and data:
            if ( data.lower() not in self.excluded_links ): 
                child_node = OpenDAPCatalogNode( server_address=urljoin( self.root_node.address, self.current_address ) )
                child_node.setLabel( data )
                self.root_node.addChild( child_node )
            self.current_address = None

class ThreddsDataElementParser(HTMLCatalogParser):
    
    def __init__( self, address, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_address = address 
        self.processHref = False  

    def execute(self):
        response = urllib2.urlopen( self.base_address )
        data = response.read()
        self.feed( data )

    def process_start_tag( self, tag, attrs ): 
        if self.processHref and (tag == 'a'):
           address = self.get_attribute( 'href', attrs )
           metadata_address = urljoin( self.base_address, address )
           md_parser = ThreddsMetadataParser( metadata_address )
           md_parser.execute()
           self.metadata = md_parser.getMetadata()
                               
    def process_data( self,  data ): 
        if ( data.find('OPENDAP:') >= 0 ) and self.has_state( 'li' ):
            self.processHref = True  
        elif self.processHref and self.has_state( 'li' ): 
            if self.has_state( 'a' ):
                self.data_address =  urljoin( self.base_address, data )     
                self.processHref = False

class ThreddsMetadataParser(HTMLCatalogParser):

    
    def __init__( self, address, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_address = address
        self.metadata = [ "<html><head><title>Metadata</title></head><body><p><h1>Metadata</h1><p><hr><p>" ] 
        self.md_decl = False
        self.md_text = False

    def execute(self):
        response = urllib2.urlopen( self.base_address )
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
    
    def __init__( self, address, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_address = address 
        self.data_element_address = None
        self.processHref = False 
        self.completeListing = args.get( 'complete', False ) 

#    def process_start_tag( self, tag, attrs ):       
#        print "Start Tag %s: %s" % ( tag, str(attrs) )
        
    def execute(self):
        response = urllib2.urlopen( self.base_address )
        self.metadata = response.read()
        self.feed( self.metadata )
                    
    def process_data( self,  data ): 
#        print "Data: %s" % ( data )
        if ( data.find('Data URL') >= 0 ) and self.has_state( 'td' ):
            self.processHref = True  
        elif self.processHref and self.has_state( 'td' ): 
            if data.startswith("http:"):
                self.data_address =  urljoin( self.base_address, data )     
                self.processHref = False

class HydraxDataElementParser(HTMLCatalogParser):
    
    def __init__( self, address, **args ):
        HTMLCatalogParser.__init__( self, **args ) 
        self.base_address = address 
        self.processHref = False 

    def process_start_tag( self, tag, attrs ): 
        if self.processHref and tag == 'input':
            address = self.get_attribute( 'value', attrs )
            if address:     
                self.data_address =  urljoin( self.base_address, address )     
                self.processHref = False
        
    def execute(self):
        link = urllib2.urlopen( self.base_address )
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
        self.current_data_item = None
        self.treeWidget = QtGui.QTreeWidget()
        self.treeWidget.setColumnCount(1)
        self.treeWidget.setMinimumHeight( 250 )
        self.treeWidget.connect( self.treeWidget, QtCore.SIGNAL("itemClicked(QTreeWidgetItem *,int)"), self.retrieveItem ) 
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        self.newServerDialog = NewServerDialog( self )

                
        layout.addWidget( self.treeWidget )
        self.setWindowTitle( "Remote Data Browser" )
        self.treeWidget.setHeaderLabel ( "Data Servers" )

        self.view = QtWebKit.QWebView( self )
        f = QtGui.QFrame( self )
        f.setFrameStyle( QtGui.QFrame.StyledPanel | QtGui.QFrame.Raised )
        f.setLineWidth(2)
        f_layout = QtGui.QVBoxLayout(f)
        f.setLayout( f_layout )
        f_layout.addWidget( self.view )
        layout.addWidget( f )
                
        button_list_layout = QtGui.QHBoxLayout()
        
        new_server_button = QtGui.QPushButton( "New Server" )  
        new_server_button.setToolTip( "Add new server")  
        self.connect( new_server_button, QtCore.SIGNAL('clicked(bool)'), self.addNewServer )
        button_list_layout.addWidget( new_server_button )
             
        self.discard_server_button = QtGui.QPushButton( "Remove Server"  )   
        self.discard_server_button.setToolTip( "Remove selected server")        
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
            address = server_file.readline().strip()
            if not address: break
            address_tokens = address.split(',')
            base_node = self.getBaseNode( int(address_tokens[0]), address_tokens[1] ) 
            if self.autoRetrieveBaseCatalogs: base_node.retrieveContent() 
        server_file.close()               

    def updateServerList( self ):
        try:    server_file = open( self.server_file_path, "w" )
        except: return
        nservers = self.treeWidget.topLevelItemCount() 
        for si in range( nservers ):
            serverItem = self.treeWidget.topLevelItem( si )
            server_file.write( "%d,%s\n" % ( serverItem.server_class, serverItem.address )  )
        server_file.close()

    def initServerFile( self ):
        if not os.path.isfile( self.server_file_path ):
            try:    server_file = open( self.server_file_path, "w" )
            except: return
            for server in self.default_server_list:
                server_file.write( server + "\n" )
            server_file.close()
            
    def getBaseNode( self, server_class, server_address ):
        if server_address: 
            if server_class == ServerClass.OPENDAP:
                return OpenDAPCatalogNode( server_address=server_address, widget=self.treeWidget, node_type=CatalogNode.Directory )         
            if server_class == ServerClass.IRODS:
                return iRodsCatalogNode( server_address=server_address, widget=self.treeWidget,  node_type=CatalogNode.Directory )
            self.current_data_item = None
        return None
                                             
    def addNewServer(self): 
        self.newServerDialog.exec_()
        base_node = self.getBaseNode( self.newServerDialog.getServerClass(), self.newServerDialog.getServerAddress() )
        if base_node:
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
            self.current_data_item = item
            if self.metadata: self.view.setHtml( self.metadata )
        except Exception, err:
            print>>sys.stderr, "Error retrieving data item: %s\n Item: %s" % ( str(err), str(item) )
            (self.data_element_address, self.metadata) = ( None, None )
            self.current_data_item = None
        self.load_data_button.setEnabled ( self.data_element_address <> None ) 
#        self.load_mdata_button.setEnabled( self.data_element_address <> None ) 
           
    def loadData( self ):
        self.current_data_item.loadData()
        self.emit(  self.new_data_element, self.data_element_address )
        print "Loading URL: ", self.data_element_address

    def loadMetadata( self ):
        pass

class RemoteDataBrowserDialog(QtGui.QDialog):

    def __init__( self, parent = None ):
        QtGui.QDialog.__init__( self, parent )
        self.browser = RemoteDataBrowser( self, closeButton = True )
        self.browser.setMinimumSize ( 700, 500 )
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget( self.browser )
                     
if __name__ == '__main__':   
    app = QtGui.QApplication(sys.argv)
    browser = RemoteDataBrowserDialog( ) # "http://dp6.nccs.nasa.gov/thredds/", CatalogNodeType.THREDDS )
    browser.show()
    app.exec_()
