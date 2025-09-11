import services.mcp2.routers.echonudge as echonudge


def test_env_reads_cached(monkeypatch):
    calls = {"count": 0}

    def fake_getenv(key, default=None):
        calls["count"] += 1
        return default

    monkeypatch.setattr(echonudge.os, "getenv", fake_getenv)
    echonudge._ollama_url.cache_clear()
    echonudge._ollama_model.cache_clear()
    echonudge._ollama_options.cache_clear()

    # multiple invocations should trigger getenv only once per helper
    echonudge._ollama_url()
    echonudge._ollama_url()
    echonudge._ollama_model()
    echonudge._ollama_model()
    echonudge._ollama_options()
    echonudge._ollama_options()

    # _ollama_options reads six env vars; url and model read one each
    assert calls["count"] == 8
