#!/usr/bin/env python

# Import required modules
import os
import re
import sys

# Get passed in variables
import inspect
stk = inspect.stack()[1]
timeSteps = inspect.getmodule(stk[0]).timeSteps

# For debugging
#sys.stdout = open('/home/aashish/Desktop/log.txt', 'w')

# re is required
import re

# paraview is required
import paraview.simple as pv

# Hard coded for now
current_path = os.path.dirname(os.path.abspath(__file__))
template_script_path = current_path + '/tp_exportp_tmpl.py'
file_string = open(template_script_path, 'r').read()
from string import Template
s = Template(file_string)

# Query active source
source_map = {}
sources = pv.GetSources()

# TODO: Check if dict is not empty
source = None
filename = None

# Find a source that has a input file
for key in sources.keys():
  source = sources[key]
  if hasattr(source, 'FileName'):
    proxy = source.SMProxy.GetXMLLabel()
    proxy = re.sub(r'\s', '', proxy)
    filename = source.FileName

    ## Load available arrays (specific to some readers for now)
    if hasattr(source, 'VariableArrayStatus') and hasattr(source, 'PointData'):
      source.VariableArrayStatus = source.PointData.keys()

    # Done
    break

if filename is None:
  sys.exit("ERROR: Could not find a valid source")

source_map[proxy] = filename
sources_str = str(proxy) + ':' + str(filename)

script_path=current_path + '/tp_exportp.py'
out_file = open(script_path, 'w')
out_file.write(s.substitute(export_rendering='True', sources=sources_str, params="'my_view0' : ['image_%t.png', '1', '600', '600']", tp_size='1', out_file='batch.py'))
out_file.close()

# Execute script to generate batch script
sys.path.append(current_path)
__import__("tp_exportp")
