vtDV3D at Goddard
===================================

.. module:: goddard
	:synopsis: Instructions on running vtDV3D at NASA Goddard.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
		
The **vtDV3D** application is installed at several locations at NASA GSFC for use by Goddard scientists.
		
GMAO
--------------

	vtDV3D is installed on oxford.gsfc.nasa.gov and dali.nccs.nasa.gov for use by GMAO scientists.   
	
	To run DV3D on ofxord:
	
	* log in to oxford ( be sure to enable X forwarding, i.e. :command:`ssh -Y ...` ).   Users who have /ford1/ mounted may be able to run DV3D from their desktop computer.
	* execute the shell command: :program:`/ford1/local/EL5/bin/vtdv3d.sh`.  

Hyperwall
---------

	vtDV3D is installed on the hyperwall cluster.  Execute the shell command: :program:`vtdv3d` to start the DV3D playlist app.  From
	the Playlist interface users can run any of the DV3D demos by choosing a demo and then clicking the :guilabel:`Run` button.
			

Dali
----------

	To run vtDV3D on dali:
	
	* ssh to to dali ( be sure to enable X forwarding, i.e. :command:`ssh -Y ...` ).  
	* execute the shell command: :program:`/discover/nobackup/tpmaxwel/pydev/bin/vtdv3d.sh`.  	
	

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
