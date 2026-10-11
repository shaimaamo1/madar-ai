import { test, expect } from "@playwright/test";

test("connected demo loads once, serves every image and resets without deleting added records", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Open interactive demo" }).click();
  await page
    .getByRole("button", { name: "Load Demo Data", exact: true })
    .click();
  const state = await page.request.get("/api/state").then((r) => r.json());
  expect(state.properties).toHaveLength(30);
  expect(state.leads).toHaveLength(40);
  expect(state.appointments).toHaveLength(15);
  expect(state.tasks).toHaveLength(20);
  await page
    .getByRole("button", { name: "Property inventory", exact: true })
    .click();
  const images = page.locator(".property-image img");
  await expect(images).toHaveCount(30);
  for (const image of await images.all()) {
    await image.scrollIntoViewIfNeeded();
    await expect
      .poll(() =>
        image.evaluate(
          (element: HTMLImageElement) =>
            element.complete && element.naturalWidth > 0,
        ),
      )
      .toBeTruthy();
  }
  await expect(page.locator(".property-body").first()).toContainText(
    "DEMO / FICTIONAL",
  );
  await page
    .getByRole("button", { name: "Edit details", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.request.post("/api/leads", {
    data: {
      name: "Added presentation customer",
      external_id: "sandbox:presentation-added",
    },
  });
  await page
    .getByRole("button", { name: "Load Demo Data", exact: true })
    .click();
  expect(
    (await page.request.get("/api/state").then((r) => r.json())).leads,
  ).toHaveLength(41);
  await page.getByRole("button", { name: "Reset demo", exact: true }).click();
  await page
    .getByRole("button", { name: "Reset fictional demo", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const reset = await page.request.get("/api/state").then((r) => r.json());
  expect(reset.leads).toHaveLength(41);
  expect(
    reset.leads.some((l: any) => l.name === "Added presentation customer"),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Analytics", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Property demand by area" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Demo analytics use fictional records; no earned revenue is implied.",
    ),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
