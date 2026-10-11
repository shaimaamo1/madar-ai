# Connected Egyptian real-estate demo

The isolated **Open interactive demo** workspace now loads 30 fictional listings, 40 fictional customers, 25 four-message conversation threads (100 messages), 15 viewing records, 20 follow-up tasks and five sales agents plus the demo administrator. Data is stored in the real application tables and connected by tenant, customer, property and adviser IDs. It is not a screenshot or a separate fake-number dashboard.

## Enable locally

From PowerShell in the existing repository:

```powershell
.\Update-Madar.cmd
```

In MADAR, sign out of the real company workspace and choose **Open interactive demo**. This creates a separate demonstration tenant; it does not convert or clear the real workspace, and logging out does not stop its Telegram poller. The dataset is already present. The banner's **Load Demo Data** button safely fills missing generated records without duplicates. **Reset demo** restores generated records only. No edits to n8n JSON or PowerShell scripts are required.

The demo login is available only when the existing local demonstration mode is enabled. Load/reset require an administrator and a tenant marked `demo=1`; real-company requests return 403. Older demo workspaces and their untracked starter/custom records are preserved. Open a fresh interactive demo for the exact new dataset counts.

## Inventory and illustrations

Listings cover apartments, villas, duplexes, penthouses, offices and commercial units in New Cairo, Fifth Settlement, New Capital, Sheikh Zayed, 6th of October, Maadi and North Coast. Prices are illustrative EGP purchase values or monthly rents; each listing includes area, applicable bedrooms, amenities, availability, description and a stable **DEMO-EG-001 … DEMO-EG-030** reference. Availability includes Available, Reserved, Sold and Rented examples. Additional property categories are accepted by the CRM/inventory forms and shared backend matching/qualification.

All 30 images are bundled, original SVG architectural illustrations with a CC0 dedication, served from `/demo-assets/`. They require no image host or network access. They are **synthetic illustrations, not photographs of verified properties**. Each listing card, description and reference identifies DEMO / FICTIONAL; the workspace also displays a persistent demo banner. See [asset license](../backend/demo_assets/LICENSE.md). Reproduce assets with `python -m scripts.generate_demo_assets`; no generated asset is substituted for a functional workflow.

## CRM, conversations and calendars

Names are fictional Egyptian profiles. Phone fields are empty, emails use reserved `demo.invalid`, and every seeded contact ID starts with `sandbox:`. Preferences match the linked inventory; a deliberately unmatched Aswan inquiry demonstrates honest no-match handling. Profiles cover all lead sources and pipeline stages and are assigned across five fictional advisers. Twenty-five Arabic/English threads cover qualification, inventory, viewing details, budget review, follow-up consent and two persistent human handoffs. Viewing records include completed, booked and cancelled states, with consistent relationships, local business hours and no overlapping active resource reservations.

All records are inserted directly by the seeder. It never calls chat/model providers, n8n, webhook registration, delivery dispatch, external calendars or notifications. Initial outbox is empty. Even if someone manually runs demo automation, existing provider delivery guards refuse all seeded `sandbox:` contacts. The real Telegram bot/token and configuration are not read or modified by generation/reset.

## Repeat loading and reset

Deterministic tenant-scoped IDs and a stable anchor timestamp make repeated loading preserve existing generated rows and avoid duplicates. `demo_seed_records` tracks only records created by this dataset; `demo_datasets` stores its version/anchor. Database migrations add these tables without rewriting existing customer data.

Reset removes/recreates tracked generated records in one transaction. Records added interactively, Telegram rehearsals, other tenants, sessions and production integration state are preserved. Generated parents referenced by added records are retained to prevent cascaded deletion or broken bookings/messages; their generated adviser relationships are retained as needed. Consequently, a used demo can contain more than the baseline counts after reset. The reset response reports retained references. A new demo tenant offers a clean presentation without deleting prior work.

## Analytics and limits

Lead sources, pipeline stages, demand by area, appointment activity, agent lead/viewing workload and completed/pending follow-ups are computed from the actual tenant records. The baseline has five completed follow-ups out of twenty and no sales/deals/earned commissions; **revenue and sales volume begin at zero**. Won lead stages are fictional scenario states and do not manufacture a financial transaction. UI labels explicitly identify fictional CRM data and demo analytics.

The 14 existing n8n exports and their 327 executable nodes are unchanged. Their original four-category qualification enum gate remains unchanged too: expanded categories work in the CRM/inventory/shared backend, but passing Duplex/Penthouse/Commercial through that particular n8n gate requires a separately authorized workflow update. Demo generation does not invoke those workflows.

## Verification

- Full Python regression suite: **137 passed, one native Windows ACL test skipped**; dataset tests verify exact counts, references, non-overlapping bookings, 30 image responses, actual analytics, repeat loading and selective reset.
- Isolation test preserves a real-company inventory item, booking, Telegram customer/history, webhook receipt and outbox byte-for-byte while loading/resetting a separate demo. Real-workspace load/reset is denied.
- Browser test loads all 30 images, edits a bundled-image listing, repeats Load, preserves an added customer after Reset, and checks analytics, Arabic RTL and mobile overflow. The existing Telegram demo browser journey also passes.
- **Four frontend localization tests and production build passed. Two browser journeys (new dataset and existing Telegram demo) passed.** Cached-dependency Linux Docker startup also passed with all 30 bundled image responses, exact record counts, Load/Reset and an empty outbox. A fresh dependency download build was not repeated; the previous Cloud DNS limitation remains distinct from this cached runtime check. Windows execution and the owner's live Telegram/n8n installation are not tested in Cloud. No live external messages or bookings are created by these checks.
