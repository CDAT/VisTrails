The vtDV3D Volume IsoSurface Module
===================================

.. module:: IsoSurface
	:synopsis: The IsoSurface Module to create isosurface visualizations in a spreadsheet cell. 
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: VTK; VolumeSlicer
	single: Modules; VolumeSlicer
		
The IsoSurface Module to create isosurface visualizations in a spreadsheet cell.
		
Module Configuration panel
--------------------------------------

	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the VolumeSlicer Module:

		*  The :guilabel:`O` command initiates a :ref:`leveling operation <leveling-operations>` to configure the opacity of the isosurfaces.
		*  The :guilabel:`C` command initiates a leveling operation to configure the scaling of the color mapping of the isosurfaces.  It determines the range of variable values that will be mapped onto the range of colors in the current colormap.
		*  The :guilabel:`c` command opens the colormap dialog in order to choose the colormap used in rendering the isosurfaces.		
		*  The :guilabel:`l` command displays a colorbar for the current colormap in the spreadsheet cell.	
		*  The :guilabel:`L` command initiates a leveling operation to configure the range of variable values for which isosurfaces will be generated.
		*  The :guilabel:`n` command displays a gui to select the number of isosurfaces.	
		
Module Ports
-------------------------------		

		The IsoSurface Module has a single input port 'volume' and a single output port 'volume', both of type AlgorithmOutputModule3D.
		It also has a single input port 'texture' of type AlgorithmOutputModule3D. These ports encapsulate connections in a VTK pipeline passing 3D rectilinear data (vtkImageData).
		The data on the 'volume' port is used to generate the isosurfaces, and the data on the 'texture' port (if present) is used to
		color the isosurfaces. 
							
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
