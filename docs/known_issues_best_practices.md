# Known Issues & Best Practices

## Known Issues
- **Environment Handling:** Care must be taken to secure `.env` files and avoid committing secrets to version control.
- **Error Handling:** Some enrichment scripts may require improved exception management for robustness, especially with live data streams.
- **Modularity:** While modular, some components have implicit dependencies that should be documented and refactored over time.

## Best Practices for Extension
- Always include comprehensive docstrings for new scripts and functions.
- Document any new API endpoints with clear schema definitions.
- Avoid hardcoding secrets or credentials; use environment variables exclusively.
- Follow existing code style and architectural patterns to maintain consistency.
- Test new features thoroughly in isolated environments before deployment.
