import nodes
import param

import itertools

"""

This module contains default subclasses of nodes.NodeType.

These calsses are not part of the core implementation, they are content, and the set of classes here
is intented to be user extended. See nodes for the documentation needed to write classes like these.

The basic nodes.NodeType has no conditional logic, so it alone is not very useful. Alone it only
produces graphs that alwayse generate the same shader, regardless of input renderState. These classes
provide conditional functionality.

"""

class ActiveNodeCacheNode(nodes.Node):
    """
    A node that stores custom code
    """
    def __init__(self,activeNode,*args,**kargs):
        nodes.Node.__init__(self,*args,**kargs)
        self.activeNode=activeNode

class CodeCacheNode(nodes.Node):
    """
    A node that stores custom code
    """
    def __init__(self,code,*args,**kargs):
        nodes.Node.__init__(self,*args,**kargs)
        self.code=code


class ConditionalInput(nodes.NodeType):
    """
    makes an active node that outputs the ConditionalInput shader input from the node's data dict
    or no active note if input is not available.
    """
    def makeFullCode(self,code):
        self.code="(in {type} input,out {type} ouput){ouput=input;}"
    
    def getNode(self,stage,inLinks,outLinks,dataDict=None):
        if len(inLinks)!=0:
            print "Error: number of inputs should be 0. Inputs: "+str(inLinks)
            return None
        if len(outLinks)!=1:
            print "Error: making node of type "+self.name+", number of outLinks shoule be 1. Outputs: "+str(outLinks)
            return None
        
        s=dataDict["ConditionalInput"]
        info=s.split()
        inputName=info[0]
        info[0]="k_"+info[0] # add prefix for shader input
        input=param.ShaderInput(*info)
        output=outLinks[0]
        assert output.getType()==input.getType()

        code=self.code.replace("{type}",output.getType())
        activeNode=nodes.ActiveNode(stage,(input,),(),(),(output,),code)
        return ActiveNodeCacheNode(activeNode,self,stage,inLinks,outLinks,dataDict)
    
    def getActiveNode(self,node,renderState,linkStatus):
        data=node.getDataDict()
        s=data["ConditionalInput"]
        info=s.split()
        inputName=info[0]
        if renderState.hasShaderInput(inputName):
            linkStatus[node.getOutLinks()[0]] = True
            return node.activeNode
        else:
            return None
            
    def setupRenderStateFactory(self,node,renderStateFactory):
        data=node.getDataDict()
        input=data["ConditionalInput"]
        renderStateFactory.shaderInputs.add(input.split()[0])


class FirstAvailable(nodes.NodeType):
    """
    takes a list of inlinks, and chooses the first active one to hook up to the output
    
    if none are active, output is inactive.
    """
    def makeFullCode(self,code):
        self.code="(in {type} input,out {type} ouput){ouput=input;}"
    
    def getNode(self,stage,inLinks,outLinks,dataDict=None):
        if len(outLinks)!=1:
            print "Error: making node of type "+self.name+", number of outLinks shoule be 1. Outputs: "+str(outLinks)
            return None
        
        t0=outLinks[0].getType()
        for x in xrange(len(inLinks)):
            t1=inLinks[x].getType()
            if t0!=t1:
                print "Error: mismatched type on inlink. Got: "+t1+" expected: "+t0
                return None
        
        code=self.code.replace("{type}",t0)        
        return CodeCacheNode(code,self,stage,inLinks,tuple(outLinks),dataDict)
    
    def getActiveNode(self,node,renderState,linkStatus):
        
        # since we don't have any shaderOutputs, might as well go inactive
        # if the result is unused rather than special case it
        if len(node.outLinks)==0: return None
        
        for input in node.getInLinks():
            if linkStatus[input]:
                output=node.outLinks[0]
                linkStatus[output] = True
                return nodes.ActiveNode(node.stage,(),(),(input,),node.outLinks,node.code)
        return None


defaultNodeTypeClassMap={None:nodes.NodeType,"ConditionalInput":ConditionalInput,"FirstAvailable":FirstAvailable}
