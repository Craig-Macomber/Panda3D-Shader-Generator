from pandac.PandaModules import *

from shadereffects.txteffects import loadEffectFromFile
from shadereffects import effectPlacement
from shadereffects.effectPlacement import applyShaderEffectPlacements

from direct.task import Task
from direct.actor import Actor
from direct.interval.IntervalGlobal import *
import math
import direct.directbase.DirectStart

from  shadereffects import pyEffects

print PandaSystem.getVersionString()



dlight = DirectionalLight('dlight')
dlight.setColor(Vec4(4.9, 0.9, 0.8, 1))
dlight.setSpecularColor(Vec4(0.9, 0.9, 0.8, 10))
dlnp = render.attachNewNode(dlight)
dlnp.setHpr(0, 0, 0)
render.setLight(dlnp)
render.setShaderInput('dlight',dlnp)


alight = AmbientLight('alight')

alight.setColor(Vec4(0.2, 0.2, 0.2, 1))
alnp = render.attachNewNode(alight)
render.setLight(alnp)
render.setShaderInput('alight',alnp)

dayCycle=dlnp.hprInterval(1.0,Point3(0,360,0))
dayCycle.loop()






pyEffects=pyEffects.loadAll("Effects")


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


# Setup some interesting shader inputs

environ.setShaderInput('tintColor',Vec4(.2,.3,.5,1))
#pandaActor.setShaderInput('tintColor',Vec4(0,0,.2,1))

#pandaActor.setShaderInput('ambient',Vec4(1,.5,.2,1))
render.setShaderInput('exposure',2)
render.setShaderInput('transparancyThreshold',.5)

# disable trasnparency so alpha to bloom filter is not crazy
render.setTransparency(TransparencyAttrib.MNone,100)



# Do some effects!

# Convenience method for loading effects files
def getEffect(name):
    return loadEffectFromFile('Effects',name)


basicProject=effectPlacement.Placement(getEffect('basicProject'))


tintFilter=effectPlacement.ExcludeNodes([environ.getChild(0).getChild(0),environ.find('**/OuterBamboo')]) & effectPlacement.RequireShaderInputs(['tintColor'])
tint=effectPlacement.Placement(getEffect('tint'),tintFilter)

normalFilter=effectPlacement.RequireVertexProperties(['normal'])

#light=effectPlacement.Placement(getEffect('light'),normalFilter)
light=effectPlacement.Placement(getEffect('light'))


ambientFilter=effectPlacement.RequireShaderInputs(['alight'])
ambient=effectPlacement.Placement(getEffect('ambientLight'),ambientFilter)

vNorms=effectPlacement.Placement(getEffect('vertexNormals'),normalFilter)
dLightFilter=effectPlacement.RequireShaderInputs(['dlight'])&normalFilter
dLight=effectPlacement.Placement(getEffect('directionalLight2'),dLightFilter)


light.subEffects.extend([ambient,dLight])
#expose=effectPlacement.Placement(getEffect('expose'),effectPlacement.RequireShaderInputs(['exposure']))
expose=pyEffects['expose']
overBrightToAlpha=effectPlacement.Placement(getEffect('overBrightToAlpha'))
transparancyThreshold=effectPlacement.Placement(getEffect('transparancyThreshold'),effectPlacement.RequireShaderInputs(['transparancyThreshold']))

basicTex=effectPlacement.Placement(getEffect('basicTex'))



color=pyEffects['color']#effectPlacement.Placement(getEffect('color'))
color.subEffects.extend([basicTex,transparancyThreshold,tint,light,expose,overBrightToAlpha])



effectPlacements=[basicProject,vNorms,color]


# auctually apply all the effects to the scene graph
applyShaderEffectPlacements(render,effectPlacements,None,False)


# a little filtering for bloom.
from direct.filter.CommonFilters import CommonFilters
# Filter to display the alpha channel as bloom.
filters = CommonFilters(base.win, base.cam)
#filterok = filters.setBloom(blend=(0,0,0,1), desat=0.5, intensity=2.5, size="large",mintrigger=0.6, maxtrigger=1.0)

run()