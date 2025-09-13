import os
import sys
from types import ModuleType


def _stub_dependencies() -> None:
    redis_mod = ModuleType("redis")
    class Redis:  # pragma: no cover - stub
        pass
    class RedisError(Exception):
        pass
    redis_exceptions = ModuleType("redis.exceptions")
    redis_exceptions.RedisError = RedisError
    redis_mod.Redis = Redis
    redis_mod.exceptions = redis_exceptions
    sys.modules.setdefault("redis", redis_mod)
    sys.modules.setdefault("redis.exceptions", redis_exceptions)

    kafka_mod = ModuleType("confluent_kafka")
    class Producer:  # pragma: no cover - stub
        pass
    kafka_mod.Producer = Producer
    sys.modules.setdefault("confluent_kafka", kafka_mod)

    cms_mod = ModuleType("core.semantic_mapping_service")
    class SemanticMappingService:  # pragma: no cover - stub
        pass
    cms_mod.SemanticMappingService = SemanticMappingService
    sys.modules.setdefault("core.semantic_mapping_service", cms_mod)

    ct_mod = ModuleType("core.confidence_tracer")
    class ConfidenceTracer:  # pragma: no cover - stub
        pass
    ct_mod.ConfidenceTracer = ConfidenceTracer
    sys.modules.setdefault("core.confidence_tracer", ct_mod)

    re_mod = ModuleType("components.risk_enforcer")
    class RiskEnforcer:  # pragma: no cover - stub
        pass
    re_mod.RiskEnforcer = RiskEnforcer
    sys.modules.setdefault("components.risk_enforcer", re_mod)
    sys.modules.setdefault("risk_enforcer", re_mod)


_stub_dependencies()

from pulse_kernel import PulseKernel


def test_load_enrichment_processors_config():
    kernel = PulseKernel.__new__(PulseKernel)
    path = os.path.join("config", "enrichment_processors.yaml")
    processors = kernel._load_enrichment_processors(path)
    modules = {p["module"]: p for p in processors}

    for mod in (
        "utils.enrichment.smc",
        "utils.enrichment.poi",
        "utils.enrichment.dss",
        "utils.enrichment.rsi",
    ):
        assert mod in modules
        assert "enabled" in modules[mod]
        assert "settings" in modules[mod]

    assert modules["utils.enrichment.rsi"]["settings"].get("period") == 14

