#!/usr/bin/python2.5

import os, sys, argparse
versionString = "v 0.0.1"

if __name__ == "__main__":
    
    from iVisServer import QiVisServer
    from PyQt4.QtGui import QApplication
    parser = argparse.ArgumentParser(description='Run vistrials hyperwall server for vtDV3D.')
    parser.add_argument('--version', action='version', version=versionString )
    parser.add_argument( '-r', metavar='resource_directory', default='~/.vistrials/', help='Directory containing the vistrails .vt files.')
    parser.add_argument( '-p', metavar='server_port', type=int, default='5000', help='The vistrials hyperwall server listens on this port for client connections.')

    args = parser.parse_args()
    app = QApplication(sys.argv)
    server = QiVisServer( args.r, args.p )
    print "Running iVis Server Job..."
    r = app.exec_()


    sys.exit(r)
