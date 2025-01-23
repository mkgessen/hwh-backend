
from ...core.base cimport BaseOp
from ...utils.helpers cimport Helper
from ..advanced cimport Advanced

cdef class Expert:
    cdef:
        readonly Advanced advanced
        readonly BaseOp extra_op
    
    cpdef double deep_process(self)
