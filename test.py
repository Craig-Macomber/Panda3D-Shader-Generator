from panda3d.core import loadPrcFileData
loadPrcFileData("","show-frame-rate-meter #t")
loadPrcFileData("","sync-video #f")

from panda3d.core import *
from direct.task import Task
from direct.actor import Actor
from direct.interval.IntervalGlobal import *
import math
import direct.directbase.DirectStart
print PandaSystem.getVersionString()

from shaderBuilder import Library,ShaderBuilder



lib=Library(["library"])
builder=lib.loadScript("graph/lit.gen")
renderStateFactory=builder.setupRenderStateFactory()


def makeShader(pandaNode,pandaRenderState=None,geomVertexFormat=None,debugName=None):
    genRenderState=renderStateFactory.getRenderState(pandaNode,pandaRenderState,geomVertexFormat)
    debugPath="ShadersOut/"+debugName if debugName else None
    return builder.getShader(genRenderState,debugPath)


"""
Shader Generator Demo

"""





# Setup an interesting scene graph to run effects on:
base.disableMouse()

#Load the first environment model
environ = loader.loadModel("models/environment")
environ.reparentTo(render)
environ.setScale(0.25,0.25,0.25)
environ.setPos(-8,42,0)

#Task to move the camera
def SpinCameraTask(task):
    angledegrees = task.time * 6.0
    angleradians = angledegrees * (math.pi / 180.0)
    base.camera.setPos(20*math.sin(angleradians),-20.0*math.cos(angleradians),3)
    base.camera.setHpr(angledegrees, 0, 0)
    return Task.cont

taskMgr.add(SpinCameraTask, "SpinCameraTask")

#Load the panda actor, and loop its animation
pandaActor = Actor.Actor("models/panda-model",{"walk":"models/panda-walk4"})
pandaActor.setScale(0.005,0.005,0.005)
pandaActor.reparentTo(render)
pandaActor.loop("walk")

#Create the four lerp intervals needed to walk back and forth
pandaPosInterval1= pandaActor.posInterval(13,Point3(0,-10,0), startPos=Point3(0,10,0))
pandaPosInterval2= pandaActor.posInterval(13,Point3(0,10,0), startPos=Point3(0,-10,0))
pandaHprInterval1= pandaActor.hprInterval(3,Point3(180,0,0), startHpr=Point3(0,0,0))
pandaHprInterval2= pandaActor.hprInterval(3,Point3(0,0,0), startHpr=Point3(180,0,0))

#Create and play the sequence that coordinates the intervals
pandaPace = Sequence(pandaPosInterval1, pandaHprInterval1,
  pandaPosInterval2, pandaHprInterval2, name = "pandaPace")
pandaPace.loop()



#Set up some lights

# A crazy bright spinning red light seems pretty cool
dlight = DirectionalLight('dlight')
dlight.setColor(Vec4(4.9, 0.9, 0.8, 1))
dlight.setSpecularColor(Vec4(0.9, 0.9, 0.8, 10))
dlnp = render.attachNewNode(dlight)
dlnp.setHpr(0, 0, 0)
#render.setLight(dlnp)
render.setShaderInput('dlight',dlnp)

dayCycle=dlnp.hprInterval(10.0,Point3(0,360,0))
dayCycle.loop()

# and an ambient light
alight = AmbientLight('alight')
alight.setColor(Vec4(0.2, 0.2, 0.2, 1))
alnp = render.attachNewNode(alight)
render.setLight(alnp)
#render.setShaderInput('alight',alnp)


#render.setTransparency(TransparencyAttrib.MNone,100)

# a helper
def _getShaderAtrib(renderState):
    shaderAtrib=renderState.getAttrib(ShaderAttrib.getClassSlot())
    if not shaderAtrib:
        shaderAtrib = ShaderAttrib.make()
    return shaderAtrib

# walk all geoms and generate shaders for them
def genShaders(node,debugName=None):
    nn=node.node()
    if nn.isGeomNode():
        for i,renderState in enumerate(nn.getGeomStates()):
            geomVertexFormat=nn.getGeom(i).getVertexData().getFormat()

            # TODO : the order of composing might be wrong!
            netRs=renderState.compose(node.getNetState())

            shader=makeShader(node,netRs,geomVertexFormat,debugName=debugName)
            shaderAtrib=_getShaderAtrib(renderState)
            shaderAtrib=shaderAtrib.setShader(shader)
            renderState=renderState.setAttrib(shaderAtrib)
            nn.setGeomState(i,renderState)
            
    
    for n in node.getChildren():
        genShaders(n,debugName)
genShaders(render,"generatedShaders")


run()
