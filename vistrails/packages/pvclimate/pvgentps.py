#!/usr/bin/env python

# Get passed in variables
import inspect
stk = inspect.stack()[1]
timeSteps = inspect.getmodule(stk[0]).timeSteps

# sys is required
import sys

# For debugging
import sys
sys.stdout = open('/home/aashish/Desktop/log.txt', 'w')

# re is required
import re

# paraview is required
import paraview.simple as pv

# Hard coded for now
file_string = open('tp_exportp_tmpl.py', 'r').read()
from string import Template
s = Template(file_string)

# TODO: Fill out sources

# Query active source
source_map = {}
source = pv.GetActiveSource()
proxy = source.SMProxy.GetXMLLabel()
proxy = re.sub(r'\s', '', proxy)

print 'proxy is ', proxy
print 'source is ', source
print 'dir(source) ', dir(source)
filename = source.FileName
source_map[proxy] = filename
sources_str = str(proxy) + ':' + str(filename)

out_file = open('tp_exportp.py', 'w')
out_file.write(s.substitute(export_rendering='True', sources=sources_str, params="'my_view0' : ['image_%t.png', '1', '600', '600']", tp_size='1', out_file='batch.py'))
out_file.close()

# Execute script to generate batch script
__import__("tp_exportp")
