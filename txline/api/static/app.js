// --- Formatting helpers ---

function formatKickoff(startTimeMs) {
  if (!startTimeMs) return '—'
  const d = new Date(startTimeMs)
  const day = d.getDate().toString().padStart(2, '0')
  const month = d.toLocaleString('en', { month: 'short' })
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  return `${day} ${month} ${hh}:${mm}`
}

function formatPrices(prices, priceNames) {
  if (!prices || prices.length === 0) return '—'
  if (priceNames && priceNames.length === prices.length) {
    return priceNames.map((n, i) => `${n}:${(prices[i] / 1000).toFixed(3)}`).join('  ')
  }
  return prices.map(p => (p / 1000).toFixed(3)).join('  ')
}

function formatPct(pct) {
  if (!pct || pct.length === 0) return '—'
  return pct.map(p => `${p}%`).join('  ')
}

function parseScore(d) {
  if (d.scoreSoccer) {
    const h = d.scoreSoccer.Home ?? d.scoreSoccer.home ?? '?'
    const a = d.scoreSoccer.Away ?? d.scoreSoccer.away ?? '?'
    return `${h} – ${a}`
  }
  if (d.score) return String(d.score)
  return '—'
}

function timeNow() {
  const now = new Date()
  return [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map(n => n.toString().padStart(2, '0'))
    .join(':')
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// --- State ---

const fixturesCache = new Map()  // fixtureId (number) -> Fixture object from /fixtures
const state = new Map()          // fixtureId (number) -> row object
let lastFlashId = null
let flashTimer = null

const tbody = document.getElementById('rows')

function ensureRow(fid) {
  if (!state.has(fid)) {
    state.set(fid, {
      fixtureId: fid,
      name: String(fid),
      competition: '—',
      kickoff: '—',
      score: '—',
      gameState: '—',
      market: '—',
      prices: '—',
      pct: '—',
      updated: '',
    })
  }
}

function resolveNameFromCache(fid) {
  const row = state.get(fid)
  if (row.name !== String(fid)) return  // already resolved
  const fix = fixturesCache.get(fid)
  if (!fix) return
  row.name = `${fix.Participant1} vs ${fix.Participant2}`
  row.competition = fix.Competition
  row.kickoff = formatKickoff(fix.StartTime)
}

// --- Flash ---

function flash(fid) {
  clearTimeout(flashTimer)
  lastFlashId = fid
  flashTimer = setTimeout(() => { lastFlashId = null; render() }, 800)
}

// --- Render ---

function render() {
  const sorted = [...state.values()].sort((a, b) => a.fixtureId - b.fixtureId)
  tbody.innerHTML = sorted.map(row => `
    <tr class="${row.fixtureId === lastFlashId ? 'flash' : ''}" data-fid="${row.fixtureId}">
      <td class="fix-name">${esc(row.name)}</td>
      <td class="comp">${esc(row.competition)}</td>
      <td class="kickoff">${esc(row.kickoff)}</td>
      <td class="score">${esc(row.score)}</td>
      <td class="state">${esc(row.gameState)}</td>
      <td class="market">${esc(row.market)}</td>
      <td class="prices">${esc(row.prices)}</td>
      <td class="pct">${esc(row.pct)}</td>
      <td class="updated">${esc(row.updated)}</td>
    </tr>
  `).join('')
}
