from v3 import *
g=loadGraph("graph/basic.txt",loadLibrary("library"))
print g.getShader(None,"test.sha")
print g.getShader(None,"test.sha")
print g.getShader("x","test.sha")