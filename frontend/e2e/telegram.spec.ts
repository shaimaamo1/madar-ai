import { test, expect } from "@playwright/test";

test("Telegram fictional demo appears in CRM and Inbox with bilingual controls", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  const setup = page.getByRole("region", { name: "Telegram guided setup" });
  await expect(setup).toBeVisible();
  await setup
    .getByLabel("Message", { exact: true })
    .fill("Buy an apartment New Cairo budget 5 million 3 bedrooms");
  await setup.getByRole("button", { name: "Simulate Telegram update" }).click();
  await expect(setup.getByRole("status")).toContainText("Palm Residence");
  await setup.getByRole("button", { name: "Simulate Telegram update" }).click();
  await expect(setup.getByRole("status")).toContainText(
    "Duplicate update ignored",
  );
  await page
    .getByRole("button", { name: "Unified inbox", exact: true })
    .click();
  await expect(
    page.getByText("Fictional Telegram customer", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Company settings", exact: true })
    .click();
  const field = setup.getByLabel("Message", { exact: true });
  await field.fill("/help");
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  const arabic = page.getByRole("region", {
    name: "إعداد تيليجرام خطوة بخطوة",
  });
  await expect(arabic.locator("input").last()).toHaveValue("/help");
  await page
    .getByRole("combobox", { name: "لغة الواجهة", exact: true })
    .selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
});
