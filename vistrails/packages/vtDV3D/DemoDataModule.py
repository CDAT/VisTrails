'''
Created on Dec 11, 2010

@author: tpmaxwel
'''
import vtk, sys, os, vtDV3D
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from InteractiveConfiguration import DV3DConfigurationWidget
from core.modules.vistrails_module import Module, ModuleError
from vtUtilities import *
from PersistentModule import * 
from NetCDFDataInterface import NetCDFDataWrapper
from netCDF4 import Dataset
from vtk.util.misc import vtkGetDataRoot
from vtGRADS import GradsReader
packagePath = os.path.dirname( __file__ )  

demoDatasets =  [ 'head', 'iron', 'dust', 'wind', 'e5ncep', 'putman' ]

def getVTKDataRoot(): 
    VTK_DATA_ROOT = os.environ( 'VTK_DATA_ROOT', vtkGetDataRoot() )
    return VTK_DATA_ROOT
         
class PM_DemoData( PersistentVisualizationModule ):

    def __init__(self, mid, **args ):
        PersistentVisualizationModule.__init__( self, mid, createColormap=False, requiresPrimaryInput=False, **args )
        self.timeSteps = [0]
        self.timeIndex = 0
        
    def generateDemoData( self ):
        VTK_DATA_ROOT = getVTKDataRoot()
        if not self.dataset in demoDatasets:
            print>>sys.stderr, "Unknown dataset: %s " % self.dataset
            self.dataset = demoDatasets[0]
        if self.dataset == 'head':
            self.reader = vtk.vtkVolume16Reader()
            self.reader.SetDataDimensions(64, 64)
            self.reader.SetDataByteOrderToLittleEndian()
            self.reader.SetFilePrefix( VTK_DATA_ROOT + "/Data/headsq/quarter" )
            self.reader.SetImageRange(1, 93)
            self.reader.SetDataSpacing(3.2, 3.2, 1.5)
#            self.addMetadata( self.reader.GetOutput() )
            self.reader.AddObserver( "EndEvent", self.addMetadataObserver )
            self.set3DOutput( port=self.reader.GetOutputPort() )
        if self.dataset == 'iron':
            self.reader = vtk.vtkStructuredPointsReader()
            self.reader.SetFileName( VTK_DATA_ROOT + "/Data/ironProt.vtk" )
#            self.addMetadata( self.reader.GetOutput() )
            self.reader.AddObserver( "EndEvent", self.addMetadataObserver )
            self.set3DOutput( port=self.reader.GetOutputPort() )
#        if dataset == 'dust':
#            filePath = os.path.normpath( "%s/../../data/DustCloud.nc" % packagePath )
#            self.dataSet = Dataset( filePath, 'r' )
#            self.variableList = self.dataSet.variables.keys() 
#            print " --- input vars: " + str( self.variableList )
#            outputImage = vtk.vtkImageData()
#            self.imageSource = vtk.vtkImageSource()
#            self.imageSource.SetOutput( outputImage )
#            return self.imageSource.GetOutputPort()
        if self.dataset == 'wind':
#            dataFile = "yotc_UV_1.nc"
#            undefVal = -999000000.0
#            invertZVal = False
#            self.NCDR = NetCDFDataWrapper( dataFile, invertZ=invertZVal, undef=undefVal) 
#            outputImage = self.NCDR.GetFloatVectorImageData( [ "u", "v" ],  0, self.fieldData ) 
            
            self.dataWrapper = GradsReader.GradsDataWrapper( glob='*e5ncep.*.ctl', TimeRange=[ 1, self.maxNTS ] ) 
            self.timeSteps = self.dataWrapper.getTimeSteps()
            self.imageData = self.dataWrapper.GetImageVectorData( self.fieldData, var=[ 'uf', 'vf', None ]  ) 

            self.set3DOutput( output=self.imageData )

        if self.dataset == 'putman':
            dataFile = "/Developer/Data/Putman/Fortuna-cubed-c2000_latlon.inst3_3d_asm1Np.20100208_0000z.nc"
            undefVal = 1.0e15
            invertZVal = False
            
            self.NCDR = NetCDFDataWrapper( dataFile, invertZ=invertZVal, undef=undefVal) 
            outputImage = self.NCDR.GetShortImageData( "T",  0, self.fieldData ) 

            self.set3DOutput( output=self.imageData )

        if self.dataset == 'e5ncep':
            self.dataWrapper = GradsReader.GradsDataWrapper( glob='*e5ncep.*.ctl', TimeRange=[ 1, self.maxNTS ] ) 
            self.timeSteps = self.dataWrapper.getTimeSteps()
            self.dataWrapper.SetCurrentVariable( 'tf',  self.timeSteps[self.timeIndex] )
            self.dataWrapper.ImportTimeSeries()
            self.imageData = self.dataWrapper.GetImageData( self.fieldData ) 
#            pointData = imageData.GetPointData()
#            array0 = pointData.GetArray(0)
#            printArgs( "GRADS IMAGE DATA", npts= imageData.GetNumberOfPoints(), ncells= imageData.GetNumberOfCells(), ncomp= imageData.GetNumberOfScalarComponents(), img_len= imageData.GetLength() )
#            printArgs( "GRADS IMAGE EXT", extent= imageData.GetExtent(), spacing= imageData.GetSpacing(), origin= imageData.GetOrigin(), dim= imageData.GetDimensions() )
#            printArgs( "GRADS POINT DATA", ntup= pointData.GetNumberOfTuples(), narrays= pointData.GetNumberOfArrays(), ncomp= pointData.GetNumberOfComponents())
#            printArgs( "GRADS Array DATA", ntup= array0.GetNumberOfTuples(), size= array0.GetSize(), dsize= array0.GetDataSize(), range= array0.GetRange(), maxid= array0.GetMaxId(), ncomp= array0.GetNumberOfComponents() )
            self.set3DOutput( output=self.imageData )

    def getTimeStepData(self):
        if self.dataset == 'wind':
            self.dataWrapper.SetTime( self.timeSteps[self.timeIndex]  )
            self.dataWrapper.GetImageVectorData( self.fieldData, image=self.imageData ) 

