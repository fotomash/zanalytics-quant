import asyncio
import sys
import time
import types

# Stub heavy dependencies before importing PulseKernel
_sms = types.ModuleType("core.semantic_mapping_service")
_sms.SemanticMappingService = object
sys.modules.setdefault("core.semantic_mapping_service", _sms)

_ct = types.ModuleType("core.confidence_tracer")
_ct.ConfidenceTracer = object
sys.modules.setdefault("core.confidence_tracer", _ct)

_re = types.ModuleType("components.risk_enforcer")
_re.RiskEnforcer = object
sys.modules.setdefault("components.risk_enforcer", _re)
sys.modules.setdefault("risk_enforcer", _re)

from pulse_kernel import PulseKernel


def _make_proc(name: str, key: str, sleep: float = 0.0) -> None:
    module = types.ModuleType(name)

    def process(data, **_settings):
        if sleep:
            time.sleep(sleep)
        return {key: data.get(key, 0) + 1}

    module.process = process
    sys.modules[name] = module


def test_enrichment_runtime():
    _make_proc("tests.runtime_proc1", "a", sleep=0.05)
    _make_proc("tests.runtime_proc2", "b", sleep=0.05)
    kernel = PulseKernel.__new__(PulseKernel)
    kernel.enrichment_processors = [
        {"module": "tests.runtime_proc1"},
        {"module": "tests.runtime_proc2"},
    ]
    data = {"a": 0, "b": 1}
    start = time.perf_counter()
    result = asyncio.run(kernel._calculate_confluence(data))
    duration = time.perf_counter() - start
    assert result == {"a": 1, "b": 2}
    assert duration < 0.4, f"runtime {duration:.3f}s exceeds 400ms"
