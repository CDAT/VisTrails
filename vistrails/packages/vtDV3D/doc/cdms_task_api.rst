The CDMS Task API
===================================

.. module:: CDMS_Task_API
	:synopsis: New tasks can be programmed using the CDMS Task API.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>
.. index::
	single: CDMS; TaskAPI
.. _CDMS task API:
		
The **CDMS task API** is used to create new tasks which will be accessible in the :mod:`CDMS Utilities Module<CDMS_Utilities>`.  Each task
is represented by a python class which inherits from the :class:`vtDV3D.CDATTask.CDATTask` class. Examples of user defined code modules can be found in the 
:file:`vtDV3D/usercode` directory.  The user should copy their code modules to the user tasks directory, which by default is defined to
be :file:`~/.vtdv3d/tasks`.  When a vtDV3D workflow executes all code modules in that directory are dynamically loaded, and all subclasses of the :class:`CDATTask` class
that are found in those modules are registered as tasks with the :mod:`CDMS Utilities Module<CDMS_Utilities>`.  All registered tasks will appear in
the :guilabel:`Tasks` drop-down list in the :mod:`CDMS Utilities Module's<CDMS_Utilities>` configuration panel.
		
