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
    def __init__(self,shaderInputs=[],shaderOutputs=[],inLinks=[],outLinks=[],code=""):
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
        
    def getNode(self,stage,inLinks=[],outLinks=[]):
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
                
        return Node(stage,self.shaderInputs,self.shaderOutputs,inLinks,outLinks,self.code)

    def __repr__(self):
        return "NodeType"+str(tuple([self.shaderInputs,self.shaderOutputs,self.inLinks,self.outLinks,self.code]))



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
                                        
                                        node=nclass(shaderInputs,shaderOutputs,inLinks,outLinks,code)
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
    


    def loadGraph(self,path):
        """
        
        path should be a path to a graph text file
        
        """
        
        nodeTypes=self.nodes
        libSource=self.libSource
        
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
                        
                        nodes.append(nodeTypes[type].getNode(stage,inLinks,outLinks))
            
            extraKeys=set(d.keys())-set(["link","node"])
            if extraKeys:
                print "Warning: throwing away invalid majorSections with unrecognized names: "+str(extraKeys)+" in file: "+currentFile
        
        return ShaderBuilder(nodes,libSource)
    


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
    
class Node(object):
    """
    
    A shader node. They can be connected to others using Links to form a graph.
    
    Specifically, the nodes and links form a cycle free directed multigraph, with data on both the edges and nodes.
    
    """
    def __init__(self,stage,shaderInputs=None,shaderOutputs=None,inLinks=None,outLinks=None,code=""):
        self.stage=stage
        self.shaderInputs=shaderInputs if shaderInputs else []
        self.shaderOutputs=shaderOutputs if shaderOutputs else []
        self.inLinks=inLinks if inLinks else []
        self.outLinks=outLinks if outLinks else []
        self.code=code
    def getStage(self): return self.stage
    def getInLinks(self): return self.inLinks
    def getOutLinks(self): return self.outLinks
    def getActiveNode(self,renderState,linkStatus):
        """
        
        override this method to make custom types of nodes that vary based on renderState and linkStatus
        
        """
        return ActiveNode(self.stage,tuple(self.shaderInputs),tuple(self.shaderOutputs),tuple(self.inLinks),tuple(self.outLinks),self.code)

    def __repr__(self):
        return "Node"+str(tuple([self.stage,self.shaderInputs,self.shaderOutputs,self.inLinks,self.outLinks,"<code>"]))


        
class Link(object):
    """
    
    An output from a shader Node, and possibly multiple inputs to multiple shader nodes.
    
    As it can be multiple inputs, links are sets of edges in the graph from one node to multiple others.
    
    """
    def __init__(self,dataType,name="<Unnamed>"):
        self.dataType=dataType
        self.name=name
    def getType(self): return self.dataType
    def __repr__(self):
        return "Link"+str(tuple([self.dataType,self.name]))

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
        
        while toProcess:
            n=toProcess.pop()
            processed.add(n)
            
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
        
        """
        
        shader=self.cache.get(renderState)
        if shader and not noChache:
            print "Shader is cached. Skipping generating shader to: "+debugFile
            return shader
        

        # process from top down to see what part of graph is active, and produce active graph
        # nodes are only processed when all nodes above them have been processed.
        # which will then be processed bottom up to generate shader
        
        activeOutputs=set() # set of activeNodes that might be needed
        activeOutLinks=set()
        
        linkStatus={}
        linkToSource={}
        
        toProcess=set(self.topNodes)
        
        
        while toProcess:
            n=toProcess.pop()
            
            
            a=n.getActiveNode(renderState,linkStatus)
            activeOutLinks.update(a.getOutLinks())
            outLinks=a.getOutLinks()
            for link in outLinks:
                linkStatus[link]= link in activeOutLinks
                linkToSource[link]=a
                    
            for link in outLinks:
                for dst in self.linkToDst[link]:
                    inLinks=dst.getInLinks()
                    for l in inLinks:
                        if l not in linkStatus: break
                    else:
                        toProcess.add(dst)
            
            if a.isOutPut():
                activeOutputs.add(a)
        
        
        
        
        # scan of active nodes to find bottoms that are needed for activeOutputs
        # walk upward from all activeOutputs marking visited nodes
        # and removing any activeOutputs hit from set of bottomActiveOutputs as they will be generated
        # as a result of others
        bottomActiveOutputs=set(activeOutputs)
        visited=set()
        toVisit=set(activeOutputs)
        linkToActiveDst=collections.defaultdict(set)
        
        while toVisit:
            n=toVisit.pop()
            if n not in visited:
                visited.add(n)
                inLinks=n.getInLinks()
                for link in inLinks:
                    linkToActiveDst[link].add(n)
                    a=linkToSource[link]
                    if a not in visited:
                        bottomActiveOutputs.discard(a)
                        toVisit.add(a)
                        
        
        # some sanity checks
        for link,dsts in linkToActiveDst.iteritems():
            for dst in dsts:
                assert link in dst.getInLinks()
        
        for link,source in linkToSource.iteritems():
            assert link in source.getOutLinks()
            
            
        
        # generate shader upwards from bottomActiveOutputs
        # this will generate the minimal part of the graph needed to provide the inputs
        
        toProcess=set(bottomActiveOutputs)
        neededNodes=[] # nodes needed from bottom up. The reverse of this is an ok order to compute them in.
        processed=set()
        
        while toProcess:
            n=toProcess.pop()
            neededNodes.append(n)
            #print neededNodes
            processed.add(n)
            
            # see if nodes providing input should be processed yet
            inLinks=n.getInLinks()
            for inLink in inLinks: # for all inputs to n
                source=linkToSource[inLink]
                assert source not in processed
                assert source not in toProcess
                outLinks=source.getOutLinks()
                # check if all uses of outputs of source are already processed
                sourceReady=True
                for link in outLinks:
                    if not sourceReady: break
                    for dst in linkToActiveDst[link]:
                        if dst not in processed:
                            sourceReady=False
                            break
                if sourceReady: # if all outputs already processed, process it
                    toProcess.add(source)
        
        
        # check casheByNodes.
        # Many different RenderStates may produce the same ActiveNode graph, so this second cache is useful.
        neededSet=frozenset(neededNodes)
        shader=self.casheByNodes.get(neededSet)
        if shader and not noChache:
            print "Shader is cached. Skipping generating shader to: "+debugFile
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
            