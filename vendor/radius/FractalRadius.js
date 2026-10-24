// Experimental auto-discovered pump/fan RGB control, scheduler target 30 FPS.
// Same acknowledged Still-preview packets as the confirmed one-shot test.
// Physical LED order and long-term update behavior have not been established.
/* global LightingMode:readonly, forcedColor:readonly, testLed:readonly */
export function Name() { return "Fractal Radius RGB - Pump and Fans"; }
export function VendorId() { return 0x36BC; }
export function ProductId() { return 0x1003; }
export function Publisher() { return "Radius Community Test"; }
export function Type() { return "Hid"; }
const RGB_COUNT = 22;
const POSITIONS = Array.from({ length: RGB_COUNT }, (_, index) => [index, 0]);
let zones = [];
let ledNames = POSITIONS.map((_, index) => "Pump RGB " + String(index + 1).padStart(2, "0"));
let ledPositions = POSITIONS.slice();
let layoutSize = [RGB_COUNT, 1];
export function Size() { return layoutSize; }
export function LedNames() {
    return ledNames;
}
// Logical protocol order; physical geometry is intentionally not asserted.
export function LedPositions() { return ledPositions; }
export function Validate(endpoint) {
    return endpoint.interface === 0 && endpoint.usage_page === 0xFF00 &&
        endpoint.usage === 1;
}

export function ControllableParameters() {
    return [
        { property: "LightingMode", group: "lighting", label: "Lighting Mode",
          type: "combobox", values: ["Canvas", "Forced", "LED Test"], default: "Canvas" },
        { property: "forcedColor", group: "lighting", label: "Forced Color",
          type: "color", min: "0", max: "360", default: "#0000ff" },
        { property: "testLed", group: "lighting", label: "Test RGB Position (all zones)",
          type: "number", min: "1", max: "4096", step: "1", default: "1" }
    ];
}

let state = "idle";
let lastFrames = null;
let statsStart = 0;
let statsFrames = 0;
let statsIo = 0;
let statsMaxIo = 0;
const TARGET_FPS = 30;
const ORANGE = [255, 10, 0];
const PREFIX = "Radius RGB: ";

function pad(report) {
    while (report.length < 64) { report.push(0); }
    if (report.length !== 64) { throw new Error("Invalid report length"); }
    return report;
}

function stillReports(zone, frame) {
    if (frame.length !== zone.count * 3) { throw new Error("RGB zone length mismatch"); }
    const stream = [];
    for (const timestamp of [0, 562, 1124]) {
        stream.push(timestamp >> 8, timestamp & 255);
        stream.push(...frame);
    }
    let checksum = 0;
    for (const value of stream) { checksum = (checksum + value) & 255; }
    const reports = [
        pad([2, 0xA4, 0x0A, 1, zone.id]),
        pad([2, 0xA4, 0x11, 1, checksum, stream.length >> 8, stream.length & 255, 1, zones.length,
             0x99, 1, 100, ...frame.slice(0, 3), 100])
    ];
    for (let offset = 0; offset < stream.length; offset += 60) {
        const chunk = stream.slice(offset, offset + 60);
        reports.push(pad([2, 0xA4, 0x12, chunk.length, ...chunk]));
    }
    return reports;
}

function exchange(report) {
    // Report ID 02 is included. No extra zero prefix or 65-byte guess.
    device.write(report, 64);
    const reply = device.read([2], 64, 2000);
    const count = device.getLastReadSize();
    if (count !== 64 || !reply || reply.length !== 64 ||
        reply[0] !== report[0] || reply[1] !== report[1] ||
        reply[2] !== report[2] || reply[3] !== 0) {
        throw new Error("ACK mismatch for A4 " + report[2].toString(16) +
                        ", received bytes: " + count);
    }
    return reply;
}

function applyFrames(frames) {
    // The header declares the full batch size. Send every active zone if any
    // changes so the controller is never left waiting for the rest of a batch.
    for (let index = 0; index < zones.length; index++) {
        for (const report of stillReports(zones[index], frames[index])) { exchange(report); }
    }
}

function fail(error) {
    state = "failed";
    device.log(PREFIX + "STOP: " + String(error) +
        ". No retry. Restore Still / FF0A00 through Adjust if needed.");
}

function sameFrame(a, b) {
    return a !== null && a.length === b.length && a.every((value, i) => value === b[i]);
}

function sameFrames(a, b) {
    return a !== null && a.length === b.length && a.every((frame, i) => sameFrame(frame, b[i]));
}

