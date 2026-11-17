import { test, expect } from "@playwright/test";
test("policy versions, appraisal inputs, warranty and evidence review", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue as manager" }).click();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  await page.goto("/settings/sources");
  await expect(
    page.getByRole("button", { name: "Save new policy version" }),
  ).toBeVisible();
  await page.getByLabel("USD per percentage point").fill("130");
  await page.getByRole("button", { name: "Save new policy version" }).click();
  await expect(page.locator(".policy-version")).toContainText("dealer-");
  await page.goto("/vehicles/1");
  await page.getByText("Edit starting appraisal", { exact: true }).click();
  await page.getByLabel("Starting value (USD)").fill("24500");
  await page.getByLabel("Battery health already included?").selectOption("yes");
  await page
    .getByLabel("Valuation source")
    .fill("Synthetic dealer appraisal reviewed for demo");
  await page.getByRole("button", { name: "Save appraisal inputs" }).click();
  await expect(page.locator(".offer")).toContainText("$24,500");
  await page.goto("/vehicles/warranty-25");
  await page.getByRole("button", { name: "Warranty", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Coverage headroom" }),
  ).toBeVisible();
  await expect(page.locator(".warranty-metrics")).toContainText("500 mi");
  await page
    .getByText("Review warranty application evidence", { exact: true })
    .click();
  await page.getByLabel("Sale state (two-letter code)").fill("IL");
  await page
    .getByLabel("Evidence reference and verification notes")
    .fill("Synthetic delivery and transfer record reviewed in browser demo.");
  await page.getByRole("button", { name: "Save warranty evidence" }).click();
  await expect(
    page.getByRole("heading", { name: "Coverage headroom" }),
  ).toBeVisible();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: "docs/warranty-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByText("Review warranty application evidence", { exact: true })
    .click();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: "docs/warranty-mobile.png", fullPage: true });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await page.goto("/vehicles/3");
  await page
    .getByText("Review / exclude this reading", { exact: true })
    .first()
    .click();
  await page
    .getByLabel("Reason for exclusion")
    .first()
    .fill(
      "Unexplained high reading; excluded pending independent measurement.",
    );
  await page
    .getByRole("button", { name: "Exclude from assessment" })
    .first()
    .click();
  await expect(
    page.getByText("excluded · excluded from assessment").first(),
  ).toBeVisible();
});
