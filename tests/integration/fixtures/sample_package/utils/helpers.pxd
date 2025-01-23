
from ..core.base cimport BaseOp

cdef class Helper:
    cdef:
        readonly BaseOp base_op
    
    cpdef double transform(self)
