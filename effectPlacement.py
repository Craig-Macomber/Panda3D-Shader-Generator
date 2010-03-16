from filter import *

class Placement:
    def __init__(self,baseNode,shaderEffect,filter=includeAll,subEffects=None):
        """
        filter is an optional Filter to specify which nodes this placement should apply to
        subEffects is optional list of Placements to go inside this one. Repersents effects
        that may be placed on nodes which this effect is also placed on,
        and are applied to the shader after this one.
        
        """
        
        
        self.baseNode=baseNode
        self.shaderEffect=shaderEffect
        self.filter=filter
        
        self.subEffects=subEffects if subEffects else []
        
        
    def appliesTo(self,node):
        """
        Checks to see of effect should be placed on node
        """
        return self.filter(node)


# appliesTo could return something special to signal not to bother checking child nodes. This would speed things up.

'''
class Funct:
    def __init__(self,funct,ops,keepList=False):
        self.funct=funct
        self.ops=ops
        self.keepList=keepList
    def appliesTo(self,node):
        l=[op.appliesTo(node) for op in self.ops]
        return self.funct(l) if self.keepList else self.funct(*l)


class And(Funct):
    def __init__(self,a,b):
        Funct.__init__(self, all, (a,b), True)

class Or(Funct):
    def __init__(self,a,b):
        Funct.__init__(self, any, (a,b), True)

class Not(Funct):
    def __init__(self,a):
        Funct.__init__(self,lambda a : not a,(a))
'''

class ExcludeNodes(Filter):
    """ Excludes listed nodes, and all below them"""
    def __init__(self,excludeNodes):
        self.excludeNodes=excludeNodes
    def __call__(self,node):
        for n in self.excludeNodes:
            if n.isAncestorOf(node): return False
        return True

class RequireShaderInputs(Filter):
    def __init__(self,requiredShaderInputs):
        self.requiredShaderInputs=requiredShaderInputs
    def __call__(self,node):
        for i in self.requiredShaderInputs:
            n=node
            while True:
                s=n.getShaderInput(i)
                if s and str(s.getName())==i:
                    break
                if not n.hasParent(): return False
                n=n.getParent()
        return True

from panda3d.core import GeomNode

class RequireVertexProperties(Filter):
    def __init__(self,requiredPeoperties):
        self.requiredPeoperties=requiredPeoperties
    def __call__(self,node):
        
        # Would use NodePath.findAllVertexColumns (string name)
        # but that also searchs child nodes
        # And does not require all geoms to have it.
        
        n=node.node()
        if not n.isOfType(GeomNode.getClassType()): return False
        for p in self.requiredPeoperties:
            for g in n.getGeoms():
                found=False
                for a in g.getVertexData().getArrays():
                    if a.hasColumn(p):
                        found=True
                        break
                if not found: return False
        return True

class RequireTextures(Filter):
    def __init__(self,textureNames):
        self.textureNames=textureNames
    def __call__(self,node):
        # What a mess! findTextureStage() seaches child nodes,
        # so we need to detach them all!
        if node.hasParent():
            if self.appliesTo(node.getParent()): return True
            
        children=[]
        
        for i in xrange(node.getNumChildren()):
            children.append(node.getChild(0))
            children[-1].detachNode()
        
        applies=True
        
        for t in self.textureNames:
            if not node.findTextureStage(t):
                applies=False
                break
        
        for n in children:
            n.reparentTo(node)
        
        return applies
        
        
        
class BlendMode(Filter):
    def __init__(self,blendMode):
        self.blendMode=blendMode
    def __call__(self,node):
        #Not done yet!
        print "Error, feature todo!"