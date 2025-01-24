from sample_package.core.base import BaseOp
from sample_package.extensions.advanced import Advanced
from sample_package.extensions.specialized.expert import Expert
from sample_package.utils.helpers import Helper

# Test the entire dependency chain
base_op = BaseOp(2.0)
helper = Helper(base_op)
advanced = Advanced(helper)
expert = Expert(advanced, BaseOp(3.0))

# Test computation through the hierarchy
result = expert.deep_process()
# expected = ((3.0 * 2.0 + 1.0) * 3.0 + (2.0 * 2.0)) * 2.0
expected = 42.0
assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"

print("All nested module tests passed!")
