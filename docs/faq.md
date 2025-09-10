# FAQ

**Q: Something isn’t working—how do I see detailed error logs?**
A: Use `docker-compose logs <service>` (add `-f` to follow in real time) or `docker logs <container>` for single containers. For service-specific errors, check Django's debug logs and MT5 bridge logs.

**Q: Can I run this without Docker?**
A: Not recommended. The MT5 and dashboard stack is designed for containerization for full reproducibility and security.

**Q: Where is my live data stored?**
A: Real-time data is cached in Redis and long-term data is stored in Postgres. Snapshots/exports may use Parquet in `/data/`.

**Q: How can I add a new feature or signal?**
A: Extend or edit the scripts in `utils/` and trigger the enrichment process.

**Q: What if the dashboard is blank?**
A: Double-check your API/DB containers, verify enrichment, and confirm `.env` credentials.

**Q: I receive errors about missing environment variables.**
A: Copy `.env.example` to `.env`, double-check the keys, and restart the containers after any updates.

**Q: The app can't connect to Postgres or Redis.**
A: Confirm your `.env` credentials, ensure the services are running (`docker ps`), and check container logs for authentication or network errors.

**Q: How do I clear cached data in Redis?**
A:
1. Run the following to flush all cached keys:
   ```bash
   docker-compose exec redis redis-cli FLUSHALL
   ```
2. Restart the services so caches repopulate with fresh data.

**Q: I need a clean database—how do I reset Postgres?**
A:
1. Stop the services:
   ```bash
   docker-compose down
   ```
2. Remove the Postgres volume (be sure you're ok losing all data):
   ```bash
   docker volume rm <name>  # or docker-compose down -v
   ```
3. Rerun migrations to recreate schema:
   ```bash
   docker-compose run django migrate
   ```
4. Restart the stack:
   ```bash
   docker-compose up -d
   ```

**Q: Docker containers fail to build/start.**
A:
1. Verify your Docker installation and version.
2. Rebuild images without cache using `docker-compose build --no-cache`.
3. Check container output with `docker-compose logs`.
4. Ensure required ports are free to avoid conflicts.

**Q: Docker containers complain about file or directory permissions.**
A: Verify host permissions on the affected paths. Run `sudo chown -R $USER:$USER <path>` or adjust with `chmod`, then rebuild the containers to apply the changes.

**Q: Startup fails with "address already in use."**
A: Another service is already bound to a required port.

1. Run `lsof -i :<port>` or `netstat -tulpn` to find the PID and service using the port.
2. Stop the offending process (`kill <PID>` or `systemctl stop <service>`).
3. Or edit the `ports:` mapping in `docker-compose.yml` to use a free port and restart the stack.

**Q: Install or build fails due to missing packages or version conflicts?**
A: Ensure you're using the supported Python version, then install dependencies with `poetry install` or `pip install -r requirements.txt`. If issues persist, clear cached wheels (e.g., `pip cache purge`) and try again.

**Q: The web UI won't compile or `npm start` fails.**
A: Remove the `web/node_modules` directory and reinstall dependencies with `npm install` (or `npm ci`). Ensure you're using the project's required Node.js version.

**Q: Celery tasks are stuck or failing—what should I do?**
A:
1. Check the Celery worker logs for errors.
2. Purge the queue:
   ```bash
   celery -A app purge -f
   ```
3. Restart the Celery service.
4. For a quick diagnostic, run [check_celery.sh](../check_celery.sh).

**Q: How do I reset the containers when data gets corrupted or outdated?**
A:
1. Stop and remove containers and volumes: `docker-compose down -v`.
2. Remove any orphan containers: `docker container prune -f`.
3. Rebuild and start fresh containers: `docker-compose up --build`.
4. Rerun database migrations if applicable.
