'''
Created on Jun 15, 2011

@author: tpmaxwel
'''
import sys, os

packagePath = os.path.dirname( __file__ )  
vtPath = os.path.normpath( packagePath + "/../../../../" ) 
print " --> Adding '%s' to python path " % vtPath
sys.path.append( vtPath  ) 
from packages.vtDV3D.Main import executeVistrail

node_index_str = os.environ.get('HW_NODE_INDEX',None)
if node_index_str == None:
    raise EnvironmentError( 0, "Must set the HW_NODE_INDEX environment variable on client nodes")
hw_node_index = int(node_index_str)

if __name__ == '__main__':
    optionsDict = {  
                   'hw_role'            : 'hw_client',
                   'hw_node_index'      : hw_node_index,
                   'fullScreen'         : 'False'
                   }
    executeVistrail( options=optionsDict )