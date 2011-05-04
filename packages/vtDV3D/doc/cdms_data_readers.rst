The vtDV3D CDMS Data Reader Modules
===================================

.. module:: CDMS_Data_Readers
	:synopsis: The vtDV3D CDMS Data Reader Modules: CDMS_VolumeReader & CDMS_SliceReader.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: CDMS; VolumeReader
	single: CDMS; SliceReader
	single: Modules; CDMS_VolumeReader
	single: Modules; CDMS_SliceReader
		
The **vtDV3D** Data Reader Modules are used to extract a variable from a CDMS dataset and initiate a visualization (VTK) pipeline. There
are currently two Data Readers: :class:`CDMS_VolumeReader` which reads 3D (lat-lon-lev) data (at each timestep) and :class:`CDMS_SliceReader` which 
reads 2D data (at each timestep).  Each Data Reader Module initiates a new VTK pipeline, and each VTK pipeline should terminate in one (and only one) spreadsheet cell.
		
The Module Configuration panel
--------------------------------------

	    Use the :guilabel:`Select Output Variable` dropdown list to select a variable from the dataset to be processed in this pipeline.   When the configuration is complete the user should click on the :guilabel:`OK` button to save the changes.
	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the CDMS Data Reader Modules:

Module Ports
-------------------------------		

		The Data Reader Modules have a single input port 'dataset' of type CDMSDataset, which encapsualtes a CDMS dataset.
		The VolumeReader has single output port 'volume' of type AlgorithmOutputModule3D and the SliceReader has single output port 'slice' of type AlgorithmOutputModule2D.
		These ports encapsulate connections in a VTK pipeline passing 3D (volume) or 2D (slice) rectilinear data (vtkImageData).
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
