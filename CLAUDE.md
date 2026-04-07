# SoundPad — notes for AI agents

## Target machine

The app runs on a Linux machine at `192.168.0.50`, user account `aj`, desktop account `kids`.

## SSH access

SSH key auth is set up. Always connect using:

```bash
ssh -i ~/.ssh/id_soundpad aj@192.168.0.50
```

Never prompt for or hardcode passwords. `install.sh` already uses this key via `SSH_OPTS`.

## Deploying updates

```bash
bash install.sh aj@192.168.0.50 kids
```

## Sensitive information

- Do not hardcode passwords, IPs, or usernames in any committed file.
- The `.ssh/` key stays local and never gets committed.
