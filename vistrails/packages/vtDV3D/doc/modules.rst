The vtDV3D Modules
===================================

.. module:: interface
	:synopsis: Overview of the DV3D Modules.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: GUI
	single: Modules; File
	single: Modules; Variable	
	
.. toctree::
	:hidden:
	
   	cdms_file
   	cdms_utilities
    cdms_task_api
   	cdms_data_readers
   	volume_renderer
   	volume_slicer
   	volume_isosurface
   	slice_plot
   	dv3d_cell
		
The **vtDV3D** user interface consists of a set of modules that are accessed through the VisTrails module palette.  The modules are
organized into three groups- cdms, vtk, and spreadsheet.
		
The CDMS Modules
-------------------

	  The CDAT modules are used to read and process datasets generated using the CDMS cdscan utility.  
	  
	  * The :mod:`CDMS_FileReader` module is used to access CDMS datasets.
	  * The :mod:`CDMS_Utilities` module is used to operate on variables in the current CDMS dataset using CDMS functions. 
	  * The :mod:`CDMS_Data_Readers` modules are used to extract a variable from a CDMS dataset and initiate a visualization (VTK) pipeline.

	  	  
The VTK Modules
-----------------

	  The VTK modules encapsulate a VTK pipeline to process and visualize rectilinear grid data.

	  * The :mod:`VolumeRenderer` module is used to create volume rendering visualizations in a spreadsheet cell.
	  * The :mod:`VolumneSlicer` module is used to create a set of draggable 2D slice visualizations in a spreadsheet cell. 
	  * The :mod:`IsoSurface` module is used to create isosurface visualizations in a spreadsheet cell.

The Spreadsheet Modules
----------------------------------

	  The Spreadsheet modules enable 2D and 3D visualization in spreadsheet cells.

	  * The :mod:`DV3DCell` module is used to create volume rendering visualizations in a spreadsheet cell.
	  * The :mod:`SlicePlot` module is used to create a 2D Matplotlib plot in a spreadsheet cell. 

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
