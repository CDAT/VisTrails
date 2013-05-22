from PyQt4 import QtGui, QtCore
import vcs
from gui.uvcdat import customizeUVCDAT
from gui.uvcdat import uvcdatCommons
import os
#from cdatguiwrap import VCSQtManager

class QThreadAnimationCreate(QtCore.QThread):
    def __init__(self,parent,canvas,cursor):
        print "ok creating thread"
        QtCore.QThread.__init__(self,parent=parent)
        self.parent=parent
        self.canvas=canvas
        self.cursor=cursor
        ## self.exiting=False
    def run(self):
        self.canvas.animate.create(thread_it=1)
        self.parent.emit(QtCore.SIGNAL("animationCreated"),self.canvas,self.cursor)
    ## def __del__(self):
    ##     self.exiting=True
    ##     self.wait()
    
    
class QAnimationView(QtGui.QWidget):
    """ Widget containing plot options: plot button, plot type combobox, cell
    col and row selection combo box, and an options button """
    
    def __init__(self, parent=None, canvas=None):
        QtGui.QWidget.__init__(self, parent)
        self.parent = parent
        self.root=parent.root
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.zoomFactor=0
        self.horizontalFactor=0
        self.verticalFactor=0
        ## Missing options for: direction, cycling, pause, min/max
        self.canvas = canvas
        ## Saving
        saveFrame = uvcdatCommons.QFramedWidget("I/O")
        saveButton = saveFrame.addButton("Save:",newRow=False,buttonType="Push",icon=customizeUVCDAT.saveMovie)
        saveLineEdit = saveFrame.addLabeledLineEdit("",newRow=False)
        self.saveType = saveFrame.addRadioFrame("",["ras","mp4"],newRow=False)
        b=self.saveType.buttons["ras"]
        b.setChecked(True)
        loadButton = saveFrame.addButton("Load:",newRow=True,buttonType="Push",icon=customizeUVCDAT.loadMovie)
        loadLineEdit = saveFrame.addLabeledLineEdit("",newRow=False)
        layout.addWidget(saveFrame)


        ## Actions
        controlsFrame = uvcdatCommons.QFramedWidget("Controls")
        #self.canvas = controlsFrame.addLabeledComboBox("Canvas",['1','2','3','4'],indent=False)
        icon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'symbol_add.ico'))
        self.createButton = controlsFrame.addButton("Generate Animation",newRow=False,icon=icon,buttonType="Push")
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"),self.create)

        ##Player section
        self.player = uvcdatCommons.QFramedWidget("Player")
        icon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'zoom_in_01.ico'))
        self.zoomInButton = self.player.addButton("Zoom In",newRow=False,icon=icon,buttonType="Push")
        self.connect(self.zoomInButton,QtCore.SIGNAL("clicked()"),self.zoomIn)
        icon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'zoom_out_01.ico'))
        self.zoomOutButton = self.player.addButton("Zoom Out",newRow=False,icon=icon,buttonType="Push")
        self.zoomOutButton.setEnabled(False)
        self.connect(self.zoomOutButton,QtCore.SIGNAL("clicked()"),self.zoomOut)
        ## Player
        grid = QtGui.QGridLayout()
        size=QtCore.QSize(40,40)
        ## UP button
        icon=QtGui.QIcon(':icons/resources/icons/pan_up.gif')
        b=QtGui.QToolButton()
        b.setIcon(icon)
        b.setIconSize(size)
        b.setToolTip("Span Up")
        b.setEnabled(False)
        grid.addWidget(b,0,1)
        self.upButton=b
        self.connect(self.upButton,QtCore.SIGNAL("clicked()"),self.up)
        ## Down button
        icon=QtGui.QIcon(':icons/resources/icons/pan_down.gif')
        b=QtGui.QToolButton()
        b.setIcon(icon)
        b.setIconSize(size)
        b.setToolTip("Span Down")
        b.setEnabled(False)
        grid.addWidget(b,2,1)
        self.downButton=b
        self.connect(self.downButton,QtCore.SIGNAL("clicked()"),self.down)
        ## Left button
        icon=QtGui.QIcon(':icons/resources/icons/pan_left.gif')
        b=QtGui.QToolButton()
        b.setIcon(icon)
        b.setIconSize(size)
        b.setToolTip("Span Left")
        b.setEnabled(False)
        grid.addWidget(b,1,0)
        self.leftButton=b
        self.connect(self.leftButton,QtCore.SIGNAL("clicked()"),self.left)
        ## Right button
        icon=QtGui.QIcon(':icons/resources/icons/pan_right.gif')
        b=QtGui.QToolButton()
        b.setIcon(icon)
        b.setIconSize(size)
        b.setToolTip("Span Right")
        b.setEnabled(False)
        grid.addWidget(b,1,2)
        self.rightButton=b
        self.connect(self.rightButton,QtCore.SIGNAL("clicked()"),self.right)
        ## Play/Stop button
        icon=QtGui.QIcon(':icons/resources/icons/player_play.gif')
        b=QtGui.QToolButton()
        b.setIcon(icon)
        b.setIconSize(size)
        b.setToolTip("Play")
        self.connect(b,QtCore.SIGNAL("clicked()"),self.run)
        grid.addWidget(b,1,1)

        
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(grid)
        ## Horizontal Pan
        self.horizPan=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.horizPan.setToolTip("Span Horizontally")
        self.horizPan.setValue(50)
        vbox.addWidget(self.horizPan)

        hbox=QtGui.QHBoxLayout()
        ## Vertical Pan
        self.vertPan=QtGui.QSlider(QtCore.Qt.Vertical)
        self.vertPan.setToolTip("Span Vertically")
        self.vertPan.setValue(50)
        hbox.addLayout(vbox)
        hbox.addWidget(self.vertPan)

        self.player.vbox.addLayout(hbox)
        ## Frames Slider
        self.framesSlider=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.framesSlider.setTickPosition(QtGui.QSlider.TicksAbove)
        self.player.newRow()
        self.FrameCount = self.player.addLabel("Frame: 0",align=QtCore.Qt.AlignCenter)
        self.player.addWidget(self.framesSlider,newRow=True)
        self.player.setEnabled(False)
        controlsFrame.addWidget(self.player,newRow=True)

        layout.addWidget(controlsFrame)

        self.connect(self,QtCore.SIGNAL("animationCreated"),self.animationCreated)
        self.animationTimer = QtCore.QBasicTimer()
        self.animationFrame = 0        
        

    def setCanvas(self,canvas):
        self.canvas = canvas
        
    def create(self):
        ### Creates animation
        c = self.cursor()
        self.setCursor(QtCore.Qt.BusyCursor)
        icon = QtGui.QIcon(":/icons/resources/icons/player_stop.gif")
        self.createButton.setIcon(icon)
        self.createButton.setText("Stop Creating Frames")
        #self.disconnect(self.createButton,QtCore.SIGNAL("clicked()"),self.create)
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"),self.stop)
        #t=QThreadAnimationCreate(self,self.canvas,c)
        #t.start()
        self.canvas.animate.create(thread_it=1)
        self.animationCreated(self.canvas, c)
        
    def animationCreated(self,canvas,cursor):
        icon = QtGui.QIcon(":/icons/resources/icons/player_play.gif")
        self.createButton.setIcon(icon)
        self.createButton.setText("Generate Animation")
        #self.disconnect(self.createButton,QtCore.SIGNAL("clicked()"),self.stop)
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"),self.create)
        ## All right now we need to prep the player
        nframes=canvas.animate.number_of_frames()
        self.framesSlider.setMaximum(nframes)
        self.player.setEnabled(True)
        self.setCursor(cursor)
    def run(self):
        ## ? Need to change player icon?
        self.animationFrame = 0
        if not self.animationTimer.isActive():
            self.animationTimer.start(100, self)
        #c = self.cursor()
        #self.setCursor(QtCore.Qt.BusyCursor)
        #canvas=int(self.canvas.currentText())-1
        #self.canvas.animate.pause(99)
        #self.canvas.animate.run()
        #self.setCursor(c)
    def stop(self):
        # ??? need to change playe ricon?
        self.animationTimer.stop()
        ### stops generating animation
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.stop_create()
    def timerEvent(self, event):
        if self.animationFrame>=self.canvas.animate.number_of_frames():
            self.animationTimer.stop()
        else:
            self.canvas.animate.draw(self.animationFrame)
