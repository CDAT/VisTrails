'''
Created on Oct 28, 2013

@author: tpmaxwel
'''
import numpy as np

dx = 6
dy = 5
dz = 4
npts = dx*dy*dz
a = np.arange( 0, npts, 1 )
a = a.reshape( ( dz, dy, dx ) )

print a[:,:,0::3].flatten()
print a.flatten()[0::3]

