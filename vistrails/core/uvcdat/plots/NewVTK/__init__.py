from packages.uvcdat_cdms.pipeline_helper import CDMSPipelineHelper

class NewVTKPipelineHelper(CDMSPipelineHelper):

    @staticmethod
    def build_plot_pipeline_action(controller, version, var_modules, 
                                   plots,row, col, template=None):
        
        # only support one plot
        plot = plots[0]
        
        # This function copies all of the modules and connections from the
        # vt file specified in the plot registry config. It returns all 
        # the generated pipeline items, as well as a list of ports that
        # accept a CDMSVariable in the pipeline.
        pipeline_items, cdms_ports = \
                CDMSPipelineHelper.create_plot_workflow_items(
                        plot.workflow, controller, row, col)
                
        # We need to match variable modules to the ports returned in above call.
        # Since our plot only works on a single variable, we'll just match the 
        # first in each list.
        variable_matches = [(var_modules[0], cdms_ports[0])]      
        
        #finalize pipeline creation
        action = CDMSPipelineHelper.finish_plot_workflow(controller,
                                                         pipeline_items, 
                                                         variable_matches, 
                                                         version)
        
        return action