function discoverZones() {
    const reply = exchange(pad([2, 0xA4, 0x08, 1]));
    const count = reply[4];
    if (count < 1 || count > 19) { throw new Error("Invalid RGB subdevice table length"); }
    const found = [];
    const seen = new Set();
    for (let index = 0; index < count; index++) {
        const offset = 5 + index * 3;
        const id = reply[offset];
        const leds = reply[offset + 1];
        if (seen.has(id)) { throw new Error("Duplicate RGB subdevice ID"); }
        seen.add(id);
        if (leds === 0) { continue; }
        if (id !== 1 && (id >> 4) !== 1) { throw new Error("Unexpected active RGB port"); }
        if (![0, 1, 2, 5].includes(reply[offset + 2])) { throw new Error("Unknown RGB protocol type"); }
        found.push({ id, count: leds, type: reply[offset + 2] });
    }
    const pump = found.find(zone => zone.id === 1);
    if (!pump || pump.count !== RGB_COUNT) { throw new Error("Expected the verified 22-position pump"); }
    const fanProtocols = new Set(found.filter(zone => zone.id !== 1).map(zone =>
        zone.type === 0 ? 2 : zone.type));
    if (fanProtocols.size > 1) {
        throw new Error("Ambiguous RGB protocols on fan port; inspect topology in Adjust first");
    }
    found.sort((a, b) => a.id - b.id);
    zones = found;
    let first = 0;
    ledNames = [];
    ledPositions = [];
    zones.forEach((zone, row) => {
        zone.row = row;
        zone.first = first;
        zone.label = zone.id === 1 ? "Pump" : "Fan RGB " + zone.id.toString(16).toUpperCase();
        for (let led = 0; led < zone.count; led++) {
            ledNames.push(zone.label + " RGB " + String(led + 1).padStart(2, "0"));
            ledPositions.push([led, row]);
        }
        first += zone.count;
    });
    layoutSize = [Math.max(...zones.map(zone => zone.count)), zones.length];
    device.setSize(layoutSize);
    device.setControllableLeds(ledNames, ledPositions);
    device.log(PREFIX + "RGB topology: " + zones.map(zone =>
        zone.label + "=" + zone.count + " positions").join(", "));
}

function rgbBytes(color) {
    if (!color || color.length !== 3 ||
        !color.every(value => Number.isInteger(value) && value >= 0 && value <= 255)) {
        throw new Error("Expected three RGB bytes from Canvas");
    }
    return [color[0], color[1], color[2]];
}

function uniformFrame(rgb, count) {
    const frame = [];
    for (let i = 0; i < count; i++) { frame.push(...rgb); }
    return frame;
}

function requestedFrames() {
    const mode = typeof LightingMode === "undefined" ? "Canvas" : LightingMode;
    let forced;
    let selected;
    if (mode === "Forced" || mode === "LED Test") {
        const hex = typeof forcedColor === "undefined" ? "#0000ff" : forcedColor;
        if (typeof hex !== "string" || !/^#[0-9a-f]{6}$/i.test(hex)) {
            throw new Error("Invalid forced color");
        }
        forced = [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16),
                  parseInt(hex.slice(5, 7), 16)];
        selected = typeof testLed === "undefined" ? 1 : Number(testLed);
        const total = zones.reduce((sum, zone) => sum + zone.count, 0);
        if (mode === "LED Test" && (!Number.isInteger(selected) || selected < 1 || selected > total)) {
            throw new Error("Test position must be 1.." + total);
        }
    }
    return zones.map(zone => {
        const frame = [];
        for (let index = 0; index < zone.count; index++) {
            const color = mode === "Forced" ? forced : mode === "LED Test" ?
                (zone.first + index === selected - 1 ? forced : [0, 0, 0]) :
                rgbBytes(device.color(index, zone.row));
            frame.push(...color);
        }
        return frame;
    });
}

function logStats() {
    const elapsed = Date.now() - statsStart;
    if (elapsed < 5000) { return; }
    device.log(PREFIX + "ACK frames/s=" + (statsFrames * 1000 / elapsed).toFixed(1) +
        ", mean/max transfer ms=" + (statsFrames ? statsIo / statsFrames : 0).toFixed(1) +
        "/" + statsMaxIo.toFixed(1) + "; target=30, unchanged frames skipped.");
    statsStart = Date.now();
    statsFrames = 0;
    statsIo = 0;
    statsMaxIo = 0;
}

export function Initialize() {
    state = "ready";
    lastFrames = null;
    statsStart = Date.now();
    statsFrames = 0;
    statsIo = 0;
    statsMaxIo = 0;
    try {
        device.setFrameRateTarget(TARGET_FPS);
        discoverZones();
        device.log(PREFIX + "READY: pump/fan RGB zones, 30 FPS scheduler target.");
    } catch (error) { fail(error); }
}

export function Render() {
    if (state !== "ready") { return; }
    try {
        const frames = requestedFrames();
        if (!sameFrames(lastFrames, frames)) {
            const first = lastFrames === null;
            const start = Date.now();
            applyFrames(frames);
            const duration = Date.now() - start;
            lastFrames = frames;
            statsFrames++;
            statsIo += duration;
            statsMaxIo = Math.max(statsMaxIo, duration);
            if (first) { device.log(PREFIX + "ACTIVE: first complete pump/fan RGB frame acknowledged."); }
        }
        logStats();
    } catch (error) { fail(error); }
}

export function Shutdown() {
    // No retry after an incomplete transaction; never write before first color.
    if (state !== "ready") { return; }
    state = "stopped";
    const orange = zones.map(zone => uniformFrame(ORANGE, zone.count));
    if (lastFrames === null || sameFrames(lastFrames, orange)) { return; }
    try {
        applyFrames(orange);
        lastFrames = orange;
        device.log(PREFIX + "STOPPED: orange acknowledged.");
    } catch (error) { fail(error); }
}

