from panda3d.core import Shader

import shadereffects

# Makes debugging shaders easier
useShaderFiles=True



def _makeShader(shaderEffects, baseShader):
    """
    
    Generates shader source from effects and converts it into a Panda3D shader object
    baseShader is source to inject effects into
    
    """

    if useShaderFiles:
        name='debug('+','.join([e.name for e in shaderEffects])+')'
        outLoc='ShadersOut/'+name+'.sha'
        print 'Making Shader: '+outLoc
    
    source=shadereffects.makeSource(shaderEffects, baseShader)
    
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
        builtEffectsShaders[key]=_makeShader(shaderEffects, baseShader)
        
    return builtEffectsShaders[key]

def applyEffects(shaderEffects, targetNodePath, baseShader):
    """
    Applies the effects to the passed nodepath
    shaderEffects=list of ShaderEffect objects, orderd by application order
    targetNodePath=Nodepath to apply to
    
    baseShader=source to inject effects into
    """
    
    targetNodePath.setShader(getShader(shaderEffects, baseShader))
    
    
