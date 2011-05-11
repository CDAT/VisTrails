The vtDV3D Volume Slicer Module
===================================

.. module:: VolumeSlicer
	:synopsis: The VolumeSlicer is used to create a set of draggable 2D slice visualizations in a spreadsheet cell. 
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: VTK; VolumeSlicer
	single: Modules; VolumeSlicer
		
The VolumeSlicer module is used to create draggable 2D slice visualizations in a spreadsheet cell.  Each 2D slice visualization can be moved through
the data by left-clicking and dragging the slice plane.  Right-clicking on a slice displays the slice position and the variable value at that point.
		
Module Configuration panel
--------------------------------------

	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the VolumeSlicer Module:

		*  The :guilabel:`O` command initiates a :ref:`leveling operation <leveling-operations>` to configure the overall opacity of the slice plots.
		*  The :guilabel:`C` command initiates a leveling operation to configure the scaling of the color mapping of the slice plot.  It determines the range of variable values that will be mapped onto the range of colors in the current colormap.
		*  The :guilabel:`c` command opens the colormap dialog in order to choose the colormap of the slice plot.		
		*  The :guilabel:`l` command displays a colorbar for the current colormap in the spreadsheet cell.	
		*  The :guilabel:`m` command enables margins on the slice planes.   Right clicking and dragging the slice margins enables rotations and translations of the planes.
		*  The :guilabel:`x` command snaps the 'x' slice back to its default ( perpendicular to the 'x' axis ) position.
		*  The :guilabel:`y` command snaps the 'y' slice back to its default ( perpendicular to the 'y' axis ) position.
		*  The :guilabel:`z` command snaps the 'z' slice back to its default ( perpendicular to the 'z' axis ) position.	
		
Module Ports
-------------------------------		

		The Volume Slicer Module has a single input port 'volume' and a single output port 'volume', both of type AlgorithmOutputModule3D.
		It also has a single output port 'slice' of type AlgorithmOutputModule2D.
		These ports encapsulate connections in a VTK pipeline passing 3D rectilinear data (vtkImageData).
		The 'slice' output port can be connected to a SlicePlot cell to generate 2D plots of the data being displayed on the last plane that was moved.
					
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
