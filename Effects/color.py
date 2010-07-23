from shadereffects import shadereffects
from shadereffects import effectPlacement
from shadereffects.filter_ import includeAll

'''
:Info
place   fshader

:fshaderparams
out float4 o_color : COLOR

:Shader
float4 color=float4(0,0,0,1);
//<color>//
o_color=color;
'''



def getPlacements():
    params=[
        shadereffects.ShaderParam.fromDefCode('fshaderparams','out float4 o_color : COLOR').makeShaderEffectParam()
        ]
    
    source='''float4 color=float4(0,0,0,1);
//<color>//
o_color=color;'''

    effect=shadereffects.ShaderEffect('color', 'fshader', source, params)
    filter=includeAll
    placement=effectPlacement.Placement(effect,filter)
    return [placement]