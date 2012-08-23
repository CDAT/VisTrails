from paraview.simple import *

class PVReaderManager:
    _readers = {}

    @staticmethod
    def get_reader(parameters):
        if frozenset(parameters.items()) in PVReaderManager._readers:
            reader = PVReaderManager._readers[frozenset(parameters.items())]
        else:
            reader = PVReaderFactory.create_reader_from_parameters(parameters)
            PVReaderManager._readers[frozenset(parameters.items())] = reader
        return reader

    @staticmethod
    def register(reader, variable):
        parameters = {}
        parameters['variable'] = variable
        parameters['group'] = reader.GetXMLGroup()
        parameters['name'] = reader.GetXMLName()
        
        if 'Stride' in dir(reader):
            parameters['stride'] = tuple(reader.Stride)
            
        if reader.GetProperty("FileNames"):
            fileNames = reader.GetProperty("FileNames")
        else:
            fileNames = reader.GetProperty('FileName')

        parameters['filename'] = fileNames[0]

        PVReaderManager._readers[frozenset(parameters.items())] = reader

        return parameters

class PVReaderFactory:
    @staticmethod
    def create_reader_from_parameters(parameters):

        reader = PVReaderFactory.create_reader(parameters['group'],
                                             parameters['name'],
                                             parameters['filename'])
        reader.Stride = list(parameters['stride'])

        return reader

    @staticmethod
    def create_reader(group, name, filename):
        prototype = servermanager.ProxyManager().GetPrototypeProxy(group,
                                                                   name)
        xml_name = paraview.make_name_valid(prototype.GetXMLLabel())
        reader_func = paraview.simple._create_func(xml_name, 
                                                   servermanager.sources)
        if prototype.GetProperty("FileNames"):
            reader = reader_func(FileNames=filename)
        else:
            reader = reader_func(FileName=filename)

        return reader
