# Processor Benchmark

The vectorized implementations of the `StructureProcessor` order block and
fair value gap detectors use NumPy arrays and achieve sub-millisecond
latency for typical batch sizes.

Benchmark executed on 1000 synthetic rows:

```
order_blocks_ms 0.6818
fvg_ms          0.6463
```

The benchmark script is available in the repository documentation and can
be reproduced using the following snippet:

```python
import numpy as np, pandas as pd, time
from utils.processors.structure import StructureProcessor

n = 1000
rng = np.random.default_rng(0)
prices = rng.normal(100, 1, size=n)
df = pd.DataFrame({
    'open': prices,
    'high': prices + 0.5,
    'low': prices - 0.5,
    'close': prices + 0.1,
})

sp = StructureProcessor()
sp.identify_order_blocks(df)  # warm up
sp.identify_fair_value_gaps(df)
start = time.perf_counter(); sp.identify_order_blocks(df); ob_ms = (time.perf_counter()-start)*1e3
start = time.perf_counter(); sp.identify_fair_value_gaps(df); fvg_ms = (time.perf_counter()-start)*1e3
print('order_blocks_ms', round(ob_ms,4))
print('fvg_ms', round(fvg_ms,4))
```

Results may vary slightly depending on hardware, but the processing time
remains well below 1 ms per 1000-row batch, satisfying the latency target.

