#!/usr/bin/env bash
# Builds, aligns, signs and verifies the FUCK 9-5 watch face APK.
#
#   ./build.sh                 # signs with ./keystore/release.jks (created on first run)
#
# To sign with an existing key instead:
#   KEYSTORE=path/to/key.jks KEY_ALIAS=alias KS_PASS=password ./build.sh
#
# Tools (set via environment if they live elsewhere):
#   AAPT2      Android Asset Packaging Tool 2
#   ANDROID_JAR  android.jar / framework-res.apk to link against
#   APKSIGNER  apksigner.jar
set -euo pipefail
cd "$(dirname "$0")"

AAPT2="${AAPT2:-aapt2}"
ANDROID_JAR="${ANDROID_JAR:?set ANDROID_JAR to an android.jar (API 36) or framework-res.apk}"
APKSIGNER="${APKSIGNER:?set APKSIGNER to apksigner.jar}"
KEYSTORE="${KEYSTORE:-keystore/release.jks}"
KS_PASS="${KS_PASS:-android}"   # only for a key created here; keep real keys private
KEY_ALIAS="${KEY_ALIAS:-release}"

VERSION_CODE=$(python3 -c "import sys; sys.path.insert(0,'tools'); import design95 as design; print(design.VERSION_CODE)")
VERSION_NAME=$(python3 -c "import sys; sys.path.insert(0,'tools'); import design95 as design; print(design.VERSION_NAME)")
MIN_SDK=$(python3 -c "import sys; sys.path.insert(0,'tools'); import design95 as design; print(design.MIN_SDK)")
TARGET_SDK=$(python3 -c "import sys; sys.path.insert(0,'tools'); import design95 as design; print(design.TARGET_SDK)")

rm -rf build && mkdir -p build/compiled

echo "== compile resources"
"$AAPT2" compile --dir src/res -o build/compiled/res.zip

echo "== link"
"$AAPT2" link \
  -o build/n95-unsigned.apk \
  -I "$ANDROID_JAR" \
  --manifest src/AndroidManifest.xml \
  --min-sdk-version "$MIN_SDK" --target-sdk-version "$TARGET_SDK" \
  --version-code "$VERSION_CODE" --version-name "$VERSION_NAME" \
  build/compiled/res.zip

echo "== align"
python3 tools/zipalign.py build/n95-unsigned.apk build/n95-aligned.apk

if [ ! -f "$KEYSTORE" ]; then
  echo "== create signing key ($KEYSTORE)"
  mkdir -p "$(dirname "$KEYSTORE")"
  keytool -genkeypair -keystore "$KEYSTORE" -storetype PKCS12 -alias "$KEY_ALIAS" \
    -keyalg RSA -keysize 3072 -validity 10000 -dname "CN=FUCK 9-5 local build" \
    -storepass "$KS_PASS" -keypass "$KS_PASS" 2>&1 | grep -v "Picked up" || true
fi

echo "== sign"
java -jar "$APKSIGNER" sign --ks "$KEYSTORE" --ks-key-alias "$KEY_ALIAS" \
  --ks-pass "pass:$KS_PASS" --key-pass "pass:$KS_PASS" \
  --v1-signing-enabled false --v2-signing-enabled true --v3-signing-enabled true \
  --out build/fuck-9-5-watchface.apk build/n95-aligned.apk 2>&1 | grep -v "Picked up" || true

echo "== verify"
java -jar "$APKSIGNER" verify --verbose --min-sdk-version "$MIN_SDK" build/fuck-9-5-watchface.apk 2>&1 | grep -v "Picked up"
python3 tools/zipalign.py --check build/fuck-9-5-watchface.apk
ls -l build/fuck-9-5-watchface.apk
