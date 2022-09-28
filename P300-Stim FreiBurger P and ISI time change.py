import psychopy.visual
import psychopy.event
from psychopy import gui, core, logging
import numpy
import math
import random
import string
from PIL import Image
import serial
from serial.tools import list_ports
import sys
from os.path import expanduser
import wx
import time
from threading import Timer

#########################################################################################################################
#########################################################################################################################
## Parameter zum Aendern
#########################################################################################################################
#########################################################################################################################

ScreenNumber=0
DesiredRefreshRate=60
ExpectedFrameRateMin=DesiredRefreshRate-1
ExpectedFrameRateMax=DesiredRefreshRate+1

LogMAR2P300Stim=0.0

TestIfGoodSubject=False
RareBlack=False

OnFrames=37
OffFramesMin=23
OffFramesJitter=15
nTrials=60
StimOri=[45, 315]
nOri=len(StimOri)

P300Rare=[0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 1,1,1,1,1,1]
P300SizeIndex=[0,1,2,3,4,5, 0,1,2,3,4,5, 0,1,2,3,4,5, 0,1,2,3,4,5, 0,1,2,3,4,5, 0,1,2,3,4,5, 0,1,2,3,4,5]
nP300Stim=len(P300Rare)

UpperLimit=1.0 # Sollte nochmal weiter unten an die Bildschirmgeometrie angepasst werden.
LowerLimit=-1.0 # Sollte nochmal weiter unten an die Bildschirmgeometrie angepasst werden.
BackgroundColor=1.0
RareBackground=1.0
FrequentBackground=1.0


ConstantOffsets=[-0.15, 0.0, +0.15, +0.3, +0.45, +0.6]
nConstantOffsets=len(ConstantOffsets)

CentralLogFilename = "PermanentLogFile.txt"
BaseFileName = "Data"


if TestIfGoodSubject:
    BackgroundColor=0.0
    RareBackground=1.0
    FrequentBackground=-1.0
    OffFramesMin=50
    OnFrames=10
    if RareBlack:
        RareBackground=-1.0
        FrequentBackground=1.0

#########################################################################################################################
#########################################################################################################################
## Misc
#########################################################################################################################
#########################################################################################################################


OriCount=[0]*nOri

def GetOri():
    global OriCount
    SelectorCounts=[x+random.randint(0, 3) for x in OriCount]
    SelectorCounts=[float(x) for x in SelectorCounts]
    SelectorCountsJitter=[x+numpy.random.random()*0.1 for x in SelectorCounts] # damit bei Gleichstand nicht immer der erste drankommt.
    MinPos= SelectorCountsJitter.index(min(SelectorCountsJitter))
    OriCount[MinPos]+=1
    return MinPos
    

#########################################################################################################################
#########################################################################################################################
## Start Hauptteil
#########################################################################################################################
#########################################################################################################################


MonitorList=psychopy.monitors.getAllMonitors()
print MonitorList
#MonitorList = [x for x in MonitorList if 'Stimulus' in x]
MonitorList = [x for x in MonitorList if 'LG' in x]


if len(MonitorList)==0:
    MonitorList=psychopy.monitors.getAllMonitors()



ExpName='P300'
myDlg = gui.Dlg(title=ExpName)
myDlg.addField('Monitor:', choices= MonitorList)
myDlg.addField('Assumed Acuity:', 3.0, color="red")
myDlg.addField('LogMAR or Dec. Acuity', choices = ['logMAR', 'Dec. Acuity'])
myDlg.addField('Stimulus duration', choices = ['short', 'long'])
myDlg.addField('# Trials:', 1000)
myDlg.show()  # show dialog and wait for OK or Cancel
if myDlg.OK:  # then the user pressed OK
    thisInfo = myDlg.data
else:
    print('user cancelled')
    core.quit()
    

TheMonitor=thisInfo[0]
if (thisInfo[2] == 'logMAR'):
    AssumedLogMAR=float(thisInfo[1])
