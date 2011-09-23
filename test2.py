from panda3d.core import loadPrcFileData,NodePath
loadPrcFileData("","notify-level-gobj debug")

import manager

shaderManager=manager.getManager(["library"],"graph/basic.gen")
shader=shaderManager.makeShader(NodePath(""))
