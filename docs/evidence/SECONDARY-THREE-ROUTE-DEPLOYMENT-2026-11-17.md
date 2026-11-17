# Secondary node — three-route deployment and Happ subscription

**Date:** 2026-11-17
**Delivery status:** DONE. Three routes deployed and checked end to end from Windows. One private HTTPS subscription delivered and verified externally.
**Android evidence:** Happ showed successful connection checks for all three original profiles over mobile data. The screenshots came before the grouped subscription.

## Reproduce the deployment

1. **Identify the target.** Read the provider's authenticated provisioning message and match the target to the authorized new server. Try to obtain an independent SSH host-key fingerprint from the provider console. For this run the owner authorized first-contact trust after the console path was unavailable. Save the observed RSA key in a dedicated known-hosts file. Compare the saved key on each connection before sending authentication data and negotiate RSA-SHA2. Record the trust decision as TOFU. A mismatch stops the run.
2. **Inventory without writes.** Verify root access, Ubuntu release, architecture, interfaces, package tools, free space, listeners and failed units. Inspect firewall policy and upstream HTTPS access. Check the intended listeners, files, units, and service identities for conflicts again immediately before writing. Save private snapshots of the firewall, listeners and boot identity. Keep provider credentials, snapshots and raw logs on the authorized private surfaces.
3. **Pin the software and isolate each route.** Fetch the exact Xray and Hysteria2 releases from their upstream repositories and compare SHA-256 digests. Use Xray 26.11.9 for VLESS RAW/TCP REALITY with Vision (I) and VLESS XHTTP REALITY (II). Use Hysteria2 2.14.0 for TLS/QUIC (III). Give each route an independent service identity, systemd unit and credentials. Use separate TCP listeners for I and II and a UDP listener for III. Generate fresh client credentials and separate REALITY key pairs. Validate the REALITY cover's TLS support before using it. Generate a dedicated leaf certificate for III and pin it in the client. Apply restrictive permissions to configs and private keys.
4. **Stage and test one route at a time.** Validate each unit and execute Xray config tests before start. For III, confirm the native QUIC data path against the loopback listener when diagnosing external failures. Start the service, make three clean client connections, and check HTTP and HTTPS response bodies, DNS resolution through the test proxy, and two independent exit-IP services against the VPS egress. Restart the service and repeat. Stop/start that route and verify earlier routes through their own clients and listeners. Enable accepted services at boot. Roll back a failed stage by disabling and removing only its new unit, private config, user and stage-specific binary where applicable. Recheck previous routes after any rollback.
5. **Verify full reboot recovery and export.** Compare the boot identity across a controlled VPS reboot. Check that all three units are enabled and active, then repeat three independent client connections per route. Verify that the local export contains three distinct importable profiles. Keep the export under the Windows user's private profile with access limited to that user, SYSTEM and Administrators.
6. **Build the Happ subscription.** Take the accepted profile lines and alter only the URI fragments. Put the country flag first so Happ can use it as the icon. Append the common requested name and the Roman numerals I, II and III. Confirm that the URI content before the fragment is identical for each original profile. Join exactly three lines and encode them as a standard Base64 subscription body. Put the same shared name in the HTTP profile-title header.
7. **Serve the subscription as a separate HTTPS service.** Check availability of an independent HTTPS listener and the temporary ACME validation listener. Issue a publicly trusted IP-address certificate through Let's Encrypt HTTP-01 when a usable DNS name is unavailable. Keep the certificate key, subscription body and randomly generated 256-bit bearer token private. Pass them to an unprivileged service through systemd credentials. Require the exact token path, suppress request-path logging, disable response caching, and return 404 for invalid paths. Enable the service and a renewal timer, and restart only the subscription service when a new certificate is installed.
8. **Verify the delivery before handoff.** Check the trusted TLS listener from loopback and from an external Windows client. Verify the group title, the exact body digest, profile count, protocol order and decoded labels. Test the invalid-token response and simulate ACME renewal against staging. Recheck that all three VPN route units remain active. Deliver one private HTTPS URL to the owner for import from the Happ clipboard.

## Recovery notes

- FACT — The first Xray provisioning attempt stopped at key parsing and rolled back. The release used a combined public-key label in its output. Updating the parser and rerunning from a clean state resolved that failure.
- FACT — One Windows data-path probe timed out after a service restart. The original probe did not identify the endpoint in the error. The test was made more specific by using a faster HTTP probe, adding one bounded retry and reporting the failed probe name. The subsequent checks passed.
- FACT — Hysteria2 passed a real loopback data-path check while the default Windows path timed out at the QUIC handshake. Windows selected an existing Happ virtual adapter for the target. A process-local UDP relay pinned to the physical Windows interface permitted native Hysteria2 to pass externally. The relay did not change global routing or Happ settings. The specific cause of the timeout inside the former path was not established.
- FACT — The initial subscription attempt obtained a valid certificate, then the Windows SSH wrapper failed while printing a non-ASCII service-manager message. The transaction rolled back. Running the wrapper in UTF-8 and retrying resolved the issue. Test non-interactive terminal encoding before starting the transaction.

## Verification and limits

| Check | Result |
| --- | --- |
| Windows end-to-end data path, restarts and earlier-route regression | PASS for I, II and III |
| VPS reboot and fresh Windows connections | PASS, three per route |
| Android Happ with the original individual profiles | Successful in-app checks shown for I, II and III over mobile data |
| Private HTTPS subscription, exactly three profiles, title/labels and invalid token | PASS from an external Windows client |
| Certificate renewal simulation | PASS |
| Grouped subscription import, flag rendering and full traffic matrix on Android | Pending direct evidence |
| Android per-operator browser egress, independent DNS-leak testing and formal Wi-Fi/mobile matrix | Pending direct evidence |

The deployment and delivery are complete in the scope above. This record is a reproduction guide and evidence checkpoint for the secondary node. Formal acceptance of the grouped Android subscription and the original node's existing project status are tracked separately.
