# soccer-lottery

Portable Agent Skill for football match analysis and soccer lottery research.

The Titan007 test skill lives at [`skills/soccer-lottery-test`](skills/soccer-lottery-test). It works with Codex, Hermes Agent, OpenClaw, and other clients that support the `SKILL.md` Agent Skills format.

## Install

Copy `skills/soccer-lottery-test` into the target agent's skills directory, then run the installer from that directory.

Codex:

```text
~/.codex/skills/soccer-lottery-test
```

Hermes Agent:

```text
~/.hermes/skills/soccer-lottery-test
```

OpenClaw:

```text
<workspace>/skills/soccer-lottery-test
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Linux or macOS:

```bash
bash install.sh
```

See [`skills/soccer-lottery-test/INSTALL.md`](skills/soccer-lottery-test/INSTALL.md) for configuration, ClawHub publishing, Hermes taps, and verification commands.

## Publish

Hermes custom tap:

```bash
hermes skills tap add OWNER/REPOSITORY
```

ClawHub:

```bash
clawhub skill publish ./skills/soccer-lottery-test --dry-run
clawhub skill publish ./skills/soccer-lottery-test
```

Do not commit `config.yaml`, `.venv`, or API credentials. The skill reads the Football-Data.org token from `config.yaml` or the `FOOTBALL_DATA_API_KEY` environment variable.

## License

MIT. Skills published through ClawHub are subject to ClawHub's MIT-0 publishing terms.
