import { expect, test } from "@playwright/test";

test.describe("login screen at mobile width", () => {
  test("opens in Hindi by default and switches to English", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "अपने खेत की योजना बनाएं, हफ़्ते-दर-हफ़्ते",
    );
    await expect(page.getByRole("button", { name: "लॉग इन करें या खाता बनाएं" })).toBeVisible();
    // The bundled Devanagari font must actually load (no tofu boxes).
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.fonts.check('16px "Farm Devanagari"', "खेत"))).toBe(
      true,
    );
    await page.screenshot({ path: "test-results/login-hi.png", fullPage: true });

    await page.getByRole("button", { name: "English" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("button", { name: "Sign in or create account" })).toBeVisible();
    await page.screenshot({ path: "test-results/login-en.png", fullPage: true });

    await page.reload();
    await expect(page.getByRole("button", { name: "Sign in or create account" })).toBeVisible();
  });

  test("touch targets are at least 44px and text at least 16px", async ({ page }) => {
    await page.goto("/");
    for (const button of await page.getByRole("button").all()) {
      const box = await button.boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
      expect(box?.width ?? 0).toBeGreaterThanOrEqual(44);
    }
    const sizes = await page
      .locator("h1, p, button")
      .evaluateAll((els) => els.map((e) => parseFloat(getComputedStyle(e).fontSize)));
    expect(Math.min(...sizes)).toBeGreaterThanOrEqual(16);
  });

  test("an invalid caretaker link shows a friendly error", async ({ page }) => {
    await page.route("**/api/v1/auth/otp/verify", (route) =>
      route.fulfill({
        status: 401,
        json: { error: { code: "LINK_INVALID", message_key: "err.link_invalid", details: {} } },
      }),
    );
    await page.goto("/login/link#token=expired-token-value-000000");
    await expect(page.getByRole("alert")).toContainText("Telegram");
    expect(page.url()).not.toContain("token=");
  });
});

test("every Hindi text node renders with the bundled Devanagari font", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("DOM.enable");
  await cdp.send("CSS.enable");
  const { root } = await cdp.send("DOM.getDocument", { depth: -1 });
  const { nodeIds } = await cdp.send("DOM.querySelectorAll", {
    nodeId: root.nodeId,
    selector: "header span, header button[lang=hi], h1, p, main button",
  });
  expect(nodeIds.length).toBeGreaterThan(3);
  for (const nodeId of nodeIds) {
    const { fonts } = await cdp.send("CSS.getPlatformFontsForNode", { nodeId });
    expect(fonts.some((f) => f.familyName === "Noto Sans Devanagari" && f.isCustomFont)).toBe(true);
  }
});
