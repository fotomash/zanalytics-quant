# ZAnalytics Migration Guide: File-Based to Redis-Based Architecture

This guide provides steps to migrate existing components to the new Redis architecture.

1. **Setup Redis** using the `redis.conf` provided.
2. **Update Django settings** to use Redis for Celery broker and result backend.
3. **Run the MT5 integration** with `python run_mt5_integration.py`.
4. **Start Celery worker and beat** using the new tasks in `tasks.py`.
5. **Launch the Streamlit dashboard** with `streamlit run unified_dashboard.py`.
6. **Use `docker-compose.yml`** for a containerised deployment.
