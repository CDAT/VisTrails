
Configuration
===================================

.. module:: configuration
	:platform: Unix
	:synopsis: Module configuration.
.. moduleauthor:: Thomas Maxwell <thomas.maxwell@nasa.gov>

All **vtDV3D** Workflow Modules support workflow and interactive configuration functions that are used to configure parameters 
for colormaps, transfer functions, and other display options.  All configuration functions are saved as provenance upon completion. 
The workflow configuration panel for a given module is displayed by clicking on that module in the VisTrails workflow panel.      
Interactive configuration functions are invoked using command keys while a Vistrails spreadsheet cell has focus.  
Consult the 'modules' tab of the help widget for a list of available command keys for the current cell. The Modules section of this 
document lists the available command keys for each Module.
        
There are two types of interactive configuration functions: gui functions and leveling functions. 

GUI Functions
--------------

        GUI functions facilitate interactive parameter configurations that require a choice from a discreet set of possible values
        ( e.g. choosing a colormap or the number of contour levels ). Typing the the gui command code pops up a gui widget.  
        All gui function command codes are lower case.

.. _leveling-operations:
        
Leveling Functions
---------------------------

        Leveling functions facilitate interactive configuration of continuously varying parameters  ( e.g. scaling a colormap or 
        configuring a transfer function ). Typing the leveling command code puts the cell into leveling mode.  Leveling is initiated
        when the user left-clicks in the cell while it is in leveling mode.  Mouse drag operations (while leveling) generate
        leveling configurations.  When the (left) mouse button is release the leveling configuration is saved as provenance and the
        cell returns to normal (non-leveling) mode. 
        
        Leveling operations are used to configure a variable value window, defined by min and max values within the range of possible values for a variable.   Dragging the mouse left/right causes the window to 
        be narrowed/widened.  Dragging the mouse up/down causes the center of the window to be moved up/down in the range of values of the variable.  

.. _global-configuration-commands:
 
Global Configuration Commands
-------------------------------

		The following interactive configuration commands are available for all modules:
		
		*  The :guilabel:`h` command opens a help dialog displaying documentation for all modules contained in the selected spreadsheet cell.
		*  The :guilabel:`a` command opens the animation dialog containing controls for starting, stopping, and stepping an animation of timeseries data. 		


         
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`