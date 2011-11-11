The vtDV3D Cell Module
===================================

.. module:: DV3DCell
	:synopsis: The DV3DCell module is used to create volume rendering visualizations in a spreadsheet cell.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: Spreadsheet; DV3DCell
	single: Modules; DV3DCell
		
The DV3DCell module is used to create 3D visualizations in a spreadsheet cell with an (optional) base map.
		
Module Configuration panel
--------------------------------------

		The configuration panels provides base map controls.  The visibility of the base map can be toggled with the :guilabel:`Enable Basemap` checkbox.
		The size of the border, which is the section of map that protrudes beyond the boundary of the ROI, can be configured by editing the :guilabel:`Border size` text field.
	  	  
Module Configuration Commands
-------------------------------

		The DV3DCell module supports the following navigation controls:

		*  Left-clicking and dragging rotates the rendered objects.
		*  Right-clicking and dragging zoom/pans the rendered objects.
		*  Shift-left-clicking and dragging translates the rendered objects.
			
Module Ports
-------------------------------		

		The DV3DCell Module has a single input port 'volume' of type AlgorithmOutputModule3D.
		This port provides a terminal connection for a VTK pipeline passing 3D rectilinear data (vtkImageData).
					
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
