"""Actual local OCR providers. OCR text is untrusted data, never instructions."""

import os
import re
import subprocess
import json
from pathlib import Path

NATIVE = Path(__file__).resolve().parents[4] / "scripts/native/battery-vision"


def configured():
    return bool(os.getenv("TESSERACT_BIN", "").strip() or NATIVE.is_file())


def candidates(transcript, confidence=None):
    matches = re.findall(
        r"(?:state\s+of\s+health|battery\s+health|\bSOH)\s*[:=]?\s*(\d{1,3}(?:\.\d+)?)\s*%",
        transcript,
        re.I,
    )
    value = float(matches[0]) if len(matches) == 1 else None
    health = value is not None and 0 <= value <= 100
    odometer = re.search(
        r"(?:odometer|mileage)\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(mi|miles|km|kilometers)\b",
        transcript,
        re.I,
    )
    date = re.search(r"\b(20\d\d-\d\d-\d\d)\b", transcript)
    flags = ["Explicit confirmation required"]
    if confidence is not None and confidence < 0.8:
        flags.append("OCR confidence is low; inspect the original image")
    if len(matches) > 1:
        flags.append("Multiple health values found")
    if not health:
        flags.append("Health measurement could not be identified")
    vin = re.search(r"\bVIN\s*[:=]?\s*([A-HJ-NPR-Z0-9]{17})\b", transcript, re.I)
    return {
        "detected_vin": vin.group(1).upper() if vin else None,
        "status": "review",
        "transcript": transcript,
        "measurement": "health" if health else "ambiguous",
        "value": value if health else None,
        "date": date.group(1) if date else None,
        "odometer": float(odometer.group(1).replace(",", "")) if odometer else None,
        "unit": ("km" if odometer.group(2).lower().startswith("k") else "mi") if odometer else None,
        "confidence": "review required",
        "review_flags": flags,
        "message": "Review extracted fields against the original image. Nothing is confirmed yet."
        if health
        else "We could not confirm this is battery health. Select the measurement type or enter a confirmed health reading.",
    }


def extract(path):
    binary = os.getenv("TESSERACT_BIN", "").strip()
    if not binary and not NATIVE.is_file():
        return {
            "status": "unavailable",
            "message": "Automatic extraction is not configured. Enter a confirmed reading manually.",
        }
    try:
        command = [binary, str(path), "stdout"] if binary else [str(NATIVE), "image", str(path)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=True)
        data = {"text": result.stdout} if binary else json.loads(result.stdout)
        return candidates(data["text"][:10000], data.get("confidence"))
    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
        return {
            "status": "failed",
            "message": "Image could not be read. Try a clearer image or enter manually.",
        }
