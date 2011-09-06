import itertools
import param

from panda3d.core import MaterialAttrib,ColorAttrib,TextureAttrib

"""

This module contains the basic NodeType implementation, including the classes it instances

"""

boolLinkType="MetaBool"

class Link(object):
    """
    
    An output from a shader Node, and possibly multiple inputs to multiple shader nodes.
    
    As it can be multiple inputs, links are sets of edges in the graph from one node to multiple others.
    
    """
    def __init__(self,dataType,name="Unnamed"):
        self.dataType=dataType
        self.name=name
    def getType(self): return self.dataType
    def getName(self): return self.name
    def __repr__(self):
        return "Link"+str(tuple([self.dataType,self.name]))
        

class ActiveNode(object):
    """
    
    ActiveNodes should never be modified, and should not be subclassed.
    
    They use the Flyweight pattern, and thus can be compared by pointer with "is"
    
    This is important as they are hashed by pointer,
    and need to compare properly and quicky for the caching to work.
    
    """
    cache = {}
    
    def __new__(cls, *v):
        o = cls.cache.get(v, None)
        if o:
            return o
        else:
            o = cls.cache[v] = object.__new__(cls)
            return o
    def __init__(self,shaderInputs,shaderOutputs,inLinks,outLinks,code,isOutPut):
        self.shaderInputs=shaderInputs
        self.shaderOutputs=shaderOutputs
        self.inLinks=inLinks
        self.outLinks=outLinks
        self.code=code
        self.outPut=isOutPut
    def getShaderInputs(self): return self.shaderInputs
    def getShaderOutputs(self): return self.shaderOutputs
    def getInLinks(self): return self.inLinks
    def getOutLinks(self): return self.outLinks
    def isOutPut(self): return self.outPut
    def getCode(self): return self.code
    def __repr__(self):
        return "ActiveNode"+str(tuple([self.shaderInputs,self.shaderOutputs,self.inLinks,self.outLinks,"<code>",self.outPut]))
 


def makeFullCode(code,shaderInputs,shaderOutputs,inLinks,outLinks):
    """
    
    the code needed to construct Nodes includes the (paramList){code} wrapping stuff, so this addes it
    and saves it to self.code
    
    """
    
    fparamChain=itertools.chain(
         ("in "+s.getType()+" "+s.getName() for s in shaderInputs),
         ("out "+s.getType()+" "+s.getName() for s in shaderOutputs),
         ("in "+s.getType()+" "+s.getName() for s in inLinks),
         ("out "+s.getType()+" "+s.getName() for s in outLinks),
         )

    return "("+",".join(fparamChain)+"){\n"+code+"\n}"
    
class Node(object):
    """
    base class for all nodes, if used directly, takes no inputs, has no
    outputs basically a noop
    
    this is all thats needed to work with ShaderBuilder
    """
    def __init__(self):
        pass
    def getActiveNode(self,renderState,linkStatus):
        return None
    def setupRenderStateFactory(self,renderStateFactory):
        pass


def assertString(s): assert isinstance(s,str)
def assertLink(s): assert isinstance(s,Link), s.__class__
def assertParam(s): assert isinstance(s,param.Param), s.__class__
def assertEqual(a,b): assert a==b, (a,b)

class LinkError(Exception):
    """Base class for exceptions in this module."""
    pass

defaultNodeClasses={}
def reg(_class,name=None):
    """
    intended for use as decorator to regester classes in the defaultNodeClasses dict
    """
    if name is None: name=_class.__name__
    defaultNodeClasses[name]=_class
    return _class

@reg
class ScriptNode(Node):
    """
    base class for nodes that can auctually be used by script files
    """
    # required by script system
    def getDefaultLink(self):
        raise LinkError("This node has no default link. Type: "+str(self.__class__))
    # required by script system
    def getLink(self,name):
        raise LinkError("This node has no link named "+name)
    

def allActive(linkStatus,links):
    return all(linkStatus[link] for link in links)
        
class LinksNode(ScriptNode):
    def __init__(self,*inLinks):
        for link in inLinks: assertLink(link)
        self.links=inLinks

@reg
class AssertActiveNode(LinksNode):
    def getActiveNode(self,renderState,linkStatus):
        assert allActive(linkStatus,self.links)
        return None
        
class AllActiveNode(LinksNode):
    def __init__(self,activeNode,*inLinks):
        LinksNode.__init__(self,*inLinks)
        self.activeNode=activeNode
    def getActiveNode(self,renderState,linkStatus):
        if allActive(linkStatus,self.links):
            for link in self.activeNode.outLinks:
                linkStatus[link]=True
            return self.activeNode
        else:
            return None
        
