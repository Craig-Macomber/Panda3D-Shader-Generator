from shaderEffects import shadereffects
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
        shadereffects.ShaderEffectParam('inout float4 color'),
        shadereffects.ShaderParam.fromDefCode('fshaderparams','in uniform float4 k_exposure').makeShaderEffectParam()
        ]
    
    effect=shadereffects.ShaderEffect('expose', 'color', 'color.xyz*=k_exposure.x;', params)
    filter=effectPlacement.RequireShaderInputs(['exposure'])
    placement=effectPlacement.Placement(effect,filter)
    return [placement]