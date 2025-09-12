import importlib
import logging
import sys
import types

import pytest


def test_policy_import_success(monkeypatch):
    policies = types.ModuleType("policies")

    def loader():
        return {"ok": True}

    policies.load_policies = loader
    monkeypatch.setitem(sys.modules, "backend", types.ModuleType("backend"))
    monkeypatch.setitem(
        sys.modules, "backend.django", types.ModuleType("backend.django")
    )
    monkeypatch.setitem(
        sys.modules, "backend.django.app", types.ModuleType("backend.django.app")
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.django.app.utils",
        types.ModuleType("backend.django.app.utils"),
    )
    monkeypatch.setitem(sys.modules, "backend.django.app.utils.policies", policies)
    sys.modules.pop("risk_enforcer", None)
    module = importlib.import_module("risk_enforcer")
    assert module.load_policies is loader


def test_policy_import_failure(monkeypatch, caplog):
    stub_backend = types.ModuleType("backend")
    stub_backend.__path__ = []  # empty namespace prevents submodule discovery
    monkeypatch.setitem(sys.modules, "backend", stub_backend)
    for name in list(sys.modules.keys()):
        if name.startswith("backend."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    sys.modules.pop("risk_enforcer", None)
    caplog.set_level(logging.WARNING)
    module = importlib.import_module("risk_enforcer")
    assert module.load_policies() == {}
    assert any("Policy loader import failed" in r.message for r in caplog.records)
