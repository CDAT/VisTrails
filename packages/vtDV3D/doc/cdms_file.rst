The vtDV3D FileReader Module
===================================

.. module:: CDMS_FileReader
	:synopsis: The FileReader Module.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: CDMS; FileReader
	single: Modules; CDMS_FileReader
		
The **vtDV3D** FileReader Module is used to access CDMS datasets.  The datasets should be created using the CDMS cdscan utility.  
		
The Module Configuration panel
--------------------------------------

	The FileReader Module's configuration panel contains four tabs, :guilabel:`dataset`, :guilabel:`time`, :guilabel:`roi`, and :guilabel:`vertScale`.  When
	the configuration is complete the user should click on the :guilabel:`OK` button to save the changes.
	
	  *  The :guilabel:`dataset` tab is used to select a CDMS dataset.  To open a new dataset click the :guilabel:`Select Dataset` button and
	  	 use the file selection dialog to choose the dataset's xml file (generated using cdscan).   The metadata for the selected dataset set can
	  	 be viewed by clicking the :guilabel:`View Metadata` button.
	  *  The :guilabel:`time` tab is used to bound the time span of interest for animations.  Select the animation :guilabel:`Start Time` and :guilabel:`End Time`
	  	 by choosing from the the drop-down menus or by editing the time indices.
	  *  The :guilabel:`roi` menu option is used to bound the lat-lon region of interest used in analysis and display operations.  Display the ROI selection widget by
	     clicking the :guilabel:`Select ROI` button. Select the roi bounds by either editing the text fields for :guilabel:`ROI Cornder1` and :guilabel:`ROI Cornder1` or
	     by right-clicking and dragging on the map.  Clicking the :guilabel:`Reset ROI` button selects a global ROI.
	  *  The :guilabel:`vertScale` menu option is used to adjust the vertical scaling of the data in all 3D visualizations.  Edit the :guilabel:`Vertical Scale`
	     text box to set the scaling factor.
	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the FileReader Module:
		

Module Ports
-------------------------------		

		The FileReader Module has a single output port 'dataset' of type CDMSDataset which encapsualte a single CDMS dataset.

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
