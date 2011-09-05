import itertools
import collections
import os

import shaderBuilder
import param
import nodes

from panda3d.core import Shader

"""
Notes:

Process stages in order, provide outputs of previous stages an inputs (use link status?)




"""


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
def assertLink(s): assert isinstance(s,shaderBuilder.Link), s.__class__
def assertParam(s): assert isinstance(s,param.Param), s.__class__

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
        raise LinkError("This node has no default link")
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
    def __init__(self,source,shaderInputs,shaderOutputs,inLinks,outLinks):
        self.source=source
        activeNode=ActiveNode(tuple(shaderInputs),tuple(shaderOutputs),tuple(inLinks),tuple(outLinks),self.source)
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
            
def metaCodeNode(source,shaderInputs,shaderOutputs,inLinks,outLinks):
    """
    makes a usable CodeNode for the specified source and I/O
    """
    fullSource=nodes.makeFullCode(source,shaderInputs,shaderOutputs,inLinks,outLinks)
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
            newOutLinks=(shaderBuilder.Link(link.getType(),link.name) for link in outLinks)
            CodeNode.__init__(self,fullSource,shaderInputs,shaderOutputs,inLinks_,newOutLinks)
            
    return CustomCodeNode




class NodeWrapper(object):
    """
    A wrapper around a node,
    intended to be returned as a node in script files
    """
    def __init__(self,scriptNode):
        self._scriptNode=scriptNode
    def __getattr__(self,name):
        return self._scriptNode.getLink(name)
        

def preprocessParam(param):
    if isinstance(param,NodeWrapper):
        return preprocessParam(param._scriptNode.getDefaultLink())
    else:
        return param

class Library(shaderBuilder.Library):
    def __init__(self,paths,nodeTypeClassMap={}):
        """
    
        path should be a path to a library folder
        
        builds an instance made from the contents of the passed folder path.
        
        
        nodeTypeClassMap should be a dict mapping strings to NodeType subclasses.
        The strings should correspond to the "class" info field used in the nodes in the library.
        no "class" info (a None in the dictionary) maps to NodeType, not a subclass.
        
        
        """
        
        
        self.nodeTypeClassMap=dict(defaultNodeClasses)
        self.nodeTypeClassMap.update(nodeTypeClassMap)
        self.loadPath(paths)
    
    def loadPath(self,paths):
        """
        
        called by init, but can be called again if you wish to reload the same paths, or a different one
        
        """
        
        
        libs=[]
        
        for root, dirs, files in itertools.chain.from_iterable(os.walk(path) for path in paths):
            for name in files:
                ext=os.path.splitext(name)[1]
                if ext==".txt":
                    currentFile=shaderBuilder.join(root, name)
                    for key,xitems in shaderBuilder._parseFile(currentFile).iteritems():
                        if key=="node":
                            for items in xitems:
                                if "info" not in items:
                                    print "node missing info section in: "+currentFile
                                else:
                                    
                                    
                                    info=shaderBuilder._parseInfoLines(items["info"],currentFile)
                                    
                                    if "name" not in info:
                                        print "invalid info entry missing name in: "+currentFile
                                    else:
                                        name=info["name"]
                                        
                                        shaderInputs=[]
                                        if "shaderinputs" in items:
                                            for s in items["shaderinputs"]:
                                                shaderInputs.append(param.shaderParamFromDefCode(s))
                                        shaderOutputs=[]
                                        if "shaderoutputs" in items:
                                            for s in items["shaderoutputs"]:
                                                shaderOutputs.append(param.shaderParamFromDefCode(s))
                                        
                                        inLinks=[]
                                        if "inlinks" in items:
                                            for s in items["inlinks"]:
                                                inLinks.append(param.linkEndFromDefCode(s))
                                        outLinks=[]
                                        if "outlinks" in items:
                                            for s in items["outlinks"]:
                                                outLinks.append(param.linkEndFromDefCode(s))
                                        
                                        
                                        code=""
                                        if "code" in items:
                                            code="\n".join(items["code"])
                                        
                                        node=metaCodeNode(code,shaderInputs,shaderOutputs,inLinks,outLinks)
                                        if name in self.nodeTypeClassMap:
                                            print "Warning: overwriting node "+repr(nodes[name])+" with "+repr(node)+" from "+currentFile
                                        self.nodeTypeClassMap[name]=node
                                
                        elif key=="lib":
                            libs.append(xitems)
                        else:
                            print "Warning: throwing away invalid majorSection with unrecognized name: "+key+" in file: "+currentFile
                            
        libSource="\n".join(itertools.chain.from_iterable(lib["code"] for lib in itertools.chain.from_iterable(libs) if "code" in lib))
        
        self.libSource=libSource
    

    
    
    
    def parseScript(self,path):
        # setup some globals with the names of the Node classes in self.nodeTypeClassMap
        globals={}
        for name,nodeType in self.nodeTypeClassMap.iteritems():
            
            # this closure is the auctual item put into the globals for the script
            # it poses as a Node class, but produces NodeWrappers instead of Nodes,
            # and also runs preprocessParam on all passed arguments
            def wrapperMaker(name,nodeType):
                def scriptNodeWrapper(*args,**kargs):
                    pargs=[preprocessParam(param) for param in args]
                    for name,param in kargs.iteritems():
                        kargs[name]=preprocessParam(param)
                    node=nodeType(*pargs,**kargs)
                    nodes.append(node)
                    return NodeWrapper(node)
                return scriptNodeWrapper
            globals[name]=wrapperMaker(name,nodeType)
        
        
        # run the script with the newly made globals
        locals={}
        execfile(path,globals,locals)
        stages={}
        for stage,func in locals.iteritems():
            nodes=[]
            stages[stage]=nodes
            func()
        return stages
        
        
