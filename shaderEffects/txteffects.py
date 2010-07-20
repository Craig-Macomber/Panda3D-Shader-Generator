from shadereffects import *


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
    
