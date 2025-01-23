
from ..core.base cimport BaseOp
from ..utils.helpers cimport Helper

cdef class Advanced:
    cdef:
        readonly Helper helper
    
    cpdef double process(self)
