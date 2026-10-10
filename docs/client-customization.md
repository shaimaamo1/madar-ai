# Client onboarding and customization

An administrator can provision a new client workspace from Company settings. This creates a separate empty tenant and an owner account with an Argon2 password hash. No seed data is copied. Sign in using its workspace slug, owner email, and privately supplied initial password; then change that password. No invitation email is sent automatically.

The Company settings onboarding checklist leads through branding, inventory, team, and external channels. Set company name/details, logo HTTPS URL, accent color, currency, customer language, Cairo/Dubai/Riyadh/UTC business timezone, business hours, assistant name and personality, new-lead follow-up delay, and custom CRM stages. Core stages are retained because domain operations use their meanings. The UI has English and Arabic navigation, RTL layout, and light/dark preferences; some operational labels remain English and require localization review before an Arabic-only commercial rollout.

Add actual verified inventory, prices, area, bedrooms, amenities, and availability. Set listing currency consistently within each tenant. Invite agents by creating accounts with secure initial passwords. Administrators may deactivate users and revoke their sessions; password changes revoke existing sessions. Deactivated agents receive no new automated assignments. Existing lead assignments remain visible and can be reassigned.

The rules assistant’s supported area aliases are in `backend/domain.py`. Unrecognized areas can be entered directly in customer preferences. Real model access is optional and is checked separately. Never advertise complete dialect comprehension or unlimited AI service without measuring performance on that client’s inquiries.

Connect the website portal with the client workspace slug. Add authorized external channels one at a time using secure per-deployment variables and a tenant binding. This version supports multiple isolated CRM workspaces but one provider integration tenant per deployment. Additional tenants’ WhatsApp, Telegram, and n8n credentials need separate instances/bindings or a future encrypted per-tenant integration store. Do not reuse one company’s provider credentials for another.

Use fictional demo reset only in demo companies. Populate real client properties before recommendations are enabled; do not convert fictional demo listings into client inventory. Record consent based on evidence collected by the client. Changing a checkbox is not itself proof of lawful consent.
