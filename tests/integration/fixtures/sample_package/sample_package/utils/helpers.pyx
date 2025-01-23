
from ..core.base cimport BaseOp

cdef class Helper:
    def __init__(self, BaseOp op):
        self.base_op = op
    
    cpdef double transform(self):
        return self.base_op.compute() + 1.0
