from v3 import *
lib=Library("library")
g=lib.loadGraph("graph/basic.txt")
print g.getShader(None,"test.sha")
print g.getShader(None,"test.sha")
print g.getShader("x","test.sha")