#            fn = self.canvas.animate.animation_files[self.animationFrame]
#            print fn
#            self.canvas.clear()
#            self.canvas.animate.vcs_self.canvas.put_png_on_canvas(fn)
            self.animationFrame += 1
    def save(self):
        pass
    def load(self):
        pass
    def zoomIn(self):
        self.zoomFactor+=0.1
        if self.zoomFactor==10:
            self.zoomInButton.setEnabled(False)
        self.zoomOutButton.setEnabled(True)
        self.upButton.setEnabled(True)
        self.downButton.setEnabled(True)
        self.leftButton.setEnabled(True)
        self.rightButton.setEnabled(True)
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.zoom(self.zoomFactor)
    def zoomOut(self):
        self.zoomFactor-=1
        self.zoomInButton.setEnabled(True)
        if self.zoomFactor==0:
            self.zoomOutButton.setEnabled(False)
            self.upButton.setEnabled(False)
            self.downButton.setEnabled(False)
            self.leftButton.setEnabled(False)
            self.rightButton.setEnabled(False)
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.zoom(self.zoomFactor)
        
    def up(self):
        self.verticalFactor+=1
        self.downButton.setEnabled(True)
        if self.verticalFactor==100:
            self.upButton.setEnabled(False)
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.vertical(self.verticalFactor)
    def down(self):
        self.verticalFactor-=1
        self.upButton.setEnabled(True)
        if self.verticalFactor==-100:
            self.downButton.setEnabled(False)
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.vertical(self.verticalFactor)
    def right(self):
        self.horizontalFactor+=1
        self.leftButton.setEnabled(True)
        if self.horizontalFactor==100:
            self.rightButton.setEnabled(False)
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.horizontal(self.horizontalFactor)
    def left(self):
        self.horizontalFactor-=1
        self.rightButton.setEnabled(True)
        if self.horizontalFactor==-100:
            self.leftButton.setEnabled(False)
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.horizontal(self.horizontalFactor)

            
