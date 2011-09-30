A shader generator for Panda3D
Specifically, a Shader Meta-Language for implementing, customizing and extending shader generators.

High level conceptual overview
==============================
This is how it works, not a ussage guide.
Some example usage is in the shader tutorial here: https://github.com/Craig-Macomber/Shader-Tut

- A Script produces a Generator Graph.

- RenderStates are used as input to the Generator Graph to produce the Active Graph for to the
  provided RenderState.

- The Active Graphs are compiled into shaders.


Scripts --> Generator Graphs
++++++++++++++++++++++++++++
Each script file describes (generates) a graph structure (The generator graph)
This is done by constructing nodes and passing in incomming edges (and possibly some constants).

    nodeInstance=NodeType(input1,input2,"SomeConstant")
    
The types of nodes in the graph are defined in nodes.py, and via libraries (which are loaded as CodeNodes from nodes.py)

These node types have 0 or more outputs, accessable as nodeInstance.name
They may (and might not) have a default output which can be accessed by just passing the node itself:

    nodeInstance2=SomeNode(nodeInstance.someOutput,nodeInstance)

Thus, the scripts describe directed acyclic graphs. The graphs do not need to be connected.

RenderStates
++++++++++++
See also renderState.py

When generating a shader from the Generator Graph, a RenderState is provided as input (and its the only input).

The shader generator uses a very similar RenderState class to panda3d.core.RenderState.

The reason the panda RenderState class is not used is tweo fold:

- It contains lots of unneeded data (hurts caching)

- It is missing some needed data (tags, geomVertexFormat etc)

To get the exact minimum needed data stored in the RenderStates for the ShaderBuilder,
the Generator Graph is used to setup a RenderStateFactory the produces ideal minimal
RenderStates for a specific Generator Graph

Generating the Shader
+++++++++++++++++++++
A shader builder uses it's Generator Graph, and a passed in RenderState and produces an Shader. 
shaderBuilder.ShaderBuilder.getShader does this. It includes caching, since the process is a
deterministic process that depends only on the Generator Graph (constant for the builder),
and the input RenderState.


Generating the Active Graph
---------------------------
The first step is to generate the Active Graph. See shaderBuilder.makeStages.

Compiling the Active Graph into Stages
--------------------------------------
See shaderBuilder.makeStage.


 



Misc Notes
==========

Outputting visual graphs requires pydot and graphviz to be installed.

Goals:

- Allow coders to provide all possible shader effects (no restrictions on shader code, stages used, inputs, outputs etc) (Done)

- Allow easy realtime configuration and tuning of effects (accessible to artists and coders) (Not started, not longer emphasized)

- Generate custom shaders based on render state and other settings on a per NodePath basis from a single configuration (Done via use of meta-language design)

- Allow easy use of multiple separate configurations applied to different NodePaths (ex: one for deferred shaded lights, one for models, one for particles. Done.)

- Produce an extensive collection of useful NodeTypes and example Graphs, sample applications etc. (Most of the remaining work is here)

It is important that adding, sharing and using libraries of effects is easy. To facilitate this, they are packed into libraries which can simply be placed in a libraries folder (even recursively)
There is however currently no name spacing. For now, manually prefix things if you with to avoid any potential conflicts.

The focus on allowing full control of the shaders is important. A shader generator that can't use custom shader inputs, render to multiple render targets, or use multiple stages (vshader, fshader, gshader etc) is not complete. This design inherently supports all of these, and more.

Many more details in shaderBuilder.py, see comments near top.

Example Meta-Language scripts are in the graph directory. These scripts create a graph structure that is used to generate the final shader graphs for different render states which are compiled into shaders.

The set of nodes that can be used in these graphs are the regestered classes from nodes.py, and those loaded from the libraries (see the library folder).

Its possibe to add custom node types implemented in python, simply provide them when instancting the shaderBuilder.Library

