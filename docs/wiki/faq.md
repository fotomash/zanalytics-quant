# FAQ

**Q: Something isn’t working—how do I see detailed error logs?**
A: Use `docker compose logs <service>` (add `-f` to follow in real time) or `docker logs <container>` for single containers. For service-specific errors, check Django's debug logs and MT5 bridge logs.

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
   docker compose exec redis redis-cli FLUSHALL
   ```
2. Restart the services so caches repopulate with fresh data.

**Q: I need a clean database—how do I reset Postgres?**
A:
1. Stop the services:
   ```bash
   docker compose down
   ```
2. Remove the Postgres volume (be sure you're ok losing all data):
   ```bash
   docker volume rm <name>  # or docker compose down -v
   ```
3. Rerun migrations to recreate schema:
   ```bash
   docker compose run django migrate
   ```
4. Restart the stack:
   ```bash
   docker compose up -d
   ```

**Q: Docker containers fail to build/start.**
A:
1. Verify your Docker installation and version.
2. Rebuild images without cache using `docker compose build --no-cache`.
3. Check container output with `docker compose logs`.
4. Ensure required ports are free to avoid conflicts.

**Q: Docker containers complain about file or directory permissions.**
A: Verify host permissions on the affected paths. Run `sudo chown -R $USER:$USER <path>` or adjust with `chmod`, then rebuild the containers to apply the changes.

**Q: Startup fails with "address already in use."**
A: Another service is already bound to a required port.

1. Run `lsof -i :<port>` or `netstat -tulpn` to find the PID and service using the port.
2. Stop the offending process (`kill <PID>` or `systemctl stop <service>`).
3. Or edit the `ports:` mapping in `docker-compose.yml` to use a free port and restart the stack.

**Q: Container is up, but `curl` to port 8001 returns connection refused?**
A: Another process is occupying 8001. Run `netstat -tln | grep 8001` to identify it, stop the offending container (e.g., `docker stop <id>`—often `tick-to-bar` or a stray zookeeper), then `docker compose restart mcp`.
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
1. Stop and remove containers and volumes: `docker compose down -v`.
2. Remove any orphan containers: `docker container prune -f`.
3. Rebuild and start fresh containers: `docker compose up --build`.
4. Rerun database migrations if applicable.

**Q: Traefik route isn't matching my service?**
A: Router labels may be off. Check `traefik.http.routers` rules in [`docker-compose.yml`](../docker-compose.yml) and match `Host`/`PathPrefix` to the request. See [troubleshooting](troubleshooting.md#traefik-routing-labels).

**Q: On macOS, commands fail with a locked keychain?**
A: Unlock it before running Docker or git:
```bash
security unlock-keychain login.keychain-db
```
Then retry the command. More tips in [troubleshooting](troubleshooting.md#macos-keychain-unlock).

**Q: How do I clean up ghost containers?**
A: Remove stragglers and rebuild:
```bash
docker compose down -v
docker container prune -f
docker compose up --build
```
See [troubleshooting](troubleshooting.md#ghost-container-cleanup) for details.

**Q: MT5 quotes look stale—how do I refresh the feed?**
A: Restart the [mt5_gateway](../mt5_gateway/README.md) container:
```bash
docker compose restart mt5
```
Verify ticks with `curl "$MT5_API_URL/ticks?symbol=EURUSD&limit=1"`.

**Q: Which header carries the API key?**
A: Use `X-API-Key` with the value from `$MCP_API_KEY`:
```bash
curl -H "X-API-Key: $MCP_API_KEY" http://localhost:8001/api/...
```
See [api-security.md](api-security.md) for rotation guidance.

**Q: Why does Whisperer still ask for approval after sending `approve: true`?**
A: Cached action state. Delete and re-add the MCP connector in the OpenAI builder, or include `force: true` with `approve: true` to bypass cache. See [WHISPERER.md](WHISPERER.md) for payload examples.