class ShaderBuilder(object):
    """
    
    A factory for shaders based off a set of Nodes. Make one instance for each distinct set of stages.
    
    """
    def __init__(self,stages,libSource=""):
        """
        
        Takes an dict of lists of Nodes, and sets this instance up to produce shaders based on them.
        
        """
        self.stages=stages
        
        # a cache of finished shaders. Maps RenderState to Shader
        self.cache={}
        
        # a cache of finished shaders. Maps set of stage source strings to Shader
        self.casheByStages={}
        
        self.header="//Cg\n//AUTO-GENERATED-SHADER//\n\n"+libSource+"\n\n"
        self.footer="\n\n//END-AUTO-GENERATED-SHADER//\n"
        
        
    
    def setupRenderStateFactory(self,factory=None):
        if factory is None: factory=renderState.RenderStateFactory()
        for n in self.sortedNodes:
            n.setupRenderStateFactory(factory)
        return factory
        
        
    def getShader(self,renderState,debugFile=None,noChache=False):
        """
        
        returns a shader appropriate for the passed RenderState
        
        will generate or fetch from cache as needed
        
        noChache forces the generation of the shader (but it will still get cached).
        Useful for use with debugFile if you need to see the source, but it may be cached
        
        caching system isn't verg good in the case where the render state is different, but the resulting shader is the same.
        It will find the shader in the cache, but it will take a while.
        
        """
        
        shader=self.cache.get(renderState)
        if shader and not noChache:
            #if debugFile: print "Shader is cached (renderState cache). Skipping generating shader to: "+debugFile
            return shader

        stages=set()
        for name,nodes in self.stages.iteritems():
            stages.add(makeStage(name,nodes,renderState))
        
        stages=frozenset(stages)
        shader=self.casheByStages.get(stages)
        if shader and not noChache:
            self.cache[renderState]=shader
            #if debugFile: print "Shader is cached (renderState cache). Skipping generating shader to: "+debugFile
            return shader

        
        # TODO : Auto generate/match unspecified semantics here
        
        stageCode="\n\n".join(stages)
        
        
        source = self.header+"\n\n"+stageCode+self.footer
        
        
        
        
        if debugFile:
            debugFile+=str(len(self.casheByStages))+".sha"
            print 'Making Shader: '+debugFile
            
        
        if debugFile:
            fOut=open(debugFile, 'w')
            fOut.write(source)
            fOut.close()
        
        shader=Shader.make(source)
        self.cache[renderState]=shader
        self.casheByStages[stages]=shader
        return shader



def makeStage(name,nodes,renderState):
    # process from top down (topological sorted order) to see what part of graph is active, and produce active graph
    # nodes are only processed when all nodes above them have been processed.
    
    activeOutputs=set() # set of activeNodes that are needed because they produce output values
    
    # linksStatus defaults to false for all links
    linkStatus=collections.defaultdict(lambda:False)
    linkToSource={}
    
    sortedActive=[]
    
    for n in nodes:
        a=n.getActiveNode(renderState,linkStatus)
        if a is not None:
            sortedActive.append(a)
            for link in a.getOutLinks():
                linkToSource[link]=a
            
            if a.isOutPut():
                activeOutputs.add(a)

    # walk upward to find all needed nodes

    neededSet=set(activeOutputs)
    neededNodes=[]
    
    for n in reversed(sortedActive):
        if n in neededSet:
            neededNodes.append(n)
            for link in n.getInLinks():
                neededSet.add(linkToSource[link])


    return makeStageFromActiveNodes(name,tuple(neededNodes))
        
    

stageCache={}
def makeStageFromActiveNodes(name,activeNodes):
    key=(name,activeNodes)
    s=stageCache.get(key)
    if s is None:
        b=shaderBuilder.StageBuilder()
        namer=shaderBuilder.AutoNamer("__"+name+"_")
        for node in activeNodes: b.addNode(node,namer)
        s=b.generateSource(name)
        
        s="\n\n".join(namer.getItems())+"\n\n"+s
        
        stageCache[key]=s
    return s


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
    def __init__(self,shaderInputs,shaderOutputs,inLinks,outLinks,code):
        self.shaderInputs=shaderInputs
        self.shaderOutputs=shaderOutputs
        self.inLinks=inLinks
        self.outLinks=outLinks
        self.code=code
    def getShaderInputs(self): return self.shaderInputs
    def getShaderOutputs(self): return self.shaderOutputs
    def getInLinks(self): return self.inLinks
    def getOutLinks(self): return self.outLinks
    def isOutPut(self): return len(self.getShaderOutputs())>0
    def getCode(self): return self.code
    def __repr__(self):
        return "ActiveNode"+str(tuple([self.shaderInputs,self.shaderOutputs,self.inLinks,self.outLinks,"<code>"]))
 