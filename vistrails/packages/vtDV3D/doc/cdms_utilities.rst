The vtDV3D CDMS_Utilities Module
===================================

.. module:: CDMS_Utilities
	:synopsis: The CDMS Utilities Module.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: CDMS; Utilities
	single: Modules; CDMS_Utilities
		
The **vtDV3D** CDMS_Utilities Module is used to operate on variables in the current CDMS dataset using CDMS functions.  
The operations create transient variables that are added to the CDMS dataset and thus available to downstream modules.  These operations,
i.e. 'tasks', are either predefined by vtDV3D or programmed by the user using the :mod:`CDMS task API <CDMS_Task_API>`.
		
The Module Configuration panel
--------------------------------------

	The CDMS_Utilities Module's configuration panel contains three tabs, :guilabel:`tasks`, :guilabel:`inputs`, and :guilabel:`outputs`.  When the configuration is complete the user should click on the :guilabel:`OK` button to save the changes.
	
	  *  The :guilabel:`tasks` tab is used to select an operation (from a predefined list) to apply to variable(s) in the CDMS dataset.  The operation is selected from the :guilabel:`Tasks` drop-down list.  When the changes are saved the name of the module in the workflow panel is changed to reflect the selected operation. 
	  *  The :guilabel:`inputs` tab is used to select the input(s) to the operation.  Use the :guilabel:`input` dropdown list of variables in the dataset to select the input to the analysis operation. 
	  *  The :guilabel:`outputs` tab allows the user to edit the name of the output of the operation.  A transient variable with this name will be added to the current dataset when the operation is executed.
	  	  
Module Configuration Commands
-------------------------------

		In addition to the :ref:`global-configuration-commands`, he following interactive configuration commands are available for the CDMS_Utilities Module:

Module Ports
-------------------------------		

		The CDMS_Utilities Modules have (by default) a single input port 'dataset' and a single output port 'dataset', both of type CDMSDataset, which encapsualte a single CDMS dataset.
		
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
