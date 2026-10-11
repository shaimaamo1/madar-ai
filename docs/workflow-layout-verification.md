# Clean n8n workflow layout verification

All **14 actual JSON exports** now contain **327 executable nodes and zero decorative nodes**. Forty Sticky Notes (including all colored section panels) were removed. Node IDs, names, versions, parameters, credentials, retries, error behavior, workflow settings and connections are preserved exactly; only positions and decorative nodes changed. A frozen pre-change semantic fingerprint for each workflow enforces this in regression tests.

Nodes are aligned on a deterministic 320-pixel horizontal / 260-pixel vertical grid. Every execution connection runs left to right; alternate branches use separate lanes. Regeneration preserves the clean layouts. The application catalog uses the same actual exports. No images, screenshots or mockups were generated for this change.

| Check | Result |
| --- | --- |
| All 14 workflow contracts and 327 functional nodes preserved | PASS |
| No Sticky Notes or decorative panels in exports | PASS |
| Deterministic layout, forward connections, node spacing | PASS |
| Lost-manifest recovery of decorated versions; two updates retain all 14 IDs without workflow POSTs | PASS |
| Python regression suite | PASS — 113 passed, 1 native Windows ACL test skipped |
| Frontend localization unit tests | PASS — 4 passed |
| Frontend TypeScript and production build | PASS |
| Actual isolated n8n 1.113.3 import/reimport and stored layouts | PASS — all 14 stored layouts match; eight-module demo and error checks passed ([evidence](n8n-runtime-acceptance.json)) |
| Windows PowerShell 5.1 and owner's local n8n | NOT VERIFIED |
| Live provider messaging | NOT VERIFIED; disabled, no real messages sent |

The runtime fixture uses only disposable Cloud/Linux containers, temporary fictional data and temporary credentials. It does not access the owner's laptop, `.env`, customer database or persistent Docker volumes. It imports inactive exports, executes the fictional Full Demo and verifies all eight business modules, appointment conflicts, provider suppression and redacted failure handling. The stored-layout check reads all fourteen workflows back through the real n8n API and compares node IDs/positions and connections with the exports.

## Windows update

From PowerShell in the existing MADAR checkout:

```powershell
.\Update-Madar.cmd
```

The existing updater pulls `codex/self-hosted-n8n`, rebuilds MADAR and updates workflows in the existing n8n at the configured address (normally `http://localhost:5678`). Existing private configuration is reused. No host Node.js/Python installation or duplicate n8n container is needed. Workflow recovery recognizes both current clean graphs and known historical decorated graphs; ambiguous/unrelated same-name workflows and active workflows are refused safely. Deactivate any managed active workflow before updating.

Refresh an open n8n workflow editor after the report passes. Choose the n8n Light theme if a white/light dotted canvas is desired: theme is an editor preference and cannot be enforced by workflow JSON. Do not import these files manually as new workflows. Do not enable workflows or customer delivery merely to apply layouts.

Historical diagram/screenshot assets were left untouched and do not show the current layout. The actual JSON exports and updated n8n editor are authoritative.
