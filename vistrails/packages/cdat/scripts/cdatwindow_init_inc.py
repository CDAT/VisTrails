
    ##########################################################################
    # included from cdatwindow_init_inc.py

    reg.add_module(CDATCell,namespace='cdat')
    reg.add_input_port(CDATCell, 'slab1',
                       (TransientVariable, "variable to be plotted"))
    reg.add_input_port(CDATCell, 'slab2',
                       (TransientVariable, "variable to be plotted"))    
    reg.add_input_port(CDATCell, 'plotType',
                       (core.modules.basic_modules.String, "Plot type"))
    reg.add_input_port(CDATCell, 'template',
                       (core.modules.basic_modules.String, "template name"))
    reg.add_input_port(CDATCell, 'gmName',
                       (core.modules.basic_modules.String, "graphics method name"))
    reg.add_input_port(CDATCell, 'gm',
                       (Module, "boxfill graphics method"))
    reg.add_input_port(CDATCell, 'canvas',
                       (Canvas, "Canvas object"))
    reg.add_input_port(CDATCell, 'col',
                       (core.modules.basic_modules.Integer, "Cell Col"))
    reg.add_input_port(CDATCell, 'row',
                       (core.modules.basic_modules.Integer, "Cell Row"))
    reg.add_input_port(CDATCell, 'continents', 
                       (core.modules.basic_modules.Integer,
                        "continents type number"), True)   
    reg.add_output_port(CDATCell, 'canvas',
                       (Canvas, "Canvas object")) 

    reg.add_module(Variable, namespace='cdat')
    reg.add_module(quickplot, namespace='cdat')    
    reg.add_input_port(Variable, 'id', 
                       (core.modules.basic_modules.String,
                        ""))
    reg.add_input_port(Variable, 'type', 
                       (core.modules.basic_modules.String,
                        "variable, axis, or weighted-axis"))
    reg.add_input_port(Variable, 'inputVariable', 
                       (get_late_type('cdms2.tvariable.TransientVariable'),
                        ""))
    reg.add_output_port(Variable, 'variable', 
                       (get_late_type('cdms2.tvariable.TransientVariable'),
                        ""))
    reg.add_input_port(Variable, 'axes',
                       (core.modules.basic_modules.String, "Axes of variables"))    
    reg.add_input_port(Variable, 'axesOperations',
                       (core.modules.basic_modules.String, "Axes Operations"))
    reg.add_input_port(Variable, 'cdmsfile', 
                       (CdmsFile, "cdmsfile"))    

    reg.add_module(GraphicsMethod, namespace='cdat')
    reg.add_input_port(GraphicsMethod, 'gmName', 
                       (core.modules.basic_modules.String,
                        "Get the graphics method object of the given name."))
    reg.add_input_port(GraphicsMethod, 'plotType',
                       (core.modules.basic_modules.String, "Plot type"))    
    reg.add_input_port(GraphicsMethod, 'slab1', 
                       (get_late_type('cdms2.tvariable.TransientVariable'),
                        "slab1"))
    reg.add_input_port(GraphicsMethod, 'slab2', 
                       (get_late_type('cdms2.tvariable.TransientVariable'),
                        "slab2"))
    reg.add_input_port(GraphicsMethod, 'color_1',
                       (core.modules.basic_modules.Integer, "color_1"), True)
    reg.add_input_port(GraphicsMethod, 'color_2',
                       (core.modules.basic_modules.Integer, "color_2"), True)
    reg.add_input_port(GraphicsMethod, 'level_1',
                       (core.modules.basic_modules.Float, "level_1"), True)
    reg.add_input_port(GraphicsMethod, 'level_2',
                       (core.modules.basic_modules.Float, "level_2"), True)        
    reg.add_output_port(GraphicsMethod, 'slab1', 
                       (get_late_type('cdms2.tvariable.TransientVariable'),
                        "slab1"))
    reg.add_output_port(GraphicsMethod, 'slab2', 
                       (get_late_type('cdms2.tvariable.TransientVariable'),
                        "slab2"))            
    reg.add_output_port(GraphicsMethod, 'canvas', (Canvas, "Canvas object"))
    
    #cdat GUI modules
    global cdatWindow
    global translator
    global plotRegistry
    import qtbrowser
    qtbrowser.useVistrails=True
    try:
        builder_window = api.get_builder_window()
        shell = QShellDialog.instance().shell
        #builder_window.use_uvcdat_window = True
    except api.NoGUI:
        shell = None
    translator = QTranslator(shell=shell)
    
    #cdatWindow = UVCDATMainWindow()
    #plotRegistry = PlotRegistry(cdatWindow)
    #plotRegistry.loadPlots()    
    #plotRegistry.registerPlots()
    #cdatWindow.show()
    #visApp = QtCore.QCoreApplication.instance()
    #if visApp:
    #    visApp.setActiveWindow(cdatWindow)
    #translator.connect(cdatWindow.recorder, QtCore.SIGNAL('recordCommands'),
    #                       translator.commandsReceived)
    #translator.connect(cdatWindow, QtCore.SIGNAL("showVisTrails"),
    #                   translator.showVisTrails)
    #translator.connect(cdatWindow, QtCore.SIGNAL("closeVisTrails"),
    #                   translator.closeVisTrails)

    # end of cdatwindow_init_inc.py
    ##########################################################################

    
