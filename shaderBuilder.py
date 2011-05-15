import collections
import itertools
import os
import os.path

from panda3d.core import Shader


join=os.path.join




class NodeType(object):
    """
    
    each instance represents a node type defined in a library
    
    """
    def __init__(self,name,shaderInputs=[],shaderOutputs=[],inLinks=[],outLinks=[],code=""):
        self.name=name
        self.shaderInputs=shaderInputs
        self.shaderOutputs=shaderOutputs
        self.inLinks=inLinks
        self.outLinks=outLinks
        
        self.makeFullCode(code)
        
    def makeFullCode(self,code):
        """
        
        the code needed to construct Nodes includes the (paramList){code} wrapping stuff, so this addes it
        and saves it to self.code
        
        """
        
        fparamChain=itertools.chain(
             ("in "+s.getType()+" "+s.getName() for s in self.shaderInputs),
             ("out "+s.getType()+" "+s.getName() for s in self.shaderOutputs),
             ("in "+s.getType()+" "+s.getName() for s in self.inLinks),
             ("out "+s.getType()+" "+s.getName() for s in self.outLinks),
             )

        self.code="("+",".join(fparamChain)+"){\n"+code+"\n}"
    
    def getName(self): return self.name
    
    def getNode(self,stage,inLinks,outLinks,dataDict=None):
        if len(inLinks)!=len(self.inLinks):
            print "Error: number of inputs does not match node type. Inputs: "+str(inLinks)+" expected: "+str(self.inLinks)
            return None
        if len(outLinks)!=len(self.outLinks):
            print "Error: number of outLinks does not match node type. Outputs: "+str(outLinks)+" expected: "+str(self.outLinks)
            return None
        for x in xrange(len(inLinks)):
            t1=self.inLinks[x].getType()
            t0=inLinks[x].getType()
            if t0!=t1:
                print "Error: mismatched type on inLinks. Got: "+t1+" expected: "+t0
        for x in xrange(len(outLinks)):
            t1=self.outLinks[x].getType()
            t0=outLinks[x].getType()
            if t0!=t1:
                print "Error: mismatched type on outlink. Got: "+t1+" expected: "+t0
                
        return Node(self,stage,inLinks,outLinks,dataDict)
    
    def getActiveNode(self,node,renderState,linkStatus):
        """
        
        override this method to make custom types of nodes that vary based on renderState and linkStatus
        
        """
        return ActiveNode(node.stage,tuple(self.shaderInputs),tuple(self.shaderOutputs),tuple(node.inLinks),tuple(node.outLinks),self.code)

    def __repr__(self):
        return "NodeType"+str(tuple([self.name,self.shaderInputs,self.shaderOutputs,self.inLinks,self.outLinks,self.code]))

class Node(object):
    """
    
    A shader node. They can be connected to others using Links to form a graph.
    
    Specifically, the nodes and links form a cycle free directed multigraph, with data on both the edges and nodes.
    
    """
    def __init__(self,nodeType,stage,inLinks=None,outLinks=None,dataDict=None):
        self.nodeType=nodeType
        self.stage=stage
        self.inLinks=inLinks if inLinks else []
        self.outLinks=outLinks if outLinks else []
        self.dataDict=dataDict if dataDict else {}
    def getType(self): return self.nodeType
    def getStage(self): return self.stage
    def getInLinks(self): return self.inLinks
    def getOutLinks(self): return self.outLinks
    def getDataDict(self): return self.dataDict
    def getActiveNode(self,renderState,linkStatus): return self.nodeType.getActiveNode(self,renderState,linkStatus)
    def __repr__(self):
        return "Node"+str(tuple([self.stage,self.inLinks,self.outLinks]))

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
    def __init__(self,stage,shaderInputs,shaderOutputs,inLinks,outLinks,code):
        self.stage=stage
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
    def getStage(self): return self.stage
    def __repr__(self):
        return "ActiveNode"+str(tuple([self.stage,self.shaderInputs,self.shaderOutputs,self.inLinks,self.outLinks,"<code>"]))

        
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
        s=line.split()
        if len(s)!=2:
            print "invalid info entry '"+line+"' in: "+currentFile
        else:
            info[s[0]]=s[1]
    return info
    


