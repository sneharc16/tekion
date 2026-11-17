import { test, expect } from "@playwright/test";

test("session expiry returns to sign-in and restores the manual capture", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue as technician" }).click();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  await page.goto("/service/19/capture");
  await page.getByLabel("Reading (%)").fill("90.25");
  await page.getByLabel("Measurement type").selectOption("health");
  await page.getByLabel("Odometer", { exact: true }).fill("60000");
  await context.clearCookies();
  await page
    .getByRole("button", { name: "Confirm and add to Timeline" })
    .click();
  await expect(page.getByRole("status")).toContainText("Your session expired");
  await page.getByRole("button", { name: "Continue as technician" }).click();
  await expect(page.getByLabel("Reading (%)")).toHaveValue("90.25");
  await expect(page.getByLabel("Odometer", { exact: true })).toHaveValue(
    "60000",
  );
  await expect(page.getByLabel("Measurement type")).toHaveValue("health");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "docs/recovered-capture-mobile.png",
    fullPage: true,
  });
});

test("keyboard navigation reaches evidence and reviewed warranty source", async ({
  page,
}) => {
  await page.goto("/");
  const manager = page.getByRole("button", { name: "Continue as manager" });
  await manager.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  await page.goto("/vehicles/1");
  const warranty = page.getByRole("button", { name: "Warranty", exact: true });
  await warranty.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Capacity provision: 60%", { exact: true }),
  ).toBeVisible();
  const source = page.getByRole("link", { name: "View manufacturer source" });
  await source.focus();
  await expect(source).toBeFocused();
  await expect(source).toHaveAttribute("href", /contentdelivery.ext.gm.com/);
  await page.screenshot({
    path: "docs/chevrolet-warranty-desktop.png",
    fullPage: true,
  });
});

test("retry after lost confirmation response does not create another reading", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue as technician" }).click();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  const before = await (await page.request.get("/api/vehicles/20")).json();
  await page.goto("/service/20/capture");
  await page.getByLabel("Reading (%)").fill("97.5");
  await page.getByLabel("Measurement type").selectOption("health");
  await page.getByLabel("Odometer", { exact: true }).fill(String(before.miles));
  let lost = false;
  await page.route("**/api/capture-drafts/*/confirm", async (route) => {
    if (!lost) {
      lost = true;
      const response = await route.fetch();
      expect(response.ok()).toBeTruthy();
      await route.abort("failed");
    } else {
      await route.continue();
    }
  });
  await page
    .getByRole("button", { name: "Confirm and add to Timeline" })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Reading (%)")).toHaveValue("97.5");
  await page
    .getByRole("button", { name: "Confirm and add to Timeline" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Reading added to the Timeline" }),
  ).toBeVisible();
  const after = await (await page.request.get("/api/vehicles/20")).json();
  expect(after.revision).toBe(before.revision + 1);
  expect(after.readings.length).toBe(before.readings.length + 1);
});
