import os

from shadereffects import ShaderEffect,ShaderParam,ShaderEffectParam,shaderParamPlaces

def _parseFile(path):
    """
    
    Read sections headed by :SectionName into lists by section name in a dictionary
    blank lines, line preceeding and ending whitespace and #Comments are stripped
    
    """
    
    d={}
    currentList=None
    
    f = open(path, 'r')
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


def _loadEffectFromDict(d,name):
    if not 'info' in d or not 'shader' in d:
        print 'error: one of the required sections is missing from effect',name
        return
    source='\n'.join(d['shader'])
    params=[ShaderEffectParam(t) for t in d.get('params',[])]
    for p in shaderParamPlaces:
        if p in d:
            params.extend(ShaderParam.fromDefCode(p,s).makeShaderEffectParam() for s in d[p])
    
    info=dict([t.split() for t in d['info']])
    #some validity checks:
    if 'place' not in info:
        print 'error: place not specified in effect',name
        return None
    paramNames=set()
    for p in params:
        if p.name in paramNames:
            print "error: conflicting params"+p.name+" in "+name
        paramNames.add(p.name)
    
    return ShaderEffect(name, info['place'], source, params)
        

def loadEffectFromFile(path,name):
    """
    Build effect from an effects file
    path should be containing folder
    name is filename without '.txt'
    
    """
    path=os.path.join(path,name+'.txt')
    d=_parseFile(path)
    e=_loadEffectFromDict(d,name)
    if e is None:
        print 'fialed loading effects file',path
    return e
    
