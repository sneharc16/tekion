import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import { writeFile } from "node:fs/promises";

test("core desktop and mobile screens pass automated accessibility checks", async ({
  page,
}) => {
  test.setTimeout(90000);
  const scans: unknown[] = [];
  async function scan(name: string) {
    await expect(page.locator(".loading")).toHaveCount(0);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const record = {
      name,
      violations: result.violations.map((v) => ({
        rule: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
      incomplete: result.incomplete.map((v) => v.id),
    };
    scans.push(record);
    await writeFile(
      "docs/accessibility-results.json",
      JSON.stringify(scans, null, 2),
    );
    expect.soft(record.violations, name).toEqual([]);
  }
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Continue as manager" }),
  ).toBeVisible();
  await scan("demo sign-in / desktop");
  await page.getByRole("button", { name: "Continue as manager" }).click();
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  await scan("work queue / desktop");
  await page.goto("/vehicles/1");
  await expect(
    page.getByRole("button", { name: "Accept appraisal", exact: true }),
  ).toBeVisible();
  await scan("Timeline and appraisal / desktop");
  await page.goto("/settings/sources");
  await expect(
    page.getByRole("heading", { name: "Sources & settings" }),
  ).toBeVisible();
  await scan("sources and policy / desktop");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/service/1/capture");
  await expect(page.getByLabel("Reading (%)")).toBeVisible();
  await scan("service capture / mobile");
  await page.goto("/work-queue");
  await expect(
    page.getByRole("heading", { name: "EV battery appraisals" }),
  ).toBeVisible();
  await scan("work queue / mobile");
  const report = await (
    await page.request.post("/api/vehicles/1/reports", {
      data: { operation_id: "accessibility-report-v1" },
    })
  ).json();
  await page.request.post("/api/reports/" + report.id + "/publish");
  await page.goto("/r/" + report.token);
  await expect(
    page.getByRole("heading", { name: "Battery Health Report" }),
  ).toBeVisible();
  await scan("public report / mobile");
});
