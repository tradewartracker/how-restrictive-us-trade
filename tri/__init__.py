"""TRI pipeline: load -> weights -> metrics -> tex.

See REFACTOR-PLAN.md for the design and DATA-PIPELINE.md for the monthly cadence.
"""
import pandas as _pd

# Keep pandas on plain numpy for arithmetic and reductions. With numexpr and
# bottleneck installed, one metrics build produced an all-zero squared-tariff
# sum that could not be reproduced afterwards (2026-09-08); determinism matters
# more than the speed-up here.
_pd.set_option("compute.use_numexpr", False)
_pd.set_option("compute.use_bottleneck", False)
