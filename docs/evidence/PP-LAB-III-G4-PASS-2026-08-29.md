# PP-LAB-III — G4 PASS — 2026-08-29

## Verdict

- `FACT` — `PP-LAB-III` построен как отдельный Hysteria2 service и прошёл полный acceptance на Android/mobile и Wi-Fi.
- `FACT` — подтверждены 3/3 clean reconnect на обеих целевых сетях, DNS/HTTP/HTTPS, два независимых exit-IP check, restart recovery и stop/start recovery/isolation.
- `FACT` — leak-oriented browser DNS test на Wi-Fi не выявил резолверов обычного доступа; наблюдались только сторонние публичные Cloudflare/Google resolvers в США.
- `FACT` — после добавления `PP-LAB-III` ранее принятые `PP-LAB-I` и `PP-LAB-II` прошли обязательную regression-проверку на Wi-Fi и mobile: 3/3 clean reconnect с полным data path для каждого маршрута на каждой сети.
- `DECISION` — `G4 / PP-LAB-III: PASS`.
- `DECISION` — весь трёхмаршрутный экспериментальный набор `PP-LAB-I + PP-LAB-II + PP-LAB-III` принят по текущему protocol baseline.

## Evidence record

```text
Evidence ID: PP-LAB-III-G4-PASS-2026-08-29
UTC timestamp: 2026-08-29T00:14:00Z
Device-local checkpoint: 2026-08-29 03:14 UTC+3
Route: PP-LAB-III
Server software/version: Hysteria2 v2.12.1; upstream SHA-256 verification PASS
Client: Happ for Android; exact app version not independently captured in this checkpoint
Networks: Android mobile + Wi-Fi
Expected: independent PP-LAB-III operation with reproducible full data path, restart recovery, stop/start isolation, no detected DNS leak by the accepted browser method, and no regression of PP-LAB-I/II
Actual: PASS
DNS resolution: PASS
HTTP: PASS
HTTPS: PASS
Exit-IP match via two independent endpoints: true
Mobile clean reconnect: 3/3 PASS
Wi-Fi clean reconnect: 3/3 PASS
Restart recovery: PASS
Stop/start recovery: PASS
Isolation from PP-LAB-I/II: PASS
PP-LAB-I regression after adding III: Wi-Fi 3/3 PASS; mobile 3/3 PASS
PP-LAB-II regression after adding III: Wi-Fi 3/3 PASS; mobile 3/3 PASS
Leak-oriented browser DNS check on Wi-Fi: PASS for the accepted project method
Verdict: PASS
```

## Architecture accepted for Stage 4

- `PP-LAB-III` uses Hysteria2 over QUIC/UDP with a dedicated UDP listener.
- The service is separate from the two Xray routes and has its own systemd unit, system user, configuration and client credential.
- Instead of requiring a domain/ACME dependency for this laboratory route, the owner explicitly accepted self-signed TLS with certificate pinning (`pinSHA256`) as the Stage 4 architecture.
- Client verification uses the pinned certificate fingerprint; plain `insecure` without pin is not the accepted security model.
- The accepted Hysteria2 version is `v2.12.1`; the downloaded binary passed upstream SHA-256 verification before installation.

## Sanitized observations

1. Read-only preflight confirmed both accepted Xray routes active, Hysteria2 absent, sufficient memory/disk, and the selected UDP listener free.
2. The first installer attempt stopped cleanly because the expected checksum asset path for an older planned version did not match upstream. Automatic rollback removed the partial Hysteria2 binary/config state; I and II remained active and the UDP listener remained free.
3. A distinguishing read-only diagnostic isolated the failure to checksum-asset retrieval while binary retrieval itself worked. The build plan was then explicitly re-approved for Hysteria2 `v2.12.1`.
4. The successful build verified upstream SHA-256, generated a dedicated self-signed certificate and random auth credential locally on the server, created a dedicated service identity/unit and started the listener. Client material was transferred only to the private POCO/Termux storage and removed from temporary server-side transport storage.
5. The server build confirmed both Xray configurations remained byte-identical and both accepted Xray units stayed active.
6. Mobile acceptance III: 3/3 clean reconnect; DNS/HTTP/HTTPS and two independent exit-IP checks passed in every round.
7. Wi-Fi acceptance III: 3/3 clean reconnect; DNS/HTTP/HTTPS and two independent exit-IP checks passed in every round.
8. Leak-oriented browser DNS test on Wi-Fi showed only public Cloudflare/Google resolvers in the United States and did not expose resolvers from the ordinary access provider; under the project's accepted browser-based method this is `DNS leak PASS`.
9. Restart recovery III: a test-harness issue caused an expected curl timeout during the restart window to terminate the local shell early. A single read-only post-restart diagnostic showed I/II/III all active, III data path restored, and the III process PID changed across restart. The route restart itself therefore passed; the false interruption was classified as a harness defect.
10. Stop/start isolation III: server-side auto-recovery was scheduled before stop. During the stopped state III became `inactive` while I and II remained `active`; after automatic start III returned `active` and the full data path passed again.
11. Final mandatory regression after adding III: `PP-LAB-I` and `PP-LAB-II` each completed 3/3 clean reconnect on Wi-Fi and 3/3 on mobile with DNS/HTTP/HTTPS and two independent exit-IP checks passing.

## Security / publication boundary

This evidence intentionally excludes the working server IP/hostname, ports beyond generic protocol description, auth credential, certificate fingerprint/pin, private certificate key, client URI, complete client config, subscription material and raw server logs/configs.

A prior `PP-LAB-II` client URI exposure in a local Termux traceback remains a separate maintenance/security TODO. It does not alter the functional acceptance result of G4.

## Final gate state

```text
G0 — PASS
G1 — PASS
G2 / PP-LAB-I — PASS
G3 / PP-LAB-II — PASS
G4 / PP-LAB-III — PASS
```

The experiment now has three manually selectable, independently accepted routes on one VPS. This provides transport diversity, not host-level high availability: the VPS/public network path remains a shared failure domain.
