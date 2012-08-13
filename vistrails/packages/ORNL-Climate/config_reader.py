from core.modules.vistrails_module import Module, ModuleError
from ConfigParser import ConfigParser
from core.modules.basic_modules import File
from packages.scikit_learn.matrix import Matrix
import numpy as np

class ConfigReader(Module):
    """Config Reader is used to read text files having the modules names and modes"""
    my_namespace = 'util'
    name         = 'ConfigReader'
    
    _input_ports  = [('file', '(edu.utah.sci.vistrails.basic:File)')]
    _output_ports = [('variable_name', '(edu.utah.sci.vistrails.basic:String)'),
                     ('ref_filename', '(edu.utah.sci.vistrails.basic:File)'),
                     ('file_names', '(edu.utah.sci.vistrails.basic:List)'),
                     ('model_names', '(edu.utah.sci.vistrails.basic:List)'),
                     ]
    
    def compute(self):
        file = self.getInputFromPort("file")
        
        config = ConfigParser()
        config.optionxform = str # keep capital letter in model names
        config.read(file.name)
        
        # read basic information
        variable_name = config.get('basic', 'variable_name')
        ref_filename = File()
        ref_filename.name = config.get('basic', 'ref_filename')
        self.setResult('variable_name', variable_name)
        self.setResult('ref_filename', ref_filename)
        
        # read model names
        file_names = []
        model_names = config.options('file_names')
        for model in model_names:
            file_names.append(config.get('file_names', model))

        self.setResult('file_names', file_names);
        self.setResult('model_names', model_names);
        

class WriteVarsIntoDataFile(Module):
    """
    """
    my_namespace = 'util'
    name         = 'WriteVarsIntoDataFile'
    
    _input_ports  = [('vars', '(edu.utah.sci.vistrails.basic:List)'),
                     ('models', '(edu.utah.sci.vistrails.basic:List)'),
                     ('ofile', '(edu.utah.sci.vistrails.basic:File)')]

    def compute(self):
        vars = self.getInputFromPort("vars")
        models = self.getInputFromPort("models")
        ofile = self.getInputFromPort("ofile")
        
        f = open(ofile.name, 'w')
        # write metadata
        # assume all variables have same length
        data = vars[0].var.data.flatten().tolist()
        f.write('DY\n')
        f.write('%d\n'%len(vars))
        f.write('%d\n'%len(data))

        # write attributes
        for i in range(len(data)-1):
            f.write('%d;'%i)
        f.write('%s\n'%len(data))

        # write ID and values
        for (model, var) in zip(models, vars):
            f.write(model)
            data = var.var.data.flatten().tolist()
            for val in data:
                f.write(';%f'%val)
            f.write(';0.0\n')
        f.close()

class ReadData(Module):
    """
    ReadData read matrix in DATA format. This format is used in VisPipeline
    """
    my_namespace = 'util'
    name         = 'Read Data'
    
    _input_ports   = [('filename', File)]
    _output_ports  = [('matrix',   Matrix)]
    def compute(self):
        filename = self.getInputFromPort("filename")
        f = open(filename.name, 'r')
        
        # read metadata
        type = f.readline()
        rows = int(f.readline().strip())
        cols = int(f.readline().strip())
        
        # read attributes
        attributes = f.readline().split(';')
        
        # read id, values and class
        values = np.zeros((rows, cols))
        ids    = []
        labels = []
        for r in range(rows):
            line = f.readline().split(';')
            ids.append(line[0])
            labels.append(str(line[0]))
            values[r,] = np.array([float(val) for val in line[1:-1]])
            klass = float(line[-1])
    
        matrix = Matrix()
        matrix.values     = values
        matrix.ids        = ids
        matrix.labels     = labels
        matrix.attributes = attributes
        
        self.setResult('matrix', matrix)
    
