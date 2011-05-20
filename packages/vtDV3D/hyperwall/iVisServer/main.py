#!/usr/bin/python2.5

import sys

versionString = "v 0.0.1"
port = None

def help():
    print "Common options:"
    print "-p [--port]     Specify port for socket connection"
    print "-h [--help]     Print this help message and quit"
    print "-v [--version]  Print version information and quit"
    sys.exit(0)

def version():
    print "iVis Server, version", versionString
    sys.exit(0)

def processArgs(argv):
    global port
    for i in range(len(argv)):
        if argv[i] == "-p" or argv[i] == "--port":
            i += 1
            port = argv[i]
        elif argv[i] == "-h" or argv[i] == "--help":
            help()
        elif argv[i] == "-v" or argv[i] == "--version":
            version()


if __name__ == "__main__":
    from iVisServer import QiVisServer
    from PyQt4.QtGui import QApplication

    processArgs(sys.argv)
    app = QApplication(sys.argv)

    
    if port is None:
        help()

    server = QiVisServer(int(port))
    print "Running iVis Server Job..."
    r = app.exec_()


    sys.exit(r)
