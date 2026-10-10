import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdirSync } from "node:fs";

const previews = "../docs/previews";
const pages = [
  "Overview",
  "Leads & CRM",
  "WhatsApp studio",
  "Property inventory",
  "Unified inbox",
  "Appointments",
  "Follow-up tasks",
  "Analytics",
  "Sales team",
  "Sales intelligence",
  "Automations",
  "Integrations",
  "Company settings",
];
async function demo(page: any) {
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
  const operations = await page.evaluate(async () =>
    (await fetch("/api/operations")).json(),
  );
  expect(operations.external_send_enabled).toBe(false);
  expect(operations.model_usage_enabled).toBe(false);
  await expect(page.locator(".toast")).not.toBeVisible({ timeout: 7000 });
}

test("WhatsApp sandbox qualifies Arabic inquiries, remembers context, respects opt-out and human ownership", async ({
  page,
}) => {
  await demo(page);
  await page
    .getByRole("button", { name: "WhatsApp studio", exact: true })
    .click();
  await page.getByLabel("Customer follow-up opt-in recorded").check();
  const input = page.getByRole("textbox", { name: "WhatsApp sandbox message" });
  await input.fill("عايز شقة في التجمع، ميزانيتي ٥ مليون و٣ غرف");
  await page.getByRole("button", { name: "Send sandbox message" }).click();
  await expect(page.getByText("Palm Residence", { exact: true })).toBeVisible();
  await expect(page.getByText("85 / 100", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Book viewing", exact: true }).click();
  await page.getByLabel("Start time").fill("2030-01-01T10:00");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await input.fill("human adviser");
  await page.getByRole("button", { name: "Send sandbox message" }).click();
  await expect(
    page.getByRole("button", { name: "Resume assistant" }),
  ).toBeVisible();
  await input.fill("My budget is still 5 million");
  await page.getByRole("button", { name: "Send sandbox message" }).click();
  await expect(
    page.getByText("My budget is still 5 million", { exact: true }),
  ).toBeVisible();
  const state = await page.evaluate(async () =>
    (await fetch("/api/state")).json(),
  );
  const lead = state.leads.find((l: any) =>
    l.external_id.startsWith("sandbox:"),
  );
  expect(
    state.messages.filter(
      (m: any) => m.lead_id === lead.id && m.direction === "outbound",
    ),
  ).toHaveLength(2);
  expect(state.outbox.filter((o: any) => o.lead_id === lead.id)).toHaveLength(
    0,
  );
  expect(
    state.appointments.filter((a: any) => a.lead_id === lead.id),
  ).toHaveLength(1);
  await page.getByRole("button", { name: "Resume assistant" }).click();
  await input.fill("stop");
  await page.getByRole("button", { name: "Send sandbox message" }).click();
  await expect(page.getByText("Opted out", { exact: true })).toBeVisible();
  await expect(page.locator(".toast")).not.toBeVisible({ timeout: 7000 });
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    window.scrollTo(0, 0);
  });
  mkdirSync(previews, { recursive: true });
  await page.screenshot({
    path: previews + "/whatsapp-conversation.png",
    fullPage: true,
  });
});

test("workflow diagrams display actual modules and inactive operation contracts", async ({
  page,
}) => {
  await demo(page);
  await page.getByRole("button", { name: "Automations", exact: true }).click();
  await expect(
    page.getByRole("tab", { name: "Omnichannel Intake", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  expect(await page.locator('[role="tablist"] [role="tab"]').count()).toBe(10);
  await expect(
    page.getByRole("img", { name: "MADAR Omnichannel Intake actual workflow" }),
  ).toBeVisible();
  await page
    .getByRole("tab", { name: "Viewing Reservations", exact: true })
    .click();
  await expect(
    page.locator('[data-node-id="reserve-conflict-safe-appointment"]'),
  ).toBeVisible();
  await page
    .getByRole("tab", { name: "WhatsApp Delivery", exact: true })
    .click();
  await expect(
    page.getByRole("img", { name: "MADAR WhatsApp Delivery actual workflow" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Evaluate due follow-ups", exact: true })
    .click();
  await expect(
    page.getByText("Due follow-ups evaluated; eligible messages queued"),
  ).toBeVisible();
});

test("all dashboard pages pass automated accessibility checks and produce real previews", async ({
  page,
}) => {
  test.setTimeout(90000);
  mkdirSync(previews, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1024 });
  await page.goto("/");
  for (const name of ["manrope.ttf", "noto-sans-arabic.ttf"]) {
    const font = await page.request.get("/fonts/" + name);
    expect(font.status()).toBe(200);
    expect((await font.body()).length).toBeGreaterThan(100000);
  }
  await page.evaluate(() =>
    Promise.all([
      document.fonts.load("600 14px Manrope"),
      document.fonts.load('400 14px "Noto Sans Arabic"'),
    ]),
  );
  await expect(
    page.getByRole("heading", { name: "Good business starts here." }),
  ).toBeVisible();
  await page.screenshot({ path: previews + "/login.png", fullPage: true });
  let scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
  await demo(page);
  for (const name of pages) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByRole("heading", {
        name:
          name === "Overview" ? "A clearer view. A smarter business." : name,
        exact: true,
      }),
    ).toBeVisible();
    scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(scan.violations, name + " accessibility violations").toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path:
        previews +
        "/" +
        name
          .toLowerCase()
          .replaceAll(/[^a-z]+/g, "-")
          .replace(/-$/, "") +
        ".png",
      fullPage: true,
    });
  }
});

test("keyboard dialog traps focus and returns it to the triggering control", async ({
  page,
}) => {
  await demo(page);
  const trigger = page.getByRole("button", { name: "New lead", exact: true });
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Close dialog" }),
  ).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    page.getByRole("button", { name: "Save", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Close dialog" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("dark and Arabic mobile layouts remain accessible and within the viewport", async ({
  page,
}) => {
  test.setTimeout(90000);
  await demo(page);
  await page.getByRole("button", { name: "Toggle theme" }).click();
  let scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.screenshot({
    path: previews + "/midnight-dashboard.png",
    fullPage: true,
  });
  for (const name of pages) {
    await page.getByRole("button", { name, exact: true }).click();
    scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(scan.violations, name + " dark accessibility").toEqual([]);
  }
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: previews + "/arabic-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "فتح القائمة" }).click();
  await page
    .getByRole("button", { name: "استوديو واتساب", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "استوديو واتساب", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
});
