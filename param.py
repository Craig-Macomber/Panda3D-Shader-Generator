def linkEndFromDefCode(defCode):
    """
    
    returns a Param representing the entry on a link into a NodeType. This allows the Nodes to have their own internal names
    for their inputs and outputs that are seperate from the names of Links. The types should match though!
    
    """
    
    t=defCode.split()
    
    name=t[-1]
    type=" ".join(t[:-1])
    return Param(name,type)


def shaderParamFromDefCode(defCode):
    """
    
    example usage:
    shaderParam=shaderParamFromDefCode("uniform sampler2D k_grassData: TEXUNIT0")
    shaderParam=shaderParamFromDefCode("float4 o_color")
    
    """
    i=defCode.find(':')
    if i==-1:
        semantic=None
        t=defCode.split()
    else:
        semantic=defCode[i+1:].strip()
        t=defCode[:i].split()
    name=t[-1]
    type=" ".join(t[:-1])
    return ShaderParam(name,type,semantic)

class Param(object):
    def __init__(self,name,type):
        self.name=name
        self.type=type
    def getName(self): return self.name
    def getType(self): return self.type
    def __repr__(self): return self.__class__.__name__+"("+self.name+", "+self.type+")"
    def __hash__(self):
        return hash(self.name)^hash(self.type)
    def __eq__(self,other):
        return self.__class__==other.__class__ and self.name==other.name and self.type==other.type
        
class ShaderParam(Param):
    def __init__(self,name,type,semantic=None):
        Param.__init__(self,name,type)
        self.semantic=semantic
    def getSemantic(self): return self.semantic
    def getDefCode(self): return self.type+" "+self.name+((" : "+self.semantic) if self.semantic else "")
    def __eq__(self,other):
        return Param.__eq__(self,other) and self.semantic==other.semantic
    def getShortType(self): return self.type.split()[-1]
    
class ShaderInput(ShaderParam): pass
class ShaderOutput(ShaderParam): pass

