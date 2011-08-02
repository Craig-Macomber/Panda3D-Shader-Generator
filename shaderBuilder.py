import collections
import itertools
import os
import os.path

from panda3d.core import Shader

import nodeTypes
import renderState
import param

join=os.path.join

debugText=True

"""

A system for generating shader generators based on the generator specifications (the graph files).

IMPORTANT:
The graph files (produced with the editor or by other means) do NOT discribe specific shaders.
They describe a shader generator (ShaderBuilder), which takes input (render states) and outputs shaders.
To enable this, the nodes is the shader graph files (defined by the libraries) are not all simply shader functions.
They are all code generators, which may or may not produce the same code in all cases.
The graph files specifify how to instance and connect the code generator nodes together.
Thus, this shaderBuilder system is an implementation of a Shader Meta-Language. It is NOT a Shader Language.

Specifically, a graph file and library files, together with any NodeType subclasses,
are used as souce code (in the Shader Meta-Language) to
essencially compile a function (ShaderBuilder instance) that accepts renderStates and retuns CG Shader code.


Usage:
- Load up a Library instance from a list of folders on disc
- Use Library.loadGraph to load up a shader generator specification graph file (perhaps made with the editor)
    that uses the NodeTypes from the Library. Returns a ShaderBuilder
- Use one or more ShaderBuilders to generate (from one or more Libraryies and graphs) to generate shaders for
    your scene

Also, you can use an editor to do realtime editing on a graph with previewing, see test.py or editor.py

Developing libraries:
Shader code defines NodeTypes in the library .txt files. New NodeTypes can be added this way.
The NodeType class can be considered a metaClass of sorts for NodeTypes defined in the libraries.
Subclass NodeType and provide the new Class to the Library to allow the class info field in
the library's nodes to refer to it. This allows new render state dependant code generation.


TODO :

Loaders really need to assoiate file name and line numbers with all the loaded items
so error reporting can be far more useful!

TODO :

Deployment system could concatenate libraries down to 1 file if desired,
or one could pregenerate shaders and store them with their models in a cache
if they don't need dynamic generation

TODO :
generate matching semantics

TODO :
associate node links with nodeType params (by some exposed public name added to the params?)

TODO :
allow multiple inputs to one source, which some nodeType might allow (ex: multiply all)

TODO :
allow editable params on NodeTypes. Saved on graph nodes, editable in editor (slider, text box, color picker etc)
    NodeType can provide editing widget --> extensible for custom nodeTypes

"""
   
        
class Link(object):
    """
    
    An output from a shader Node, and possibly multiple inputs to multiple shader nodes.
    
    As it can be multiple inputs, links are sets of edges in the graph from one node to multiple others.
    
    """
    def __init__(self,dataType,name="Unnamed"):
        self.dataType=dataType
        self.name=name
    def getType(self): return self.dataType
    def __repr__(self):
        return "Link"+str(tuple([self.dataType,self.name]))
        
        
        
        

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
    