else:
    AssumedLogMAR=-numpy.log10(float(thisInfo[1]))
FoundThresholdLog=AssumedLogMAR+LogMAR2P300Stim
nTrials=thisInfo[4]

trans_table = string.maketrans( string.punctuation, "_"*len(string.punctuation))

TheMonitor_CleanedStr = TheMonitor.encode('ascii').translate(trans_table)

TimeStr=str(psychopy.core.getAbsTime())
LogFileName = "P300_"+TimeStr+".txt"

StartAcuity=10.0 ** (-AssumedLogMAR)
print StartAcuity

if (thisInfo[3] == 'short'):
    OnFrames=6
    OffFramesMin=7
else:
    OnFrames=37
    OffFramesMin=23

#########################################################################################################################
#########################################################################################################################
## Bildschirm
#########################################################################################################################
#########################################################################################################################

# Philosophie: Die im Monitor Center eingestellten Parameter sollen gelten und es wird versucht, diese tatsaechlich einzustellen.

MyMonitor=psychopy.monitors.Monitor(TheMonitor)

print (psychopy.monitors.getAllMonitors())

Dist = MyMonitor.getDistance()
WidthCm = MyMonitor.getWidth()
SizePixels = MyMonitor.getSizePix()
WidthPixels=SizePixels[0]
HeightPixels=SizePixels[1]

print ("Dist, WidthCm, SizePixels", Dist, WidthCm, SizePixels)
PixPerCm=WidthPixels/WidthCm

app = wx.App(False)
disp=wx.Display(ScreenNumber)
dispGeom=wx.Display.GetGeometry(disp)
dispWidth = dispGeom[2]
dispHeight = dispGeom[3]
print wx.Display.GetCount(), "displays, selected display is #", ScreenNumber
print "Screen info from wx library"
dispMode=wx.Display.GetCurrentMode(disp)
dispFreq=dispMode.refresh
dispDepth=dispMode.Depth
print "refresh frequency", dispFreq, "(0 = unknown)"
print "width height", dispWidth, dispHeight
#print "scale factor", wx.Display.GetScaleFactor(disp)
#print "resolution", wx.Display.GetPPI(disp)
#print "available:"
#print wx.Display.GetModes(disp)


if (WidthPixels != dispWidth):
    print ("ALERT: assumed monitor pixels and real (logical) monitor pixels (wx library) do not match.", WidthPixels, dispWidth)
    print "Trying to adjust real monitor pixels"
    NewMode=wx.VideoMode(width=WidthPixels, height=HeightPixels, depth=dispDepth, freq=DesiredRefreshRate)
    wx.Display.ChangeMode(disp, mode=NewMode)
    dispGeom=wx.Display.GetGeometry(disp)
    dispWidth = dispGeom[2]
    dispHeight = dispGeom[3]
    print "new width height", dispWidth, dispHeight
    if (WidthPixels != dispWidth):
        print "XXXXXXXXXX Screen resolution still not matching."
        wx.MessageBox("Screen resolution problem encountered.", "WARNING", wx.OK)

win = psychopy.visual.Window(
    units="deg",
    fullscr=False,
    monitor=TheMonitor,
    waitBlanking=True,
    size=(WidthPixels,HeightPixels),
    color=BackgroundColor,
    allowStencil = True,
    winType='pyglet',
    allowGUI=False,
    checkTiming=True,
    screen=ScreenNumber
)

xSizePix=win.size[0]
ySizePix=win.size[1]
print "window size", xSizePix, ySizePix
if (xSizePix != WidthPixels):
    print ("ALERT: window pixels and monitor pixels do not match.", xSizePix, WidthPixels)

FrameRate=win.getActualFrameRate(nIdentical=10, nMaxFrames=100, nWarmUpFrames=10, threshold=1)

