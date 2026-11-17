import { existsSync } from "node:fs";
import { test, expect } from "@playwright/test";
async function signIn(page: any, role: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue as " + role }).click();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
}
test("actual photo OCR distinguishes health and charge, drafts survive navigation", async ({
  page,
}) => {
  test.skip(
    !existsSync("scripts/native/battery-vision") && !process.env.TESSERACT_BIN,
    "No local OCR provider configured",
  );
  await signIn(page, "technician");
  await page.goto("/service/1/capture");
  await page.getByRole("button", { name: "Upload photo", exact: true }).click();
  await page
    .getByLabel("Upload diagnostic image")
    .setInputFiles("data/seed/sample-charge.png");
  await expect(
    page.getByAltText("Original uploaded diagnostic evidence"),
  ).toBeVisible();
  const chargeResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/extract") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Extract with configured OCR" })
    .click();
  expect((await chargeResponse).ok()).toBeTruthy();
  await expect(
    page.getByText("We could not confirm this is battery health.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Measurement type")).toHaveValue("ambiguous");
  await page
    .getByLabel("Upload diagnostic image")
    .setInputFiles("data/seed/sample-health.png");
  const healthResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/extract") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Extract with configured OCR" })
    .click();
  expect((await healthResponse).ok()).toBeTruthy();
  await expect(page.getByLabel("Reading (%)")).toHaveValue("92");
  await expect(page.getByLabel("Odometer", { exact: true })).toHaveValue(
    "28500",
  );
  await page.goto("/vehicles/1");
  await expect(
    page.getByRole("button", { name: "Accept appraisal", exact: true }),
  ).toHaveCount(0);
  await page.goto("/service/1/capture");
  await expect(page.getByLabel("Reading (%)")).toHaveValue("92");
  await expect(
    page.getByAltText("Original uploaded diagnostic evidence"),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: "docs/ocr-mobile.png", fullPage: true });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
});
test("manager correction preserves original and sources stay honest", async ({
  page,
}) => {
  await signIn(page, "manager");
  await page.goto("/vehicles/9");
  const before = await (await page.request.get("/api/vehicles/9")).json();
  const old = [...before.readings]
    .filter((r: any) => r.state === "confirmed")
    .sort((a: any, b: any) => a.date.localeCompare(b.date))
    .at(-1);
  const record = page
    .locator(".evidence")
    .filter({ hasText: old.value + "% battery health" })
    .first();
  await record.getByText("Correct this reading", { exact: true }).click();
  await record
    .getByLabel("Corrected health (%)")
    .fill((old.value - 0.1).toFixed(2));
  await record
    .getByLabel("Correction reason")
    .fill("Corrected from original sample diagnostic record.");
  await record.getByRole("button", { name: "Confirm correction" }).click();
  await expect(
    page.getByText("superseded · excluded from assessment").first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByRole("button", { name: "Check model recalls" }).click();
  await expect(
    page.getByText("Fixture mode: no external verification performed."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Find EPA variants" }).click();
  await expect(
    page.getByRole("heading", { name: "EPA vehicle options" }),
  ).toBeVisible();
  await page.screenshot({ path: "docs/sources-desktop.png", fullPage: true });
});
test("sales sees summaries and published reports without private offer data", async ({
  page,
}) => {
  await signIn(page, "sales");
  await page.goto("/vehicles/1");
  await expect(
    page.getByRole("heading", { name: "Evidence workspace" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Accept appraisal", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Add reading", exact: true }),
  ).toHaveCount(0);
  const r = await (await page.request.get("/api/vehicles/1")).json();
  expect(r.base).toBeUndefined();
  expect(r.policy).toBeUndefined();
  await page.goto("/reports");
  await expect(
    page.getByRole("heading", { name: "Battery reports" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("button", { name: "Continue as sales" }),
  ).toBeVisible();
});
