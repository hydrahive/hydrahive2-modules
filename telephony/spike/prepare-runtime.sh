#!/usr/bin/env bash
set -euo pipefail

readonly CONTAINER_NAME="hh-telephony-spike"
readonly IMAGE="images:ubuntu/24.04"
readonly BARESIP_SHA="3d30821f099925d24167f8a99e93ba4d1be98599"
readonly LIBRE_SHA="ceefe9ff499aa1bcfb6255aff1737434dd385322"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PATCH_DIR="$SCRIPT_DIR/../patches"
readonly LIBRE_PATCH="libre-rport-contact.patch"
readonly BARESIP_PATCH="baresip-rport-contact.patch"
readonly RUNTIME_ROOT="/opt/hh-telephony-spike"
created=0

cleanup_failed_build() {
    local exit_code=$?
    if [[ $exit_code -ne 0 && $created -eq 1 ]]; then
        echo "Build failed; removing the newly created isolated container." >&2
        incus delete --force "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    exit "$exit_code"
}
trap cleanup_failed_build EXIT

command -v incus >/dev/null || {
    echo "incus is required" >&2
    exit 69
}
for patch in "$LIBRE_PATCH" "$BARESIP_PATCH"; do
    [[ -f "$PATCH_DIR/$patch" ]] || {
        echo "missing pinned source patch: $patch" >&2
        exit 66
    }
done

if incus info "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "Refusing to overwrite existing container: $CONTAINER_NAME" >&2
    exit 73
fi

incus init "$IMAGE" "$CONTAINER_NAME" \
    --config boot.autostart=false \
    --config limits.cpu=2 \
    --config limits.memory=1GiB \
    --config limits.processes=256
created=1
incus config device add "$CONTAINER_NAME" eth0 nic \
    nictype=bridged parent=br0 name=eth0
incus start "$CONTAINER_NAME"
for patch in "$LIBRE_PATCH" "$BARESIP_PATCH"; do
    incus file push "$PATCH_DIR/$patch" "$CONTAINER_NAME/root/$patch"
done

incus exec "$CONTAINER_NAME" -- bash -lc "
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    build-essential ca-certificates cmake git pkg-config libssl-dev python3
rm -rf /var/lib/apt/lists/*

install -d -m 0755 /usr/local/src/hh-sip-build /opt/baresip
cd /usr/local/src/hh-sip-build
git clone --filter=blob:none https://github.com/baresip/re.git libre
git -C libre checkout '$LIBRE_SHA'
test \"\$(git -C libre rev-parse HEAD)\" = '$LIBRE_SHA'
git -C libre apply --check "/root/$LIBRE_PATCH"
git -C libre apply "/root/$LIBRE_PATCH"
cmake -S libre -B libre/build \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_INSTALL_PREFIX=/opt/baresip \
    -DCMAKE_INSTALL_LIBDIR=lib
cmake --build libre/build --parallel 2
cmake --build libre/build --target retest --parallel 2
(cd libre && ./build/test/retest -r test_sipreg_rport_contact)
cmake --install libre/build
printf '%s\n' /opt/baresip/lib > /etc/ld.so.conf.d/baresip.conf
ldconfig

git clone --filter=blob:none https://github.com/baresip/baresip.git baresip
git -C baresip checkout '$BARESIP_SHA'
test \"\$(git -C baresip rev-parse HEAD)\" = '$BARESIP_SHA'
git -C baresip apply --check "/root/$BARESIP_PATCH"
git -C baresip apply "/root/$BARESIP_PATCH"
export PKG_CONFIG_PATH=/opt/baresip/lib/pkgconfig
cmake -S baresip -B baresip/build \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_INSTALL_PREFIX=/opt/baresip \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DRE_INCLUDE_DIR=/opt/baresip/include/re \
    -DRE_LIBRARY=/opt/baresip/lib/libre.so \
    -Dre_DIR=/opt/baresip/lib/cmake/re \
    -DMODULES='stdio;ctrl_tcp;g711;auconv;auresamp;aufile;ausine;uuid;account;menu;serreg;debug_cmd;netroam'
cmake --build baresip/build --parallel 2
(cd baresip/build && ./test/selftest \
    test_account_sipnat_received test_ua_alloc test_ua_register)
cmake --install baresip/build
ldconfig
rm -rf /usr/local/src/hh-sip-build "/root/$LIBRE_PATCH" "/root/$BARESIP_PATCH"
help_output=\"\$(/opt/baresip/bin/baresip -h 2>&1 || true)\"
grep -q 'Usage: baresip' <<<\"\$help_output\"
install -d -m 0755 '$RUNTIME_ROOT/spike'
"

for filename in \
    __init__.py cli.py config.py ctrl_tcp.py incoming_probe.py incoming_runtime.py probe.py \
    stdin_payload.py stdin_probe.py stdin_incoming_probe.py \
    run-probe.sh run-stdin-probe.sh run-stdin-incoming-probe.sh; do
    incus file push "$SCRIPT_DIR/$filename" \
        "$CONTAINER_NAME$RUNTIME_ROOT/spike/$filename"
done
incus exec "$CONTAINER_NAME" -- chmod 0755 \
    "$RUNTIME_ROOT/spike/run-probe.sh" \
    "$RUNTIME_ROOT/spike/run-stdin-probe.sh" \
    "$RUNTIME_ROOT/spike/run-stdin-incoming-probe.sh"

trap - EXIT
echo "ready: $CONTAINER_NAME"
echo "run: incus exec $CONTAINER_NAME -- $RUNTIME_ROOT/spike/run-probe.sh"
