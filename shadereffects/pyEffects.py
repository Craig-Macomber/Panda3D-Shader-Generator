import os
import sys

# http://aroberge.blogspot.com/2008/12/plugins-part-3-simple-class-based.html

def loadAll(path):
    '''find all the .py effects files and imports them'''
    plugin_files = [x[:-3] for x in os.listdir(path) if x.endswith(".py")]
    sys.path.insert(0, path)
    placements=[]
    for plugin in plugin_files:
        effectModule = __import__(plugin)
        placements.extend(effectModule.getPlacements())
    return dict([(p.shaderEffect.name,p) for p in placements])