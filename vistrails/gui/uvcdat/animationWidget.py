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
        self.parent.emit(QtCore.SIGNAL("animationCreated"),self.cursor)
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
        self.zoomFactor=1
        self.horizontalFactor=0
        self.verticalFactor=0
        ## Missing options for: direction, cycling, pause, min/max
        self.canvas = canvas
        ## Saving
        saveFrame = uvcdatCommons.QFramedWidget("I/O")
        saveButton = saveFrame.addButton("Save:",newRow=False,buttonType="Push",icon=customizeUVCDAT.saveMovie)
        self.connect(saveButton,QtCore.SIGNAL("clicked()"),self.save)

        #self.saveType = saveFrame.addRadioFrame("",["mp4",],newRow=False)
        #b=self.saveType.buttons["mp4"]
        #b.setChecked(True)
        #loadButton = saveFrame.addButton("Load:",newRow=True,buttonType="Push",icon=customizeUVCDAT.loadMovie)
        #loadLineEdit = saveFrame.addLabeledLineEdit("",newRow=False)
        layout.addWidget(saveFrame)


        ## Actions
        controlsFrame = uvcdatCommons.QFramedWidget("Controls")
        #self.canvas = controlsFrame.addLabeledComboBox("Canvas",['1','2','3','4'],indent=False)
        icon = QtGui.QIcon(os.path.join(customizeUVCDAT.ICONPATH, 'symbol_add.ico'))
        self.createButton = controlsFrame.addButton("Generate Animation",newRow=False,icon=icon,buttonType="Push")
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"),self.create)

        ##Player section
        self.player = uvcdatCommons.QFramedWidget("Player")
        self.zoomButton = self.player.addLabeledSlider("Zoom: x",minimum=4,maximum=40,newRow=False,divider=4)
        self.connect(self.zoomButton,QtCore.SIGNAL("valueChanged(int)"),self.zoom)
        ## Player
        grid = QtGui.QGridLayout()
        size=QtCore.QSize(40,40)
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
        self.horizPan.setMinimum(-100)
        self.horizPan.setMaximum(100)
        self.horizPan.setToolTip("Span Horizontally")
        self.horizPan.setValue(0)
        vbox.addWidget(self.horizPan)
        self.connect(self.horizPan,QtCore.SIGNAL("valueChanged(int)"),self.horizPanned)

        hbox=QtGui.QHBoxLayout()
        ## Vertical Pan
        self.vertPan=QtGui.QSlider(QtCore.Qt.Vertical)
        self.vertPan.setMinimum(-100)
        self.vertPan.setMaximum(100)
        self.vertPan.setToolTip("Span Vertically")
        self.vertPan.setValue(0)
        hbox.addLayout(vbox)
        hbox.addWidget(self.vertPan)
        self.connect(self.vertPan,QtCore.SIGNAL("valueChanged(int)"),self.vertPanned)


        self.player.vbox.addLayout(hbox)
        ## Frames Slider
        self.framesSlider=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.framesSlider.setTickPosition(QtGui.QSlider.TicksAbove)
        self.connect(self.framesSlider,QtCore.SIGNAL("valueChanged(int)"),self.changedFrame)
        self.player.newRow()
        self.frameCount = self.player.addLabel("Frame: 0",align=QtCore.Qt.AlignCenter)
        self.player.addWidget(self.framesSlider,newRow=True)
        self.doLoop = self.player.addCheckBox("Loop",newRow=False)
        self.doLoop.setChecked(True)
        self.player.setEnabled(False)
        controlsFrame.addWidget(self.player,newRow=True)

        layout.addWidget(controlsFrame)

        self.connect(self,QtCore.SIGNAL("animationCreated"),self.animationCreated)
        self.animationTimer = QtCore.QBasicTimer()
        self.animationFrame = 0        
        
    def horizPanned(self,value):
        self.canvas.animate.horizontal(value)
        self.canvas.animate.frame(self.framesSlider.value())

    def vertPanned(self,value):
        self.canvas.animate.vertical(-value)
        self.canvas.animate.frame(self.framesSlider.value())

    def setCanvas(self,canvas):
        self.canvas = canvas
    def changedFrame(self,value):
        print "Going to Frame:",value
        self.canvas.animate.frame(value)
        self.frameCount.setText("Frame: %i" % value)

    def create(self):
        ### Creates animation
        self.previousCursor = self.cursor()
        self.setCursor(QtCore.Qt.BusyCursor)
        icon = QtGui.QIcon(":/icons/resources/icons/player_stop.gif")
        self.createButton.setIcon(icon)
        self.createButton.setText("Stop Creating Frames")
        #self.disconnect(self.createButton,QtCore.SIGNAL("clicked()"),self.create)
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"),self.stop)
        #t=QThreadAnimationCreate(self,self.canvas,c)
        #t.start()
        C = self.canvas.animate.create(thread_it=1)
        #self.connect(self,QtCore.SIGNAL("AnimationCreated"),self.animationCreated)
        self.connect(C,QtCore.SIGNAL("AnimationCreated"),self.animationCreated)

    def animationCreated(self,*args):
        print "done creating:",args
        icon = QtGui.QIcon(":/icons/resources/icons/player_play.gif")
        self.createButton.setIcon(icon)
        self.createButton.setText("Generate Animation")
        #self.disconnect(self.createButton,QtCore.SIGNAL("clicked()"),self.stop)
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"),self.create)
        ## All right now we need to prep the player
        nframes=self.canvas.animate.number_of_frames()-1
        self.framesSlider.setMaximum(nframes)
        self.player.setEnabled(True)
        self.setCursor(self.previousCursor)
        self.framesSlider.setValue(0)
        self.changedFrame(0) #in case the tick was already on 0


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
            if self.doLoop.isChecked():
                self.animationFrame = 0
                self.canvas.animate.draw(0)
                self.framesSlider.setValue(0)
            else:
                self.animationTimer.stop()
        else:
            self.canvas.animate.draw(self.animationFrame)
            self.framesSlider.setValue(self.animationFrame)
            self.animationFrame += 1
    def save(self):
        self.canvas.animate.save(str(QtGui.QFileDialog.getSaveFileName(None,"MP4 file name...",filter="MP4 file (*.mp4, *.mpeg)")))

    def load(self):
        pass
    def zoom(self,value):
        self.zoomFactor=value/4.
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.zoom(self.zoomFactor)
        self.canvas.animate.frame(self.framesSlider.value())
        
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

            