#            outputImage = self.NCDR.GetFloatVectorImageData( [ "u", "v" ],  self.timeSteps[self.timeIndex], self.fieldData ) 
#            return AlgorithmOutputModule( output=outputImage )

        if self.dataset == 'e5ncep':
#            self.dataWrapper.SetCurrentVariable( 'tf',  self.timeSteps[self.timeIndex] )
            self.dataWrapper.SetTime( self.timeSteps[self.timeIndex]  )
            self.dataWrapper.GetImageData( self.fieldData, image=self.imageData ) 
        
    def processParameterChange( self, parameter_name, new_parameter_value ):
        if parameter_name == 'timestep':
            nts = len( self.timeSteps )
            ts = int( new_parameter_value[0] ) % nts
            if ts <> self.timeIndex:
                self.timeIndex = ts
                self.getTimeStepData()
        self.parmUpdating[ parameter_name ] = False 
#        print "%s.processParameterChange" % ( self.__class__.__name__ )                  
                
    def getParameterDisplay( self, parmName, parmValue ):
        if parmName == 'timestep':
            if self.dataset == 'e5ncep':
                nts = len( self.timeSteps )
                ts = int( parmValue[0] ) % nts
                return self.dataWrapper.GetTimeString( ts ), 10
        return None, 1
        
    def execute(self, **args ):
        """ compute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """   
        self.dataset = self.wmod.forceGetInputFromPort( "dataset", demoDatasets[0] )    
        self.maxNTS = int( self.wmod.forceGetInputFromPort( "maxNTimeSteps",  '10' ) )   
        self.initializeMetadata()
        self.generateDemoData()
        
class DemoDataConfigurationWidget(DV3DConfigurationWidget):
    """
    DemoDataConfigurationWidget ...
    
    """
    
    def __init__(self, module, controller, parent=None):
        """ DemoDataConfigurationWidget(module: Module,
                                       controller: VistrailController,
                                       parent: QWidget)
                                       -> DemoDataConfigurationWidget
        Setup the dialog ...
        
        """
        DV3DConfigurationWidget.__init__(self, module, controller, 'Demo Data Configuration', parent)
 
                         
    def createLayout(self):
        """ createEditor() -> None
        Configure sections
        
        """
        self.dataset = demoDatasets[0] # module.forceGetInputFromPort( "dataset", demoDatasets[0] )    
        
        datasetTab = QWidget()        
        self.tabbedWidget.addTab( datasetTab, 'dataset' )                 
        layout = QGridLayout()
        datasetTab.setLayout( layout ) 

#        source_label = QLabel( "Source:"  )
#        layout.addWidget( source_label, 0, 0 ) 

#        self.sourceCombo =  QComboBox ( self.parent() )
#        source_label.setBuddy( self.sourceCombo )
#        self.sourceCombo.setMaximumHeight( 30 )
#        layout.addWidget( self.sourceCombo, 0, 1, 1, 2  )
#        for source in ( 'vtk', 'cdat' ): self.sourceCombo.addItem( source )   
#        self.connect( self.sourceCombo, SIGNAL("currentIndexChanged(QString)"), self.updateParameter )  
       
        dataset_label = QLabel( "dataset:"  )
        layout.addWidget( dataset_label, 1, 0 ) 

        self.datasetCombo =  QComboBox ( self.parent() )
        dataset_label.setBuddy( self.datasetCombo )
        self.datasetCombo.setMaximumHeight( 30 )
        layout.addWidget( self.datasetCombo, 1, 1, 1, 2 )
        for dataset in demoDatasets: self.datasetCombo.addItem( dataset )  
        self.connect( self.datasetCombo, SIGNAL("currentIndexChanged(QString)"), self.updateDataset ) 
        self.datasetCombo.setCurrentIndex(0) 

        max_ts_label = QLabel( "max timesteps:"  )
        layout.addWidget( max_ts_label, 2, 0 ) 
        self.maxNTimeStepInput =  QLineEdit()
        self.maxNTimeStepInput.setText( str( self.maxNTimeSteps ) )
        self.maxNTimeStepInput.setValidator ( QIntValidator( 1, 100000, datasetTab ) )
        layout.addWidget( self.maxNTimeStepInput, 2, 1, 1, 2 )
        self.connect( self.maxNTimeStepInput, SIGNAL("textChanged()"), self.setMaxNTimeSteps ) 
        
    def setMaxNTimeSteps( self, val=None ):
        self.maxNTimeSteps = int( str( val if val <> None else self.maxNTimeStepInput.text() ) )

    def updateDataset( self, dset_name ): 
        self.dataset = dset_name

    def sizeHint(self):
        return QSize(300,200)

    def updateController(self, controller):
        self.persistParameter(  'dataset', [ self.dataset, ])
        self.persistParameter(  'maxNTimeSteps', [ self.maxNTimeSteps, ])

    def okTriggered(self, checked = False):
        """ okTriggered(checked: bool) -> None
        Update vistrail controller (if neccesssary) then close the widget
        
        """
        self.updateController(self.controller)
        self.emit(SIGNAL('doneConfigure()'))
        self.close()


from packages.vtDV3D.WorkflowModule import WorkflowModule

class DemoData(WorkflowModule):
    
    PersistentModuleClass = PM_DemoData
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
         
         
if __name__ == '__main__':
    dd = DemoData()
    test = dd.getDemoData( 'e5ncep' )
    pass