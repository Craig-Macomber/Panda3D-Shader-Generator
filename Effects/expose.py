from shaderEffects import shaderEffects
from shaderEffects import effectPlacement


'''
:Info
place   color

:Params
inout float4 color

:fshaderparams
in uniform float4 k_exposure

:Shader
color.xyz*=k_exposure.x;
'''



def getPlacements():
    params=[
        shaderEffects.ShaderEffectParam('inout float4 color'),
        shaderEffects.ShaderParam.fromDefCode('fshaderparams','in uniform float4 k_exposure').makeShaderEffectParam()
        ]
    
    effect=shaderEffects.ShaderEffect('expose', 'color', 'color.xyz*=k_exposure.x;', params)
    filter=effectPlacement.RequireShaderInputs(['exposure'])
    placement=effectPlacement.Placement(effect,filter)
    return [placement]