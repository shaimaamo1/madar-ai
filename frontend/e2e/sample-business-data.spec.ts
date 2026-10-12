import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Run only against an explicitly designated, disposable fixture server. Never
// use the laptop's real tenant or bot for an automated sample import/reset.
test("real-tenant sample confirmation, bilingual UI, 30 photos and safe removal", async ({
  page,
}) => {
  test.skip(
    process.env.MADAR_SAMPLE_E2E_FIXTURE !== "true",
    "Requires disposable real-workspace fixture",
  );
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("Workspace", { exact: true }).fill("madar");
  await page.getByLabel("Email", { exact: true }).fill("admin@madar.local");
  await page
    .getByLabel("Password", { exact: true })
    .fill("TestOnlyPassword123!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  const panel = page.getByRole("region", {
    name: "Sample business data",
    exact: true,
  });
  await panel
    .getByRole("button", { name: "Load Sample Business Data", exact: true })
    .click();
  await expect(
    panel.getByRole("button", { name: "Confirm import", exact: true }),
  ).toBeDisabled();
  expect(
    (await page.request.get("/api/state").then((r) => r.json())).properties,
  ).toHaveLength(0);
  await panel.getByRole("checkbox").check();
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(
    page
      .getByRole("region", { name: "بيانات أعمال تجريبية", exact: true })
      .getByRole("checkbox"),
  ).toBeChecked();
  await page
    .getByRole("combobox", { name: "لغة الواجهة", exact: true })
    .selectOption("en");
  await panel
    .getByRole("button", { name: "Confirm import", exact: true })
    .click();
  await expect(panel.getByRole("dialog")).toHaveCount(0);
  await expect(panel.getByRole("status")).toContainText(
    "Sample dataset loaded",
  );
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  let state = await page.request.get("/api/state").then((r) => r.json());
  expect(state.properties).toHaveLength(30);
  expect(state.leads).toHaveLength(40);
  expect(state.appointments).toHaveLength(15);
  expect(state.tasks).toHaveLength(20);
  expect(state.messages).toHaveLength(100);
  expect(state.outbox).toHaveLength(0);
  expect(state.users.filter((u: any) => u.sample && !u.active)).toHaveLength(5);
  const original = state.properties.map((p: any) => p.id).sort();
  await panel
    .getByRole("button", { name: "Load Sample Business Data", exact: true })
    .click();
  await panel.getByRole("checkbox").check();
  await panel
    .getByRole("button", { name: "Confirm import", exact: true })
    .click();
  await expect(panel.getByRole("dialog")).toHaveCount(0);
  state = await page.request.get("/api/state").then((r) => r.json());
  expect(state.properties.map((p: any) => p.id).sort()).toEqual(original);
  await page
    .getByRole("navigation", { name: "Workspace pages" })
    .getByRole("button", { name: "Property inventory", exact: true })
    .click();
  const images = page.locator(".property-image img");
  await expect(images).toHaveCount(30);
  for (const image of await images.all()) {
    await image.scrollIntoViewIfNeeded();
    await expect
      .poll(() =>
        image.evaluate(
          (e: HTMLImageElement) => e.complete && e.naturalWidth > 0,
        ),
      )
      .toBe(true);
  }
  await expect(
    page.locator(".property-body").getByText(/Sample \/ Fictional/),
  ).toHaveCount(30);
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("ar");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 1280, height: 720 });
  await page
    .getByRole("combobox", { name: "لغة الواجهة", exact: true })
    .selectOption("en");
  await panel
    .getByRole("button", { name: "Remove Sample Business Data", exact: true })
    .click();
  await expect(
    panel.getByRole("button", { name: "Confirm removal", exact: true }),
  ).toBeDisabled();
  await panel.getByRole("checkbox").check();
  await panel
    .getByRole("button", { name: "Confirm removal", exact: true })
    .click();
  await expect(panel.getByRole("dialog")).toHaveCount(0);
  state = await page.request.get("/api/state").then((r) => r.json());
  expect(state.properties).toHaveLength(0);
  expect(state.leads).toHaveLength(0);
  expect(state.users).toHaveLength(1);
  expect(errors).toEqual([]);
});

