"""
some usage assistance stuff resides here.
"""
from panda3d.core import ShaderAttrib
import shaderBuilder

def getManager(libPaths,scriptPath,nodeTypeClassMap={},renderStateFactory=None):
    """ a utility function to avoid having to make the library and builders for simple cases """
    lib=shaderBuilder.Library(libPaths,nodeTypeClassMap)
    builder=lib.loadScript(scriptPath)
    return Manager(builder,renderStateFactory)

# a helper
def _getShaderAtrib(renderState):
    shaderAtrib=renderState.getAttrib(ShaderAttrib.getClassSlot())
    if not shaderAtrib:
        shaderAtrib = ShaderAttrib.make()
    return shaderAtrib



class Manager(object):
    def __init__(self,builder,renderStateFactory=None):
        self.builder=builder
        self.renderStateFactory=builder.setupRenderStateFactory(renderStateFactory)
    
    def makeShader(self,pandaNode,pandaRenderState=None,geomVertexFormat=None,debugPath=None):
        genRenderState=self.renderStateFactory.getRenderState(pandaNode,pandaRenderState,geomVertexFormat)
        return self.builder.getShader(genRenderState,debugPath)
    
    def genShaders(self,node,debugPath=None):
        """ walk all geoms and generate shaders for them """
        nn=node.node()
        if nn.isGeomNode():
            for i,renderState in enumerate(nn.getGeomStates()):
                geomVertexFormat=nn.getGeom(i).getVertexData().getFormat()
    
                # TODO : the order of composing might be wrong!
                netRs=renderState.compose(node.getNetState())
    
                shader=self.makeShader(node,netRs,geomVertexFormat,debugPath=debugPath)
                shaderAtrib=_getShaderAtrib(renderState)
                shaderAtrib=shaderAtrib.setShader(shader)
                renderState=renderState.setAttrib(shaderAtrib)
                nn.setGeomState(i,renderState)
        
        for n in node.getChildren():
            self.genShaders(n,debugPath)