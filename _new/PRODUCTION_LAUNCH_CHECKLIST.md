# 🚀 PRODUCTION LAUNCH CHECKLIST

## Pre-Deployment (T-24 hours)
- [ ] Code review completed and approved
- [ ] All tests passing (unit, integration, e2e)
- [ ] Configuration files validated
- [ ] Docker images built and tagged
- [ ] Database migrations prepared
- [ ] Rollback plan documented and tested

## Deployment (T-0)
- [ ] Create feature branch: `feat/pulse-adaptive-wyckoff`
- [ ] Deploy configuration updates
- [ ] Update Django URLs with new endpoints
- [ ] Deploy Docker services in order:
  - [ ] Redis (if not running)
  - [ ] PostgreSQL (if not running)
  - [ ] Django application
  - [ ] Pulse Kernel service
  - [ ] Tick-to-Bar service
  - [ ] News Monitor service
- [ ] Verify health endpoints:
  - [ ] `/api/pulse/health`
  - [ ] `/api/pulse/wyckoff/health`
- [ ] Enable Prometheus metrics collection
- [ ] Configure Grafana dashboards

## Shadow Mode Validation (T+0 to T+48 hours)
- [ ] Confirm dual Redis streams active
- [ ] Monitor key metrics:
  - [ ] False positive rate < 15%
  - [ ] Phase flip rate < 10%
  - [ ] Processing latency < 200ms
  - [ ] No memory leaks
  - [ ] No unhandled exceptions
- [ ] Compare adaptive vs legacy performance
- [ ] Document any anomalies

## Production Promotion (T+48 hours)
- [ ] Review 48-hour metrics report
- [ ] Team approval obtained
- [ ] Disable legacy Wyckoff stream
- [ ] Update documentation
- [ ] Notify stakeholders
- [ ] Monitor for additional 24 hours

## Post-Launch (T+72 hours)
- [ ] Conduct retrospective
- [ ] Document lessons learned
- [ ] Plan next iteration improvements
- [ ] Schedule first calibration run

## Emergency Rollback Procedure
If critical issues detected:
1. [ ] Set `wyckoff.news_buffer.enabled: false` in config
2. [ ] Set `confluence_weights.wyckoff: 0.0` to disable
3. [ ] Restart Pulse Kernel service
4. [ ] Clear problematic Redis streams
5. [ ] Revert to previous Docker image if needed
