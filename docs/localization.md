# Arabic and English interface

Updated 11 October 2026. The application uses matching English and Arabic catalogs with 760 entries. The language selector offers **العربية (AR)** and **English (EN)** on login, the dashboard, editing dialogs and the public inquiry portal. It changes the interface immediately and persists `madar-language` in this browser's local storage. Closing/reopening a normal browser profile retains the preference; clearing site storage removes it.

The thirteen dashboard pages, navigation, forms, buttons, empty states, notices, validation/errors, consent/delivery statuses, CRM stages, analytics, sales recommendations and displayed workflow labels use the shared catalog. Arabic uses professional real estate terminology for Egypt and the Gulf. Arabic uses Noto Sans Arabic and RTL; English uses Manrope and LTR. MADAR AI retains its identity. The licensed fonts are bundled locally.

Language changes never reload the application, change React keys, remount form controls, translate API payloads or rewrite data. Unsaved input, selected options, searches, comparisons, consent checkboxes and unsent messages stay intact. Dialogs have their own selector inside the existing keyboard focus trap. Standard/custom stages still retain their canonical stored names. Customer/company names, property titles/descriptions, custom notes and original conversations stay in their source language. Locale selection is separate from the company's default **customer** language.

`Intl` formats Arabic numerals, percentages and EGP/SAR/AED/USD currencies. Dates use the company's configured timezone; the public company endpoint now exposes only the additional non-sensitive timezone field. The inquiry trend explicitly uses UTC buckets and labels. Machine identifiers, environment variable names and integration brands remain unchanged. Workflow graphs retain the actual left-to-right source topology, with Arabic text direction/anchors and translated tabs, node names and stage groups. Downloads remain original importable source JSON.

Verified-data property marketing previews switch language and format listing facts without publishing. Unknown runtime errors receive a generic localized message; known API and native-browser validation errors provide translated guidance without raw exception/credential details. Existing backend response contracts remain unchanged apart from the public timezone addition.

## Verification

- Four unit tests check matching catalog keys/interpolation, Arabic coverage, untranslated literal detection, canonical input/key preservation, all actual workflow labels and locale formatting.
- Five new Chromium journeys check persisted/instant switching, DOM/control and form value preservation, canonical data saved via the real API, every Arabic page, every workflow module, desktop/mobile overflow, accessibility, unsent messages, search/comparison/settings state, login/network/server/native validation messages, and public inquiry/booking confirmations.
- The nine original browser journeys continue to exercise the business workflow and English light/dark accessibility, keyboard dialogs, mobile RTL and WhatsApp sandbox safeguards.
- Screenshots: [Arabic desktop](previews/bilingual-arabic-desktop.png), [Arabic mobile](previews/bilingual-arabic-mobile.png), and the refreshed [English gallery](previews/README.md).

The tests use isolated fictional data with external sending, n8n and paid models disabled. Automated axe scans are useful evidence, not a full accessibility certification. See the [current verification report](bilingual-verification.md) for actual results and remaining local checks.

## Maintaining translations

Add each new interface key to both `frontend/src/locales/en.json` and `ar.json`; preserve identical `{placeholder}` names. Render interface text with `tr`, known dynamic labels with `localize`, and numbers/dates/money with the shared formatters. Preserve user-authored content, control values, keys and wire formats. The source checks reject raw interface JSX text or translated editable values/identities.

```bash
npm --prefix frontend run test:unit
npm --prefix frontend run build
# Use your own isolated demo API serving the freshly built frontend:
MADAR_E2E_BASE_URL=http://localhost:8000 npm --prefix frontend run test:e2e
```

The fourteen browser tests create exactly ten fictional workspaces in a successful run. Repeat testing against the same API may hit its existing ten-demo-creations/five-minute limit; use a fresh owned test process or wait, without weakening that limit.
