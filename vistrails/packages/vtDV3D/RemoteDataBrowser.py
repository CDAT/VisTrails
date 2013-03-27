
import urllib2, sys, os
from HTMLParser import HTMLParser
from urlparse import *
from PyQt4 import QtCore, QtGui
#        split_url = urlsplit(catalog_url) urlunsplit(split_url)

class HTMLState:
    HTML = 0
    Header = 1
    Body = 2
    Table = 3
    TableRow = 4
    Anchor = 5
    
class CatalogNodeType:
    THREDDS = QtGui.QTreeWidgetItem.UserType + 1
    
class CatalogNode( QtGui.QTreeWidgetItem ):
    Directory = 0
    DataObject = 1
    Style = None
    
    def __init__( self, url, node_type, widget = None ):
         if widget: 
            QtGui.QTreeWidgetItem.__init__( self, widget, node_type  )
            CatalogNode.Style = widget.style() 
            self.setIcon( 0, CatalogNode.Style.standardIcon( QtGui.QStyle.SP_DriveNetIcon ) ) 
            self.setText( 0, "%s Catalog" % ( self.getCatalogType() ) )
         else: 
             QtGui.QTreeWidgetItem.__init__( self, node_type  )  
         self.url = url
         self.node_type = None
         self.parser = None
         
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
            if self.type() == CatalogNodeType.THREDDS: self.parser = HTMLThreddsResponseParser( self ) 
            if self.parser: self.parser.execute()
            else: print>>sys.stderr, "Error, unimplemented Catalog type: %d " % self.type()
        
    def __repr__(self): 
        return " %s Node: '%s' <%s>" % ( self.getType(), str(self.text(0)), self.url )

class HTMLThreddsResponseParser(HTMLParser):
    
    def __init__( self, base_node ):
        HTMLParser.__init__( self )    
        self.root_node = base_node
        self.child_node = None
        self.state_stack = [ HTMLState.HTML ]
        self.state_list = { 'head':HTMLState.Header, 'body':HTMLState.Body, 'table':HTMLState.Table, 'tr':HTMLState.TableRow, 'a':HTMLState.Anchor }
        
    def execute(self):
        response = urllib2.urlopen( self.root_node.url )
        self.feed( response.read() )
        
    def state(self,frame=0):
        return self.state_stack[ -1-frame ]
    
    def inCatalogEntry(self):
       return ( self.state() == HTMLState.Anchor ) and ( self.state(1) == HTMLState.TableRow )
        
    def handle_starttag(self, tag, attrs):
        for item in self.state_list.items():
            if tag == item[0]: 
                self.state_stack.append( item[1] )
                break            
        if ( tag == 'a' ) and self.inCatalogEntry():
            url = self.get_attribute( 'href', attrs )
            self.child_node = CatalogNode( urljoin( self.root_node.url, url ), self.root_node.type() )
            
    def get_attribute( self, tag, attrs ):
        for item in attrs:
            if tag == item[0]: return item[1]
        return None
        
    def handle_endtag(self, tag):
        for key in self.state_list:
            if tag == key: 
                self.state_stack.pop()
                break
        
    def handle_data( self, data ):
        if self.child_node and self.inCatalogEntry() and data:
            self.child_node.setLabel( data.strip() )
            self.root_node.addChild ( self.child_node )
            print "Adding Child:", str( self.child_node )
            self.child_node = None

class RemoteDataBrowser(QtGui.QDialog):

    def __init__( self, address, catalog_type, parent = None ):
        QtGui.QDialog.__init__( self, parent )
        self.setFixedSize( 500, 500 )
        self.treeWidget = QtGui.QTreeWidget()
        self.treeWidget.setColumnCount(1)
        self.treeWidget.connect( self.treeWidget, QtCore.SIGNAL("itemClicked(QTreeWidgetItem *,int)"), self.retrieveItem ) 
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self.treeWidget)
        self.setWindowTitle( "Remote Data Browser" )
        self.treeWidget.setHeaderLabel ( address )
        base_node = CatalogNode( address, catalog_type, self.treeWidget ) 
        base_node.retrieveContent()  
                
    def retrieveItem( self, item, index ):
        print "Retrieving item: ", str(item)
        item.retrieveContent()          

if __name__ == '__main__':   
    app = QtGui.QApplication(sys.argv)
    browser = RemoteDataBrowser( "http://dp6.nccs.nasa.gov/thredds/", CatalogNodeType.THREDDS )
    browser.show()
    app.exec_()