print "frame rate (PsychoPy)", FrameRate
if (FrameRate<ExpectedFrameRateMin) or (FrameRate>ExpectedFrameRateMax):
    print "XXXXXXXXX FRAME RATE NOT AS EXPECTED:",FrameRate,", should be", DesiredRefreshRate, "XXXXXXX "
    print "Trying to adjust frame rate"
    NewMode=wx.VideoMode(width=WidthPixels, height=HeightPixels, depth=dispDepth, freq=DesiredRefreshRate)
    FrameRate=win.getActualFrameRate()
    print "new frame rate", FrameRate
    if (FrameRate<ExpectedFrameRateMin) or (FrameRate>ExpectedFrameRateMax):
        print "XXXXXXXXXX Frame rate still not matching."
        wx.MessageBox("Frame rate problem encountered.", "WARNING", wx.OK)


grating = psychopy.visual.GratingStim(
    win=win,
    units="deg",
    size=(10, 10),
    mask='raisedCos',
    maskParams = {'fringeWidth':0.5}
)
psychopy.event.Mouse(visible=True)

xSizePix=win.size[0]
ySizePix=win.size[1]
xm=xSizePix/2
ym=ySizePix/2


#########################################################################################################################
#########################################################################################################################
## Reize vorbereiten
#########################################################################################################################
#########################################################################################################################

TemplatePixels=xSizePix
if ySizePix<xSizePix:
    TemplatePixels=ySizePix
TemplateDeg=psychopy.tools.monitorunittools.pix2deg(TemplatePixels, MyMonitor)
print TemplatePixels, TemplateDeg
thick=1.0
thick=TemplateDeg/5.0*0.95
size=thick*5.0



###### Closed Ring Stimulus (FreiBurger)
angles=numpy.linspace(90, 450, num=360)
anglesList=angles.tolist()
vertexlist = [psychopy.tools.coordinatetools.pol2cart(elem, size/2, units='deg') for elem in anglesList]

myBar = psychopy.visual.Rect(win, units = "deg", width=thick, height=thick*7, lineColor='white', fillColor='white')
myRing=psychopy.visual.ShapeStim(win, units='deg', lineColor='black', fillColor='black', lineWidth=0, vertices=vertexlist, interpolate=True)
myBackground=psychopy.visual.Rect(win, width=2, height=2, units='norm', fillColor=FrequentBackground)


if TestIfGoodSubject:
    tmp_Landolt = psychopy.visual.BufferImageStim(win, stim=[myBackground])
else:
    tmp_Landolt = psychopy.visual.BufferImageStim(win, stim=[myBackground, myRing, myBar])



###### Closed Circle
ngles=numpy.linspace(90, 450, num=360)
anglesList=angles.tolist()
vertexlist = [psychopy.tools.coordinatetools.pol2cart(elem, size/2, units='deg') for elem in anglesList]

myRing=psychopy.visual.ShapeStim(win, units='deg', lineColor='black', fillColor='black', lineWidth=0, vertices=vertexlist, interpolate=True)
myBackground=psychopy.visual.Rect(win, width=2, height=2, units='norm', fillColor=FrequentBackground)

if TestIfGoodSubject:
    tmp_ClosedRing = psychopy.visual.BufferImageStim(win, stim=[myBackground])
else:
    tmp_ClosedRing = psychopy.visual.BufferImageStim(win, stim=[myBackground, myRing])



UpperLimit=numpy.log10(psychopy.tools.monitorunittools.pix2deg(min(xSizePix, ySizePix), MyMonitor)*60/5*0.8)
LowerLimit=numpy.log10(psychopy.tools.monitorunittools.pix2deg(1, MyMonitor)*60) 

print "LowerLimit", LowerLimit, "UpperLimit", UpperLimit

