import os
import shutil
from PyQt4 import QtGui

################################################################################

def parseMeminfo():
    """parseMeminfo() -> dictionary
    Parses /proc/meminfo and returns appropriate dictionary. Only available on
    Linux."""
    result = {}
    for line in file('/proc/meminfo'):
        (key, value) = line.split(':')
        value = value[:-1]
        if value.endswith(' kB'):
            value = int(value[:-3]) * 1024
        else:
            try:
                value = int(value)
            except ValueError:
                raise VistrailsInternalError("I was expecting '%s' to be int" 
                                             % value)
        result[key] = value
    return result

def guessTotalMemory():
    """ guessTotalMemory() -> int 
    Return system memory in bytes. 
    
    """
    return parseMeminfo()['MemTotal']

def temporaryDirectory():
    """ temporaryDirectory() -> str 
    Returns the path to the system's temporary directory 
    
    """
    return "/tmp/"

def homeDirectory():
    """ homeDirectory() -> str 
    Returns user's home directory using environment variable $HOME
    
    """
    return os.getenv('HOME')

def remoteCopyProgram():
    return "scp -p"

def remoteShellProgram():
    return "ssh -p"

def graphVizDotCommandLine():
    return 'dot -Tplain -o '

def removeGraphvizTemporaries():
    """ removeGraphvizTemporaries() -> None 
    Removes temporary files generated by dot 
    
    """
    os.unlink(temporaryDirectory() + "dot_output_vistrails.txt")
    os.unlink(temporaryDirectory() + "dot_tmp_vistrails.txt")

def link_or_copy(src, dst):
    """link_or_copy(src:str, dst:str) -> None 
    Tries to create a hard link to a file. If it is not possible, it will
    copy file src to dst 
    
    """
    # Links if possible, but we're across devices, we need to copy.
    try:
        os.link(src, dst)
    except OSError, e:
        if e.errno == 18:
            # Across-device linking is not possible. Let's copy.
            shutil.copyfile(src, dst)
        else:
            raise e

def getClipboard():
    """ getClipboard() -> int  
    Returns which part of system clipboard will be used by QtGui.QClipboard.
    On Linux, the global mouse selection should be used.

    """
    return QtGui.QClipboard.Selection

################################################################################

import unittest

class TestLinux(unittest.TestCase):
     """ Class to test Linux specific functions """
     
     def test1(self):
         """ Test if guessTotalMemory() is returning an int >= 0"""
         result = guessTotalMemory()
         assert type(result) == type(1) or type(result) == type(1L)
         assert result >= 0

     def test2(self):
         """ Test if homeDirectory is not empty """
         result = homeDirectory()
         assert result != ""

     def test3(self):
         """ Test if temporaryDirectory is not empty """
         result = temporaryDirectory()
         assert result != ""

     def test4(self):
         """ Test if origin of link_or_copy'ed file is deleteable. """
         import tempfile
         import os
         (fd1, name1) = tempfile.mkstemp()
         os.close(fd1)
         (fd2, name2) = tempfile.mkstemp()
         os.close(fd2)
         os.unlink(name2)
         link_or_copy(name1, name2)
         try:
             os.unlink(name1)
         except:
             self.fail("Should not throw")
         os.unlink(name2)

if __name__ == '__main__':
    unittest.main()
             
