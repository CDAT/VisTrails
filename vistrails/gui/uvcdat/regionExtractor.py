import cdms2
import os
from cdms2.MV2 import *
import scipy.io

packagePath = os.path.dirname( __file__ )  
defaultMaskDir = os.path.join( packagePath, 'resources/mask' )

class RegionExtractor:
    """
    RegionExtractor is the class that ...
    """
    
    def __init__(self, type):
        self.type = type;
        if type=='Transcom Regions':
            name='_mask_transcom.mat'
        elif type=='Koeppen-Geiger':
            name='_mask_koeppen.mat'
        elif type=='Dominant \"pure\" PFT':
            name='_mask_hurtt_synmap.mat'
        elif type=='Vegetated Mask':
            name='_mask_vegetated.mat'
        else:
            return
        
        filename = os.path.join(defaultMaskDir, name)
        # read regions from file
        self.file = scipy.io.loadmat(filename)
        code=self.file['code']
        self.regions = {}
        for r in range(code.shape[0]):
            if type=='Vegetated Mask':
                self.regions[str(code[r,0][0])]=r
            else:
                self.regions[str(code[r,0][0])]=r+1
        
    def __call__(self, _var, region):
        var = _var.clone()
        if not region in self.regions.keys():
            return None
        
        val = self.regions[region]
        # reading mask data
        regions_data = self.file['mask']
        regions_var  = cdms2.createVariable(
                         ones(regions_data.shape),
                         grid = cdms2.createUniformGrid(89.75, 360, -0.5, -180, 720, 0.5),
                         mask = where(equal(regions_data, val), 0, 1))
        lats = cdms2.createUniformLatitudeAxis(89.75, 360, -0.5)
        lons = cdms2.createUniformLongitudeAxis(-180, 720, 0.5)
        regions_var.setAxisList((lats,lons))
        
        new_mask_var = regions_var.regrid(var.getGrid(), regridTool='regrid2', regridMethod='linear')
        new_mask = getmask(new_mask_var)
 
        if var.mask <> None:
            var.mask = logical_or(var.mask, new_mask)
        else:
            var.mask = new_mask;
            
        return var
    
    def getRegions(self):
        if self.type <> None:
            return self.regions.keys()
        return None

REGIONS_1 = RegionExtractor('Transcom Regions')
REGIONS_2 = RegionExtractor('Koeppen-Geiger')
REGIONS_3 = RegionExtractor('Dominant \"pure\" PFT')
REGIONS_4 = RegionExtractor('Vegetated Mask')