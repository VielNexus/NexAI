# Release Packaging

Release packaging is handled by:

```text
scripts/package_release.py
```

Run:

```powershell
python .\scripts\package_release.py
```

or:

```bash
python scripts/package_release.py
```

## Required Inputs

The release builder expects:

- `install-agentx.sh`
- `AgentX/agentx`
- `apps/api`
- `AgentXWeb`
- `AgentXWeb/dist/index.html`

Build AgentXWeb first:

```bash
cd AgentXWeb
npm install
npm run build
```

## Outputs

By default the script writes:

| Output | Purpose |
| --- | --- |
| `dist/agentx-<version>.zip` | Release archive |
| `dist/agentx-<version>.zip.sha256` | SHA256 checksum |
| `dist/release-manifest.json` | File manifest and metadata |

The version is read from:

```text
AgentX/agentx/version.py
```

## Included Roots

The release includes:

- `install-agentx.sh`
- root `README.md`
- `LICENSE`
- `RELEASE.md`
- `AgentX`
- `AgentXWeb`
- `apps`

## Exclusions

The release intentionally excludes:

- `.git`
- virtualenvs
- `node_modules`
- test folders
- Python caches
- pytest caches
- egg-info
- runtime data
- runtime logs
- API data
- editor junk
- desktop app folder
- AgentXWeb source files

`AgentXWeb/dist` is retained because it is the built frontend shipped in the release.

## Validation

The script validates:

- Required repo paths exist.
- Python files compile in the staged release tree.
- Required archive paths are present.
- Forbidden content is absent.
- The final archive checksum is generated.

If `AgentXWeb/dist/index.html` is older than `AgentXWeb/src`, the script warns that the frontend may need rebuilding.
