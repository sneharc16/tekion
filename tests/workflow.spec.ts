import { writeFile } from "node:fs/promises";
import { test, expect } from "@playwright/test";
test("capture through immutable report with SOC guard", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue as manager" }).click();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
  await page.screenshot({ path: "docs/queue-desktop.png", fullPage: true });
  await page.goto("/service/2/capture");
  await page.getByLabel("Reading (%)").fill("80");
  await page.getByLabel("Odometer", { exact: true }).fill("31000");
  await page.getByLabel("Measurement type").selectOption("charge");
  await page
    .getByRole("button", { name: "Confirm and add to Timeline" })
    .click();
  await expect(page.getByRole("alert")).toContainText("could not confirm");
  const existing = await (await page.request.get("/api/vehicles/2")).json();
  const used = new Set(existing.readings.map((r: any) => r.value));
  const next = Array.from({ length: 100 }, (_, i) => 91 + i / 100).find(
    (n) => !used.has(n),
  )!;
  await page.getByLabel("Measurement type").selectOption("health");
  await page.getByLabel("Reading (%)").fill(next.toFixed(2));
  await page
    .getByRole("button", { name: "Confirm and add to Timeline" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Reading added to the Timeline" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open updated appraisal" }).click();
  await page
    .getByLabel("Review / override reason")
    .fill("Reviewed limited evidence and approved this demo offer.");
  await page
    .getByRole("button", { name: "Accept appraisal", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Appraisal saved");
  await page.screenshot({ path: "docs/detail-desktop.png", fullPage: true });
  await page.getByRole("button", { name: "Preview battery report" }).click();
  await page
    .getByRole("button", { name: "Publish report", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Open public report", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Battery Health Report" }),
  ).toBeVisible();
  const reportToken = page.url().split("/r/")[1];
  const snapshot = await (
    await page.request.get("/api/public/reports/" + reportToken)
  ).json();
  await writeFile(
    "docs/report-snapshot.json",
    JSON.stringify({ snapshot, url: page.url() }, null, 2),
  );
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download PDF" }).click();
  const pdf = await download;
  await pdf.saveAs("docs/sample-report.pdf");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "docs/report-mobile.png", fullPage: true });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await page.goto("/work-queue");
  await expect(page.locator(".loading")).toHaveCount(0);
  await expect(page.getByText("26 vehicles in inventory")).toBeAttached();
  await page.screenshot({ path: "docs/queue-mobile.png", fullPage: true });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await page.goto("/service/1/capture");
  await expect(page.getByLabel("Reading (%)")).toBeVisible();
  await page.screenshot({ path: "docs/capture-mobile.png", fullPage: true });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/vehicles/1");
  await expect(
    page.getByRole("button", { name: "Accept appraisal", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "docs/detail-tablet.png", fullPage: true });
  await page
    .getByRole("link", { name: "Review appraisal", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Evidence into an offer" }),
  ).toBeInViewport();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
});
