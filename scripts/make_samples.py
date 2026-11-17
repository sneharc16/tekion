from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

Path("data/seed").mkdir(exist_ok=True)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 38)
except OSError:
    font = ImageFont.load_default(size=38)
for name, label in [("sample-health", "Battery health: 92%"), ("sample-charge", "Battery: 80%")]:
    image = Image.new("RGB", (1200, 620), "white")
    d = ImageDraw.Draw(image)
    lines = [
        "SAMPLE DIAGNOSTIC SCREEN",
        "Synthetic demonstration - not an OEM certificate",
        label,
        "Date: 2026-11-16",
        "Odometer: 28500 mi",
        "State of charge: 80%"
        if name == "sample-health"
        else "Charge level only - not capacity health",
    ]
    for i, line in enumerate(lines):
        d.text((40, 35 + i * 85), line, fill="#123f3b" if i == 0 else "#222630", font=font)
    image.save("data/seed/" + name + ".png")
