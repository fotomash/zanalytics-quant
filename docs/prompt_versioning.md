# Manifest Versioning

The `session_manifest.yaml` file now includes a `version` field to track which configuration revision produced the session configuration.

## Bumping the Version

1. Update `session_manifest.yaml` and any design templates to the new version string.
2. Adjust tooling or loaders to recognize the version if needed.
3. Commit the changes with a descriptive message summarizing the manifest update.

Use semantic identifiers such as `1.0`, `1.1`, etc. to keep versions easy to compare.
