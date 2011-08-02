import collections
import itertools

"""

This module contains the basic NodeType implementation, including the classes it instances

"""

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
            print "Error: making node of type "+self.name+", number of outLinks does not match node type. Outputs: "+str(outLinks)+" expected: "+str(self.outLinks)
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
    
    def prepNode(self,node):
        """
        returns a set of nodes to replace the passed node with for the final ShaderBuilder stage
        usally this just returns the origional node in a singleton set, but for composite nodes,
        this is where they expand themselves to all of their contained nodes
        
        getActiveNode will only be called on nodes after they have been preped, so perhaps this design is a bit of a hack.
        Maybe using another class for preped nodes would be better, but that would require another NodeType like class, and add lots of complexity
        This is used to keep the process very simple, and will prabably only be needed for composite nodes.
        """
        return set([node])
        
    def getActiveNode(self,node,renderState,linkStatus):
        """
        
        override this method to make custom types of nodes that vary based on renderState and linkStatus
        
        returns an ActiveNode for this context,
        or returns None if the Node has not active outputs and should not generate any code
        
        linkStatus for each link defaults to False. This method must add an entry in linkStatus
        for each entry in node.outLinks that should be non False
        
        There is an entry in linkStatus for each entry in node.inLinks (unless left at the default False by its source)
        
        the interpretation of the values in linkStatus is only done by this method, but it is commonly overwritten.
        Convention is that True means active, and False values mean inactive. Subclasses may use custon link types that
        do not translate to passed paramaters (meaning not made as links on the activeNodes), but contain other data.
        linkStatus can potentially be used to pass any generation time information through the graph
        such as constants, LODs etc.
        
        deafult (implemented here) is that if all inputs are Active (Truthy), genrate node, else no active outputs
        and return None.
        
        """
        if all(linkStatus[link] for link in node.inLinks):
            for link in node.outLinks: linkStatus[link] = True
            return ActiveNode(node.stage,tuple(self.shaderInputs),tuple(self.shaderOutputs),tuple(node.inLinks),tuple(node.outLinks),self.code)
        else:
            return None
    
    def setupRenderStateFactory(self,node,renderStateFactory):
        """
        
        regester all renderState values that need to be recorded from nodes for this NodeType
        
        this basic NodeType does not look at the RenderState, so nothing needs to be regestered
        
        """
        pass
    
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
    def setupRenderStateFactory(self,renderStateFactory): return self.nodeType.setupRenderStateFactory(self,renderStateFactory)
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
 