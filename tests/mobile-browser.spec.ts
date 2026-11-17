import { test, expect } from "@playwright/test";

test.use({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});

test("touch capture, pack boundary and public report on a mobile browser", async ({
  page,
  browserName,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue as manager" }).tap();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation).toBeInViewport();
  await navigation.getByRole("link", { name: "Reports", exact: true }).tap();
  await expect(page).toHaveURL(/\/reports$/);
  await expect(
    navigation.getByRole("link", { name: "Reports", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.goto("/service/24/capture");
  await expect(
    page.getByRole("button", { name: "Enter reading", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const confirmation = page.getByRole("button", {
    name: "Confirm and add to Timeline",
  });
  const navBounds = await navigation.boundingBox();
  const buttonBounds = await confirmation.boundingBox();
  expect(buttonBounds!.y + buttonBounds!.height).toBeLessThanOrEqual(
    navBounds!.y,
  );
  await page.screenshot({ path: `docs/capture-viewport-${browserName}.png` });
  const before = await (await page.request.get("/api/vehicles/24")).json();
  await page.getByLabel("Measurement type").selectOption("health");
  await page.getByLabel("Reading (%)").fill("90.75");
  await page.getByLabel("Odometer", { exact: true }).fill(String(before.miles));
  await page.getByRole("button", { name: "Confirm and add to Timeline" }).tap();
  await expect(
    page.getByRole("heading", { name: "Reading added to the Timeline" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open updated appraisal" }).tap();
  await page.getByRole("link", { name: "Review appraisal", exact: true }).tap();
  await expect(
    page.getByRole("heading", { name: "Evidence into an offer" }),
  ).toBeInViewport();
  await page
    .getByLabel("Review / override reason")
    .fill("Reviewed current measurement and sample battery evidence.");
  await page
    .getByRole("button", { name: "Accept appraisal", exact: true })
    .tap();
  await expect(page.getByRole("status")).toContainText("Appraisal saved");
  await page.getByRole("button", { name: "Preview battery report" }).tap();
  await page.getByRole("button", { name: "Publish report", exact: true }).tap();
  await page
    .getByRole("link", { name: "Open public report", exact: true })
    .tap();
  await expect(
    page.getByRole("heading", { name: "Battery Health Report" }),
  ).toBeVisible();
  await expect(
    page.getByAltText("QR code for this exact report version"),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await page.screenshot({
    path: `docs/report-touch-${browserName}.png`,
    fullPage: true,
  });
  await page.goto("/vehicles/4");
  await expect(
    page.getByText("Pack replacement", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator(".recharts-line-curve")).toHaveCount(2);
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: `docs/detail-viewport-${browserName}.png` });
  await page.screenshot({
    path: `docs/pack-touch-${browserName}.png`,
    fullPage: true,
  });
});
