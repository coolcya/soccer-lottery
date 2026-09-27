# Installation

This directory is a portable Agent Skill. It works in Codex, Hermes Agent, OpenClaw, and other clients that read `SKILL.md` skills.

## 1. Copy the skill

Copy the whole `soccer-lottery` directory to the skills directory used by your agent.

| Client | Typical destination |
| --- | --- |
| Codex | `~/.codex/skills/soccer-lottery` (Windows: `%USERPROFILE%\.codex\skills\soccer-lottery`) |
| Hermes Agent | `~/.hermes/skills/soccer-lottery` |
| OpenClaw | `<workspace>/skills/soccer-lottery` |

The destination directory name should remain `soccer-lottery` so the frontmatter name and invocation key match.

## 2. Install Python dependencies

Run the installer from the copied skill directory.

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Linux or macOS:

```bash
bash install.sh
```

The installers create `.venv`, install `requirements.txt`, and copy `config.example.yaml` to `config.yaml` when needed.

Manual equivalent:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp config.example.yaml config.yaml
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

## 3. Configure Football-Data.org

Edit `config.yaml`:

```yaml
api:
  football_data:
    key: "YOUR_FOOTBALL_DATA_API_KEY"
```

Alternatively, set the environment variable `FOOTBALL_DATA_API_KEY`. The environment variable takes precedence over `config.yaml`.

Never commit or publish `config.yaml`; it is intentionally excluded from the release archive.

## 4. Verify

Windows:

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_match_data.py
.\.venv\Scripts\python.exe .\scripts\fetch_zgzcw_odds.py --date 2026-09-27 --open-only
```

Linux or macOS:

```bash
.venv/bin/python scripts/fetch_match_data.py
.venv/bin/python scripts/fetch_zgzcw_odds.py --date 2026-09-27 --open-only
```

The odds command must return JSON containing `source_only: true`, `fallback_allowed: false`, and `valid: true` when the approved source is available.

## Client-specific notes

### Codex

Use the direct copy method above. Codex discovers skills under `~/.codex/skills/` (or `%USERPROFILE%\.codex\skills\` on Windows).

### Hermes Agent

Direct copy into `~/.hermes/skills/soccer-lottery` is supported. For managed updates from GitHub, publish a repository containing this skill under `skills/soccer-lottery`, then add it as a custom tap:

```bash
hermes skills tap add OWNER/REPOSITORY
```

Use `/skills browse` in Hermes to inspect and install the skill from the tap.

### OpenClaw and ClawHub

Local installs live under the OpenClaw workspace `skills/` directory. To publish and install through ClawHub:

```bash
npm install -g clawhub
clawhub login
clawhub skill publish ./soccer-lottery --dry-run
clawhub skill publish ./soccer-lottery
clawhub install OWNER/soccer-lottery
```

ClawHub publishes skills under MIT-0. Do not publish this directory until the scan confirms that no API key or private config file is present.

## Recommended upload strategy

1. GitHub repository and Release archive: best universal option for Codex, Hermes, and manual OpenClaw installs.
2. ClawHub: best discovery and install flow for OpenClaw.
3. Hermes custom tap: best managed update flow for Hermes; keep the skill at `skills/soccer-lottery` in the repository.

A repository layout that supports all three is:

```text
repository-root/
  README.md
  LICENSE
  skills/
    soccer-lottery/
      SKILL.md
      INSTALL.md
      requirements.txt
      config.example.yaml
      scripts/
```

## Security

The release archive excludes `.venv/`, `config.yaml`, `__pycache__/`, and `*.pyc`. The API key used during local testing has appeared in chat history, so regenerate it at Football-Data.org before publishing a repository or skill package.
