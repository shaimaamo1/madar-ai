# WhatsApp Business: sandbox first, official Meta API when authorized

## Try the working system without credentials

Run the existing Windows launcher, open **Open interactive demo**, then select **WhatsApp studio**. Record fictional opt-in, send an Egyptian Arabic or English inquiry, and inspect intent, qualification, adviser assignment, matching inventory and CRM history. Try:

- `عايز شقة في التجمع، ميزانيتي خمسة مليون، تلات غرف و١٨٠ متر وحمام سباحة`
- `Can I book a viewing?` → choose **Book viewing**, confirm the listing, adviser and explicit future time.
- `عايز مستشار يكلمني` → persistent handoff; later inquiries are recorded without automated replies. **Resume assistant** explicitly restores it.
- `متبعتش رسائل تاني` → opt-out; `موافق على المتابعة` → explicit re-opt-in.

The studio works only in an isolated fictional demo tenant. Its endpoint is authenticated, administrator-only and subject to the browser origin guard. It never queues provider delivery or invokes a model. Sandbox contacts retain a `sandbox:` identity; the dispatcher refuses these contacts even if an operator later enables real sending. Replay IDs are scoped to tenant/channel and cannot be reused for another sandbox contact.

## What is implemented

MADAR receives Meta's exact signed webhook body at **`POST /webhooks/meta`**, responds to the challenge at **`GET /webhooks/meta`**, normalizes text messages into the tenant CRM, and stores inbound/outbound conversation history atomically with event receipts and the outbox. Verified webhook receipt is not delivery permission. A dedicated WhatsApp workflow uses the server-side adapter at `https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages`; it does not embed Meta tokens in n8n.

The deterministic assistant understands explicit budgets (including common spoken Egyptian numbers), regions, buy/rent intent, property type, bedrooms, minimum area and a bounded amenity vocabulary. It remembers recorded preferences across turns and uses only available inventory matching all constraints. Replies use Egyptian Arabic when the inquiry contains Arabic. A separately gated model can interpret explicitly quoted preferences; it cannot invent listing facts or book times. This is domain-specific qualification, not unrestricted generative conversation. Negated or complex requests should be checked by an adviser; forms provide authoritative preference editing.

Appointment booking needs an explicit customer, inventory listing, active adviser and timezone-aware future time. SQLite transactions protect adviser, listing and customer conflicts. n8n booking events additionally bind a stable event ID to the exact request hash, so retries return the original confirmation and changed payloads return 409.

## Future live configuration — requires owner authorization

No live account is configured or verified by this upgrade. Before any live test:

1. In [Meta for Developers](https://developers.facebook.com/docs/whatsapp/cloud-api/), configure the correct business/app, WhatsApp Business Account and phone number. Obtain the appropriate provider-issued token and scopes; follow Meta's current business verification and app/phone onboarding requirements.
2. Keep `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `META_APP_SECRET`, and `WHATSAPP_VERIFY_TOKEN` in private server settings. The app secret verifies HMAC; the challenge verify token is a separate random secret. Use the local secret file protected by the Windows launcher or a managed secret store in an approved deployment. Do not use browser variables, Git, screenshots or chat. The n8n API key is separate and does not authorize Meta.
3. Bind exactly the tenant that owns the provider channels using `MADAR_INTEGRATION_WORKSPACE` or `MADAR_INTEGRATION_TENANT_ID`. This release supports one provider-tenant binding per deployment; separate client deployments are required for separate credentials.
4. With approval, provide a public HTTPS callback ending in `/webhooks/meta`, subscribe to WhatsApp message events and complete Meta's verification challenge. Windows localhost is not a public webhook callback. The launcher does not create a tunnel, open firewall ports, change n8n, or publish a service. Do not point Meta at n8n's normalized JSON intake: raw-body signature verification belongs at MADAR.
5. Verify read-only phone access through **Integrations → WhatsApp Business → Verify access** after credentials and account ownership are authorized. This check alone does not prove delivery.
6. After explicit approval of recipients, templates, consent and costs, perform an official Meta test-account exchange. Check inbound signature validation, replay suppression, CRM state, handoff, opt-out, service-window expiry, template parameters, delivery statuses and failed/uncertain outcome reconciliation. Keep actual customers out of this verification.

The Windows Compose configuration deliberately forces `MADAR_ALLOW_EXTERNAL_SEND=false` and `MADAR_ALLOW_MODEL_USAGE=false`. Supplying tokens or activating an n8n workflow cannot bypass those flags. This guide does not enable them. An approved live deployment requires a separately reviewed configuration. Workflows remain inactive after import.

## Delivery policy and limitations

- Customer opt-out blocks all delivery. Proactive follow-up needs recorded consent; explicit re-opt-in clears opt-out and records an audit event. Operator changes record their actor and time.
- Free-form WhatsApp delivery requires an inbound WhatsApp message within the last 24 hours. Website chat does not open the WhatsApp window.
- Outside that window, use a template approved in Meta for that language and purpose. **Unified inbox → Queue approved template** accepts text body parameters in the exact approved order (`|` separator in the UI). Header media, buttons, carousel templates, audio and image parsing are not implemented. Provider approval and account restrictions remain authoritative; the app does not claim to verify template approval locally.
- Persistent human takeover pauses automated replies and sales-task/reactivation queues; appointments can still create consented reminders. Handoff tasks are never treated as customer follow-up messages. Resume is an explicit, audited operation.
- 429/5xx responses retry with exponential backoff and a five-attempt cap. The fifth failure becomes Failed. Network uncertainty becomes Uncertain, is not blindly replayed, and opens a deduplicated operator incident when reconciliation runs. Provider statuses update outbox delivery records.
- The Error Monitor records only sanitized workflow/execution identifiers and a fixed incident category. Customer bodies and provider error strings are not copied into incident records. n8n success/error execution retention is disabled in exports; review your n8n instance's own history/backup/access policies.
- Human replies are recorded and queued only through the same dispatcher gates. Queueing a reply or template is not proof it was sent.

See [workflow contracts](workflow-architecture.md), [verification report](premium-verification.md) and [Windows startup](windows.md). No real message, workflow activation or billable model request is authorized by these files.
