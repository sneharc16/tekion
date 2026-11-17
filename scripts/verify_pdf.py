"""Verify the downloaded report against its API snapshot and decode its printed QR."""

import json
import subprocess
from pathlib import Path

expected = json.loads(Path("docs/report-snapshot.json").read_text())
result = subprocess.run(
    ["scripts/native/battery-vision", "pdf", "docs/sample-report.pdf", "docs/report-page"],
    capture_output=True,
    text=True,
    check=True,
    timeout=60,
)
inspection = json.loads(result.stdout)
text = "\n".join(p["pdf_text"] for p in inspection["pages"])
snapshot = expected["snapshot"]
assert snapshot["vehicle"] in text
assert "Version " + str(snapshot["version"]) in text
assert snapshot["as_of"] in text
if snapshot["interval"]:
    assert f"{snapshot['interval'][0]}–{snapshot['interval'][1]}%" in text
for reading in snapshot["readings"]:
    assert reading["date"] in text and f"{reading['value']:g}%" in text
codes = [q for p in inspection["pages"] for q in p["qr"]]
assert expected["url"] in codes, "Printed QR must open the exact published report version"
assert not any(
    x in text for x in ["Starting dealer appraisal", "Override amount", "Uncertainty reserve"]
)
for page in inspection["pages"]:
    if "Warranty information" in page["pdf_text"]:
        assert " ".join(snapshot["warranty"].split()) in " ".join(page["pdf_text"].split()), (
            "Warranty heading and text must stay on the same page"
        )
summary = {
    "pages": len(inspection["pages"]),
    "matched_readings": len(snapshot["readings"]),
    "snapshot_values_match": True,
    "qr_exact_version": True,
    "internal_valuation_absent": True,
    "warranty_heading_with_text": True,
}
Path("docs/pdf-verification.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary))