class Library(object):
    def __init__(self,paths,nodeTypeClassMap={}):
        """
    
        path should be a path to a library folder
        
        builds an instance made from the contents of the passed folder path.
        
        
        nodeTypeClassMap should be a dict mapping strings to NodeType subclasses.
        The strings should correspond to the "class" info field used in the nodes in the library.
        no "class" info (a None in the dictionary) maps to NodeType, not a subclass.
        
        
        """
        
        
        self.nodeTypeClassMap=dict(nodeTypes.defaultNodeTypeClassMap)
        self.nodeTypeClassMap.update(nodeTypeClassMap)
        self.loadPath(paths)
        
    def loadPath(self,paths):
        """
        
        called by init, but can be called again if you wish to reload the same paths, or a different one
        
        """
        
        
        nodes={}
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
                                        
                                        class_=info.get("class")
                                        
                                        nclass=self.nodeTypeClassMap.get(class_)
                                        if nclass is None:
                                            nclass=self.nodeTypeClassMap[None]
                                            print "Warning: unrecognized class: "+class_+" in file: "+currentFile
                                        
                                        node=nclass(name,shaderInputs,shaderOutputs,inLinks,outLinks,code)
                                        if name in nodes:
                                            print "Warning: overwriting node "+repr(nodes[name])+" with "+repr(node)+" from "+currentFile
                                        nodes[name]=node
                                
                        elif key=="lib":
                            libs.append(xitems)
                        else:
                            print "Warning: throwing away invalid majorSection with unrecognized name: "+key+" in file: "+currentFile
                            
        libSource="\n".join(itertools.chain.from_iterable(lib["code"] for lib in itertools.chain.from_iterable(libs) if "code" in lib))
        
        self.nodes=nodes
        self.libSource=libSource
    


    def parseGraph(self,path):
        """
        
        path should be a path to a graph text file
        
        returns nodes from graph
        
        """
        
        nodeTypes=self.nodes
        
        links={}
        nodes=[]
        d=_parseFile(path)
        for items in d["link"]:
            if "info" not in items:
                print "link missing info section in: "+path
            else:
                info=_parseInfoLines(items["info"],path)
                
                if "name" not in info:
                    print "invalid info entry missing name in: "+path
                else:
                    name=info["name"]
                    if "type" not in info:
                        print "invalid info entry missing type in link: "+name+" in file: "+path
                    else:
                        dataType=info["type"]
                        links[name]=Link(dataType,name)
                        
        for items in d["node"]:
            if "info" not in items:
                print "node missing info section in: "+path
            else:
                
                
                info=_parseInfoLines(items["info"],path)
                
                if "type" not in info:
                    print "invalid info entry missing type in a node in: "+path
                else:
                    type=info["type"]
                    if "stage" not in info:
                        print "invalid info entry missing stage in a node in: "+path
                    else:
                        stage=info["stage"]
                        inLinks=[]
                        outLinks=[]
                        if "inlinks" in items:
                            for s in items["inlinks"]:
                                if s in links:
                                    inLinks.append(links[s])
                                else:
                                    print "missing link of name: "+s+" in file: "+path
                                    
                        if "outlinks" in items:
                            for s in items["outlinks"]:
                                if s in links:
                                    outLinks.append(links[s])
                                else:
                                    print "missing link of name: "+s+" in file: "+path
                        
                        dataDict={}
                        if "data" in items:
                            dataDict=_parseInfoLines(items["data"],path)
                        
                        if type in nodeTypes:
                            nodes.append(nodeTypes[type].getNode(stage,inLinks,outLinks,dataDict))
                        else:
                            print "using non existant nodeTypes of name: "+type+" in file: "+path
            
            extraKeys=set(d.keys())-set(["link","node"])
            if extraKeys:
                print "Warning: throwing away invalid majorSections with unrecognized names: "+str(extraKeys)+" in file: "+currentFile
        
        return nodes
    
    def saveGraph(self,nodes,path):
        
        # get all links
        links=set()
        for n in nodes:
            links.update(n.getOutLinks())
            links.update(n.getInLinks())
        
        # force all links to have unique names
        linkNamer=AutoNamer("link")
        for n in links:
            linkNamer.addItem(n)
                
        
        
        
        f = open(path, 'w')
        f.write("# Graph file for shader generator #\n")
        
        linkDict=linkNamer.getItems()
        for link,name in linkDict.iteritems():
            f.write(":: link\n")
            f.write(": info\n")
            f.write("name "+name+"\n")
            f.write("type "+link.getType()+"\n")
        
        
        
        for n in nodes:
            f.write(":: node\n")
            f.write(": info\n")
            type=n.getType().getName()
            f.write("type "+type+"\n")
            f.write("stage "+n.getStage()+"\n")
            d=n.getDataDict()
            if d:
                f.write(": data\n")
                for key,value in d.iteritems():
                    f.write(key+" "+value+"\n")
            f.write(": outlinks\n")
            for link in n.getOutLinks():
                f.write(linkDict[link]+"\n")
            f.write(": inlinks\n")
            for link in n.getInLinks():
                f.write(linkDict[link]+"\n")
            
        f.close()
    
    def makeBuilder(self,nodes):
        return ShaderBuilder(nodes,self.libSource)
        
    def loadGraph(self,path):
        nodes=self.parseGraph(path)
        return self.makeBuilder(nodes)
    



    


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
        
        inputs=node.getShaderInputs()
        outputs=node.getShaderOutputs()
        self.inputs.update(inputs)
        self.outputs.update(outputs)
        
        inLinks=node.getInLinks()
        outLinks=node.getOutLinks()
        
        for link in itertools.chain(inLinks,outLinks):
            self._addLink(link)
            
        ld=self.links.getItems()
        
        
        fname=functionNamer.nextName()

        f="void "+fname+node.getCode()
        if debugText:f="//"+str(node)+'\n'+f
        functionNamer.addItem(f)
        
        
        paramChain=itertools.chain(
            (s.getName() for s in inputs),
            (s.getName() for s in outputs),
            (ld[s] for s in itertools.chain(inLinks,outLinks)),
            )
        
        
        
        callSource=fname+"("+",".join(paramChain)+");"
        self.sourceLines.append(callSource)
        
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

    

