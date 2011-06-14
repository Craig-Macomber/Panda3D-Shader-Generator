from panda3d.core import NodePath,PandaNode, CullFaceAttrib, TextNode, Texture
from panda3d.core import DirectionalLight, VBase4, AmbientLight, Point3, Texture, Camera, Vec4,Vec3
from panda3d.core import FrameBufferProperties, RenderModeAttrib
from panda3d.core import MouseAndKeyboard 
from panda3d.core import MouseWatcher 
from panda3d.core import ModifierButtons 
from panda3d.core import KeyboardButton 
from panda3d.core import ButtonThrower 
from panda3d.core import CardMaker,PGTop, GraphicsOutput, WindowProperties, CardMaker

from direct.directtools.DirectGeometry import LineNodePath


from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from direct.gui.DirectButton import DirectButton,DirectFrame
from direct.gui import DirectGuiGlobals as DGG

class Window(DirectObject):
    """Represents a window on screen"""
    def __init__(self):
        DirectObject.__init__(self)
        #base=pandabase.getBase()
        #self.win=base.addWindow(self)
        
        props=WindowProperties(WindowProperties.getDefault())
        props.setUndecorated(False)
        props.setOrigin(50,100)
        props.setSize(500,450)
        props.setTitle("Shader Editor")
        
        self.win=base.openWindow(props=props)
        # Give the window a chance to truly open.
        base.graphicsEngine.openWindows()
        
        
        camera2d=base.makeCamera2d(self.win)
        self.render2d=NodePath("render2d")
        camera2d.node().setScene(self.render2d)

        # aparently the DisplayRegion we want is the second (of several), so index 1
        self.mainDisplayRegion=self.win.getDisplayRegion(1)
        
        self.scene=NodePath("scene")
        self.mainDisplayRegion.getCamera().reparentTo(self.scene)
        
        self.render2d.setDepthTest(0)
        self.render2d.setDepthWrite(0)
        self.render2d.setMaterialOff(1)
        self.render2d.setTwoSided(1)
        
        self.render2dPG = self.render2d.attachNewNode(PGTop("render2dPG")) 
        self.pixel2d = self.render2dPG.attachNewNode(PandaNode("aspect2d")) 
        self.pixel2d.setPos(-1,0,1)
        
        name="x"
        self.buttonThrowers = [] 
        for i in range(self.win.getNumInputDevices()): 
            name = self.win.getInputDeviceName(i) 
            mk = base.dataRoot.attachNewNode(MouseAndKeyboard(self.win, i, name)) 
            mw = mk.attachNewNode(MouseWatcher(name)) 
            bt = mw.attachNewNode(ButtonThrower(name)) 
            if (i != 0): 
                bt.node().setPrefix('mousedev'+str(i)+'-') 
            mods = ModifierButtons() 
            bt.node().setModifierButtons(mods) 
            self.buttonThrowers.append(bt) 
    
                
        self.mouseWatcher = self.buttonThrowers[0].getParent() 
        self.mouseWatcherNode = self.mouseWatcher.node() 
                


        
        self.render2dPG.node().setMouseWatcher(self.mouseWatcherNode) 
        

        self.toolBarNode=self.pixel2d.attachNewNode("ToolBar")
        self.panelNode=self.pixel2d.attachNewNode("Panels")


        self.accept('window-event', self._winResized)
        
        
        self._winResized()
        
        
    def _winResized(self,*args):
        aspectRatio = float(self.win.getXSize()) / float(self.win.getYSize())
        # Fix up some anything that depends on the aspectRatio
        self.mainDisplayRegion.getCamera().node().getLens().setAspectRatio(aspectRatio)
        self.pixel2d.setScale(2.0 / self.win.getXSize(), 1.0, 2.0 / self.win.getYSize())
        self.panelNode.setPos(self.win.getXSize(),0,0)



buttonHeight=20.0
buttonWidth=150.0
nodeWidth=250.0

def frameProps(text,width,height=buttonHeight,borderWidth=2,textAlign=TextNode.ALeft):
    """Get a dict for keyword params for DirectFrame classes"""
    textx=borderWidth+2#width/2
    return {
        'frameSize':(0,width,0,height),
        'text_pos':(textx,height-buttonHeight+buttonHeight/2.9),
        'text_scale':(buttonHeight/1.5,buttonHeight/1.5),
        'borderWidth':(borderWidth,borderWidth),
        'text':text,
        'text_align':textAlign,
    }

dataPrefix="editor_"
def getData(node,name,default=None):
    return node.getDataDict().get(dataPrefix+name,default)
def setData(node,name,data):
    node.getDataDict()[dataPrefix+name]=str(data)


class NodeDisplay(object):
    def __init__(self,n,editor):
        self.n=n
        self.editor=editor
        nodeType=n.getType()
        
        self.rowCount=max(len(nodeType.inLinks),len(nodeType.outLinks))
        h=1+self.rowCount
        
        self.frame=DirectButton(**frameProps(n.getType().getName(),nodeWidth,height=h*buttonHeight))
        self.frame.bind(DGG.B1PRESS,self.startDrag)
        self.frame.reparentTo(editor.graphNode)
        self.frame.setPythonTag("nodeDisplay",self)
        
        yindex=2
        for i in nodeType.inLinks:
            t=DirectButton(**frameProps(i.type+" "+i.name,nodeWidth/2,height=buttonHeight))
            t.setPos(0,0,buttonHeight*(h-yindex))
            t.reparentTo(self.frame)
            yindex+=1
        
        yindex=2
        for i in nodeType.outLinks:
            t=DirectButton(**frameProps(i.type+" "+i.name,nodeWidth/2,height=buttonHeight))
            t.setPos(nodeWidth/2,0,buttonHeight*(h-yindex))
            t.reparentTo(self.frame)
            yindex+=1
        
        
    def update(self):
        x=int(getData(self.n,"x",100))
        y=int(getData(self.n,"y",-100))
        self.frame.setPos(x,0,y)
    def drag(self,deltaX,deltaY):
        x=int(getData(self.n,"x",100))
        y=int(getData(self.n,"y",-100))
        setData(self.n,"x",x+deltaX)
        setData(self.n,"y",y-deltaY)
        self.update()
        
    def startDrag(self,event=None):
        self.editor._setMouseState(1,True)
        self.editor.beginDrag()
        self.editor.dragSet=set([self])
        return True
        
