# soccer-lottery

Portable Agent Skill for football match analysis and soccer lottery research.

The skill lives at [`skills/soccer-lottery`](skills/soccer-lottery). It works with Codex, Hermes Agent, OpenClaw, and other clients that support the `SKILL.md` Agent Skills format.

## Install

Copy `skills/soccer-lottery` into the target agent's skills directory, then run the installer from that directory.

Codex:

```text
~/.codex/skills/soccer-lottery
```

Hermes Agent:

```text
~/.hermes/skills/soccer-lottery
```

OpenClaw:

```text
<workspace>/skills/soccer-lottery
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Linux or macOS:

```bash
bash install.sh
```

See [`skills/soccer-lottery/INSTALL.md`](skills/soccer-lottery/INSTALL.md) for configuration, ClawHub publishing, Hermes taps, and verification commands.

## Publish

Hermes custom tap:

```bash
hermes skills tap add OWNER/REPOSITORY
```

ClawHub:

```bash
clawhub skill publish ./skills/soccer-lottery --dry-run
clawhub skill publish ./skills/soccer-lottery
```

Do not commit `config.yaml`, `.venv`, or API credentials. The skill reads the Football-Data.org token from `config.yaml` or the `FOOTBALL_DATA_API_KEY` environment variable.

## License

MIT. Skills published through ClawHub are subject to ClawHub's MIT-0 publishing terms.
