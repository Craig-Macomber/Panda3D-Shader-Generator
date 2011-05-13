from panda3d.core import NodePath,PandaNode, CullFaceAttrib, TextNode, Texture
from panda3d.core import DirectionalLight, VBase4, AmbientLight, Point3, Texture, Camera, Vec4
from panda3d.core import FrameBufferProperties, RenderModeAttrib
from panda3d.core import MouseAndKeyboard 
from panda3d.core import MouseWatcher 
from panda3d.core import ModifierButtons 
from panda3d.core import KeyboardButton 
from panda3d.core import ButtonThrower 
from panda3d.core import CardMaker,PGTop, GraphicsOutput, WindowProperties

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
        props.setSize(900,750)
        props.setTitle("Shader Editor")
        
        self.win=base.openWindow(props=props)
        # Give the window a chance to truly open.
        base.graphicsEngine.openWindows()
        
        
        camera2d=base.makeCamera2d(self.win)
        self.render2d=NodePath("render2d")
        camera2d.node().setScene(self.render2d)

        # aparently the DisplayRegion we want is the second (of several), so index 1
        self.mainDisplayRegion=self.win.getDisplayRegion(1)
        
        #print self.win.getDisplayRegions()
        
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

class Editor(Window):
    def __init__(self,library,graphPath):
        Window.__init__(self)
        self.lib=library
        self.graphNode=self.pixel2d.attachNewNode("graphNode")
        self.loadPath(graphPath)
        
    def loadPath(self,graphPath):
        self.path=graphPath
        self.nodes=self.lib.parseGraph(self.path)
        self.redrawGraph()
    
    def redrawGraph(self):
        for c in self.graphNode.getChildren():
            c.removeNode()
        
        for n in self.nodes:
            np=NodePath("graphNode")
            np.reparentTo(self.graphNode)
        
        
    def previewBuilder(self):
        return self.lib.makeBuilder(self.nodes)
        
    def save(self,newPath=None):
        path=self.path if newPath is None else newPath
        self.lib.saveGraph(self.nodes,path)
        