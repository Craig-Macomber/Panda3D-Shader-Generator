"""
Filtering System:
Designed to create Filter objects than can be called with an item and return a boolean
returned boolean states whether or not the passed item passed the filter
"""

class Filter(object):
    def __init__(self,call,*params):
        """
        call should be a function that accepts the paramaters (self,item)
        params is stored to self.params and can be used in call
        if subclassing, overwriting __call__(self,item) instead of calling Filter.__init__ with call is acceptable
        in the case where a subclass replaces __call__(self,item), Filter.__init__ does not need to be called,
        though can be to save params if desired.
        """
        self.params=params
        self.call=call
    
    def __call__(self,item):
        return self.call(self,item)
    
    def __and__(self,other):
        print "x"
        return Filter((lambda self,item: self.params[0](item) and self.params[1](item)),self,other)
    
    def __or__(self,other):
        return Filter(lambda self,item: self.params[0](item) or self.params[1](item),self,other)
    
    def __xor__(self,other):
        return Filter(lambda self,item: self.params[0](item) ^ self.params[1](item),self,other)
    
    def __invert__(self):
        return Filter(lambda self,item: not self.params[0](item),self)
    

includeAll=Filter(lambda self,item: True)
includeNone=Filter(lambda self,item: False)



class ClassFilter(Filter):
    def __init__(self,matchClass):
        self.matchClass=matchClass
    def __call__(self,item):
        return isinstance(item,self.matchClass)

class IsFilter(Filter):
    def __init__(self,other):
        self.other=other
    def __call__(self,item):
        return item is self.other

class IsCallFilter(Filter):
    def __init__(self,call):
        self.call=call
    def __call__(self,item):
        return item is self.call()

