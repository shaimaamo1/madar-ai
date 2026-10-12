import { test, expect } from "@playwright/test";

for (const legacy of [false, true]) {
  test(`30 distinct photorealistic assets display using ${legacy ? "existing legacy" : "new canonical"} URLs`, async ({
    page,
  }) => {
    if (legacy)
      await page.route("**/api/state", async (route) => {
        const response = await route.fetch();
        const state = await response.json();
        if (state.properties)
          state.properties = state.properties.map((p: any) => ({
            ...p,
            image: p.image?.replace(/\.webp$/, ".svg"),
          }));
        await route.fulfill({ response, json: state });
      });
    await page.goto("/");
    await page.getByRole("button", { name: "Open interactive demo" }).click();
    await page
      .getByRole("button", { name: "Property inventory", exact: true })
      .click();
    const images = page.locator(".property-image img");
    await expect(images).toHaveCount(30);
    const urls = new Set<string>();
    for (const image of await images.all()) {
      await image.scrollIntoViewIfNeeded();
      await expect
        .poll(() =>
          image.evaluate(
            (node: HTMLImageElement) =>
              node.complete &&
              node.naturalWidth === 1024 &&
              node.naturalHeight > 600,
          ),
        )
        .toBeTruthy();
      const src = await image.getAttribute("src");
      urls.add(src!);
      expect(src).toMatch(legacy ? /\.svg$/ : /\.webp$/);
      await expect(image).toHaveAttribute(
        "alt",
        /Illustrative synthetic property image/,
      );
    }
    expect(urls.size).toBe(30);
    await expect(page.locator(".property-body").first()).toContainText(
      "AI-generated illustrative image",
    );
  });
}
