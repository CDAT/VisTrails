The vtDV3D Vector Field Slicer Module
===================================

.. module:: VectorCutPlane
	:synopsis: The VectorCutPlane is used to create a set of draggable 2D slice visualizations of a vector field in a spreadsheet cell. 
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: VTK; VectorCutPlane
	single: Modules; VectorCutPlane
		
The VectorCutPlane module is used to create draggable 2D slice visualizations of a vector field in a spreadsheet cell.  Each 2D slice visualization can be moved through
the data by left-clicking and dragging the slice plane.  The slice plane holds a configurable array of glyphs representing the vector field.
		
Module Configuration panel
--------------------------------------

	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the VolumeSlicer Module:

		*  The :guilabel:`T` command initiates a :ref:`leveling operation <leveling-operations>` to configure the density and scaling of the glyphs.
		*  The :guilabel:`C` command initiates a leveling operation to configure the scaling of the color mapping of the glyphs.  It determines the range of variable values that will be mapped onto the range of colors in the current colormap.
		*  The :guilabel:`c` command opens the colormap dialog in order to choose the colormap of the glyphs.		
		*  The :guilabel:`l` command displays a colorbar for the current colormap in the spreadsheet cell.	
		*  The :guilabel:`x` command orients the slice plane in the 'x' ( i.e. perpendicular to the 'x' axis ) direction.
		*  The :guilabel:`y` command orients the slice plane in the 'y' ( i.e. perpendicular to the 'y' axis ) direction.
		*  The :guilabel:`z` command orients the slice plane in the 'z' ( i.e. perpendicular to the 'z' axis ) direction.	
		
Module Ports
-------------------------------		

		The VectorCutPlane Module has an input port 'vector' and an output port 'volume', both of type AlgorithmOutputModule3D.
		These ports encapsulate connections in a VTK pipeline passing 3D rectilinear data (vtkImageData).  The input port should be 
		downstream of a :class:`CDMS_VectorReader` Module and the output port should be upstream of a :class:`DV3D_Cell` Module.
		It also has an output port 'slice' of type AlgorithmOutputModule2D which can be connected to a SlicePlot cell to generate 2D plots 
		of the data being displayed on the last plane that was moved (UNDER CONSTRUCTION).
		The 'colors' input port can be used to provide a dataset for coloring the glyphs (UNDER CONSTRUCTION). 
					
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
