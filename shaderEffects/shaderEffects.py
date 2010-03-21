"""

Todo:
vshader out -> fshader in should be considered somehow
LOD/fallback (Shaders with multiple sources/different spots foe sub effects to be placed or not)

Handel multiple application of an effect (Effect specifies action, mulltiple application, error, single application)
    Also, multiple application of an effect using different inputs. Generally, named inputs support+multiple application support
        goood for lights (light1, light2 etc)
        and other things (wind1, wind2, what ever)


"""

from pandac.PandaModules import *


# Makes debugging shaders easier
useShaderFiles=True

def pathPrefix():    
    if base.appRunner!=None:
        return base.appRunner.multifileRoot+'/'
    else:
        return ''


def readFile(path):
    return open(pathPrefix()+path, 'r')
    
def parseFile(path):
    """
    
    Read sections headed by :SectionName into lists by section name in a dictionary
    blank lines, line preceeding and ending whitespace and #Comments are stripped
    
    """
    
    d={}
    currentList=None
    
    f = readFile(path)
    for t in f.readlines(): 
        # Remove comments
        i=t.find('#')
        if i!=-1: t=t[:i]
        
        # Strip excess whitespace
        t=t.strip()
        
        
        if len(t)>0:
            # Process line
            
            if t[0]==':':
                # if section header, prefixed with :
                currentList=[]
                d[t[1:].lower()]=currentList
            else:
                if currentList!=None:
                    currentList.append(t)
    return d

shaderParamPlaces=('vshaderparams','fshaderparams')


def mergeShaderParams(params):
    d={}
    for p in params:
        key=(p.name,p.place)
        if key in d:
            m=d[key].merge(p)
            if m==None:
                print 'Error: Incompatable shaderParams for '+key
            else:
                d[key]=m
        else:
            d[key]=p
    return d.values()

def injectEffectCalls(source,shaderEffects):
    """
    
    Injects the calls to the effects at the relevent locations in source
    
    """
     # dict of lists of callSources keyed by placment spot
    shadersPlacementLists={}
    
    shaderParams=[]
    
    for s in shaderEffects:
        c=shadersPlacementLists.get(s.applySpotName,[])
        c.append(s.callSource)
        shadersPlacementLists[s.applySpotName]=c
    
    for s in shadersPlacementLists:
        calls=shadersPlacementLists[s]
        source=source.replace('//<'+s+'>//','\n'.join(calls))
    
    return source
    
def makeShader(shaderEffects, baseShader):
    """
    
    Generates shader source from effects and converts it into a Panda3D shader object
    baseShader is source to inject effects into
    
    """

    if useShaderFiles:
        name='debug('+','.join([e.name for e in shaderEffects])+')'
        outLoc='ShadersOut/'+name+'.sha'
        print 'Making Shader: '+outLoc
    
    methodsSource='\n'.join([s.methodSource for s in shaderEffects])
    
    source=baseShader
    
    source=source.replace('//<__methods__>//',methodsSource)
    
    
    source=injectEffectCalls(source,shaderEffects)
    shaderParams=[]
    
    for s in shaderEffects:
        shaderParams.extend(s.shaderParams)
    
    
    shaderParamsDefsCode=dict([(p,[]) for p in shaderParamPlaces])
    
      
    shaderParams=mergeShaderParams(shaderParams)
    
    for s in shaderParams:
        shaderParamsDefsCode[s.place].append(s.defCode())
    
    for s in shaderParamPlaces:
        source=source.replace('//<__'+s+'__>//',',\n'.join(shaderParamsDefsCode[s]))
    
    
    if useShaderFiles:
        fOut=open(outLoc, 'w')
        fOut.write(source)
        fOut.close()
           
    shader=Shader.make(source)
        
    return shader

# Shader cache for getShader
builtEffectsShaders={}

def getShader(shaderEffects, baseShader):
    """
    
    Cashes shaders from makeShader to avoid regeneration or multiple identicle shaders
    
    """
    key=(tuple(shaderEffects), baseShader)
    if key not in builtEffectsShaders:
        builtEffectsShaders[key]=makeShader(shaderEffects, baseShader)
        
    return builtEffectsShaders[key]