class Editor(Window):
    def __init__(self,library,graphPath):
        Window.__init__(self)
        self.lib=library
        self.graphNode=self.pixel2d.attachNewNode("graphNode")
        self.loadPath(graphPath)
        self.dragSet=set()
        self.dragging=False
        self.hadFocus=False
        self.lastMouseX=self.lastMouseY=0
        self.mouseDown=False
        
        save=DirectButton(command=self.save,**frameProps("Save",50))
        save.reparentTo(self.toolBarNode)
        save.setPos(0,0,-buttonHeight)
        
        
        self.accept("mouse1",self._setMouseState,[1,True])
        self.accept("mouse1-up",self._setMouseState,[1,False])
        base.taskMgr.add(self.update,"update")
        
        self.lines=None
        self.updateLines=True
        
        self.updateLinkToSourceDisplay()
        
        
        
    def updateLinkToSourceDisplay(self):
        d={}
        for c in self.getDisplays():
            for n in c.n.getOutLinks():
                d[n]=c
        self.linkToSourceDisplay=d
        
        
    def getDisplays(self):
        for c in self.graphNode.getChildren():
            t=c.getPythonTag("nodeDisplay")
            if t is not None:
                yield t
    
    def _setMouseState(self,button,state):
        self.mouseDown=state
        event="mouseDown" if state else "mouseUp"
        #self.handleEvent(event,self.lastMouseX,self.lastMouseY)
        
    def update(self,task=None):
        if self.win.getProperties().getForeground():
            data=self.win.getPointer(0)
            x=data.getX()
            y=data.getY()
            if not self.hadFocus:
                #gotFocus
                self.hadFocus=True
            else:
                if self.lastMouseX!=x or self.lastMouseY!=y:
                    if self.mouseDown:
                        if not self.dragging:
                            self.dragSet=set([self.graphNode])
                            self.beginDrag()
                        self.mouseDrag(self.lastMouseX,self.lastMouseY,x,y)
                    else:
                        self.dragging=False
                        if data.getInWindow():
                            pass #mouseMove",self.lastMouseX,self.lastMouseY,x,y
            self.lastMouseX=x
            self.lastMouseY=y
        else:
            if self.hadFocus:
                pass #lostFocus
            self.hadFocus=False
        
        if self.updateLines: self.redrawLines()
        
        return Task.cont
        
    def mouseDrag(self,lastMouseX,lastMouseY,x,y):
        deltaX=x-lastMouseX
        deltaY=y-lastMouseY
        if self.dragging:
            for d in self.dragSet:
                if d is self.graphNode:
                    d.setPos(d,deltaX,0,-deltaY)
                else:
                    d.drag(deltaX,deltaY)
                    self.updateLines=True
    
    def beginDrag(self):
        self.dragging=True
        
    def loadPath(self,graphPath):
        self.path=graphPath
        self.nodes=self.lib.parseGraph(self.path)
        self.redrawGraph()
    
    def redrawGraph(self):
        for c in self.graphNode.getChildren():
            c.destroy()
        
        for n in self.nodes:
            display=NodeDisplay(n,self)

        self.updateLinkToSourceDisplay()
        
        self.updateNodePaths()
        self.updateLines=True
        
    def updateNodePaths(self):
        for c in self.graphNode.getChildren():
            self.updateNodePath(c)
        
    def redrawLines(self):
        
        if self.lines: self.lines.remove()
        
        self.lines=self.graphNode.attachNewNode("lines")
        lines=LineNodePath(parent=self.lines,thickness=2)
        lines.setColor(1,0,0,1)
        
        sourceOffset=Vec3(nodeWidth,0,-buttonHeight/2)
        dstOffset=Vec3(0,0,-buttonHeight/2)
        
        for dst in self.getDisplays():
            dstRow=-1
            for link in dst.n.getInLinks():
                dstRow+=1
                source=self.linkToSourceDisplay.get(link)
                if source:
                    sourceRow=0
                    
                    for oLink in source.n.outLinks:
                        if oLink is link:
                            break
                        sourceRow+=1
                    
                    srcVec=source.frame.getPos()+sourceOffset
                    srcVec.setZ(srcVec.getZ()+(source.rowCount-sourceRow)*buttonHeight)
                    
                    dstVec=dst.frame.getPos()+dstOffset
                    dstVec.setZ(dstVec.getZ()+(dst.rowCount-dstRow)*buttonHeight)
                    
                    lines.drawArrow2d(srcVec,dstVec,20,20)
                    
        lines.create()
        self.updateLines=False
        
    def updateNodePath(self,np):
        n=np.getPythonTag("nodeDisplay")
        n.update()
        
    def previewBuilder(self):
        return self.lib.makeBuilder(self.nodes)
        
    def save(self,newPath=None):
        path=self.path if newPath is None else newPath
        self.lib.saveGraph(self.nodes,path)
        