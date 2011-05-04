The vtDV3D Volume Renderer Module
===================================

.. module:: VolumeRenderer
	:synopsis: The VolumeRenderer module is used to create volume rendering visualizations in a spreadsheet cell.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: VTK; VolumeRenderer
	single: Modules; VolumeRenderer
		
The VolumeRenderer module is used to create volume rendering visualizations in a spreadsheet cell. 
		
Module Configuration panel
--------------------------------------

	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the VolumeRenderer Module:

		*  The :guilabel:`O` command initiates a :ref:`leveling operation <leveling-operations>` to configure the overall opacity of the volume rendering.
		*  The :guilabel:`T` command initiates a :ref:`leveling operation <leveling-operations>` to configure the transfer function of the volume rendering.  The transfer function maps values of the variable to opacity at each point of the volume.
		*  The :guilabel:`C` command initiates a leveling operation to configure the scaling of the color mapping of the volume rendering.  It determines the range of variable values that will be mapped onto the range of colors in the current colormap.
		*  The :guilabel:`c` command opens the colormap dialog in order to choose the colormap of the volume rendering.		
		*  The :guilabel:`l` command displays a colorbar for the current colormap in the spreadsheet cell.	
		
Module Ports
-------------------------------		

		The Volume Renderer Module has a single input port 'volume' and a single output port 'volume', both of type AlgorithmOutputModule3D.
		These ports encapsulate connections in a VTK pipeline passing 3D rectilinear data (vtkImageData).
					
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
