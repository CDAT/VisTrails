#!/usr/bin/env python

# Import required modules
import os
import re
import sys

## Get passed in variables
import inspect
stk = inspect.stack()[1]
timeSteps = inspect.getmodule(stk[0]).timeSteps
fileNames = inspect.getmodule(stk[0]).fileNames

## For debugging
#sys.stdout = open('/home/aashish/Desktop/log.txt', 'w')

## re is required
import re

## paraview is required
import paraview.simple as pv

## Hard coded for now
current_path = os.path.dirname(os.path.abspath(__file__))
template_script_path = current_path + '/tp_exportp_tmpl.py'
file_string = open(template_script_path, 'r').read()
from string import Template
s = Template(file_string)

## Query active source
source_map = {}
sources = pv.GetSources()

## TODO: Check if dict is not empty
source = None
filename = None

## Find a source that has a input file
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

## Generate spatio-temporal parallel script file (temporary)
import tempfile
spt_temp_file = tempfile.NamedTemporaryFile(mode='w', prefix='tp_exportp', suffix='.py')

# Generate placeholder batch file
temp_dir = tempfile.gettempdir()
#batch_file = tempfile.NamedTemporaryFile(mode='w', prefix='batch', suffix='.py')
batch_file_fullpath = temp_dir + "/batch.py"
batch_file = open(batch_file_fullpath, 'w')

spt_temp_file.write(s.substitute(export_rendering='True', sources=sources_str, params="'my_view0' : ['image_%t.png', '1', '600', '600']", tp_size='1', out_file=batch_file_fullpath))
spt_temp_file.flush()

## Execute script to generate batch script
sys.path.append(tempfile.gettempdir())
spt_temp_module = os.path.basename(spt_temp_file.name).rsplit('.')[0]

if len(spt_temp_module) == 0:
  sys.exit("ERROR: Failed to locate spatio-temporal parallel script file")

__import__(spt_temp_module)

## Now since done executing delete temporary files
spt_temp_file.close()

# Read batch.py and replace file names here
import re
batch_content = open(batch_file_fullpath, 'r').read()
new_batch_content = re.sub("FileName=[\'[A-Za-z0-9\.\/\_]*\']", fileNames, batch_content)
batch_file.write(new_batch_content)
batch_file.flush()
# Do not close batch file