class CodeNode(AllActiveNode):
    """
    base class for nodes that fixed contain arbitrary code
    """
    def __init__(self,source,shaderInputs,shaderOutputs,inLinks,outLinks,isOutPut):
        self.source=source
        activeNode=ActiveNode(tuple(shaderInputs),tuple(shaderOutputs),tuple(inLinks),tuple(outLinks),self.source,isOutPut)
        AllActiveNode.__init__(self,activeNode,*inLinks)
    def getLink(self,name):
        for link in self.activeNode.getOutLinks():
            if link.name==name:
                return link
        raise LinkError("This node has no link named "+name)
    def getDefaultLink(self):
        links=self.activeNode.getOutLinks()
        if len(links)>0:
            return links[0]
        else:
            raise LinkError("This node has no default link because it has no outputs")
            
def metaCodeNode(source,shaderInputs,shaderOutputs,inLinks,outLinks,isOutPut):
    """
    makes a usable CodeNode for the specified source and I/O
    """
    fullSource=makeFullCode(source,shaderInputs,shaderOutputs,inLinks,outLinks)
    for l in inLinks: assertParam(l)
    for l in outLinks: assertParam(l)
    class CustomCodeNode(CodeNode):
        def __init__(self,*inLinks_):
            if len(inLinks)!=len(inLinks_):
                raise LinkError("Error: number of inputs does not match node type. Inputs: "+str(inLinks)+" expected: "+str(_inLinks))
            for x in xrange(len(inLinks)):
                t1=inLinks_[x].getType()
                t0=inLinks[x].getType()
                if t0!=t1:
                    raise LinkError("Error: mismatched type on inLinks. Got: "+t1+" expected: "+t0)
            newOutLinks=(Link(link.getType(),link.name) for link in outLinks)
            CodeNode.__init__(self,fullSource,shaderInputs,shaderOutputs,inLinks_,newOutLinks,isOutPut)
            
    return CustomCodeNode


def makePassThroughCode(type,backwards=False):
    if backwards:
        s="(out {t} ouput,in {t} input)"
    else:
        s="(in {t} input,out {t} ouput)"
    return s.replace("{t}",type)+"{ouput=input;}"
    
class SingleOutputMixin(object):
    def __init__(self,outLink):
        self.outLink=outLink
    def getDefaultLink(self):
        return self.outLink


@reg
class Input(SingleOutputMixin,ScriptNode):
    """
    makes an active node that outputs the ConditionalInput shader input from the node's data dict
    or no active note if input is not available.
    """
    def __init__(self,inputDef):
        
        ScriptNode.__init__(self)
        assertString(inputDef)
        
        input=param.shaderParamFromDefCode(inputDef)
        
        name=input.getName()
        if name.startswith("k_"):
            name=input.name[2:]
        self.inputName=name
        
        
        source=makePassThroughCode(input.getType())
        
        outLink=Link(input.getShortType())
        SingleOutputMixin.__init__(self,outLink)
        self.activeNode=ActiveNode((input,),(),(),(outLink,),source,False)

        
    def getActiveNode(self,renderState,linkStatus):
        linkStatus[self.outLink] = True
        return self.activeNode


@reg
class ConditionalInput(Input):
    """
    makes an active node that outputs the ConditionalInput shader input from the node's data dict
    or no active note if input is not available.
    """
    def getActiveNode(self,renderState,linkStatus):
        if renderState.hasShaderInput(self.inputName):
            return Input.getActiveNode(self,renderState,linkStatus)
        else:
            return None
            
    def setupRenderStateFactory(self,renderStateFactory):
        renderStateFactory.shaderInputs.add(self.inputName)

@reg
class FirstAvailable(SingleOutputMixin,LinksNode):
    """
    takes a list of inlinks, and chooses the first active one to hook up to the output
    
    if none are active, output is inactive.
    """
    def __init__(self,*inlinks):
        LinksNode.__init__(self,*inlinks)
        assert len(inlinks)>0
        firstType=inlinks[0].getType()
        for link in inlinks:
            assertEqual(firstType,link.getType())
            
        outLink=Link(firstType)
        SingleOutputMixin.__init__(self,outLink)
        self.source=makePassThroughCode(firstType)
        
        
    def getActiveNode(self,renderState,linkStatus):
        for input in self.links:
            if linkStatus[input]:
                linkStatus[self.outLink] = True
                return ActiveNode((),(),(input,),(self.outLink,),self.source,False)
        return None


@reg
class RequireTag(SingleOutputMixin,ScriptNode):
    """
    this node produces no activeNode, but marks it's outlink as active if the tag is present
    """
    def __init__(self,tagName):
        ScriptNode.__init__(self)
        assertString(tagName)
        self.tagName=tagName
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNode(self,renderState,linkStatus):
        if renderState.hasTag(self.tagName):
            linkStatus[self.outLink] = True
        return None
            
    def setupRenderStateFactory(self,renderStateFactory):
        renderStateFactory.tags.add(self.tagName)

