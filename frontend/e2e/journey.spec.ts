import { test, expect } from "@playwright/test";

test("demo website inquiry becomes a qualified CRM lead and booked viewing", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
  await page.screenshot({
    path: "../var/screenshots/dashboard.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Integrations", exact: true }).click();
  await page.getByRole("button", { name: "Open website chat" }).click();
  await page.getByLabel("I agree to follow-up").check();
  await page
    .getByRole("textbox", { name: "Website inquiry" })
    .fill("I want an apartment in New Cairo, budget 5 million, 3 bedrooms");
  await page.getByRole("button", { name: "Send inquiry" }).click();
  await expect(
    page.getByRole("dialog").getByText(/These available properties/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Leads & CRM" }).click();
  await expect(
    page.getByText("Website demo visitor", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open Website demo visitor" }).click();
  await expect(page.getByText("Palm Residence", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Book viewing" }).click();
  await page
    .getByLabel("Property", { exact: true })
    .selectOption({ label: "Palm Residence" });
  await page.getByLabel("Start time").fill("2030-01-01T10:00");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: "Appointments", exact: true }).click();
  await expect(page.getByText("Palm Residence", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Complete", exact: true }).click();
  await expect(page.getByText("Completed", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Automations", exact: true }).click();
  await page.getByRole("button", { name: "Evaluate due follow-ups" }).click();
  await expect(
    page.getByText("Website demo visitor", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.screenshot({
    path: "../var/screenshots/dark-mode.png",
    fullPage: true,
  });
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  expect(errors).toEqual([]);
});

test("property creation, comparison, settings and task completion persist", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await page
    .getByRole("button", { name: "Property inventory", exact: true })
    .click();
  await page.getByRole("button", { name: "Add property" }).click();
  await page.getByLabel("Property title").fill("Browser Test Residence");
  await page.getByLabel("Location", { exact: true }).fill("New Cairo");
  await page.getByLabel("Price in company currency").fill("4000000");
  await page.getByLabel("Size (m²)").fill("160");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Browser Test Residence" }),
  ).toBeVisible();
  await page
    .getByRole("checkbox", { name: "Compare Browser Test Residence" })
    .check();
  await page.getByRole("checkbox", { name: "Compare Palm Residence" }).check();
  await page.getByRole("button", { name: "Compare (2)" }).click();
  await expect(
    page.getByRole("dialog").getByText("Price / m²").first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  await page.getByLabel("Company name").fill("Browser Estates");
  await page.getByRole("button", { name: "Save company settings" }).click();
  await expect(
    page.getByRole("button", { name: /Browser Estates/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Follow-up tasks", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Complete", exact: true })
    .first()
    .click();
  await expect(
    page.getByText("Completed", { exact: true }).first(),
  ).toBeVisible();
});

test("mobile dashboard stays within viewport and navigation works", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../var/screenshots/mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .getByRole("button", { name: "Unified inbox", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Unified inbox", exact: true }),
  ).toBeVisible();
});

test("anonymous public portal books a viewing without dashboard access", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view. A smarter business." }),
  ).toBeVisible();
  const state = await page.evaluate(async () =>
    (await fetch("/api/state")).json(),
  );
  await page.goto("/chat?company=" + state.company.slug);
  await page.getByLabel("I agree to follow-up").check();
  await page
    .getByRole("textbox", { name: "Website inquiry" })
    .fill("New Cairo apartment, 5 million budget, 3 bedrooms");
  await page.getByRole("button", { name: "Send inquiry" }).click();
  await page
    .getByRole("button", { name: /Palm Residence.*View times/ })
    .click();
  await page.locator(".slot-picker .button").first().click();
  await expect(page.getByText(/Viewing confirmed:/)).toBeVisible();
});
