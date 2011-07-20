'''
Created on Jul 20, 2011

@author: tpmaxwel
'''
import sys
from userpackages.vtDV3D import executeVistrail
optionsDict = {  'hw_role'  : 'none' }

try:
    if len( sys.argv ) > 1: executeVistrail( sys.argv[1], options=optionsDict )
    else:                   executeVistrail( options=optionsDict )

except Exception, err:
    print " executeVistrail exception: %s " % str( err )
