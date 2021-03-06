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
    def __str__(self):
        name=self.getName()
        text=self.getType()
        if name != "Unnamed":text=text+" "+name
        return text
        

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
    def __init__(self,shaderInputs,inLinks,outLinks,code,isOutPut,comment="",stage=None):
        self.shaderInputs=shaderInputs
        self.inLinks=inLinks
        self.outLinks=outLinks
        self.code=code
        self.outPut=isOutPut
        if isOutPut: assert stage is not None
        self.stage=stage
        self.comment=comment
    def getShaderInputs(self): return self.shaderInputs
    def getInLinks(self): return self.inLinks
    def getOutLinks(self): return self.outLinks
    def isOutPut(self): return self.outPut
    def getCode(self): return self.code
    def getComment(self): return self.comment
    def __repr__(self):
        return "ActiveNode"+str(tuple([self.shaderInputs,self.inLinks,self.outLinks,"<code>",self.outPut]))
 
class ActiveOutput(object):
    """
    
    ActiveOutputs should never be modified, and should not be subclassed.
    
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
    def __init__(self,stage,inLink,shaderOutput):
        self.shaderOutput=shaderOutput
        self.inLink=inLink
        self.stage=stage
    def isOutPut(self): return True
    def getOutLinks(self): return ()
    def getInLinks(self): return (self.inLink,)
    def __repr__(self):
        return "ActiveOutput"+str(tuple([self.stage,self.inLink,self.shaderOutput]))
 




def makeFullCode(code,shaderInputs,inLinks,outLinks):
    """
    
    the code needed to construct Nodes includes the (paramList){code} wrapping stuff, so this addes it
    and saves it to self.code
    
    """
    
    fparamChain=itertools.chain(
         ("in "+s.getType()+" "+s.getName() for s in shaderInputs),
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
    def getActiveNodes(self,renderState,linkStatus):
        return ()
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
    def getActiveNodes(self,renderState,linkStatus):
        assert allActive(linkStatus,self.links), "{0}: links:{1}".format(self,[link for link in self.links if not linkStatus[link]])
        return ()
        
class AllActiveNode(LinksNode):
    def __init__(self,activeNode,*inLinks):
        LinksNode.__init__(self,*inLinks)
        self.activeNode=activeNode
    def getActiveNodes(self,renderState,linkStatus):
        if allActive(linkStatus,self.links):
            for link in self.activeNode.outLinks:
                linkStatus[link]=True
            return (self.activeNode,)
        else:
            return ()
        
class CodeNode(AllActiveNode):
    """
    base class for nodes that fixed contain arbitrary code
    """
    def __init__(self,source,shaderInputs,inLinks,outLinks,isOutPut,stage=None,comment="CodeNode"):
        self.source=source
        activeNode=ActiveNode(tuple(shaderInputs),tuple(inLinks),tuple(outLinks),self.source,isOutPut,comment,stage)
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
            raise LinkError("This node ("+self.activeNode.comment+") has no default link because it has no outputs")
            
def metaCodeNode(name,source,shaderInputs,inLinks,outLinks,isOutPut=False,stage=None):
    """
    makes a usable CodeNode for the specified source and I/O
    """
    fullSource=makeFullCode(source,shaderInputs,inLinks,outLinks)
    for l in inLinks: assertParam(l)
    for l in outLinks: assertParam(l)
    class CustomCodeNode(CodeNode):
        def __init__(self,*inLinks_):
            if len(inLinks)!=len(inLinks_):
                raise LinkError("Error: number of inputs does not match node type. Inputs: "+str(inLinks_)+" expected: "+str(inLinks))
            for x in xrange(len(inLinks)):
                t1=inLinks_[x].getType()
                t0=inLinks[x].getType()
                if t0!=t1:
                    raise LinkError("Error: mismatched type on inLinks. Got: "+t1+" expected: "+t0)
            newOutLinks=(Link(link.getType(),link.name) for link in outLinks)
            CodeNode.__init__(self,fullSource,shaderInputs,inLinks_,newOutLinks,isOutPut,stage,"CodeNode: "+name)
            
    return CustomCodeNode


def makePassThroughCode(type,backwards=False):
    if backwards:
        s="(out {0} ouput,in {0} input)"
    else:
        s="(in {0} input,out {0} ouput)"
    return s.format(type)+"{ouput=input;}"
    
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
        self.activeNode=ActiveNode((input,),(),(outLink,),source,False,"Input: "+inputDef)

        
    def getActiveNodes(self,renderState,linkStatus):
        linkStatus[self.outLink] = True
        return (self.activeNode,)


@reg
class ConditionalInput(Input):
    """
    makes an active node that outputs the ConditionalInput shader input from the node's data dict
    or no active note if input is not available.
    """
    def getActiveNodes(self,renderState,linkStatus):
        if renderState.hasShaderInput(self.inputName):
            return Input.getActiveNodes(self,renderState,linkStatus)
        else:
            return ()
            
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
        
        
    def getActiveNodes(self,renderState,linkStatus):
        for i,input in enumerate(self.links):
            if linkStatus[input]:
                linkStatus[self.outLink] = True
                return (ActiveNode((),(input,),(self.outLink,),self.source,False,
                    "FirstAvailable: choose #"+str(i)+" (0-"+str(len(self.links)-1)+")"),)
        return ()

@reg
class AllAvailable(SingleOutputMixin,LinksNode):
    """
    takes a list of inlinks, and outputs if they are all available 
    """
    def __init__(self,*inlinks):
        LinksNode.__init__(self,*inlinks)
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        for input in self.links:
            if not linkStatus[input]: return ()
        linkStatus[self.outLink] = True
        return ()

@reg
class AnyAvailable(SingleOutputMixin,LinksNode):
    """
    takes a list of inlinks, and outputs if they any are available 
    """
    def __init__(self,*inlinks):
        LinksNode.__init__(self,*inlinks)
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        for input in self.links:
            if linkStatus[input]:
                linkStatus[self.outLink] = True
        return ()

@reg
class NoneAvailable(SingleOutputMixin,LinksNode):
    """
    takes a list of inlinks, and outputs if they any are available 
    """
    def __init__(self,*inlinks):
        LinksNode.__init__(self,*inlinks)
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        for input in self.links:
            if linkStatus[input]: return ()
        linkStatus[self.outLink] = True
        return ()

@reg
class HasTag(SingleOutputMixin,ScriptNode):
    """
    this node produces no activeNode, but marks it's outlink as active if the tag is present
    """
    def __init__(self,tagName):
        ScriptNode.__init__(self)
        assertString(tagName)
        self.tagName=tagName
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        if renderState.hasTag(self.tagName):
            linkStatus[self.outLink] = True
        return ()
            
    def setupRenderStateFactory(self,renderStateFactory):
        renderStateFactory.tags.add(self.tagName)



@reg
class HasFlag(SingleOutputMixin,ScriptNode):
    """
    this node produces no activeNode, but marks it's outlink as active if the tag is present
    """
    def __init__(self,flagName):
        ScriptNode.__init__(self)
        assertString(flagName)
        self.flagName=flagName
        outLink=Link(boolLinkType)
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        if renderState.hasFlag(self.flagName):
            linkStatus[self.outLink] = True
        return ()
            
    def setupRenderStateFactory(self,renderStateFactory):
        renderStateFactory.flags.add(self.flagName)


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
        self.activeNode=ActiveNode((),(dataLink,),(outLink,),source,False,"ConditionalPassThrough")
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        if linkStatus[self.conditionLink]:
            linkStatus[self.outLink] = True
            return (self.activeNode,)
        else:
            return ()


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
        source=makeFullCode(code,(),params,(self.outLink,))
        return ActiveNode((),inlinks,(self.outLink,),source,False,"Operator: "+self.op)
        
    def getActiveNodes(self,renderState,linkStatus):
        if self.requireAll:
            if allActive(linkStatus,self.links):
                linkStatus[self.outLink]=True
                return (self.activeNode,)
            else:
                return () 
        else:
            activeInputs=[link for link in self.links if linkStatus[link]]
            if len(activeInputs)>0:
                linkStatus[self.outLink]=True
                return (self.makeActiveNode(tuple(activeInputs)),)
            else:
                return ()

@reg
class Output(ScriptNode):
    def __init__(self,stage,inlink,outputDef):
        ScriptNode.__init__(self)
        assertString(stage)
        assertString(outputDef)
        output=param.shaderParamFromDefCode(outputDef)
        
        assertEqual(inlink.getType(),output.getShortType())
        
        source=makePassThroughCode(output.getType(),True)
        self.activeNode=ActiveOutput(stage,inlink,output)

        self.inlink=inlink
        
        self.shaderInput=Input(outputDef)
    
    def getDefaultLink(self):
        return self.shaderInput.getDefaultLink()
        
    def getActiveNodes(self,renderState,linkStatus):
        assert linkStatus[self.inlink], "Output node '{out}'' must have active input '{input}'".format(out=self.shaderInput.activeNode,input=self.inlink)
        return (self.activeNode,self.shaderInput.getActiveNodes(renderState,linkStatus)[0])

@reg
class ConditionalOutput(Output):
    def getActiveNodes(self,renderState,linkStatus):
        if linkStatus[self.inlink]:
            return Output.getActiveNodes(self,renderState,linkStatus)
        else:
            return ()

@reg
class Constant(SingleOutputMixin,ScriptNode):
    def __init__(self,type,value):
        ScriptNode.__init__(self)
        assertString(type)
        assertString(value)
        
        outLink=Link(type,"output")
        
        SingleOutputMixin.__init__(self,outLink)
        code="output="+value+";"
        source=makeFullCode(code,(),(),(self.outLink,))
        self.activeNode=ActiveNode((),(),(self.outLink,),source,False,"Constant: "+type+"="+value)
    
    def getActiveNodes(self,renderState,linkStatus):
        linkStatus[self.outLink]=True
        return (self.activeNode,)


def metaHasRenderAttrib(slot):
    class HasRenderAttrib(SingleOutputMixin,ScriptNode):
        def __init__(self):
            ScriptNode.__init__(self)
            outLink=Link(boolLinkType)
            SingleOutputMixin.__init__(self,outLink)
            
        def getActiveNodes(self,renderState,linkStatus):
            if renderState.hasRenderAttrib(slot):
                linkStatus[self.outLink] = True
            return ()
                
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
        
    def getActiveNodes(self,renderState,linkStatus):
        if renderState.hasGeomVertexDataColumns(self.name):
            linkStatus[self.outLink] = True
        return ()
            
    def setupRenderStateFactory(self,renderStateFactory):
        renderStateFactory.geomVertexDataColumns.add(self.name)
        

@reg
class Select(SingleOutputMixin,ScriptNode):
    """
    Passes through the dataLinkA input if conditionLink is true, else dataLinkB
    """
    def __init__(self,conditionLink,dataLinkA,dataLinkB):
        ScriptNode.__init__(self)
        assertLink(conditionLink)
        assertEqual(dataLinkA.getType(),dataLinkB.getType())
        self.conditionLink=conditionLink
        self.dataLinks=(dataLinkA,dataLinkB)
        type=dataLinkA.getType()
        outLink=Link(type)
        source=makePassThroughCode(type)
        self.activeNodes=(
                ActiveNode((),(dataLinkA,),(outLink,),source,False,"SelectA"),
                ActiveNode((),(dataLinkB,),(outLink,),source,False,"SelectB")
                )
        SingleOutputMixin.__init__(self,outLink)
        
    def getActiveNodes(self,renderState,linkStatus):
        source=0 if linkStatus[self.conditionLink] else 1
        if linkStatus[self.dataLinks[source]]:
            linkStatus[self.outLink] = True
            return (self.activeNodes[source],)
        return ()
