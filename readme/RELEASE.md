# Release Packaging

Use the deterministic packaging script to build a clean release archive:

```powershell
python .\scripts\package_release.py
```

The release archive:

- defaults to `agentx-<version>.zip`
- includes `install-agentx.sh`, `AgentX`, `apps`, and built `AgentXWeb/dist`
- requires `AgentXWeb/dist/index.html`
- excludes local state such as `.git`, virtualenvs, caches, logs, data directories, editor junk, frontend source, and tests
- writes:
  - `dist/agentx-<version>.zip`
  - `dist/agentx-<version>.zip.sha256`
  - `dist/release-manifest.json`

The script validates:

- required roots and built assets exist
- forbidden content is not present in the final archive
- expected archive layout is present
- shipped Python files compile in the staged release tree

The final release summary prints the version, archive path, SHA256, file count, size, and warnings.
