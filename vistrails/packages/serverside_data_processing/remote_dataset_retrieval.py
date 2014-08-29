'''
Created on Aug 15, 2013

@author: tpmaxwel
'''

import os, sys, urllib2, copy, httplib
from HTMLParser import HTMLParser

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
#             if tag == 'a':
#                 if self.state_stack[ -1 ] == 'a': self.state_stack.pop()
#                 return
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
    
    def __init__( self, url, **args ):
        HTMLCatalogParser.__init__( self, **args )    
        self.child_node_list = []
        self.child_node = None
        self.url = url

    def execute(self):
        try:
            response = urllib2.urlopen( self.url )
            self.feed( response.read() )
        except Exception, err:
            print>>sys.stderr, "Error connecting to server:\n%s"  % str(err) 
            
    def inCatalogEntry(self):
       return self.has_state( 'a' ) and self.has_state( 'tr' )
        
    def process_start_tag( self, tag, attrs ):          
        if ( tag == 'a' ) and self.has_state( 'tr' ):
            url = self.get_attribute( 'href', attrs )
            self.child_node =  [ url, None ]

    def process_data( self,  data ): 
        if self.child_node and self.inCatalogEntry() and data:         
            self.child_node[1] = data.strip() 
            self.child_node_list.append ( self.child_node )
            self.child_node = None

class DatasetCatalogRetriever:
    
    def __init__( self, location, **args ):
       self.parser = None
       self.address = location
#       location = args.get('address',None)
       if location:
           self.set_dataset_address( location )
       
    def set_dataset_address(self, dset_address ):
        if "thredds" in dset_address:
            location = os.path.join( dset_address, "catalog.html" )
            self.parser = ThreddsDirectoryParser( location )

    def get_file_list( self, patterns ):
        import fnmatch
        file_list = []
        if self.parser:
            self.parser.execute()
            child_node_list =[file_rec[1] for file_rec in self.parser.child_node_list ]
        else:
            child_node_list = [ f for f in os.listdir( self.address ) if os.path.isfile( os.path.join( self.address, f ) ) ]

        for child_node in child_node_list:
            for pattern in patterns:
                if fnmatch.fnmatch( child_node, pattern ):
                    file_list.append( child_node ) 
                    break

        file_list.reverse()  
        return file_list     