Warnung='ATTENTION: VISUAL ACUITY NOT POSSIBLE FOR THIS SCREEN!' 
RequestedLogArcminPreliminary=FoundThresholdLog+ConstantOffsets[5]
RequestedLogArcmin=numpy.clip(RequestedLogArcminPreliminary, LowerLimit, UpperLimit)
if (RequestedLogArcminPreliminary!=RequestedLogArcmin):
    myDlg = gui.Dlg(title=Warnung, labelButtonOK=' I dont care ', labelButtonCancel=' oups...lets start over ')
    myDlg.addText('Visual acuity corresponding to the largest ringsize has been clipped',color="red")
    myDlg.addFixedField(label='largest Ring size corresponds to (logMAR)', initial=RequestedLogArcminPreliminary, tip="logMAR")
    myDlg.addFixedField(label='clipped to', initial=RequestedLogArcmin)
    myDlg.show()  # show dialog and wait for OK or Cancel
    if myDlg.OK:  # then the user pressed OK
        thisInfo = myDlg.data
    else:
        print('user cancelled')
        core.quit()

#########################################################################################################################
#########################################################################################################################
## Serielle Schnittstelle vorbereiten
#########################################################################################################################
#########################################################################################################################



TriggerSerialPortName='/dev/cu.usbmodem143201' #oder 14301
NumatoModel=16 
nNibbles=int(NumatoModel/8)
print(TriggerSerialPortName)


TriggerSerial=None
StandardTriggerDuration=0.003



def InitTriggerNumato():
    global TriggerSerial
    global TriggerSerialPortName
    global nNibbles



    try:
        TriggerSerial = serial.Serial(TriggerSerialPortName, 19200)
        print "Serial port for buttons found:", TriggerSerial
    except:
        Warnungtriggeroutput='ATTENTION: Trigger Output is not possible!' 
        if TriggerSerial==False or TriggerSerial==None:
            myDlg = gui.Dlg(title=Warnungtriggeroutput, labelButtonOK=' I dont care ', labelButtonCancel=' oups yes I am...lets start over ')
            myDlg.addText('the Trigger Serial Port Name has not been found, Are you at a different location?',color="red")
           
            myDlg.show()  # show dialog and wait for OK or Cancel
            if myDlg.OK:  # then the user pressed OK
                thisInfo = myDlg.data
                TriggerSerial=False
                TriggerSerial=None
                return None
            else:
                print('user cancelled')
                core.quit()
#        

#    try:
#        TriggerSerial = serial.Serial(TriggerSerialPortName, 19200)
#        print "Serial port for buttons found:", TriggerSerial
#    except:
#        TriggerSerial=False
#        TriggerSerial=None
#        print "No trigger adapter found."
#    return None




    HexString="ff"
    HexString=HexString.zfill(nNibbles)
    TriggerSerial.write("gpio iomask "+HexString+"\r")
    Echo=TriggerSerial.read_until("\n")
#    print "Echo", Echo
    Dummy=TriggerSerial.read_until(">")

    HexString="00"
    HexString=HexString.zfill(nNibbles)
    TriggerSerial.write("gpio iodir "+HexString+"\r")
    Echo=TriggerSerial.read_until("\n")
#    print "Echo", Echo
    Dummy=TriggerSerial.read_until(">")
    TriggerSerial.write("gpio set "+HexString+"\r")
    Echo=TriggerSerial.read_until("\n")
#    print "Echo", Echo
    Dummy=TriggerSerial.read_until(">")
    TriggerSerial.reset_input_buffer()
    return TriggerSerial


def SetTriggerNumato(Value):
    global TriggerSerial
    global nNibbles
    if (TriggerSerial is None):
        return 0
        
    HexString=hex(Value)
    HexString=HexString[2:]
    HexString=HexString.zfill(nNibbles)
#    print "HexString", HexString
    TriggerSerial.write("gpio writeall "+HexString+"\r")
    Echo=TriggerSerial.read_until("\n")
#    print Echo
    Dummy=TriggerSerial.read_until(">")

