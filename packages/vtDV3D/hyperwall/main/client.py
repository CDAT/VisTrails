'''
Created on Jun 15, 2011

@author: tpmaxwel
'''
import sys, os
from userpackages.vtDV3D import executeVistrail

node_index_str = os.environ.get('HW_NODE_INDEX',None)
if node_index_str == None:
    raise EnvironmentError( 0, "Must set the HW_NODE_INDEX environment variable on client nodes")
hw_node_index = int(node_index_str)

if __name__ == '__main__':
    optionsDict = {  
                   'hw_role'            : 'client',
                   'hw_node_index'      : hw_node_index,
                   }
    executeVistrail( options=optionsDict )