// Authenticated synthetic Telegram updates exercise the genuine intake path;
// polling and delivery stay disabled. This is not a live bot delivery test.
test("Telegram intake and confirmed viewing appear in the real CRM and Inbox", async ({
  page,
}) => {
  test.skip(
    process.env.MADAR_SAMPLE_TELEGRAM_E2E_FIXTURE !== "true",
    "Requires synthetic Telegram fixture",
  );
  await page.request
    .post("/api/auth/login", {
      data: {
        workspace: "madar",
        email: "admin@madar.local",
        password: "TestOnlyPassword123!",
      },
    })
    .then((r) => expect(r.ok()).toBe(true));
  await page.request
    .post("/api/sample-data/load", { data: { confirmed: true } })
    .then((r) => expect(r.ok()).toBe(true));
  const inquiry = "Buy apartment New Cairo budget 5 million 3 bedrooms";
  const sender = {
    id: 707001,
    first_name: "Fixture Telegram buyer",
    language_code: "en",
  };
  const message = {
    message_id: 1,
    chat: { id: 707001, type: "private" },
    from: sender,
    text: inquiry,
  };
  async function incoming(data: object) {
    const response = await page.request.post("/webhooks/telegram", {
      headers: {
        "x-telegram-bot-api-secret-token": "fictional-browser-sample-secret",
      },
      data,
    });
    expect(response.ok()).toBe(true);
  }
  const event = { update_id: 707001, message };
  await incoming(event);
  await incoming(event);
  async function state() {
    return page.request.get("/api/state").then((r) => r.json());
  }
  let data = await state();
  const lead = data.leads.find((l: any) => l.external_id === "707001");
  expect(lead).toBeDefined();
  expect(lead.sample).toBeUndefined();
  expect(data.messages.filter((m: any) => m.lead_id === lead.id)).toHaveLength(
    2,
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Unified inbox", exact: true })
    .click();
  await page
    .locator(".inbox-list")
    .getByRole("button")
    .filter({ hasText: "Fixture Telegram buyer" })
    .click();
  await expect(
    page
      .locator(".conversation-header")
      .getByRole("heading", { name: "Fixture Telegram buyer" }),
  ).toBeVisible();
  await expect(
    page.locator(".conversation").getByText(inquiry, { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".conversation").getByText(/Palm Residence/),
  ).toBeVisible();
  async function callback(id: number) {
    const latest = (await state()).outbox.sort((a: any, b: any) =>
      b.created_at.localeCompare(a.created_at),
    )[0];
    const choice = JSON.parse(latest.template).inline_keyboard[0][0]
      .callback_data;
    await incoming({
      update_id: id,
      callback_query: {
        id: `fixture-${id}`,
        data: choice,
        from: sender,
        message,
      },
    });
  }
  await callback(707002);
  await callback(707003);
  expect((await state()).appointments).toHaveLength(15);
  await callback(707004);
  data = await state();
  const booking = data.appointments.find((a: any) => a.lead_id === lead.id);
  expect(booking).toBeDefined();
  expect(booking.sample).toBeUndefined();
  expect(booking.notes).toContain("Sample / Fictional property");
  expect(
    (await page.request.get("/api/analytics").then((r) => r.json()))
      .total_leads,
  ).toBe(1);
  await page.reload();
  await page.getByRole("button", { name: "Appointments", exact: true }).click();
  const card = page
    .locator(".appointment-card")
    .filter({ hasText: "Fixture Telegram buyer" });
  await expect(
    card.getByRole("heading", { name: "Palm Residence", exact: true }),
  ).toBeVisible();
  await expect(card.getByText("Booked", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  const panel = page.getByRole("region", {
    name: "Sample business data",
    exact: true,
  });
  await expect(
    panel.getByRole("button", {
      name: "Remove Sample Business Data",
      exact: true,
    }),
  ).toBeDisabled();
  expect(
    (
      await page.request.post("/api/sample-data/remove", {
        data: { confirmed: true },
      })
    ).status(),
  ).toBe(409);
  expect(
    (await state()).appointments.some((a: any) => a.id === booking.id),
  ).toBe(true);
  expect(data.outbox.every((o: any) => o.status === "Pending")).toBe(true);
});