#def SendTriggerPulse(Value):
#    global StandardTriggerDuration
#    SetTriggerNumato(Value)
#    time.sleep(StandardTriggerDuration)
#    SetTriggerNumato(0)
    
#def SendLongTriggerPulse(Value, Secs):
#    SetTriggerNumato(Value)
#    time.sleep(Secs)
#    SetTriggerNumato(0)
    
def SendAsyncTrigger(Value):
    global StandardTriggerDuration
    SetTriggerNumato(Value)
    Timer(StandardTriggerDuration, InterruptHandlerEndTrigger, ()).start()

def InterruptHandlerEndTrigger():
    SetTriggerNumato(0)


def CloseTriggerNumato():
    global TriggerSerial
    if (TriggerSerial is not None):
        TriggerSerial.close()

    
InitTriggerNumato()    








###Altes Triggersystem
#SerialPortList=[comport.device for comport in serial.tools.list_ports.comports()]
#SerialPortList=[x.encode('UTF8') for x in SerialPortList]
#SerialPortList = [x for x in SerialPortList if not 'Bluetooth' in x]
#print SerialPortList
#
#print serial.tools.list_ports
#SerialFound=True
#try:
#    mySerialPort=SerialPortList[0]
#    TriggerOutput = serial.Serial(mySerialPort, timeout=None)
#except:
#    SerialFound=False
#    print "No serial port found."

#########################################################################################################################
#########################################################################################################################
## Noch ein paar Vorbereitungen
#########################################################################################################################
#########################################################################################################################
psychopy.event.Mouse(visible=False)
home = expanduser("~")
logging.console.setLevel(logging.WARNING)
CurrentLog = logging.LogFile(home+"/Desktop/Data/"+LogFileName, level=logging.INFO, filemode='w',)
CentralLog = logging.LogFile(CentralLogFilename, level=logging.WARNING, filemode='a')

psychopy.event.clearEvents(eventType=None)
repetitionCnt=0
TheKeys=[]
StimCnt=0

Selector = numpy.arange(nP300Stim)

deg2Pix = psychopy.tools.monitorunittools.deg2pix(1, MyMonitor)
print ("Pixels per degree:", deg2Pix)
ParameterText="MESSAGETYPE:blockparam;MONITOR:"+TheMonitor_CleanedStr+";STIMULUSCOMPUTERTIME:"+str(psychopy.core.getAbsTime())+";LOWERLIMIT:"+str(LowerLimit)+";UPPERLIMIT:"+str(UpperLimit)+";VALUNITS:logMAR;ASSUMEDLOGMAR:"+str(AssumedLogMAR)+";Screendistance(cm):"+str(Dist)+ ";"
logging.log(level=logging.DATA, msg=ParameterText)
RequestedLogArcmin=-numpy.log10(StartAcuity)
DisplayedLogArcmin=0.0
P300StimCnt=0
#########################################################################################################################
#########################################################################################################################
## Die Schleife
#########################################################################################################################
#########################################################################################################################
psychopy.event.clearEvents()

trialClock=psychopy.core.CountdownTimer(start=1.0)

