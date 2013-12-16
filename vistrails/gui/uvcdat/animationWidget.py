from PyQt4 import QtGui, QtCore
import vcs
from gui.uvcdat import customizeUVCDAT
from gui.uvcdat import uvcdatCommons
import os

def unique_connect(signal, handler):
    """Uses new style connect, adding the unique connection bit flag so that
    duplicate connections cannot be made
    """
    connectionType = QtCore.Qt.AutoConnection | QtCore.Qt.UniqueConnection
    signal.connect(handler, connectionType)
    
class QAnimationView(QtGui.QWidget):
    """ Widget containing plot options: plot button, plot type combobox, cell
    col and row selection combo box, and an options button """
    
    #static
    STOP_PATH = ":/icons/resources/icons/player_stop.gif"
    PLAY_PATH = ":/icons/resources/icons/player_play.gif"
    STOP_ICON = None
    PLAY_ICON = None
    
    def animAutoMinMax(self,value):
        if value == 0:
            self.animMin.setEnabled(True)
            self.animMax.setEnabled(True)
        else:
            self.animMin.setEnabled(False)
            self.animMax.setEnabled(False)

    def __init__(self, parent=None, canvas=None):
        QtGui.QWidget.__init__(self, parent)
        self.parent = parent
        self.root=parent.root
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        self.zoomFactor=1
        self.horizontalFactor=0
        self.verticalFactor=0
        self.creatingAnimation = False
        self.canvas = None
        
        if QAnimationView.STOP_ICON is None:
            QAnimationView.STOP_ICON = QtGui.QIcon(QAnimationView.STOP_PATH)
        if QAnimationView.PLAY_ICON is None:
            QAnimationView.PLAY_ICON = QtGui.QIcon(QAnimationView.PLAY_PATH)
        
        ## Missing options for: direction, cycling, pause, min/max
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
        self.connect(self.createButton,QtCore.SIGNAL("clicked()"), self.createOrStopClicked)

        self.animMinMax = controlsFrame.addCheckBox("Auto Min/Max")
        self.animMinMax.setChecked(True)
        self.connect(self.animMinMax,QtCore.SIGNAL("stateChanged(int)"),self.animAutoMinMax)
        self.animMin = controlsFrame.addLabeledLineEdit("Min:",newRow=False)
        self.animMax = controlsFrame.addLabeledLineEdit("Max:",newRow=False)
        self.animMax.setText("200")
        self.animMin.setEnabled(False)
        self.animMax.setEnabled(False)
        ##Player section
        self.player = uvcdatCommons.QFramedWidget("Player")
        self.zoomButton = self.player.addLabeledSlider("Zoom: x",minimum=4,maximum=40,newRow=False,divider=4)
        self.connect(self.zoomButton,QtCore.SIGNAL("valueChanged(int)"),self.zoom)
        ## Player
        grid = QtGui.QGridLayout()
        size=QtCore.QSize(40,40)
        ## Play/Stop button
        icon=QAnimationView.PLAY_ICON
        b=QtGui.QToolButton()
        b.setIcon(icon)
        b.setIconSize(size)
        b.setToolTip("Play")
        self.connect(b,QtCore.SIGNAL("clicked()"),self.playStopClicked)
        self.playstop=b
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
        self.connect(self.framesSlider,QtCore.SIGNAL("sliderPressed()"),self.stop)
        self.connect(self.framesSlider,QtCore.SIGNAL("sliderMoved(int)"),self.changedFrame)
        #self.connect(self.framesSlider,QtCore.SIGNAL("valueChanged(int)"),self.changedFrame)
        self.player.newRow()
        self.frameCount = self.player.addLabel("Frame: 0",align=QtCore.Qt.AlignCenter)
        self.player.addWidget(self.framesSlider,newRow=True)
        self.doLoop = self.player.addCheckBox("Loop",newRow=False)
        self.doLoop.setChecked(True)
        self.doLoop.clicked.connect(self.loopClicked)
        
        self.player.newRow()
        self.player.addLabel("Playback Speed",align=QtCore.Qt.AlignLeft)
        self.speedSlider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.speedSlider.setMinimum(0.1)
        self.speedSlider.setMaximum(60)
        self.speedSlider.setToolTip("Frames per second")
        self.player.addWidget(self.speedSlider, newRow=True)
        self.connect(self.speedSlider,QtCore.SIGNAL("sliderMoved(int)"),self.speedChanged)

        self.player.setEnabled(False)
        controlsFrame.addWidget(self.player,newRow=True)

        layout.addWidget(controlsFrame)

        self.setCanvas(canvas)
        self.stopCreating()
        
    def loopClicked(self, checked):
        self.canvas.animate.loop = checked
        
    def horizPanned(self,value):
        self.canvas.animate.horizontal(value)
        self.canvas.animate.frame(self.framesSlider.value())

    def vertPanned(self,value):
        self.canvas.animate.vertical(-value)
        self.canvas.animate.frame(self.framesSlider.value())
        
    def disconnectAnimationSignals(self):
        self.canvas.animate.signals.drew.disconnect(self.drew)
        self.canvas.animate.signals.paused.disconnect(self.paused)
        
    def connectAnimationSignals(self):
        unique_connect(self.canvas.animate.signals.drew, self.drew)
        unique_connect(self.canvas.animate.signals.paused, self.paused)

    def setCanvas(self,canvas):
        if self.canvas is not None:
            self.disconnectAnimationSignals()
            
        self.canvas = canvas
        
        if canvas is None:
            self.setEnabled(False)
            return
        
        self.setEnabled(True)
        
        self.connectAnimationSignals()
        
        self.doLoop.setChecked(canvas.animate.loop)
        
        self.speedSlider.setValue(canvas.animate.fps())
        
        created = (canvas.animate.create_flg == 1)
        self.createButton.setEnabled(not created)
        self.player.setEnabled(created)
        
        if created:
            self.framesSlider.setMaximum(canvas.animate.number_of_frames()-1)
            self.updatePlayStopIcon()
        
    def changedFrame(self,value):
        self.canvas.animate.frame(value)
    
    def speedChanged(self, value):
        self.canvas.animate.fps(value)
        

    def createOrStopClicked(self):
        ### Creates or stops creating animation
        if self.canvas.animate.create_flg == 1:
            return
        elif self.creatingAnimation:
            self.stopCreating()
            return

        self.creatingAnimation = True

        icon = QAnimationView.STOP_ICON
        self.createButton.setIcon(icon)
        self.createButton.setText("Stop Creating Frames")

        if self.animMinMax.isChecked():
            min=None
            max=None
        else:
            try:
                min = eval(str(self.animMin.text()))
            except:
                min = None
            try:
                max = eval(str(self.animMax.text()))
            except:
                max = None
                
        animationSignals = self.canvas.animate.signals
        unique_connect(animationSignals.created, self.animationCreated)
        unique_connect(animationSignals.canceled, self.stopCreating)
        self.canvas.animate.create(thread_it=1,min=min,max=max)
        
    def stopCreating(self):
        self.creatingAnimation = False
        self.createButton.setIcon(QAnimationView.PLAY_ICON)
        self.createButton.setText("Generate Animation")

    def animationCreated(self):
        self.stopCreating()
        self.setCanvas(self.canvas) #sets up widgets based on animation object
        
        #update toolbar
        controller = self.root.get_current_project_controller()
        sheet = controller.get_sheet_widget(controller.current_sheetName)
        coords = controller.current_cell_coords
        sheet.getCellToolBar(coords[0], coords[1]).snapTo(coords[0], coords[1])

    def playStopClicked(self):
        if self.canvas.animate.create_flg == 1:
            if self.canvas.animate.run_flg == 0:
                self.canvas.animate.run()
            else:
                self.canvas.animate.stop()
            self.updatePlayStopIcon()

    def updatePlayStopIcon(self):
        if self.canvas.animate.run_flg == 0:
            self.playstop.setIcon(QAnimationView.PLAY_ICON)
        else:
            self.playstop.setIcon(QAnimationView.STOP_ICON)

    def stop(self):
        self.canvas.animate.pause_run()

    def drew(self):
        self.framesSlider.setValue(self.canvas.animate.current_frame)
        self.frameCount.setText("Frame: %d" % self.canvas.animate.current_frame)
        
    def paused(self):
        self.updatePlayStopIcon()
        
    def save(self):
        fnm = str(QtGui.QFileDialog.getSaveFileName(None,"MP4 file name...",filter="MP4 file (*.mp4, *.mpeg)"))
        if fnm[-4:].lower() not in [".mp4",".mov",".avi"]:
            fnm+=".mp4"
        self.canvas.animate.save(fnm)

    def load(self):
        pass

    def zoom(self,value):
        self.zoomFactor=value/4.
        #canvas=int(self.canvas.currentText())-1
        self.canvas.animate.zoom(self.zoomFactor)
        self.canvas.animate.frame(self.framesSlider.value())

