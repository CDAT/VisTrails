'''
Created on Jun 15, 2011

@author: tpmaxwel
'''
import sys, os
from vtUtilities import *

if __name__ == '__main__':
    optionsDict = {  'hw_role'  : 'server' }
    executeVistrail( 'HyperwallWorkflow', options=optionsDict )
