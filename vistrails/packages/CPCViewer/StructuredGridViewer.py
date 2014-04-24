'''
Created on Apr 23, 2014

@author: tpmaxwell
'''

from packages.CPCViewer.DV3DPlot import DV3DPlot


class StructuredGridPlot(DV3DPlot):  
    

    def __init__( self, vtk_render_window = None , **args ):
        DV3DPlot.__init__( self, vtk_render_window,  **args  )

if __name__ == '__main__':
    pass