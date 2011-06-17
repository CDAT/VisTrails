'''
Created on Jun 15, 2011

@author: tpmaxwel
'''
import sys, os
from vtUtilities import *

if __name__ == '__main__':
    optionsDict = { 
                   'hw_name'            : 'Hyperwall',
                   'hw_role'            : 'client',
                   'hw_server_port'     : 50000, 
                   'hw_resource_path'   : os.path.expanduser( '~/.vistrails/workflows' ),                   
                   'hw_server'          : 'vislin01',
                   'hw_x'               : 0,
                   'hw_y'               : 0,
                   'hw_width'           : 5,
                   'hw_height'          : 3,
                   'hw_displayWidth'    : 1,
                   'hw_displayHeight'   : 1,
                   }
    executeVistrail( options=optionsDict )
