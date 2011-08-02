from panda3d.core import ShaderAttrib


# Since the NodeType subclasses need some convention on what will be used for the renderState
# objects, we will go ahead and define our renderState class here
# if using addational custom NodeType sublcasses, you many want to subclass RenderState.
# to optimize caching, this RenderState class only stores the minimum state data that is needed.
# The set of what to store is collected by the RenderStateFactory

class RenderStateFactory(object):
    def __init__(self):
        self.tags=set() # add tags we care about here, by name
        self.shaderInputs=set() # add shaderInput names we care about here, by name
    def getRenderState(self,pandaNode,pandaRenderState=None):
        """
        returns a RenderState instance for a given pandaNode, and optionally a specified panda3d.RenderState
        
        since this is usally used on geoms, but tags and such are set on pandaNodes or NodePaths
        (pandaNode may be either), the pandaRenderState is will default to pandaNode.getNetState(),
        but can be passed seperatly as in the cause when using geoms. In that case, pandaNode should
        be the panda3d.GeomNode
        
        """
        if pandaRenderState is None: pandaRenderState=pandaNode.getNetState()
        
        return self._getRenderState(self._getTagDict(pandaNode),pandaRenderState)
    
    def _getTagDict(self,pandaNode):
        tags={}
        for t in self.tags:
            if pandaNode.hasNetTag(): tags[t]=pandaNode.getNetTag(t)
        return tags
    
    def _getRenderState(self,tagDict,pandaRenderState):
        shaderAtrib=pandaRenderState.getAttrib(ShaderAttrib.getClassSlot())
        if shaderAtrib:
            # basically we want the intersection of self.shaderInputs, and the shader inputs in shaderAtrib
            # but to do this, we need this rather contrived approach,
            # since there is no way to get the set of shader inputs in a shaderAtrib,
            # or ask if it contains one
            shaderInputs=frozenset(s for s in self.shaderInputs if shaderAtrib.getShaderInput(s).getName() is not None)
        else:
            shaderInputs=frozenset()

        return RenderState(pandaRenderState,tagDict,shaderInputs)
    
class RenderState(object):
    """
    
    Panda3D has a RenderState class, but we don't use it directly for a few reasons:
    It stores stuff we want to ignore (which could be removed, but its simpler to just store what we want)
    It does not store everything we may want (allowing tags to trigger shader generator stuff is cool)
    
    Flyweight is not used here because it can be confusing when the class gets subclassed,
    and isn't needed anyway. Regardless, a fast comparison, and good hash are needed for the cache.
    When subclassing to add more fields, be sure to __eq__ the comparison and __hash__ methods.
    
    """
    def __init__(self,pandaRenderState,tagDict,shaderInputSet):
        self.shaderInputs=shaderInputSet
        self.tags=tagDict
        # TODO : better hash
        self._hash = hash(shaderInputSet) ^ len(tagDict)
    
    def hasShaderInput(self,name):
        return name in self.shaderInputs
    
    def hasTag(self,name):
        return name in self.tags
    
    def getTag(self,name,default=None):
        return self.tag.get(name,default)
    
    def __hash__(self):
        return self._hash
    
    def __eq__(self,other):
        return self.shaderInputs==other.shaderInputs and self.tags==other.tags
    
    def __repr__(self): return "RenderState"+str((self.shaderInputs,self.tags))
        
