from panda3d.core import loadPrcFileData
loadPrcFileData("","notify-level-gobj debug")

from shaderBuilder import *

lib=Library(["library"])

builder=lib.loadScript("graph/lit.gen")

s = builder.getShader(None,"ShadersOut/debug.sha")
