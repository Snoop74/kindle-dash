#!/bin/sh
[ -z "$DASH_FIXED" ] && sed -i "s/\r\$//" /mnt/us/extensions/kindle-dash/dash.sh /mnt/us/extensions/kindle-dash/dash.conf && DASH_FIXED=1 exec /bin/sh "$0" "$@" # strip CRLF once
# kindle-dash: wake at fixed local times, download dashboard PNG, show it, sleep.
# Target: Kindle Paperwhite 4 (FW 5.10.x), jailbroken + KUAL.

DIR="/mnt/us/extensions/kindle-dash"
. "$DIR/dash.conf"
LOG="$DIR/dash.log"
IMG="$DIR/dashboard.png"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# Keep log small
[ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 200000 ] && tail -n 300 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"

wifi_on() {
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    lipc-set-prop com.lab126.wifid enable 1 2>/dev/null
    i=0
    while [ $i -lt 60 ]; do
        state=$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)
        [ "$state" = "CONNECTED" ] && return 0
        sleep 1; i=$((i + 1))
    done
    log "wifi: not connected (state=$state)"
    return 1
}

wifi_off() {
    lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
}

sync_time() {
    # Best effort; Kindle has no Amazon time sync while jailbroken/offline
    if command -v ntpdate >/dev/null 2>&1; then
        ntpdate -s "$NTP_SERVER" 2>/dev/null && log "time synced" && return
    fi
    if command -v sntp >/dev/null 2>&1; then
        sntp -s "$NTP_SERVER" 2>/dev/null && log "time synced (sntp)" && return
    fi
    log "time sync skipped (no ntp tool)"
}

fetch() {
    rm -f "$IMG.tmp"
    curl -fsSL -m 60 -o "$IMG.tmp" "$DASH_URL" 2>>"$LOG" \
      || curl -fsSLk -m 60 -o "$IMG.tmp" "$DASH_URL" 2>>"$LOG" \
      || wget -q -O "$IMG.tmp" "$DASH_URL" 2>>"$LOG"
    if [ -s "$IMG.tmp" ]; then
        mv "$IMG.tmp" "$IMG"; log "fetched ok"; return 0
    fi
    log "fetch FAILED, keeping old image"; return 1
}

show() {
    [ -f "$IMG" ] || return
    eips -c
    eips -f -g "$IMG"
    # Low battery warning in the corner
    bat=$(gasgauge-info -c 2>/dev/null | tr -dc '0-9')
    [ -n "$bat" ] && [ "$bat" -lt 15 ] && eips 1 1 "PIL %$bat - SARJ ET"
}

# Seconds until next refresh slot (REFRESH_HOURS in local time, UTC offset fixed)
secs_until_next() {
    now=$(date +%s)
    local_sod=$(( (now + UTC_OFFSET_SEC) % 86400 ))
    best=999999
    for h in $REFRESH_HOURS; do
        t=$(( h * 3600 - local_sod ))
        [ $t -le 60 ] && t=$(( t + 86400 ))
        [ $t -lt $best ] && best=$t
    done
    echo $best
}

suspend_for() {
    secs=$1
    for rtc in /sys/class/rtc/rtc1 /sys/class/rtc/rtc0; do
        if [ -w "$rtc/wakealarm" ]; then
            echo 0 > "$rtc/wakealarm"
            echo "+$secs" > "$rtc/wakealarm"
            log "suspend ${secs}s via $rtc"
            sync
            echo mem > /sys/power/state
            return 0
        fi
    done
    log "no rtc wakealarm, falling back to sleep"
    sleep "$secs"
}

refresh_once() {
    if wifi_on; then
        sync_time
        fetch
    fi
    wifi_off
    show
}

case "$1" in
    test)
        # One-shot: download and show, GUI keeps running. Safe first test.
        log "=== test run ==="
        refresh_once
        ;;
    start)
        # Detach from KUAL: GUI stop below would otherwise kill us
        nohup /bin/sh "$0" run > /dev/null 2>&1 &
        ;;
    run)
        log "=== dashboard start ==="
        # Stop Kindle GUI so it does not redraw over us (FW 5.x upstart)
        stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
        lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
        sleep 3
        while true; do
            refresh_once
            suspend_for "$(secs_until_next)"
            sleep 5  # let drivers settle after resume
        done
        ;;
    *)
        echo "usage: $0 test|start|run"
        ;;
esac