class ShaderBuilder(object):
    """
    
    A factory for shaders based off a set of Nodes. Make one instance for each distinct set of Nodes.
    
    """
    def __init__(self,nodes,libSource=""):
        """
        
        Takes an iterable of Nodes, and sets this instance up to produce shaders based on them.
        
        """
        nodeSet=set()
        for n in nodes: nodeSet.update(n.getType().prepNode(n))
            
        nodes=nodeSet
        
        # a cache of finished shaders. Maps RenderState to Shader
        self.cache={}
        
        # a cache of finished shaders. Maps set of needed ActiveNodes to Shader
        self.casheByNodes={}
        
        self.header="//Cg\n//AUTO-GENERATED-SHADER//\n\n"+libSource+"\n\n"
        self.footer="\n\n//END-AUTO-GENERATED-SHADER//\n"
        
        # needed for generateing all shaders, so precomputed and stored.
        self.topNodes=set()
    
        self.linkToDst=collections.defaultdict(set)
        links=set() # just used for checking if links have multiple sources (aka invalid)
        
        
        
        for n in nodes:
            inLinks=n.getInLinks()
            for l in inLinks:
                self.linkToDst[l].add(n)
                
            outLinks=n.getOutLinks()
            for l in outLinks:
                if l in links: print "Error: Multisourced link"
                links.add(l)
                
            if not inLinks:
                self.topNodes.add(n)
                
        
        # make a pass to verify that all links have a source
        for s in self.linkToDst.values():
            if not s-links:
                print "Error: unsourced link"
        
        # detect cycles
        
        toProcess=set(self.topNodes)
        processed=set()
        processedLinks=set()
        self.sortedNodes=[]
        
        # process from top down (topological sort), cycles will get skipped, which we use to detect them
        while toProcess:
            n=toProcess.pop()
            processed.add(n)
            self.sortedNodes.append(n)
            
            outLinks=n.getOutLinks()
            processedLinks.update(outLinks)

            for link in outLinks:
                for dst in self.linkToDst[link]:
                    if dst.getStage()!=n.getStage():
                        print "Error: mismatched stages in dependant nodes: "+repr(n)+repr(dst)
                    inLinks=set(dst.getInLinks())
                    if not inLinks-processedLinks: # if processed all incomming links
                        toProcess.add(dst)
        
        cycleNodes=nodes-processed
        if cycleNodes:
            print "Error: cycles containing these nodes: "+str(cycleNodes)
        
    
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

        # process from top down (topological sorted order) to see what part of graph is active, and produce active graph
        # nodes are only processed when all nodes above them have been processed.
        
        activeOutputs=set() # set of activeNodes that are needed because they produce output values
        
        # linksStatus defaults to false for all links
        linkStatus=collections.defaultdict(lambda:False)
        linkToSource={}
        
        sortedActive=[]
        
        for n in self.sortedNodes:
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


        # check casheByNodes.
        # Many different RenderStates may produce the same ActiveNode graph, so this second cache is useful.
        neededSet=frozenset(neededNodes)
        shader=self.casheByNodes.get(neededSet)
        if shader and not noChache:
            self.cache[renderState]=shader
            if debugFile: print "Shader is cached (neededSet cache). Skipping generating shader to: "+debugFile
            return shader
          
        # no shader cached, so produce the source and shader
        
        stages=collections.defaultdict(StageBuilder)
        functions=AutoNamer("__f")
        
        for n in neededNodes:
            # process n
            s=stages[n.getStage()]
            s.addNode(n,functions)
        
        
        # TODO : Auto generate/match unspecified semantics here
        
        
        funcs="\n\n".join(functions.getItems())
        stageCode="\n\n".join(stage.generateSource(name) for name,stage in stages.iteritems())
        
        
        source = self.header+funcs+"\n\n"+stageCode+self.footer
        
        
        
        
        if debugFile:
            debugFile+=str(len(self.casheByNodes))+".sha"
            print 'Making Shader: '+debugFile
            
        
        if debugFile:
            fOut=open(debugFile, 'w')
            fOut.write(source)
            fOut.close()
        
        shader=Shader.make(source)
        self.cache[renderState]=shader
        self.casheByNodes[neededSet]=shader
        return shader
            