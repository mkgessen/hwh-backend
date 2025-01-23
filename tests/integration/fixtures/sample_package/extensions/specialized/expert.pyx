
from ...core.base cimport BaseOp
from ...utils.helpers cimport Helper
from ..advanced cimport Advanced

cdef class Expert:
    def __init__(self, Advanced advanced, BaseOp extra_op):
        self.advanced = advanced
        self.extra_op = extra_op
    
    cpdef double deep_process(self):
        # Use functionality from all levels
        base_result = self.extra_op.compute()
        advanced_result = self.advanced.process()
        return (base_result + advanced_result) * 2.0
