
from ..core.base cimport BaseOp
from ..utils.helpers cimport Helper

cdef class Advanced:
    def __init__(self, Helper helper):
        self.helper = helper
    
    cpdef double process(self):
        return self.helper.transform() * 3.0
