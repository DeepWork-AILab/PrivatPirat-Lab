# Foxy Baby — hardening / firewall / post-reboot checkpoint

**Date:** 2026-09-04 (morning, MSK)  
**Status:** `MAINTENANCE / POST-REBOOT OPERATIONAL PASS`  
**Scope:** provider-diverse secondary VPS used for three independently selectable PrivatPirat transport profiles. This record does **not** replace the accepted `PP-LAB-01` G2/G3/G4 baseline and does not by itself promote Foxy Baby to a formal protocol gate PASS.

## Evidence boundary

- This is sanitized public evidence.
- Working IP/hostname, SSH host-key fingerprint, selected ports, client identifiers, UUIDs, REALITY material, Hysteria credentials, TLS private material, working URIs, subscription URLs and raw configs/logs are intentionally omitted.
- Raw diagnostics and rollback backups remain outside Git.

## Starting point

- `FACT` — all three Foxy Baby transport profiles were already deployed and usable before this maintenance window.
- `FACT` — Route I uses VLESS/TCP/REALITY, Route II uses VLESS/XHTTP/REALITY, and Route III uses Hysteria2/TLS/QUIC.
- `FACT` — client checks showed that all three profiles use the same provider egress identity; transport switching therefore does not create IP-reputation diversity.
- `FACT` — the server exposed password-based SSH access before hardening and had received automated password-guess traffic.

## SSH hardening

The maintenance window first established a fresh independent key-only login before removing password access. Timestamped rollback backups were created before SSH policy changes.

Final effective SSH state:

- `FACT` — public-key authentication is enabled.
- `FACT` — password authentication is disabled.
- `FACT` — keyboard-interactive authentication is disabled.
- `FACT` — direct root SSH login is disabled.
- `FACT` — `MaxAuthTries` is reduced to `3`.
- `FACT` — a fresh post-change key-only login succeeded.
- `FACT` — the administrative non-root account has non-interactive sudo capability for routine maintenance, so normal operations no longer require repeated password entry.

`DECISION` — day-to-day Foxy Baby administration is key-only; passwords are retained only as recovery material outside the public repository.

## Inbound firewall

A dedicated nftables input policy was introduced only after SSH key access and rollback were proven.

- `FACT` — a pre-change nftables snapshot was saved outside Git.
- `FACT` — deployment used a temporary automatic rollback timer before persistence was committed.
- `FACT` — the firewall input chain has default-drop semantics.
- `FACT` — established/related traffic, loopback, required ICMP/IPv6-ICMP and minimal DHCP safety traffic are allowed.
- `FACT` — inbound application exposure is limited to SSH plus the three intended PrivatPirat route listeners.
- `FACT` — the candidate ruleset passed syntax validation before activation.
- `FACT` — a fresh SSH session and external route-listener checks passed while the temporary firewall was active.
- `FACT` — only after those checks passed was firewall persistence enabled and the emergency rollback timer disarmed.

`DECISION` — no change was made to global outbound policy, forwarding policy or VPN route configuration during this firewall step.

## Controlled reboot and recovery

A controlled reboot was performed after SSH and firewall hardening.

- `FACT` — the node booted a newer installed Ubuntu kernel (`6.8.0-139-generic`; pre-reboot kernel was `6.8.0-138-generic`).
- `FACT` — the reboot-required flag was cleared after boot.
- `FACT` — failed systemd units after reboot: `0`.
- `FACT` — the dedicated firewall returned automatically and its ruleset was present after boot.
- `FACT` — all three PrivatPirat route services returned `active` and remain configured for boot persistence.
- `FACT` — the two TCP route listeners were externally reachable after reboot.
- `FACT` — the Hysteria2 UDP listener was present after reboot.
- `FACT` — fresh key-only SSH administration remained available after reboot.

`DECISION` — infrastructure-level post-reboot recovery for Foxy Baby is accepted as PASS for this maintenance checkpoint.

## Client-side post-reboot observation

Android/Happ was used after the controlled reboot to exercise each route individually.

- `FACT` — Route I connected and normal traffic used the expected Foxy Baby egress identity.
- `FACT` — Route II connected and normal traffic used the same expected egress identity.
- `FACT` — Route III initially produced one transient TLS-handshake error immediately after the reboot window, then Happ retried and established the connection without a server change.
- `FACT` — after the retry, Route III carried normal traffic through the same expected egress identity.
- `FACT` — ChatGPT was usable through Foxy Baby during the final operational check, whereas the operator had observed application-level failures through this node on the previous day.

`DECISION` — the ChatGPT result is recorded as an operational observation, not as evidence that SSH/firewall hardening caused the application to start working.

`HYPOTHESIS` — the previous-day application failure may have involved transient client/session/network or anti-abuse behavior; current evidence does not isolate the cause.

## Formal acceptance boundary

This checkpoint is deliberately narrower than the repository's full route acceptance protocol.

- `FACT` — post-reboot infrastructure recovery is proven.
- `FACT` — each route was exercised from the Android client after reboot.
- `FACT` — the observations in this maintenance window do not constitute the full protocol matrix of repeated clean reconnects, DNS checks, multiple independent HTTP/HTTPS endpoints, dual exit-IP checks, both target network classes, and per-route stop/start regression.

`DECISION` — do not label Foxy Baby as a new formal G2/G3/G4 node solely from this maintenance record.

## Next actions

- `TODO` — keep the now-working server configuration frozen unless a concrete failure or approved maintenance change requires another write.
- `TODO` — before giving access to other people, create recipient-specific client credentials/links rather than distributing the operator's own client credentials.
- `TODO` — if Foxy Baby is to become a formally accepted provider-diverse backup node, run the complete acceptance protocol and record a separate sanitized evidence file.
- `TODO` — after recipient-specific credentials exist, define revocation/rotation handling so one recipient can be removed without rotating every other user.

## Maintenance verdict

`SSH_KEY_ONLY=PASS`  
`PASSWORD_SSH_DISABLED=PASS`  
`ROOT_SSH_DISABLED=PASS`  
`PASSWORDLESS_ADMIN_SUDO=PASS`  
`INPUT_FIREWALL=PASS`  
`FIREWALL_REBOOT_RECOVERY=PASS`  
`ROUTE_I_REBOOT_RECOVERY=PASS`  
`ROUTE_II_REBOOT_RECOVERY=PASS`  
`ROUTE_III_REBOOT_RECOVERY=PASS`  
`FAILED_SYSTEMD_UNITS=0`  
`ANDROID_POST_REBOOT_OPERATIONAL_CHECK=PASS`  
`CHATGPT_OPERATIONAL_OBSERVATION=PASS`  
`FORMAL_NEW_NODE_GATE=NOT_CLAIMED`
