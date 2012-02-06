'''
Created on Feb 4, 2012

@author: tpmaxwel
'''
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os, sys, threading, subprocess, time
ControlEventType =  QEvent.User + 1
   
class QtControllerEvent( QEvent ):
 
    def __init__( self, controlEventData ):
         QEvent.__init__ ( self, ControlEventType )
         try:
             self.controlEventType = controlEventData[1]
             if ( self.controlEventType == 'P' ) or  ( self.controlEventType == 'R' ):
                 self.buttonId = ( int(controlEventData[2]), int(controlEventData[3]) )
#                 print " Button event : %s "  % str( self.buttonId  )
             if ( self.controlEventType.lower() == 'j' ):
                 sx = '0x'+controlEventData[2:4]
                 sy = '0x'+controlEventData[4:6]
                 self.jx = ( int( sx, 0 ) - 128 ) / 128.0;
                 self.jy = ( 128 - int( sy, 0 ) ) / 128.0;
#                 print " Joystick event : %s %s ( %d %d ) (%.2f %.2f ) "  % ( sx, sy, ix, iy, self.jx, self.jy )
         except Exception, err:
             print>>sys.stderr, " ControllerEvent Error: ", str(err)
     
class Joystick( threading.Thread ):

    def __init__( self ):
        threading.Thread.__init__( self )
        self.active = False 
        self.daemon = True
        self.targets = set()     
        try:
            from WirelessControllerInterface import WirelessController
            self.controller = WirelessController()
        except:
            print " No working Wireless Controller installed."
            self.controller = None 
           
    def enabled( self ):
        return ( self.controller <> None )
    
    def addTarget( self, target ):
        self.targets.add( target )

    def stop(self):
        self.isActive = False

    def run(self):
        if self.controller == None: return 
        if self.controller.start() == 0:
            self.isActive = True
            while self.isActive:
                status, event_spec = self.controller.getEventData( )  
                if status < 0: break  
                if event_spec[0] == 'E':
                   print>>sys.stderr, "Control device generated error: ",  event_spec
                else:
#                    print "Posting event: %s, status = %d" % ( event_spec, status )
                    for target in self.targets:
                        QApplication.postEvent( target, QtControllerEvent( event_spec ) )  
            self.controller.stop()
         
joystick = Joystick()
joystick.start()