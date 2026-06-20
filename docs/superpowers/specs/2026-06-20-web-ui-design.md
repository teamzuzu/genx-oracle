# TxLINE Web UI Design

**Date:** 2026-06-20
**Project:** genx-oracle
**Status:** Approved

## Overview

A vanilla HTML/JS/CSS live dashboard served directly from `txline-server` at `/`. Mirrors the `txline-watch` CLI — one row per fixture, updated in real-time from the same SSE endpoints.

---

## 1. File Layout

| File | Purpose |
|------|---------|
| `txline/api/static/index.html` | Page shell: `<head>`, `<table>` skeleton, loads CSS + JS |
| `txline/api/static/app.js` | All application logic — state, SSE handlers, render loop |
| `txline/api/static/style.css` | Dark theme, table layout, flash animation |
| `txline/api/server.py` (modified) | Mount `StaticFiles` at `/` after existing route registrations |

No build step. No external runtime dependencies. `StaticFiles` requires `pip install aiofiles` (already a FastAPI transitive dep).

---

## 2. FastAPI Wiring

```python
from fastapi.staticfiles import StaticFiles

# Inside create_app(), AFTER all @app.get() routes are registered:
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
```

`html=True` means a request to `/` returns `index.html`. Routes registered before the mount take priority — `/fixtures`, `/odds/stream`, `/scores/stream` continue to work unchanged.

---

## 3. HTML Shell (`index.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TxLINE Live</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>TxLINE Live</h1>
  <table id="dashboard">
    <thead>
      <tr>
        <th>Fixture</th>
        <th>Competition</th>
        <th>Kickoff</th>
        <th>Score</th>
        <th>State</th>
        <th>Market</th>
        <th>Prices</th>
        <th>Pct</th>
        <th>Updated</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
  <script src="app.js"></script>
</body>
</html>
```

Columns exactly mirror the CLI dashboard.

---

## 4. Application Logic (`app.js`)

### State

```js
const fixturesCache = new Map()   // fixtureId -> Fixture object
const state = new Map()           // fixtureId -> row object (see below)
let lastFlashId = null
let flashTimer = null
```

Row shape mirrors `FixtureState` from the CLI:

```js
{
  fixtureId,
  name,           // "Team A vs Team B" or raw id string until resolved
  competition,    // "—" until resolved
  kickoff,        // "19 Jun 14:00" or "—"
  score,          // "2 – 1" or "—"
  gameState,      // "FirstHalf" etc or "—"
  market,         // "1X2" etc or "—"
  prices,         // "over:1.788  under:2.269" or "—"
  pct,            // "55.93%  44.07%" or "—"
  updated,        // "HH:MM:SS"
}
```

### Startup sequence

```
1. fetch("/fixtures").then(data => populate fixturesCache)
2. new EventSource("/odds/stream")  — listen for "odds" events
3. new EventSource("/scores/stream") — listen for "scores" events
```

Fixture fetch failure is non-fatal — dashboard runs with raw IDs until resolved.

### Price/score formatting (matches CLI exactly)

| Data | Raw | Displayed |
|------|-----|-----------|
| `Prices` | `[1788, 2269]` | `1788/1000 = 1.788` |
| With `PriceNames` | `["over","under"], [1788,2269]` | `over:1.788  under:2.269` |
| `Pct` | `["55.928","44.072"]` | `55.928%  44.072%` |
| `scoreSoccer` | `{Home:2,Away:1}` | `2 – 1` |
| `StartTime` | `1781830800000` ms | `new Date(ms)` → `"19 Jun 14:00"` |

### Event handlers

**odds event:**
```js
const d = JSON.parse(e.data)
const fid = d.FixtureId
ensureRow(fid)
resolveNameFromCache(fid)
state.get(fid).market = d.SuperOddsType
state.get(fid).prices = formatPrices(d.Prices, d.PriceNames)
state.get(fid).pct = formatPct(d.Pct)
state.get(fid).updated = timeNow()
flash(fid)
render()
```

**scores event:**
```js
const d = JSON.parse(e.data)
const fid = d.fixtureId
ensureRow(fid)
resolveNameFromCache(fid)
state.get(fid).score = parseScore(d)
state.get(fid).gameState = d.gameState
state.get(fid).updated = timeNow()
flash(fid)
render()
```

### Flash highlight

```js
function flash(fid) {
  clearTimeout(flashTimer)
  lastFlashId = fid
  flashTimer = setTimeout(() => { lastFlashId = null; render() }, 800)
}
```

`render()` adds class `flash` to the `<tr>` whose `data-fid` matches `lastFlashId`.

### Render

```js
function render() {
  const sorted = [...state.values()].sort((a, b) => a.fixtureId - b.fixtureId)
  tbody.innerHTML = sorted.map(row => `
    <tr class="${row.fixtureId === lastFlashId ? 'flash' : ''}" data-fid="${row.fixtureId}">
      <td>${row.name}</td>
      ...
    </tr>
  `).join('')
}
```

Full `innerHTML` rebuild on every event is fine at the scale of dozens of fixtures.

---

## 5. Styles (`style.css`)

Dark background matching terminal aesthetic:

- Background: `#0d1117` (GitHub dark)
- Text: `#e6edf3`
- Table borders: `#30363d`
- Header: `#161b22`
- Score column: green (`#3fb950`)
- State column: yellow (`#d29922`)
- Prices column: bright white
- Pct column: cyan (`#58a6ff`)
- Flash row: `background: #1c2d3a` (brief blue tint, 0.8s transition back)

---

## 6. Error Handling

- EventSource auto-reconnects on disconnect (browser native behaviour)
- Fixture fetch failure: `console.warn`, proceed with raw IDs
- Malformed SSE data: `try/catch` around JSON.parse, skip event

---

## 7. No Tests

This is a static UI — no unit tests. Verification is manual: start `txline-server` and open `http://localhost:8000` in a browser.

---

## 8. No Controls

No filter input. No reconnect button. No connection status indicator. The page auto-connects on load and shows all fixtures. A `?fixtureId=12345` URL query param can be added in a future iteration.