def applyEffects(shaderEffects, targetNodePath, baseShader):
    """
    Applies the effects to the passed nodepath
    shaderEffects=list of ShaderEffect objects, orderd by application order
    targetNodePath=Nodepath to apply to
    
    baseShader=source to inject effects into
    """
    
    targetNodePath.setShader(getShader(shaderEffects, baseShader))
    
    
    
class ShaderEffect:
    """
    
    Will eventually be a RenderAttrib (maybe)
    
    
    """
    def __init__(self, name, applySpotName, source, params, extraMethodsSource=""):
        """
        name describes the effect. It is not important for correct operation other than it must
        be valid text to place in a shader, and must be unique
        
        applySpotName=token for insertion location in base shader
        source=shader source code
        params=list of ShaderEffectParam objects passed to method wraping source in final shader code
        
        currently assumes one instance of applySpotName
        eventually effects may be able to be applied to all instances of applySpotName
        but also applied to other effects, so the effect would only apply to
        instances of applySpotName withing the parent effect(s) and possibly its children.

        """
        self.name=name
        self.applySpotName=applySpotName
        
        # Make a method name that should be pretty sure not to conflict with anything in the shader
        methodName='_Effect_'+name+'_'
        
        self.callSource=methodName+'('+', '.join([p.evaluationCode for p in params])+');'
        self.methodSource='void '+methodName+'('+', '.join([p.defCode for p in params])+'){\n'+source+'\n}'
        
        self.methodSource=extraMethodsSource+'\n'+self.methodSource
        
        self.source=source
        
        self.params=params

        
        self.shaderParams=[]
        for p in params:
            if p.shaderParam!=None: self.shaderParams.append(p.shaderParam)
        
        
        ShaderEffect.applySubEffectsCache={}
        
    def __str__(self):
        return self.name
        
    def applySubEffects(self,effects):
        """Returns a new ShaderEffect with sub effects applied"""
        key=tuple(effects)
        if key not in ShaderEffect.applySubEffectsCache:

            source=injectEffectCalls(self.source,effects)
            
            extraMethodsSource='\n'.join([s.methodSource for s in effects])
            
            # Collect all needed shaderParams (Shader input requirements)
            params=list(self.params)
            for s in effects:
                for p in s.params:
                    if p.shaderParam!=None:
                        params.append(p)
                #params.extend(s.shaderParams)
                    
            #shaderParams=mergeShaderParams(shaderParams)
            
            name=self.name+"__"+"_".join([s.name for s in effects])
            newEffect=ShaderEffect(name,self.applySpotName,source,params,extraMethodsSource)
            
            ShaderEffect.applySubEffectsCache[key]=newEffect
            
        return ShaderEffect.applySubEffectsCache[key]


def loadEffectFromFile(path,name):
    """
    Build effect from an effects file
    path should be containing folder
    name is filename without '.txt'
    
    """
    path=path+'/'+name+'.txt'
    d=parseFile(path)

    if 'info' in d and 'shader' in d:
        if 'params' not in d: d['params']=[]
        
        source='\n'.join(d['shader'])
        params=[ShaderEffectParam(t) for t in d['params']]
        info=dict([t.split() for t in d['info']])
        if 'place' not in info:
            print 'error: place not specified in effects file '+path
            return
        
        
        
        shaderParams=[]
        
        for p in shaderParamPlaces:
            if p in d:
                for s in d[p]:  
                    shaderParams.append(ShaderParam.fromDefCode(p,s))
        
        paramNames=set([p.name for p in params])
        for p in shaderParams:
            if p.name in paramNames:
                print "error: conflicting param and shaderParam "+p.name+" in "+path
            else:
                paramNames.add(p.name)
                params.append(p.makeShaderEffectParam())
        
                
        return ShaderEffect(name, info['place'], source, params)
        
    else:
        print 'error: one of the required sections is missing from effects file at '+path
    
        
