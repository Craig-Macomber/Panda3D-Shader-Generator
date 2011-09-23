import itertools
import collections
import os
import renderState

import param
import nodes

import inspect

from panda3d.core import Shader

"""

A system for generating shader generators based on the generator specifications (the graph files).

IMPORTANT:
The script files do NOT discribe specific shaders.
They describe a shader generator (ShaderBuilder), which takes input (render states) and outputs shaders.
To enable this, the nodes is the shader graph files (defined by the libraries) are not all simply shader functions.
They are all code generators, which may or may not produce the same code in all cases.
The graph files specifify how to instance and connect the code generator nodes together.
Thus, this shaderBuilder system is an implementation of a Shader Meta-Language. It is NOT a Shader Language.

Specifically, a script file and library files, together with any NodeType subclasses,
are used as souce code (in the Shader Meta-Language) to
essencially compile a function (ShaderBuilder instance) that accepts renderStates and retuns CG Shader code.


Usage:
- Load up a Library instance from a list of folders on disc
- Use Library.loadScript to load up a shader generator specification graph file (perhaps made with the editor)
    that uses the NodeTypes from the Library. Returns a ShaderBuilder
- Use one or more ShaderBuilders to generate (from one or more Libraryies and scripts) to generate shaders for
    your scene


TODO :

Loaders really need to assoiate file name and line numbers with all the loaded items
so error reporting can be far more useful!

TODO :

Deployment system could concatenate libraries down to 1 file if desired,
or one could pregenerate shaders and store them with their models in a cache
if they don't need dynamic generation

TODO :
auto generate semantics?

TODO :
fix generator graph node text for first line (line 1)
"""


join=os.path.join


debugText=True
        

def _parseFile(path):
    majorSections=collections.defaultdict(list)
    f = open(path, 'r')
                
    majorSection=None
    section=None
    
    lineNum=0
    
    def warnText(): return "Warning: "+path+" line "+str(lineNum)+": "
    
    for t in f.readlines():
        lineNum+=1
    
        # Remove comments
        i=t.find('#')
        if i!=-1: t=t[:i]
        
        # Strip excess whitespace
        t=t.strip()
        
        
        if len(t)>0:
            # Process line
            if len(t)>1 and t[0:2]=='::':
                section=None
                majorSection=t[2:].lower().strip()
                majorSectionList=majorSections[majorSection]
                d={}
                majorSectionList.append(d)
                
            elif t[0]==':':
                # if section header, prefixed with :
                if majorSection is None:
                    print warnText()+"throwing away invalid section occuring before first majorSection in: "+path
                else:
                    currentList=[]
                    section=t[1:].lower().strip()
                    d[section]=currentList
                    
            else:
                if section is None:
                    print warnText()+"throwing away invalid line occuring before first section in: "+path+" section: "+str(section)
                elif currentList!=None:
                    currentList.append(t)
    f.close()
    return majorSections

def _parseInfoLines(lines,currentFile):
    info={}
    for line in lines:
        s=line.split(None, 1)
        if len(s)!=2:
            print "invalid info entry '"+line+"' in: "+currentFile
        else:
            info[s[0]]=s[1]
    return info
    




class NodeWrapper(object):
    """
    A wrapper around a node,
    intended to be returned as a node in script files
    
    sourceTracker is an optional debug dict for link to source scriptNode tracking
    """
    def __init__(self,scriptNode,sourceTracker=None):
        self._scriptNode=scriptNode
        self.sourceTracker=sourceTracker
    def __getattr__(self,name):
        link=self._scriptNode.getLink(name)
        if self.sourceTracker is not None: self.sourceTracker[link]=self._scriptNode
        return link
        

def preprocessParam(param,sourceTracker=None):
    if isinstance(param,NodeWrapper):
        link=param._scriptNode.getDefaultLink()
        if sourceTracker is not None: sourceTracker[link]=param._scriptNode
        return link
    else:
        return param

