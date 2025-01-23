
cdef class BaseOp:
    def __init__(self, double value):
        print("moro")
        self.value = value
    
    cpdef double compute(self):
        print("poro")

        return self.value * 2.0