@reg
class ConditionalPassThrough(SingleOutputMixin,ScriptNode):
    def __init__(self,conditionLink,dataLink):
        ScriptNode.__init__(self)
        assertLink(conditionLink)
        self.conditionLink=conditionLink
        self.dataLink=dataLink
        type=dataLink.getType()
        outLink=Link(type)
        source=makePassThroughCode(type)
        self.activeNode=ActiveNode((),(),(dataLink,),(outLink,),source,False)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNode(self,renderState,linkStatus):
        if linkStatus[self.conditionLink]:
            linkStatus[self.outLink] = True
            return self.activeNode
        else:
            return None


@reg
class Operator(SingleOutputMixin,LinksNode):
    def __init__(self,requireAll,op,*inlinks):
        LinksNode.__init__(self,*inlinks)
        self.requireAll=bool(requireAll)
        assertString(op)
        self.op=op
        
        assert len(inlinks)>0
        firstType=inlinks[0].getType()
#         for link in inlinks:
#             assert firstType==link.getType()
        
        outLink=Link(firstType,"output")
        
        SingleOutputMixin.__init__(self,outLink)
        if requireAll:
            self.activeNode=self.makeActiveNode(inlinks)
    
    def makeActiveNode(self,inlinks):
        params=[param.Param("input"+str(i),link.getType()) for i,link in enumerate(inlinks)]
        type=self.outLink.getType()
        code="output="+self.op.join(p.getName() for p in params)+";"
        source=makeFullCode(code,(),(),params,(self.outLink,))
        return ActiveNode((),(),inlinks,(self.outLink,),source,False)
        
    def getActiveNode(self,renderState,linkStatus):
        if self.requireAll:
            if allActive(linkStatus,self.links):
                linkStatus[self.outLink]=True
                return self.activeNode
            else:
                None 
        else:
            activeInputs=[link for link in self.links if linkStatus[link]]
            if len(activeInputs)>0:
                linkStatus[self.outLink]=True
                return self.makeActiveNode(tuple(activeInputs))
            else:
                return None

@reg
class Output(ScriptNode):
    def __init__(self,inlink,outputDef):
        ScriptNode.__init__(self)
        assertString(outputDef)
        output=param.shaderParamFromDefCode(outputDef)
        
        assertEqual(inlink.getType(),output.getShortType())
        
        source=makePassThroughCode(output.getType(),True)
        self.activeNode=ActiveNode((),(output,),(inlink,),(),source,True)

        self.inlink=inlink
        
    def getActiveNode(self,renderState,linkStatus):
        assert linkStatus[self.inlink]
        return self.activeNode

@reg
class Constant(SingleOutputMixin,ScriptNode):
    def __init__(self,type,value):
        ScriptNode.__init__(self)
        assertString(type)
        assertString(value)
        
        outLink=Link(type,"output")
        
        SingleOutputMixin.__init__(self,outLink)
        code="output="+value+";"
        source=makeFullCode(code,(),(),(),(self.outLink,))
        self.activeNode=ActiveNode((),(),(),(self.outLink,),source,False)
    
    def getActiveNode(self,renderState,linkStatus):
        linkStatus[self.outLink]=True
        return self.activeNode


def metaHasRenderAttrib(slot):
    class HasRenderAttrib(SingleOutputMixin,ScriptNode):
        def __init__(self):
            ScriptNode.__init__(self)
            outLink=Link(boolLinkType)
            SingleOutputMixin.__init__(self,outLink)
            
        def getActiveNode(self,renderState,linkStatus):
            if renderState.hasRenderAttrib(slot):
                linkStatus[self.outLink] = True
            return None
                
        def setupRenderStateFactory(self,renderStateFactory):
            renderStateFactory.hasRenderAttribs.add(slot)
    return HasRenderAttrib
    
reg(metaHasRenderAttrib(MaterialAttrib.getClassSlot()),"HasMaterial")
reg(metaHasRenderAttrib(ColorAttrib.getClassSlot()),"HasColorAttrib")
reg(metaHasRenderAttrib(TextureAttrib.getClassSlot()),"HasTextureAttrib")

@reg
class HasColumn(SingleOutputMixin,ScriptNode):
    def __init__(self,name):
        assertString(name)
        self.name=name
        ScriptNode.__init__(self)
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNode(self,renderState,linkStatus):
        if renderState.hasGeomVertexDataColumns(self.name):
            linkStatus[self.outLink] = True
        return None
            
    def setupRenderStateFactory(self,renderStateFactory):
        renderStateFactory.geomVertexDataColumns.add(self.name)