class Library(object):
    def __init__(self,paths,nodeTypeClassMap={}):
        """
    
        path should be a path to a library folder
        
        builds an instance made from the contents of the passed folder path.
        
        
        nodeTypeClassMap should be a dict mapping strings to NodeType subclasses.
        The strings should correspond to the "class" info field used in the nodes in the library.
        no "class" info (a None in the dictionary) maps to NodeType, not a subclass.
        
        
        """
        
        
        self.nodeTypeClassMap=dict(nodes.defaultNodeClasses)
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
                    currentFile=join(root, name)
                    for key,xitems in _parseFile(currentFile).iteritems():
                        if key=="node":
                            for items in xitems:
                                if "info" not in items:
                                    print "node missing info section in: "+currentFile
                                else:
                                    
                                    
                                    info=_parseInfoLines(items["info"],currentFile)
                                    
                                    if "name" not in info:
                                        print "invalid info entry missing name in: "+currentFile
                                    else:
                                        name=info["name"]
                                        
                                        shaderInputs=[]
                                        if "shaderinputs" in items:
                                            for s in items["shaderinputs"]:
                                                shaderInputs.append(param.shaderParamFromDefCode(s))
                                        
                                        if "output" in info:
                                            o=info["output"]
                                            assert o in ["True","False"]
                                            isOutPut=o=="True"
                                            assert "stage" in info
                                            stage=info["stage"]
                                        else:
                                            isOutPut=False
                                            stage=None
                                        
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
                                        
                                        node=nodes.metaCodeNode(name,code,shaderInputs,inLinks,outLinks,isOutPut=isOutPut,stage=stage)
                                        if name in self.nodeTypeClassMap:
                                            print "Warning: overwriting node "+repr(self.nodeTypeClassMap[name])+" with "+repr(node)+" from "+currentFile
                                        self.nodeTypeClassMap[name]=node
                                
                        elif key=="lib":
                            libs.append(xitems)
                        else:
                            print "Warning: throwing away invalid majorSection with unrecognized name: "+key+" in file: "+currentFile
                            
        libSource="\n".join(itertools.chain.from_iterable(lib["code"] for lib in itertools.chain.from_iterable(libs) if "code" in lib))
        
        self.libSource=libSource
    

    
    def loadScript(self,path,viewGraph=False):
        return ShaderBuilder(self.parseScript(path,viewGraph),self.libSource)
    
    def parseScript(self,path,viewGraph=False):
        # setup some globals with the names of the Node classes in self.nodeTypeClassMap
        globals={}
        if viewGraph:
            nodeInfoDict={}
            sourceTracker={}
        else:
            sourceTracker=None
        
        for name,nodeType in self.nodeTypeClassMap.iteritems():
            
            # this closure is the auctual item put into the globals for the script
            # it poses as a Node class, but produces NodeWrappers instead of Nodes,
            # and also runs preprocessParam on all passed arguments
            def wrapperMaker(name,nodeType):
                def scriptNodeWrapper(*args,**kargs):    
                    pargs=[preprocessParam(param,sourceTracker) for param in args]
                    for name,param in kargs.iteritems():
                        kargs[name]=preprocessParam(param)
                    node=nodeType(*pargs,**kargs)
                    nodeList.append(node)
                    if viewGraph:
                        stack=inspect.stack()
                        frame, filename, lineNum, functionName, contextLines, contextIndex=stack[1]
                        debugInfo=(filename, lineNum, contextLines[contextIndex].rstrip(), pargs, kargs)
                        nodeInfoDict[node]=debugInfo
                    return NodeWrapper(node,sourceTracker)
                return scriptNodeWrapper
            globals[name]=wrapperMaker(name,nodeType)
        
        
        # run the script with the newly made globals
        locals={}
        nodeList=[]
        execfile(path,globals,locals)
        
        if viewGraph:
            import pydot
            
            graph = pydot.Dot(graph_type='digraph')
                
            for node,info in nodeInfoDict.iteritems():
                filename, lineNum, line, pargs, kargs=info
                graph.add_node(pydot.Node(strId(node), label=str(lineNum)+": "+line, shape="rectangle"))
                for a in pargs:
                    if isinstance(a,nodes.Link):
                        e = pydot.Edge( strId(sourceTracker[a]),strId(node), label=str(a) )
                        graph.add_edge(e)
                for name,a in kargs.iteritems():
                    if isinstance(a,nodes.Link):
                        e = pydot.Edge( strId(sourceTracker[a]),strId(node), label=name+"="+str(a))
                        graph.add_edge(e)
            writeGraph(graph,path)
            
        return nodeList


def strId(obj): return str(id(obj))

def writeGraph(graph,path):
    format="svg"
    finalPath=path+"."+format
    print 'Making Graph: '+finalPath
    graph.write(finalPath,format=format)
        
class ShaderBuilder(object):
    """
    
    A factory for shaders based off a set of Nodes. Make one instance for each distinct set of stages.
    
    """
    def __init__(self,nodes,libSource=""):
        """
        
        Takes an dict of lists of Nodes, and sets this instance up to produce shaders based on them.
        
        """
        self.nodes=nodes
        
        # a cache of finished shaders. Maps RenderState to Shader
        self.cache={}
        
        # a cache of finished shaders. Maps set of stage source strings to Shader
        self.casheByStages={}
        
        self.header="//Cg\n//AUTO-GENERATED-SHADER//\n\n"+libSource+"\n\n"
        self.footer="\n\n//END-AUTO-GENERATED-SHADER//\n"
        
        
    
    def setupRenderStateFactory(self,factory=None):
        if factory is None: factory=renderState.RenderStateFactory()
        for n in self.nodes:
            n.setupRenderStateFactory(factory)
        return factory
        
        
    def getShader(self,renderState,debugFile=None,noChache=False,debugGraphPath=None):
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
        
        
        if debugGraphPath:
            debugGraphPath+=str(len(self.casheByStages))
            
        stages=makeStages(self.nodes,renderState,debugGraphPath)
        
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



