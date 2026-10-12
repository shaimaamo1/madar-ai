import { test, expect, Page, BrowserContext } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import arabic from "../src/locales/ar.json";
import { mkdirSync } from "node:fs";
const ar: Record<string, string> = arabic;
const names = [
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
  "System Health",
];
// One isolated fictional tenant for this read/locale suite keeps the full 14-test
// run within the existing ten-demo-creation rate limit. Credentials stay in memory.
let demoCookies: Awaited<ReturnType<BrowserContext["cookies"]>> = [];
test.beforeAll(async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
  demoCookies = await context.cookies();
  await context.close();
});
async function demo(page: Page) {
  await page.context().addCookies(demoCookies);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
}
async function language(page: Page, value: "en" | "ar", dialog = false) {
  const area = dialog ? page.getByRole("dialog") : page;
  await area
    .getByRole("combobox", {
      name: new RegExp("^(Language|" + ar.Language + ")$"),
    })
    .selectOption(value);
  await expect(page.locator("html")).toHaveAttribute("lang", value);
  await expect(page.locator("html")).toHaveAttribute(
    "dir",
    value === "ar" ? "rtl" : "ltr",
  );
}

test("switching inside a form preserves every input, canonical value and DOM control", async ({
  page,
}) => {
  await demo(page);
  await page.evaluate(() => {
    (window as any).noReloadMarker = "preserved";
  });
  await page.getByRole("button", { name: "New lead", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Full name").fill("Bilingual Fictional Customer");
  await dialog.getByLabel("Phone", { exact: true }).fill("+201234567899");
  await dialog.getByLabel("Budget", { exact: true }).fill("1234000");
  await dialog.getByLabel("Preferred area").fill("New Cairo");
  await dialog.getByLabel("Lead source").selectOption("whatsapp");
  await dialog.getByLabel("Property type").selectOption("Villa");
  await dialog.getByLabel("Intent", { exact: true }).selectOption("rent");
  await dialog.getByLabel("Follow-up consent recorded").check();
  await dialog.locator('[name="name"]').evaluate((el) => {
    (el as any).preserveMarker = "same-control";
  });
  await language(page, "ar", true);
  await expect(dialog.getByLabel(ar["Full name"])).toHaveValue(
    "Bilingual Fictional Customer",
  );
  await expect(dialog.getByLabel(ar["Budget"], { exact: true })).toHaveValue(
    "1234000",
  );
  await expect(dialog.getByLabel(ar["Lead source"])).toHaveValue("whatsapp");
  await expect(dialog.getByLabel(ar["Property type"])).toHaveValue("Villa");
  await expect(dialog.getByLabel(ar["Intent"], { exact: true })).toHaveValue(
    "rent",
  );
  await expect(
    dialog.getByLabel(ar["Follow-up consent recorded"]),
  ).toBeChecked();
  expect(
    await dialog
      .locator('[name="name"]')
      .evaluate((el) => (el as any).preserveMarker),
  ).toBe("same-control");
  expect(await page.evaluate(() => (window as any).noReloadMarker)).toBe(
    "preserved",
  );
  await dialog.getByRole("button", { name: ar.Save, exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.locator(".toast")).toContainText(ar["Saved successfully"]);
  const state = await page.evaluate(async () =>
    (await fetch("/api/state")).json(),
  );
  const lead = state.leads.find(
    (row: any) => row.name === "Bilingual Fictional Customer",
  );
  expect(lead).toMatchObject({
    source: "whatsapp",
    property_type: "Villa",
    intent: "rent",
    budget: 1234000,
    consent: 1,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: ar["A clearer view. A smarter business."],
    }),
  ).toBeVisible();
  await expect(page.getByRole("combobox", { name: ar.Language })).toHaveValue(
    "ar",
  );
  await language(page, "en");
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
});

test("every Arabic page, workflow module and mobile layout is translated and accessible", async ({
  page,
}) => {
  test.setTimeout(120000);
  await demo(page);
  await page.setViewportSize({ width: 1440, height: 1024 });
  await language(page, "ar");
  mkdirSync("../var/screenshots/i18n", { recursive: true });
  for (const name of names) {
    await page.getByRole("button", { name: ar[name], exact: true }).click();
    await expect(
      page.getByRole("heading", {
        name: ar[
          name === "Overview" ? "A clearer view. A smarter business." : name
        ],
        exact: true,
      }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      name + " desktop overflow",
    ).toBeTruthy();
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(scan.violations, name + " Arabic accessibility").toEqual([]);
    // Canonical user statuses and navigation may never leak into rendered Arabic UI.
    const rawLabels = await page
      .locator(
        "nav button span, .pill, .tabs button, .conversation-preview small, th, .field > select option",
      )
      .allTextContents();
    for (const text of rawLabels)
      expect(text.trim()).not.toMatch(
        /^(?:New|Qualified|Viewing|Negotiation|Won|Lost|Available|Reserved|Sent|Pending|Completed|Open|Save|Company settings|Appointments)$/,
      );
    if (name === "Overview") {
      const state = await page.evaluate(async () =>
        (await fetch("/api/state")).json(),
      );
      await expect(page.locator(".stats-grid").first()).toContainText(
        new Intl.NumberFormat("ar-EG").format(state.leads.length),
      );
      const sidebar = await page.locator(".sidebar").boundingBox();
      expect(sidebar!.x + sidebar!.width).toBe(1440);
      expect(
        await page
          .locator("body")
          .evaluate((el) => getComputedStyle(el).fontFamily),
      ).toContain("Noto Sans Arabic");
      await page.locator(".toast").waitFor({ state: "hidden" });
      await page.screenshot({
        path: "../var/screenshots/i18n/bilingual-arabic-desktop.png",
        fullPage: true,
      });
    }
    if (name === "Automations")
      for (const tab of await page.getByRole("tab").all()) {
        await tab.click();
        const texts = await page
          .locator(".workflow-map .node-label, .workflow-map .group-label")
          .allTextContents();
        for (const text of texts) expect(text).toMatch(/[\u0600-\u06ff]/);
      }
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      name + " mobile overflow",
    ).toBeTruthy();
    await page.setViewportSize({ width: 1440, height: 1024 });
  }
  await page.getByRole("button", { name: ar.Overview, exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../var/screenshots/i18n/bilingual-arabic-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: ar["Open navigation"] }).click();
  await page
    .getByRole("button", { name: ar["Leads & CRM"], exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: ar["Leads & CRM"], exact: true }),
  ).toBeVisible();
});

test("settings, search, comparison and unsent messages survive locale changes", async ({
  page,
}) => {
  await demo(page);
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  await page.getByLabel("Company name").fill("Unsaved Company");
  await page.getByLabel("Currency", { exact: true }).selectOption("SAR");
  await page.getByLabel("Business timezone").selectOption("Asia/Riyadh");
  await language(page, "ar");
  await expect(page.getByLabel(ar["Company name"])).toHaveValue(
    "Unsaved Company",
  );
  await expect(page.getByLabel(ar.Currency, { exact: true })).toHaveValue(
    "SAR",
  );
  await expect(page.getByLabel(ar["Business timezone"])).toHaveValue(
    "Asia/Riyadh",
  );
  await language(page, "en");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Property inventory", exact: true })
    .click();
  await page.getByRole("checkbox", { name: "Compare Palm Residence" }).check();
  await page.getByPlaceholder("Search inventory…").fill("Palm");
  await language(page, "ar");
  await expect(
    page.getByRole("checkbox", {
      name: ar["Compare {name}"].replace("{name}", "Palm Residence"),
    }),
  ).toBeChecked();
  await expect(page.getByPlaceholder(ar["Search inventory…"])).toHaveValue(
    "Palm",
  );
  await page
    .getByRole("button", { name: ar["WhatsApp studio"], exact: true })
    .click();
  await page
    .getByRole("textbox", { name: ar["WhatsApp sandbox message"] })
    .fill("My message has not been sent");
  await page.getByLabel(ar["Customer follow-up opt-in recorded"]).check();
  await language(page, "en");
  await expect(
    page.getByRole("textbox", { name: "WhatsApp sandbox message" }),
  ).toHaveValue("My message has not been sent");
  await expect(
    page.getByLabel("Customer follow-up opt-in recorded"),
  ).toBeChecked();
  const operations = await page.evaluate(async () =>
    (await fetch("/api/operations")).json(),
  );
  expect(operations.external_send_enabled).toBe(false);
  expect(operations.model_usage_enabled).toBe(false);
});

test("login validation, network and server errors translate without losing credentials", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page.getByLabel("Workspace", { exact: true }).fill("fictional");
  await page
    .getByLabel("Email", { exact: true })
    .fill("fictional@example.invalid");
  await page
    .getByLabel("Password", { exact: true })
    .fill("fictional test password");
  await language(page, "ar");
  await expect(page.getByLabel(ar.Password, { exact: true })).toHaveValue(
    "fictional test password",
  );
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Invalid workspace or credentials" }),
    }),
  );
  await page.getByRole("button", { name: ar["Sign in"], exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    ar["Invalid workspace or credentials"],
  );
  await language(page, "en");
  await expect(page.getByRole("alert")).toHaveText(
    "Invalid workspace or credentials",
  );
  await page.unroute("**/api/auth/login");
  await page.route("**/api/auth/login", (route) => route.abort());
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Unable to connect. Check your connection and try again.",
  );
  await language(page, "ar");
  await expect(page.getByRole("alert")).toHaveText(
    ar["Unable to connect. Check your connection and try again."],
  );
  const email = page.getByLabel(ar.Email, { exact: true });
  await email.fill("invalid");
  await email.evaluate((el: HTMLInputElement) => el.reportValidity());
  expect(
    await email.evaluate((el: HTMLInputElement) => el.validationMessage),
  ).toBe(ar["Enter a valid email address."]);
  await language(page, "en");
  expect(
    await page
      .getByLabel("Email", { exact: true })
      .evaluate((el: HTMLInputElement) => el.validationMessage),
  ).toBe("Enter a valid email address.");
  await language(page, "ar");
  const nextPage = await context.newPage();
  await nextPage.goto("/");
  await expect(nextPage.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(
    nextPage.getByRole("heading", { name: ar["Good business starts here."] }),
  ).toBeVisible();
  await nextPage.close();
});

