The vtDV3D Slice Plot Module
===================================

.. module:: SlicePlot
	:synopsis: The SlicePlot module is used to create a 2D Matplotlib plot in a spreadsheet cell. 
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: Spreadsheet; DV3DCell
	single: Modules; DV3DCell
		
The SlicePlot module is used to create a 2D Matplotlib plot in a spreadsheet cell.  It converts a VTK (vtkImageData) data object to a MplFigureManager data object which
can be displayed using the matplotlib package.
		
Module Configuration panel
--------------------------------------

	  	  
Module Configuration Commands
-------------------------------

			
Module Ports
-------------------------------		

		The SlicePlot Module has a single input port 'slice' of type AlgorithmOutputModule2D and a output port 'FigureManager' of type MplFigureManager.
		The 'FigureManager' port should be connected to a MplFigureCell module (from the matplotlib package) to generate a matplotlib plot in a spreadsheet cell.
					
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
