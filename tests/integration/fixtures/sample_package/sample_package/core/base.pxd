
cdef class BaseOp:
    cdef:
        readonly double value
    
    cpdef double compute(self)
