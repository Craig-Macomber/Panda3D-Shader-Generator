"""
Builds shader source strings

Process:
Create ShaderEffect instances
use makeSource to inject ShaderEffects into a base shader file

ToDo:
Handel multiple application of an effect (Effect specifies action, mulltiple application, error, single application)
    Also, multiple application of an effect using different inputs. Generally, named inputs support+multiple application support
        goood for lights (light1, light2 etc)
        and other things (wind1, wind2, whatever)
"""

import collections


# The simplest practical base shader
baseShader='''//Cg
// Auto Generated Shader //


//<__methods__>//

void vshader(
//<__vshaderparams__>//
)
{
//<vshader>//
}


void fshader( 
//<__fshaderparams__>//
) 
{ 
//<fshader>//
} 
'''


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
    shadersPlacementLists=collections.defaultdict(list)

    for s in shaderEffects:
        shadersPlacementLists[s.applySpotName].append(s.callSource)
        
    for s in shadersPlacementLists:
        calls=shadersPlacementLists[s]
        placeHolder='//<'+s+'>//'
        loc=source.find(placeHolder)
        if loc==-1:
            # not found
            print 'Error: placeHolder',placeHolder,'not found for placing ShaderEffect calls',str(calls)
        else:
            source=source.replace(placeHolder,'\n'.join(calls)+'\n'+placeHolder)
    return source

def makeSource(shaderEffects, baseShaderSource=None):
    shaderEffects=[s.flatten() for s in shaderEffects]
    
    methodsSource='\n'.join(s.methodSource for s in shaderEffects)
    
    source=baseShaderSource if baseShaderSource else baseShader
    
    source=source.replace('//<__methods__>//',methodsSource)
    
    
    source=_injectEffectCalls(source,shaderEffects)
    shaderParams=[]
    
    for s in shaderEffects:
        shaderParams.extend(s.shaderParams)
    
    shaderParams=_mergeShaderParams(shaderParams)
    
    # make sure everything mapped from out -->> in has a unique semantic
    # CG tends to do horrible things (mainly mixup shader inputs) semantics are not specified
    # Thus, we run this pass to go through all the semantics, and fix NAME_X ones into NAME0, NAME1 etc
    # and make sure all ShaderParams with the same name and same semantic name get the same number.
    # this should be unneccesary, but CG is not too smart. Doing this does gain us one feature however
    # it lets up control what in/out paramaters get mapped to what semantic NAME, and still
    # lets us set the number manually if wanted
    
    # already used semantic name strings
    semantics=set()
    
    # semantic name to list of shaderParams with it
    # entries in here need to have semantic numbers assigned
    needCustomSemantic=collections.defaultdict(list)
    for p in shaderParams:
        if p.semantic:
            if p.semantic.endswith('_X'):
                needCustomSemantic[p.semantic[:-2]].append(p)
            else:
                semantics.add(p.semantic)
    
    # needCustomSemantic is now filled, so go ahead and assign numbers
    # assign the new semantic string including the number to a copy of the semantic
    # this copying prevents us from unexpecdidly editing the passed in shaderParams
    for name,shaderParamList in needCustomSemantic.iteritems():
        nameToValue={}
        for s in shaderParamList:
            if s.name in nameToValue:
                value=nameToValue[s.name]
            else:
                value=0
                while name+str(value) in semantics:
                    value+=1
                nameToValue[s.name]=value
            shaderParams.remove(s)
            newS=s.copy()
            newS.semantic=name+str(value)
            semantics.add(newS.semantic)
            shaderParams.append(newS)
    
    # the whole semantics mess is now sorted out,
    # and the shaderParams are ready to be injected into the source
    # first we sort them by place in this dict
    shaderParamsDefsCode=collections.defaultdict(list)
    for s in shaderParams:
        shaderParamsDefsCode[s.place].append(s.defCode())
    
    # and finally inject the shaderParams into the source
    for s in shaderParamPlaces:
        source=source.replace('//<__'+s+'__>//',',\n'.join(shaderParamsDefsCode[s]))
    
    return source
    
