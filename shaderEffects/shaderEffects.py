"""
Builds shader source strings

Process:
Create ShaderEffect instances
use makeSource to inject ShaderEffects into a base shader file

"""



"""

Todo:
vshader out -> fshader in should be considered somehow
LOD/fallback (Shaders with multiple sources/different spots foe sub effects to be placed or not)

Handel multiple application of an effect (Effect specifies action, mulltiple application, error, single application)
    Also, multiple application of an effect using different inputs. Generally, named inputs support+multiple application support
        goood for lights (light1, light2 etc)
        and other things (wind1, wind2, what ever)


"""

shaderParamPlaces=('vshaderparams','fshaderparams')

def _mergeShaderParams(params):
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

def _injectEffectCalls(source,shaderEffects):
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

def makeSource(shaderEffects, baseShader):
    methodsSource='\n'.join([s.methodSource for s in shaderEffects])
    
    source=baseShader
    
    source=source.replace('//<__methods__>//',methodsSource)
    
    
    source=_injectEffectCalls(source,shaderEffects)
    shaderParams=[]
    
    for s in shaderEffects:
        shaderParams.extend(s.shaderParams)
    
    
    shaderParamsDefsCode=dict([(p,[]) for p in shaderParamPlaces])
    
      
    shaderParams=_mergeShaderParams(shaderParams)
    
    for s in shaderParams:
        shaderParamsDefsCode[s.place].append(s.defCode())
    
    for s in shaderParamPlaces:
        source=source.replace('//<__'+s+'__>//',',\n'.join(shaderParamsDefsCode[s]))
    
    return source
    
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

            source=_injectEffectCalls(self.source,effects)
            
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

        
class ShaderParam:
    """
    This is a param for the shader itself, not a param for an effect.
    It it used for gettting shaderInputs avaliable shaderside, as well as
    exposing special things like mat_modelproj and vtx_position
    
    This is also used for shader outputs, like the final color, transformed vertex position,
    and passing stuff from vshader to fshader
    """
    def __init__(self,place,name,type,xin,out,semantic=None,shaderInput=None):
        """
        type=ex: "float4" or "uniform float4x4"
        xin=boolean for input or not 
        out=boolean for output or not
        shaderInput=ShaderInput object, optional. This would usally be a default value if provided
        place=placement spot. Usally fshaderParams of vshaderParams, string
        semantic=string after : such as POSITION
        
        
        to build from a string see staticmethod fromDefCode
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
        """
        example usage:
        shaderParam=ShaderParam.fromDefCode("vshaderparams","in uniform sampler2D k_grassData: TEXUNIT0")
        """
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
        """
        Combines self and other if compatable into a single ShaderParam that is returned.
        None returned if incompatable
        Used for merging things that are equivelent, merging in and out to inout, and/or merging no semantic with one with a semantic specified
        mainly used to try and resolve name comflicts for params, and cause an error if they conflict
        """
        
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