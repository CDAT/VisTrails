'''
Created on Jun 15, 2011

@author: tpmaxwel
'''
import sys, os
if __name__ == '__main__':
    from userpackages.vtDV3D import executeVistrail
    optionsDict = {  'hw_role': 'server', 'debug': 'False' } #, 'hw_nodes': 'localhost' }
    try:
        executeVistrail( 'DemoWorkflow9', options=optionsDict )
        
    except Exception, err:
        print " executeVistrail exception: %s " % str( err )

