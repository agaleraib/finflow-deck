# LXC live environment — canonical configuration

This directory holds the **source of truth** for the Proxmox LXC that serves the
uniqueness PoC playground to external testers. It is **not** applied
automatically — the LXC's live `/etc/caddy/Caddyfile` is the running copy, and
updates happen manually (see below). The files here exist so the correct
configuration survives in git rather than only in the head of whoever set up
the container.

## Context

- **LXC:** CT 101 on Proxmox node0, hostname `playground`, IPv4 `10.1.10.225`
- **Purpose:** isolated, always-on environment for external testers to run
  uniqueness PoC experiments without interfering with dev work on the Mac Studio
- **Access:** UniFi WireGuard VPN (`FinFlow-Testers`, 192.168.3.0/24) → UniFi
  firewall (allow-list to LXC only) → Caddy Basic Auth → playground web UI or
  Samba runs share (read-only)
- **Backing stack:** Ubuntu 24.04 LTS, Bun, Hono, Caddy 2.11, Samba, systemd
- **Runs persistence:** dedicated 32 GB ZFS volume mounted at
  `/srv/playground/runs`, controlled via the `UNIQUENESS_RUNS_DIR` env var in
  `/srv/playground/app/.env.live`

See the initial-setup playbook in the workstream-B session history for the
full Part A (Proxmox provisioning) + Part B (systemd, Caddy, Samba, promotion
script) walkthrough.

## Files

- **`Caddyfile`** — canonical reverse-proxy + static-file serving config.
  The running copy lives at `/etc/caddy/Caddyfile` on the LXC. The two files
  should be kept in sync. Differences between this file and the running copy
  are a bug.

## ⚠ Auth — the per-tester bcrypt hashes are NOT in this file

The `basic_auth` block in `deploy/lxc/Caddyfile` contains **placeholder
comments**, not real bcrypt hashes. The live `/etc/caddy/Caddyfile` on the
LXC has the real hashes. These two copies are **intentionally out of sync**
for the auth block only — every other block should match.

**Do not cp this file verbatim to the LXC.** Doing so overwrites the real
hashes with empty comments, which means `basic_auth * { }` with no users,
which means every tester is locked out on the next reload. Caddy will not
complain about an empty user list; it just silently 401s everyone.

Safe reconciliation workflow when you need to update any other block:

```bash
ssh playground
# 1. Edit /etc/caddy/Caddyfile directly on the LXC, by hand, applying
#    the same change you made in deploy/lxc/Caddyfile in the repo
# 2. Or: copy the real basic_auth block aside, cp the repo file,
#    paste the real block back in, validate, reload:
sed -n '/basic_auth \* {/,/^    }/p' /etc/caddy/Caddyfile > /tmp/auth.snippet
cp /srv/playground/app/deploy/lxc/Caddyfile /etc/caddy/Caddyfile
# manually merge /tmp/auth.snippet into the new /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl reload caddy
```

### Adding a new tester

1. On the LXC as root: `caddy hash-password` → enter the tester's password
   twice → copy the resulting `$2a$14$...` string.
2. Create a Unix + Samba user with the same name:
   ```
   useradd -M -s /usr/sbin/nologin -g playground-testers <name>
   smbpasswd -a <name>   # same password as Caddy, for Finder SMB mount
   ```
3. Append a `<name> <hash>` line inside the `basic_auth * { }` block of
   `/etc/caddy/Caddyfile` on the LXC. Do **not** edit the repo copy.
4. `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`
5. `systemctl reload caddy`
6. Tell the tester their username (their first name), password, and point
   them at `docs/tester-onboarding.md`.

### Removing a tester

1. Delete the `<name> <hash>` line from `/etc/caddy/Caddyfile` on the LXC.
2. `systemctl reload caddy`
3. `smbpasswd -x <name> && userdel <name>` to revoke SMB access.
4. (Optional) revoke the tester's WireGuard client in UniFi.

### Future improvement (TODO, parked)

Move the hashes out of the Caddyfile and into environment variables loaded
by a systemd drop-in for `caddy.service`. Then `deploy/lxc/Caddyfile` can
be the single source of truth, no sync dance required. Blockers:

- Need to verify Caddy's `{env.VAR}` placeholder expands inside the
  `basic_auth` directive without edge cases — bcrypt hashes contain `$`
  characters and Caddy has multiple interpolator syntaxes, worth testing
  on a throwaway Caddy instance before trusting it on the real LXC.
- Need a systemd drop-in at `/etc/systemd/system/caddy.service.d/env.conf`
  with `EnvironmentFile=/etc/caddy/auth.env` (separate from
  `.env.live` — Caddy shouldn't read the same file that holds the
  Anthropic API key).

Not urgent; the current placeholder-in-repo approach works for 2 testers.
Revisit when the tester pool grows past a handful or when we want
password rotation to be a one-command operation.

## What is NOT here (and why)

- **`.env.live`** — contains the live Anthropic API key. Never committed.
  Lives only at `/srv/playground/app/.env.live` on the LXC, `chmod 640`,
  owned `root:playground`.
- **systemd unit** — `/etc/systemd/system/finflow-api-live.service`. Stable
  enough that drift is unlikely; if you change it, document the change here
  and copy the new version into this directory.
- **smb.conf** — the `[runs]` share stanza. Samba config is mostly default
  Ubuntu; the only FinFlow-specific lines are the `[runs]` share and the
  global `server min protocol = SMB2` hardening. Both can be reconstructed
  from scratch using the session playbook.
- **`update-live.sh`** — lives at `/srv/playground/app/update-live.sh` on
  the LXC, owned by the `playground` user. It's a short bash script; the
  session playbook has the full source if it ever needs to be recreated.

## Updating the running Caddyfile

When you change `deploy/lxc/Caddyfile` in this repo:

1. Commit and push the change to `playground-live` (via `live-promote`)
2. SSH to the LXC as root: `ssh playground`
3. Copy the file into place: `cp /srv/playground/app/deploy/lxc/Caddyfile /etc/caddy/Caddyfile`
4. Validate: `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`
5. Reload: `systemctl reload caddy`
6. Verify: `tail -f /var/log/caddy/playground-access.log` and hit an endpoint

This is deliberately manual. `update-live.sh` restarts the api service but
does **not** touch Caddy — a typo in the Caddyfile would otherwise take down
the entire tester environment mid-promotion, and we'd rather catch it with a
deliberate `caddy validate` step before applying.

## Bootstrapping a new LXC from scratch

If you ever need to rebuild the LXC (Proxmox restore, hardware migration,
etc.), use the workstream-B setup playbook as the primary reference. The files
in this directory are drop-in replacements for the hand-written configs in
that playbook — after the base container is up and packages are installed,
copy `Caddyfile` into `/etc/caddy/` and reload instead of generating it from
scratch. Do not re-add `uri strip_prefix /poc` inside the `handle /poc/*`
block — the Hono api mounts routes *at* `/poc`, so stripping the prefix
returns 404 for every dropdown endpoint. This mistake cost us ~30 minutes on
2026-04-09.
