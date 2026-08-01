import { expect, test } from "@playwright/test";

const BE = "http://127.0.0.1:10951";
const FE = "http://127.0.0.1:10950";

test.describe("Fleet Audit", () => {
  test("Backend health", async ({ request }) => {
    const resp = await request.get(`${BE}/api/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });

  test("Backend capabilities", async ({ request }) => {
    const resp = await request.get(`${BE}/api/capabilities`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.tool_surface.total).toBeGreaterThan(0);
  });

  test("Frontend loads with dashboard", async ({ page }) => {
    await page.goto(FE, { timeout: 15000 });
    await expect(page.locator("#root")).toBeAttached();
    await expect(page.getByTestId("dashboard")).toBeAttached();
  });

  test("No console errors on dashboard", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto(FE, { timeout: 15000 });
    await page.waitForTimeout(2000);
    expect(errors.filter((e) => !e.includes("favicon"))).toEqual([]);
  });
});
