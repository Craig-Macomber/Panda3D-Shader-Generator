from panda3d.core import Shader

import shadereffects

# Makes debugging shaders easier
useShaderFiles=True

# Shader cache for getShader
builtEffectsShaders={}

def _makeShader(shaderEffects, baseShader=None):
    """
    
    Generates shader source from effects and converts it into a Panda3D shader object
    baseShader is source to inject effects into
    
    """

    
    
    source=shadereffects.makeSource(shaderEffects, baseShader)
    key=source
    if key not in builtEffectsShaders:
        if useShaderFiles:
            # preflatten should not impact anything much, but lets us get the full names
            shaderEffects=[s.flatten() for s in shaderEffects]
            name='debug('+','.join([e.name for e in shaderEffects])+')'
            outLoc='ShadersOut/'+name+'.sha'
            print 'Making Shader: '+outLoc
            
        builtEffectsShaders[key]=Shader.make(source)
      
        if useShaderFiles:
            fOut=open(outLoc, 'w')
            fOut.write(source)
            fOut.close()
        
    return builtEffectsShaders[key]


def getShader(shaderEffects, baseShader=None):
    """
    
    Cashes shaders from makeShader to avoid regeneration or multiple identicle shaders
    
    """
    return _makeShader(shaderEffects, baseShader)

def applyEffects(shaderEffects, targetNodePath, baseShader=None):
    """
    Applies the effects to the passed nodepath
    shaderEffects=list of ShaderEffect objects, orderd by application order
    targetNodePath=Nodepath to apply to
    
    baseShader=source to inject effects into
    """
    
    targetNodePath.setShader(getShader(shaderEffects, baseShader))
    
    
