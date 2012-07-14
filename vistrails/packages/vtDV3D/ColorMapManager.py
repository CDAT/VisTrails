'''
Created on Dec 3, 2010
Hacked from the Enthought MayaVi2 lut_manager
@author: tpmaxwel
'''

import os.path
import sys, vtk
import cPickle

pkl_path = os.path.join( os.path.dirname( __file__ ), 'colormaps.pkl' )
colormap_file = open( pkl_path, 'rb' )
colormaps = cPickle.load( colormap_file )
colormap_file.close()

class ColorMapManager():
    
    def __init__(self, lut, display_lut = None, **args ): 
        self.lut = lut   
        self.display_lut = vtk.vtkLookupTable() 
        self.reverse_lut = False
        self.number_of_colors =  args.get('ncolors',256)
        self.alpha_range = [ 1.0, 1.0 ]
        self.cmap_name = 'blue-red'
        
    def setAlphaRange( self, range ):
        self.alpha_range = range
        self.load_lut()
     
    @staticmethod
    def getColormaps():
        return colormaps
    
    def getDisplayLookupTable(self):
        return self.display_lut
  
    def setDisplayRange( self, dataRange ):
        self.display_lut.SetTableRange( dataRange[0], dataRange[1] )
        self.display_lut.Modified()
    
    def set_lut(self, vtk_lut, lut_lst):
        """Setup the vtkLookupTable (`vtk_lut`) using the passed list of
        lut values."""
        n_col = len(lut_lst)
        vtk_lut.SetNumberOfColors( n_col )
        vtk_lut.Build()
        ascale = ( self.alpha_range[1] - self.alpha_range[0] ) / ( n_col - 1 )
        for i in range(0, n_col):
            lt = lut_lst[i]
            alpha = self.alpha_range[0] + i*ascale
            vtk_lut.SetTableValue(i, lt[0], lt[1], lt[2], alpha )
    
    def check_lut_first_line(self, line, file_name=''):
        """Check the line to see if this is a valid LUT file."""
        first = line.split()
        if first[0] != "LOOKUP_TABLE":
            errmsg = "Error: The input data file \"%s\"\n"%(file_name)
            errmsg = errmsg+ "is not a proper lookup table file."\
                     " No LOOKUP_TABLE tag in first line. Try again."
            raise IOError, errmsg
        try:
            n_color = first[2]
        except:
            
            raise IOError, "Error: No size for LookupTable specified."
        else:
            return n_color
    
    def parse_lut_file(self, file_name):
        """Parse the file specified by its name `file_name` for a LUT and
        return the list of parsed values."""
        
        input = open(file_name, "r")
    
        line = input.readline()
        n_color = self.check_lut_first_line(line, file_name)
    
        lut = []
        for line in input.readlines():
            entr = line.split()
            if len(entr) != 4:
                errmsg="Error: insufficient or too much data in line "\
                        "-- \"%s\""%(entr)
                raise IOError, errmsg
    
            tmp = []
            for color in entr:
                try:
                    tmp.append(float(color))
                except:
                    raise IOError, \
                          "Unknown entry '%s'in lookup table input."%color
            lut.append(tmp)
    
        return lut
    
    def load_lut_from_file(self, file_name):
        lut_list = []
        if len(file_name) > 0:
            try:
                f = open(file_name, 'r')
            except IOError:
                msg = "Cannot open Lookup Table file: %s\n"%file_name
                error(msg)
            else:
                f.close()
                try:
                    lut_list = self.parse_lut_file(file_name)
                except IOError, err_msg:
                    msg = "Sorry could not parse LUT file: %s\n" % file_name
                    msg += str( err_msg )
                    raise IOError, msg
                else:
                    if self.reverse_lut:
                        lut_list.reverse()
                    self.lut = self.set_lut(self.lut, lut_list)
                    
    def load_lut_from_list(self, list):
        self.set_lut(self.lut, list)                    

    def load_lut(self, value=None):
        if( value <> None ): self.cmap_name = str( value )
        hue_range = None
        print " --> Load LUT: %s " % self.cmap_name  
       
        if self.cmap_name == 'file':
            if self.file_name:
                self.load_lut_from_file(self.file_name)
            #self.lut.force_build()
            return
        
        reverse = self.reverse_lut
        if self.cmap_name in colormaps:
            lut = colormaps[self.cmap_name]
            if reverse:
                lut = lut[::-1, :]
            n_total = len(lut)
            n_color = self.number_of_colors
            if not n_color >= n_total:
                lut = lut[::round(n_total/float(n_color))]
            self.load_lut_from_list(lut.tolist())
        elif self.cmap_name == 'blue-red':
            if reverse:
                hue_range = 0.0, 0.6667
                saturation_range = 1.0, 1.0
                value_range = 1.0, 1.0
            else:
                hue_range = 0.6667, 0.0
                saturation_range = 1.0, 1.0
                value_range = 1.0, 1.0
        elif self.cmap_name == 'black-white':
            if reverse:
                hue_range = 0.0, 0.0
                saturation_range = 0.0, 0.0
                value_range = 1.0, 0.0
            else:
                hue_range = 0.0, 0.0
                saturation_range = 0.0, 0.0
                value_range = 0.0, 1.0
        else:
            print>>sys.stderr, "Error-- Unrecognized colormap: %s" % self.cmap_name
        
        if hue_range:        
            self.lut.SetHueRange( hue_range )
            self.lut.SetSaturationRange( saturation_range )
            self.lut.SetValueRange( value_range )
            self.lut.SetAlphaRange( self.alpha_range )
            self.lut.SetNumberOfTableValues( self.number_of_colors )
            self.lut.SetRampToSQRT()            
            self.lut.Modified()
            self.lut.ForceBuild()
            
        self.display_lut.SetTable( self.lut.GetTable() )
        self.display_lut.SetValueRange( self.lut.GetValueRange() )
        self.display_lut.Modified()
                  
if __name__ == '__main__':  
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    
#    new_colormaps = {}
#    for cmap_name in colormaps:
#        cmap = colormaps[ cmap_name ]
#        new_colormaps[cmap_name] = cmap
#
#    pkl_path = os.path.join( os.path.dirname( __file__ ), 'colormaps1.pkl' )
#    colormap_file = open( pkl_path, 'wb' )
#    colormaps = cPickle.dump( new_colormaps, colormap_file )
#    colormap_file.close()
              
    app = QApplication(['ImageSlicerTest'])
    renWin = vtk.vtkRenderWindow() 
       
    for key in colormaps:
        print "%s" % key
        
    lut = vtk.vtkLookupTable()
    cm = ColorMapManager( lut )
    cm.load_lut('gist_earth')

    colorBarActor = vtk.vtkScalarBarActor()
    colorBarActor.SetLookupTable( lut )
 
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)    
    
    aRenderer = vtk.vtkRenderer()
    renWin.AddRenderer(aRenderer)
    aRenderer.AddActor( colorBarActor )
   
    iren.Initialize()
    renWin.Render()
    iren.Start()
    
    app.exec_()   

 