class Library(object):
    def __init__(self,path,nodeTypeClassMap={}):
        """
    
        path should be a path to a library folder
        
        builds an instance made from the contents of the passed folder path.
        
        
        nodeTypeClassMap should be a dict mapping strings to NodeType subclasses.
        The strings should correspond to the "class" info field used in the nodes in the library.
        no "class" info (a None in the dictionary) maps to NodeType, not a subclass.
        
        
        """
        
        
        self.nodeTypeClassMap={None:NodeType}
        self.nodeTypeClassMap.update(nodeTypeClassMap)
        self.loadPath(path)
        
    def loadPath(self,path):
        """
        
        called by init, but can be called again if you wish to reload the same path, or a different one
        
        """
        
        
        nodes={}
        libs=[]
        
        for root, dirs, files in os.walk(path):
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
                                                shaderInputs.append(shaderParamFromDefCode(s))
                                        shaderOutputs=[]
                                        if "shaderoutputs" in items:
                                            for s in items["shaderoutputs"]:
                                                shaderOutputs.append(shaderParamFromDefCode(s))
                                        
                                        inLinks=[]
                                        if "inlinks" in items:
                                            for s in items["inlinks"]:
                                                inLinks.append(linkEndFromDefCode(s))
                                        outLinks=[]
                                        if "outlinks" in items:
                                            for s in items["outlinks"]:
                                                outLinks.append(linkEndFromDefCode(s))
                                        
                                        
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
                    print "invalid info entry missing type in: "+path
                else:
                    type=info["type"]
                    if "stage" not in info:
                        print "invalid info entry missing stage in: "+path
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
                            dataDict=_parseInfoLines(items["data"],currentFile)
                        
                        nodes.append(nodeTypes[type].getNode(stage,inLinks,outLinks,dataDict))
            
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
        return makeBuilder(nodes)
    


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
    def __repr__(self): return "Param("+self.name+", "+self.type+")"

class ShaderParam(Param):
    def __init__(self,name,type,semantic=None):
        Param.__init__(self,name,type)
        self.semantic=semantic
    def getSemantic(self): return self.semantic
    def getDefCode(self): return self.type+" "+self.name+((" : "+self.semantic) if self.semantic else "")
    
    
class ShaderInput(ShaderParam): pass
class ShaderOutput(ShaderParam): pass

    


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
        linkDeclarations='\n'.join(link.getType()+" "+name+";" for link,name in self.links.getItems().iteritems())
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
        
        nodes=set(nodes)
        
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
            if debugFile: print "Shader is cached. Skipping generating shader to: "+debugFile
            return shader
        

        # process from top down (topological sorted order) to see what part of graph is active, and produce active graph
        # nodes are only processed when all nodes above them have been processed.
        
        activeOutputs=set() # set of activeNodes that might be needed
        activeOutLinks=set()
        
        linkStatus={}
        linkToSource={}
        
        sortedActive=[]
        
        for n in self.sortedNodes:
            a=n.getActiveNode(renderState,linkStatus)
            sortedActive.append(a)
            activeOutLinks.update(a.getOutLinks())
            outLinks=a.getOutLinks()
            for link in outLinks:
                linkStatus[link]= link in activeOutLinks
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
            if debugFile: print "Shader is cached. Skipping generating shader to: "+debugFile
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
            print 'Making Shader: '+debugFile
            
        
        if debugFile:
            fOut=open(debugFile, 'w')
            fOut.write(source)
            fOut.close()
        
        shader=Shader.make(source)
        self.cache[renderState]=shader
        self.casheByNodes[neededSet]=shader
        return shader
            