class ShaderParam:
    def __init__(self,place,name,type,xin,out,semantic=None,shaderInput=None):
        """
        This is a param for the shader itself, not an effect.
        It it used for gettting shaderInputs avaliable shaderside, as well as
        exposing special things like mat_modelproj and vtx_position
        
        This is also used for shader outputs, like the final color, transformed vertex position,
        and passing stuff from vshader to fshader
        
        type=ex: "float4" or "uniform float4x4"
        xin=boolean for input or not 
        out=boolean for output or not
        shaderInput=ShaderInput object, optional. This would usally be a default value if provided
        place=placement spot. Usally fshaderParams of vshaderParams, string
        semantic=string after : such as POSITION
        
        """
        
        if not (xin or out): print 'Error, ShaderParam '+name+' is not in or out'
        
        
        self.name=name
        self.place=place
        self.type=type
        self.xin=xin
        self.out=out
        self.shaderInput=shaderInput
        self.semantic=semantic
        
    def makeShaderEffectParam(self):
        return ShaderEffectParam(self.defCode(True),self)
    
    @staticmethod
    def fromDefCode(place,defCode):
        i=defCode.find(':')
        if i==-1:
            semantic=None
            t=defCode.split()
        else:
            semantic=defCode[i+1:].strip()
            t=defCode[:i].split()
        shaderParamName=t[-1]
        out=xin=t[0]=='inout'
        out|=t[0]=='out'
        xin|=t[0]=='in'
        type=' '.join(t[1:-1])
        
        return ShaderParam(place,shaderParamName,type,xin,out,semantic=semantic)
    
    
    def merge(self,other):
        """ Combines self and other if compatable into a single ShaderParam that is returned.
        None returned if incompatable"""
        
        if self.name!=other.name or self.type!=other.type or self.shaderInput!=other.shaderInput or (self.semantic!=None and other.semantic!=None and self.semantic!=other.semantic):
            return None
        
        return ShaderParam(self.place,self.name,self.type,self.xin or other.xin, self.out or other.out, self.shaderInput)
    
    
    def defCode(self,skipSemantic=False):
        return ('in' if self.xin else '')+('out ' if self.out else ' ')+self.type+' '+self.name+(' : '+self.semantic if self.semantic and not skipSemantic else '')

class ShaderEffectParam:
    def __init__(self,defCode,shaderParam=None):
        """
        defCode=code in method def, ex: "inout float4 o_color"
        shaderParam=ShaderParam object, optional
        """
        
        #evaluationCode=shader code placed in ShaderEffect's wraper method call to compute the value to be passed
        self.evaluationCode=defCode.split()[-1]

        
        self.name=self.evaluationCode
        
        self.defCode=defCode
        self.shaderParam=shaderParam


def applyShaderEffectPlacements(baseNode,ShaderEffectPlacements,baseShader,effectLs=False):

    
    # nodeDict will store (node:[ShaderEffect list])
    nodeDict={}
    
    # Used to build nodeDict
    def traverseTree(currentNode,shaderEffectPlacement):
        def makeEffect(placement):
            if placement.appliesTo(currentNode):
                subEffects=[]
                for s in placement.subEffects:
                    subEffect=makeEffect(s)
                    if subEffect:
                        subEffects.append(subEffect)
                if subEffects:
                    return placement.shaderEffect.applySubEffects(subEffects)
                else:
                    return placement.shaderEffect
            return None
            
        effect=makeEffect(shaderEffectPlacement)
        
        if effect:
            effects=nodeDict.get(currentNode,[])
            effects.append(effect)
            nodeDict[currentNode]=effects
        for i in xrange(currentNode.getNumChildren()):
            traverseTree(currentNode.getChild(i),shaderEffectPlacement)
    
    # Build nodeDict
    for p in ShaderEffectPlacements:
        traverseTree(baseNode,p)
    
    
    def applyToTree(currentNode,parentShader):
        if effectLs:
            print "    "*currentNode.getNumNodes()+currentNode.getName()+": "+", ".join([e.name for e in nodeDict.get(currentNode,[])])
        effectHolderList=nodeDict.get(currentNode,[])
        shader=getShader(effectHolderList,baseShader)
        if shader is not parentShader:
            currentNode.setShader(shader)
        for i in xrange(currentNode.getNumChildren()):
            applyToTree(currentNode.getChild(i),shader)
            
    applyToTree(baseNode,None)


