The vtDV3D CDMS Data Reader Modules
===================================

.. module:: CDMS_Data_Readers
	:synopsis: The vtDV3D CDMS Data Reader Modules: CDMS_VolumeReader & CDMS_SliceReader.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: CDMS; VolumeReader
	single: CDMS; SliceReader
	single: CDMS; VectorReader
	single: Modules; CDMS_VolumeReader
	single: Modules; CDMS_SliceReader
	single: Modules; CDMS_VectorReader
		
The **vtDV3D** Data Reader Modules are used to extract a variable from a CDMS dataset and initiate a visualization (VTK) pipeline. There
are currently three Data Readers: :class:`CDMS_VolumeReader` which reads 3D (lat-lon-lev) data (at each timestep), :class:`CDMS_SliceReader` which 
reads 2D data (at each timestep) and :class:`CDMS_VectorReader` which reads 3D vector field data (at each timestep).  Each Data Reader Module initiates a new VTK pipeline, and each VTK pipeline should terminate in one (and only one) spreadsheet cell.
		
The Module Configuration panel
--------------------------------------

	    Use the :guilabel:`Select Output Variable` dropdown list to select a variable from the dataset to be processed in this pipeline. 
	    In the case of vector data the user is provided with three drop-down lists to select variables representing the x, y, and z components of the vector field.
	    When the configuration is complete the user should click on the :guilabel:`OK` button to save the changes.
	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the CDMS Data Reader Modules:

Module Ports
-------------------------------		

		The Data Reader Modules have a single input port 'dataset' of type CDMSDataset, which encapsualtes a CDMS dataset.
		The VolumeReader has single output port 'volume' of type AlgorithmOutputModule3D, the SliceReader has single output port 'slice' of type AlgorithmOutputModule2D,
		and the VectorReader has single output port 'vector' of type AlgorithmOutputModule3D.
		These ports encapsulate connections in a VTK pipeline passing 3D with 1 component (volume), 2D with 1 component (slice),
		or 3D with 3 components (vector) rectilinear data (vtkImageData).
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
