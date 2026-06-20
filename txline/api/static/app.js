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
