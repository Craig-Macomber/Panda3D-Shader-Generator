"""
some usage assistance stuff resides here.
"""
from panda3d.core import ShaderAttrib
import shaderBuilder

def getManager(libPaths,scriptPath,nodeTypeClassMap={},renderStateFactory=None,viewDebugScriptGraph=False,debugPath=None):
    """ a utility function to avoid having to make the library and builders for simple cases """
    lib=shaderBuilder.Library(libPaths,nodeTypeClassMap)
    builder=lib.loadScript(scriptPath,viewGraph=viewDebugScriptGraph)
    return Manager(builder,renderStateFactory,debugPath=debugPath)

# a helper
def _getShaderAtrib(renderState):
    shaderAtrib=renderState.getAttrib(ShaderAttrib.getClassSlot())
    if not shaderAtrib:
        shaderAtrib = ShaderAttrib.make()
    return shaderAtrib



class Manager(object):
    def __init__(self,builder,renderStateFactory=None,debugPath=None,flags=()):
        self.builder=builder
        self.renderStateFactory=builder.setupRenderStateFactory(renderStateFactory)
        self.debugPath=debugPath
        self.flags=set(flags)
    def makeShader(self,pandaNode,pandaRenderState=None,geomVertexFormat=None,debugCodePrefix=None,debugGraphPrefix=None,extraFlags=()):
        genRenderState=self.renderStateFactory.getRenderState(pandaNode,pandaRenderState,geomVertexFormat,self.flags|set(extraFlags))
        debugPath=None
        debugGraphPath=None
        if self.debugPath is not None:
            if debugCodePrefix is not None: debugPath=self.debugPath+debugCodePrefix
            if debugGraphPrefix is not None: debugGraphPath=self.debugPath+debugGraphPrefix
        return self.builder.getShader(genRenderState,debugPath,debugGraphPath=debugGraphPath)
    
    def genShaders(self,node,debugCodePrefix=None,debugGraphPrefix=None):
        """ walk all geoms and generate shaders for them """
        nn=node.node()
        if nn.isGeomNode():
            for i,renderState in enumerate(nn.getGeomStates()):
                geomVertexFormat=nn.getGeom(i).getVertexData().getFormat()
    
                # TODO : the order of composing might be wrong!
                netRs=renderState.compose(node.getNetState())
    
                shader=self.makeShader(node,netRs,geomVertexFormat,debugCodePrefix=debugCodePrefix,debugGraphPrefix=debugGraphPrefix)
                shaderAtrib=_getShaderAtrib(renderState)
                shaderAtrib=shaderAtrib.setShader(shader)
                renderState=renderState.setAttrib(shaderAtrib)
                nn.setGeomState(i,renderState)
        
        for n in node.getChildren():
            self.genShaders(n,debugCodePrefix,debugGraphPrefix)