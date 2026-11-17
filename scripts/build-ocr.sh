#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ]; then
  echo "Use TESSERACT_BIN on this platform; native Vision requires macOS."
  exit 1
fi
swiftc -module-cache-path "${TMPDIR:-/tmp}/battery-swift-cache" scripts/native/vision.swift -o scripts/native/battery-vision
printf '%s\n' 'Local Vision OCR is ready. It runs on uploaded images only when requested.'