test("public inquiry, property times and booking confirmation localize while messages retain their language", async ({
  page,
}) => {
  await demo(page);
  const state = await page.evaluate(async () =>
    (await fetch("/api/state")).json(),
  );
  await page.goto("/chat?company=" + state.company.slug);
  await language(page, "ar");
  await page
    .getByLabel(ar["I agree to follow-up about my property inquiry"])
    .check();
  await page
    .getByRole("textbox", { name: ar["Website inquiry"] })
    .fill("عايز شقة في التجمع ميزانيتي ٥ مليون و٣ غرف");
  await page.getByRole("button", { name: ar["Send inquiry"] }).click();
  await page
    .getByRole("button", {
      name: new RegExp("Palm Residence.*" + ar["View times"]),
    })
    .click();
  await page.locator(".slot-picker .button").first().click();
  await expect(page.locator(".booking-notice")).toContainText(
    "تم تأكيد المعاينة",
  );
  await language(page, "en");
  await expect(page.locator(".booking-notice")).toContainText(
    "Viewing confirmed:",
  );
  await expect(
    page.getByText("عايز شقة في التجمع ميزانيتي ٥ مليون و٣ غرف", {
      exact: true,
    }),
  ).toBeVisible();
});

test("System Health, queued real demo and grounded agents stay honest and bilingual", async ({
  page,
}) => {
  await demo(page);
  await page
    .getByRole("button", { name: "System Health", exact: true })
    .click();
  await expect(
    page.getByText("Authenticated API responded", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Local API access is not configured", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Queue full demo", exact: true })
    .click();
  await expect(page.getByText("Queued", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Queue full demo", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Not yet reported", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Evaluate agents", exact: true })
    .click();
  await expect(
    page.getByText("Reply drafting agent", { exact: true }),
  ).toBeVisible();
  const selection = await page
    .getByLabel("Customer", { exact: true })
    .inputValue();
  await expect(page.locator(".toast")).not.toBeVisible({ timeout: 7000 });
  await page.screenshot({
    path: "../var/screenshots/i18n/system-health.png",
    fullPage: true,
  });
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await language(page, "ar");
  await expect(page.getByLabel(ar.Customer, { exact: true })).toHaveValue(
    selection,
  );
  await expect(
    page.getByText(ar["Reply drafting agent"], { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(ar.Queued, { exact: true })).toBeVisible();
  await expect(
    page.getByText(ar["Local API access is not configured"], { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "../var/screenshots/i18n/system-health-arabic.png",
    fullPage: true,
  });
  const runs = await page.evaluate(async () =>
    (await fetch("/api/demo/runs")).json(),
  );
  expect(runs[0].status).toBe("Queued");
  expect(runs[0].steps).toHaveLength(0);
  expect(runs[0].execution_id).toBe("");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});