class ShaderEffect:
    """
    
    A graphical effect for injection into a shader.
    
    
    """
    def __init__(self, name, applySpotName, source, params, extraMethodsSource=""):
        """
        name describes the effect. It is not important for correct operation other than it must
        be valid text to place in a shader, and must be unique
        
        applySpotName=token for insertion location in base shader
        source=shader source code
        params=list of ShaderEffectParam objects passed to method wraping source in final shader code
        

        """
        self.name=name
        self.applySpotName=applySpotName
        
        # Make a method name that should be pretty sure not to conflict with anything in the shader
        methodName='_Effect_'+name+'_'
        
        self.callSource=methodName+'('+', '.join([p.evaluationCode for p in params])+');'
        self.methodSource='void '+methodName+'('+', '.join([p.defCode for p in params])+'){\n'+source+'\n}'
        
        self.methodSource=extraMethodsSource+'\n'+self.methodSource
        
        self.extraMethodsSource=extraMethodsSource
        self.source=source
        self.params=params

        
        self.shaderParams=[]
        for p in params:
            if p.shaderParam: self.shaderParams.append(p.shaderParam)
        
        
        self.subEffects=[]
    
    def __eq__(self, other):
        if isinstance(other, ShaderEffect):
            return (self.name == other.name and
                    self.methodSource == other.methodSource and
                    self.params == other.params)
                    
        return NotImplemented
    
    
    def __str__(self):
        return self.name
    
    def shallowCopy(self):
        """Make a copy suitable for modifying subEffects list (but not the subEffects themselves) without disrupting the origional"""
        s=ShaderEffect(self.name,self.applySpotName,self.source,self.params,self.extraMethodsSource)
        s.subEffects=list(self.subEffects)
        return s
    
    def flatten(self):
        """reduce effects tree to a single effect, and returns it. Does not modify self"""
        if not self.subEffects:
            return self.shallowCopy()
        
        effects=[e.flatten() for e in self.subEffects]
        
        source=_injectEffectCalls(self.source,effects)
        
        extraMethodsSource='\n'.join(s.methodSource for s in effects)+'\n'+self.extraMethodsSource
        
        # Collect all needed shaderParams (Shader input requirements)
        params=list(self.params)
        for s in effects:
            params.extend(p for p in s.params if p.shaderParam)

        name=self.name+"__"+"_".join(s.name for s in effects)
        newEffect=ShaderEffect(name,self.applySpotName,source,params,extraMethodsSource)
        return newEffect

        
class ShaderParam:
    """
    This is a param for the shader itself, not a param for an effect.
    It it used for gettting shaderInputs avaliable shaderside, as well as
    exposing special things like mat_modelproj and vtx_position
    
    This is also used for shader outputs, like the final color, transformed vertex position,
    and passing stuff from vshader to fshader
    """
    def __init__(self,place,name,type,in_,out,semantic=None,shaderInput=None):
        """
        type=ex: "float4" or "uniform float4x4"
        in_=boolean for input or not 
        out=boolean for output or not
        shaderInput=ShaderInput object, optional. This would usally be a default value if provided
        place=placement spot. Usally fshaderParams of vshaderParams, string
        semantic=string after : such as POSITION
        
        
        to build from a string see staticmethod fromDefCode
        """
        
        if not (in_ or out): print 'Error, ShaderParam '+name+' is not in or out'
        
        
        self.name=name
        self.place=place
        self.type=type
        self.in_=in_
        self.out=out
        self.shaderInput=shaderInput
        self.semantic=semantic
    
    def __eq__(self, other):
        if isinstance(other, ShaderParam):
            return (self.defCode() == other.defCode() and
                    self.place == other.place)
                    
        return NotImplemented
    
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
        out=in_=t[0]=='inout'
        out|=t[0]=='out'
        in_|=t[0]=='in'
        type=' '.join(t[1:-1])
        
        return ShaderParam(place,shaderParamName,type,in_,out,semantic=semantic)
    
    def copy(self):
        return ShaderParam.fromDefCode(self.place,self.defCode())
    
    def merge(self,other):
        """
        Combines self and other if compatable into a single ShaderParam that is returned.
        None returned if incompatable
        Used for merging things that are equivelent, merging in and out to inout, and/or merging no semantic with one with a semantic specified
        mainly used to try and resolve name comflicts for params, and cause an error if they conflict
        """
        
        if self.name!=other.name or self.type!=other.type or self.shaderInput!=other.shaderInput or (self.semantic!=None and other.semantic!=None and self.semantic!=other.semantic):
            return None
        
        return ShaderParam(self.place,self.name,self.type,self.in_ or other.in_, self.out or other.out, self.shaderInput)
    
    
    def defCode(self,skipSemantic=False):
        return ('in' if self.in_ else '')+('out ' if self.out else ' ')+self.type+' '+self.name+(' : '+self.semantic if self.semantic and not skipSemantic else '')

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
        
    def __eq__(self, other):
        if isinstance(other, ShaderEffectParam):
            return (self.defCode == other.defCode and
                    self.shaderParam == other.shaderParam)
                    
        return NotImplemented