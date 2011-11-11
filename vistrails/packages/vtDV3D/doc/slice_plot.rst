The vtDV3D Slice Plot Module
===================================

.. module:: SlicePlot
	:synopsis: The SlicePlot module is used to create a 2D Matplotlib plot in a spreadsheet cell. 
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: Spreadsheet; DV3DCell
	single: Modules; DV3DCell
		
The SlicePlot module is used to create a 2D Matplotlib plot in a spreadsheet cell.  
		
Module Configuration panel
--------------------------------------

	The SlicePlot Module's configuration panel contains one tabs, :guilabel:`plot`, for configuring the plot type.   This panel
	has three drop-down lists:
	
	*  The :guilabel:`Fill Type` drop-down enables configuration of the plot fill type, and has three values:
		1. :guilabel:`Image`: An image of the slice, copied from the slice plane.
		2. :guilabel:`Levels`: Each contour level is filled with a color derived from the associated Volume Slicer module's colormap.
		2. :guilabel:`None`: No fill.

	*  The :guilabel:`Contour Type` drop-down enables configuration of the contours, and has three values:
		1. :guilabel:`Unlabeled`: Unlabeled contour lines with colors derived from the SlicePlot module's colormap.
		2. :guilabel:`Labeled`: Labeled contour lines with colors derived from the SlicePlot module's colormap.
		2. :guilabel:`None`: No contour lines.

	*  The :guilabel:`Number of Contours` drop-down enables configuration of the number of contours.  The contour values are linearly
	   distributed across the color scaling range of the associated Volume Slicer module's colormap.
	  	  
Module Configuration Commands
-------------------------------

		*  The :guilabel:`C` command initiates a leveling operation to configure the scaling of the colormap of the SlicePlot module.  It determines the range of variable values that will be mapped onto the range of colors in the current colormap.
		*  The :guilabel:`c` command opens the colormap dialog in order to choose the colormap of the SlicePlot module.		
		*  The :guilabel:`l` command displays a colorbar for the current colormap in the spreadsheet cell.	

			
Module Ports
-------------------------------		

		The SlicePlot Module has a single input port 'slice' of type AlgorithmOutputModule2D.
					
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
