# Captured product previews

These are Chromium captures of the implemented application using fictional, isolated demo data. They are not mockups. The workflow SVGs are rendered from the actual inactive JSON exports; they are not evidence of execution on n8n. No customer records, keys or live provider accounts appear here.

| View | Preview |
| --- | --- |
| Executive dashboard | [Overview](overview.png) |
| Midnight theme | [Dark dashboard](midnight-dashboard.png) |
| Arabic mobile | [RTL mobile](arabic-mobile.png) |
| Login | [Sign-in](login.png) |
| CRM | [Leads](leads-crm.png) |
| WhatsApp conversation | [Working sandbox](whatsapp-conversation.png) |
| WhatsApp studio | [New conversation](whatsapp-studio.png) |
| Inventory | [Properties](property-inventory.png) |
| Inbox | [Unified inbox](unified-inbox.png) |
| Appointments | [Viewings](appointments.png) |
| Follow-up tasks | [Tasks](follow-up-tasks.png) |
| Sales analytics | [Analytics](analytics.png) |
| Team | [Sales advisers](sales-team.png) |
| Intelligence | [Next best actions](sales-intelligence.png) |
| Automation | [Workflow studio and outbox](automations.png) |
| Integrations | [Channel setup](integrations.png) |
| Settings | [Company configuration](company-settings.png) |
| Actual intake architecture | [Rendered PNG](omnichannel-architecture.png) · [Scalable SVG](../diagrams/madar-omnichannel-intake.svg) |

![Executive dashboard](overview.png)

![WhatsApp sandbox conversation](whatsapp-conversation.png)

![Actual n8n intake graph](omnichannel-architecture.png)

The browser suite regenerates application captures in this directory. It requires a local API with demo mode on and external/model flags off. Repeated runs against one long-lived API can hit the deliberate 10-demo-sessions/5-minute rate limit; use a fresh isolated test API/container or wait for the window. The tests do not weaken that protection. All ten module diagrams regenerate using `scripts/generate_architecture.py`.

Typography is self-hosted Manrope and Noto Sans Arabic from the Google Fonts repository, with their SIL Open Font License texts bundled under `frontend/public/fonts/`. No font CDN request is required by the dashboard.

## Bilingual milestone

Actual fictional-data Chromium captures: [Arabic desktop](bilingual-arabic-desktop.png) and [Arabic mobile](bilingual-arabic-mobile.png). The English page previews are refreshed with the working language selector. Customer and listing names intentionally retain their original content.

## Enterprise runtime previews (11 October 2026)

- [Actual n8n intake canvas](actual-n8n-intake-canvas.png): imported 41-node workflow in an isolated n8n 1.113.3 editor; inactive.
- [Verified full-demo System Health](enterprise-verified-demo.png) and [Arabic version](enterprise-verified-demo-arabic.png): actual isolated n8n success, eight business outcomes, grounded agents; Windows/Meta explicitly unverified.
- [Provider-free System Health](system-health.png) and [Arabic version](system-health-arabic.png): queued local execution correctly remains unverified when n8n is absent.

All records are fictional. Runtime fixtures are disposable; owner Windows/n8n and live providers were not tested. SVG architecture artifacts represent the importable JSON directly.