def makeStages(nodes,renderState,debugGraphPath=None):
    # process from top down (topological sorted order) to see what part of graph is active, and produce active graph
    # nodes are only processed when all nodes above them have been processed.
    
    # set of activeNodes that are needed because they produce output values
    activeOutputs=collections.defaultdict(set)
    
    # linksStatus defaults to false for all links
    linkStatus=collections.defaultdict(lambda:False)
    linkToSource={}
    
    sortedActive=[]
    
    for n in nodes:
        aa=n.getActiveNodes(renderState,linkStatus)
        for a in aa:
            sortedActive.append(a)
            for link in a.getOutLinks():
                linkToSource[link]=a
            
            if a.isOutPut():
                activeOutputs[a.stage].add(a)
    path=None
    for name,outputs in activeOutputs.iteritems():
        if debugGraphPath: path=debugGraphPath+name
        yield makeStage(name,sortedActive,outputs,linkToSource,path)
    
def makeStage(name,sortedActive,activeOutputs,linkToSource,debugGraphPath=None):
    # walk upward to find all needed nodes
    neededSet=set(activeOutputs)
    neededNodes=[]
    
    for n in reversed(sortedActive):
        if n in neededSet:
            neededNodes.append(n)
            for link in n.getInLinks():
                neededSet.add(linkToSource[link])

    if debugGraphPath:
        import pydot
            
        graph = pydot.Dot(graph_type='digraph')
        
            
        for node in neededSet:
            if isinstance(node,nodes.ActiveOutput):
                n=pydot.Node(strId(node), label=node.stage+" Output: "+str(node.shaderOutput), shape="rectangle")
            else:
                n=pydot.Node(strId(node), label=node.getComment(), shape="rectangle")
            graph.add_node(n)
            for link in node.getInLinks():
                e = pydot.Edge( strId(linkToSource[link]),strId(node), label=str(link) )
                graph.add_edge(e)
        
        writeGraph(graph,debugGraphPath)

    return makeStageFromActiveNodes(name,tuple(neededNodes))
        
    

stageCache={}
def makeStageFromActiveNodes(name,activeNodes):
    key=(name,activeNodes)
    s=stageCache.get(key)
    if s is None:
        b=StageBuilder()
        namer=AutoNamer("__"+name+"_")
        for node in activeNodes: b.addNode(node,namer)
        s=b.generateSource(name)
        
        s="\n\n".join(namer.getItems())+"\n\n"+s
        
        stageCache[key]=s
    return s

class AutoNamer(object):
    """
    
    A simple class for associating unique names with hashables
    
    """
    def __init__(self,prefix):
        self.items={}
        self.prefix=prefix
    def addItem(self,item):
        if item not in self.items:
            self.items[item]=self.nextName()
    def getItems(self): return self.items
    def nextName(self): return self.prefix+str(len(self.items))
    

class StageBuilder(object):
    """
    
    Used by ShaderBuilder to build the different stages in the shaders
    
    All nodes used in here are ActiveNodes
    
    built bottom up
    
    """
    def __init__(self):
        self.links=AutoNamer("__x")
        self.inputs=set()
        self.outputs=set()
        self.sourceLines=[]
    def _addLink(self,link):
        self.links.addItem(link)
        
    def addNode(self,node,functionNamer):
        """
        links=list of links passed to Node's function. Contains in and out ones.
        """
        if isinstance(node,nodes.ActiveOutput):
            self._addLink(node.inLink)
            o=node.shaderOutput
            self.outputs.add(o)
            code=o.getName()+"="+self.links.getItems()[node.inLink]+";"
            self.sourceLines.append(code)
        else:
            inputs=node.getShaderInputs()
            self.inputs.update(inputs)
            
            inLinks=node.getInLinks()
            outLinks=node.getOutLinks()
            
            for link in itertools.chain(inLinks,outLinks):
                self._addLink(link)
                
            ld=self.links.getItems()
            
            paramChain=itertools.chain(
                (s.getName() for s in inputs),
                (ld[s] for s in itertools.chain(inLinks,outLinks)),
                )
            
            fname=functionNamer.nextName()        
            callSource=fname+"("+",".join(paramChain)+");"
            self.sourceLines.append(callSource)
            
            # make the function
            f="void "+fname+node.getCode()
            
            if debugText:
                comment="//"+node.getComment()
                f=comment+'\n'+f
                self.sourceLines.append('\n'+comment)
            functionNamer.addItem(f)
        
        
    def generateSource(self,name):
        paramChain=itertools.chain(
            ("in "+s.getDefCode() for s in self.inputs),
            ("out "+s.getDefCode() for s in self.outputs)
            )
    
        header="void "+name+"(\n  "+",\n  ".join(paramChain)+")\n{\n\n"
        footer="}"
        linkDeclarations='\n'.join(link.getType()+" "+name+";//"+link.name for link,name in self.links.getItems().iteritems())
        source='\n'.join(reversed(self.sourceLines))
        return header+linkDeclarations+'\n\n'+source+'\n'+footer