ThisOffFrames=OffFramesMin
trialCnt=0
while trialCnt<nTrials:
    if P300StimCnt==0:
        numpy.random.shuffle(Selector)
    SelectedStim=Selector[P300StimCnt]
    P300StimCnt+=1
    if P300StimCnt>=nP300Stim:
        P300StimCnt=0
    OneSizeIndex=P300SizeIndex[SelectedStim]
    IsRare=P300Rare[SelectedStim]
    RequestedLogArcminPreliminary=FoundThresholdLog+ConstantOffsets[OneSizeIndex]
    RequestedLogArcmin=numpy.clip(RequestedLogArcminPreliminary, LowerLimit, UpperLimit)
    if (RequestedLogArcminPreliminary!=RequestedLogArcmin):
        print "Clipped:", RequestedLogArcminPreliminary, "-->", RequestedLogArcmin
    OptotypeDeg=10.0**(RequestedLogArcmin)/60
    TargetPixX=int(round(float(WidthPixels)*OptotypeDeg/thick))
    TargetPixY=int(round(float(HeightPixels)*OptotypeDeg/thick))
    if (IsRare==0):
        pic = tmp_ClosedRing.image
        OriSelector=10
        OptotypeOri=0
    else:
        pic = tmp_Landolt.image       
        OriSelector=GetOri() #numpy.random.randint(nOri)
        OptotypeOri=StimOri[OriSelector]
    if TestIfGoodSubject:
        TargetPixX=xSizePix
        TargetPixY=ySizePix
        OptotypeOri=0
    pic=pic.resize((TargetPixX, TargetPixY), Image.ANTIALIAS)
    screenshot = psychopy.visual.ImageStim(win, pic, ori=OptotypeOri)
    DisplayedLogArcmin=numpy.log10(float(TargetPixX)/float(xSizePix)*60)
    screenshot.draw()
    Value=(OneSizeIndex+((OriSelector+5)*6)) # Trigger fuer P300-Sequenz sind alle >=100ms, und wenn seltener Reiz, dann >=200ms
#    print Value
    ParameterText="MESSAGETYPE:trialparam;+REQUESTEDLOGARCMIN:"+str(RequestedLogArcmin)+";REQUESTEDLOGARCMINPRELIMINARY:"+str(RequestedLogArcminPreliminary)+";DISPLAYEDLOGARCMIN:"+str(DisplayedLogArcmin)+";TRIGGERDURATION:"+str(Value)+";PRECEEDINGOFFFRAMES:"+str(ThisOffFrames)+";ISRARE:"+str(IsRare)+";"
    logging.log(level=logging.DATA, msg=ParameterText)
    
    while (trialClock.getTime()>0):
        pass
    TheKey=psychopy.event.getKeys(keyList=['escape', 'num_07', 'num_1', 'num_2', 'num_3', 'num_4', 'num_5', 'num_6', 'num_7', 'num_8', 'num_9'], modifiers=False, timeStamped=False)
    if len(TheKey)>0:
        OneKey=TheKey[0]
#        print "OneKey", OneKey
        if OneKey=='escape':
            trialCnt=nTrials
        elif OneKey=='num_0':
            SendAsyncTrigger(200)
        elif OneKey=='num_1':
            SendAsyncTrigger(201)
        elif OneKey=='num_2':
            SendAsyncTrigger(202)
        elif OneKey=='num_3':
            SendAsyncTrigger(203)
        elif OneKey=='num_4':
            SendAsyncTrigger(204)
        elif OneKey=='num_5':
            SendAsyncTrigger(205)
        elif OneKey=='num_6':
            SendAsyncTrigger(206)
        elif OneKey=='num_7':
            SendAsyncTrigger(207)
        elif OneKey=='num_8':
            SendAsyncTrigger(208)
        elif OneKey=='num_9':
            SendAsyncTrigger(209)
        psychopy.clock.wait(0.1)


    psychopy.event.clearEvents(eventType='keyboard')
    win.callOnFlip(SendAsyncTrigger, Value)
    win.flip() ######### Stimulus is displayed
    
    trialClock.reset(t=OnFrames/FrameRate-(1/FrameRate/2))
    trialCnt += 1
#    while (trialClock.getTime()>0):
#        pass
    psychopy.clock.wait(0.01)

    ThisOffFrames=OffFramesMin+random.randint(0, OffFramesJitter)
    while (trialClock.getTime()>0):
        pass
    win.flip() ######### ISI starts
    trialClock.reset(t=ThisOffFrames/FrameRate-(1/FrameRate/2))




#########################################################################################################################
#########################################################################################################################
## Aufraeumen
#########################################################################################################################
#########################################################################################################################

CloseTriggerNumato()
psychopy.event.Mouse(visible=True)
logging.flush()
win.close()

