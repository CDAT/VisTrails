'''
Created on Apr 15, 2011

@author: tpmaxwel
'''

"""
   This file stores vtDV3D configuration and can be used across the package

"""
from core.configuration import ConfigurationObject
configuration = ConfigurationObject( vtk_data_root='~/data', 
                                     debug = False, 
                                     hw_resource_path='',
                                     hw_name="Hyperwall", 
                                     hw_role="none",
                                     hw_x=0, hw_y=0, hw_width=1, hw_height=1,
                                     hw_displayWidth=-1, hw_displayHeight=-1,
                                     hw_server="localhost", 
                                     hw_server_port=50000 )