export interface Token { text: string; kind: 'ok' | 'wrong' | 'missing' | 'extra'; expected?: string }

const strip = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/œ/g, 'oe').replace(/æ/g, 'ae').replace(/ß/g, 'ss')
const clean = (s: string) => s.toLowerCase().replace(/[.,!?;:«»„“"()\u2026]/g, ' ').replace(/\u2019/g, "'").trim()
const words = (s: string) => clean(s).split(/\s+/).filter(Boolean)

export function compare(expected: string, attempt: string, strictAccents: boolean) {
  const E = words(expected), A = words(attempt)
  const norm = (w: string) => (strictAccents ? w : strip(w))
  // LCS alignment
  const n = E.length, m = A.length
  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = norm(E[i]) === norm(A[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
  const out: Token[] = []
  let i = 0, j = 0, ok = 0
  while (i < n && j < m) {
    if (norm(E[i]) === norm(A[j])) { out.push({ text: E[i], kind: 'ok' }); ok++; i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) {
      // expected word missing (maybe substituted)
      if (dp[i + 1][j + 1] === dp[i + 1][j] && j < m) { out.push({ text: A[j], kind: 'wrong', expected: E[i] }); i++; j++ }
      else { out.push({ text: E[i], kind: 'missing' }); i++ }
    } else { out.push({ text: A[j], kind: 'extra' }); j++ }
  }
  while (i < n) { out.push({ text: E[i++], kind: 'missing' }) }
  while (j < m) { out.push({ text: A[j++], kind: 'extra' }) }
  const score = n === 0 ? 1 : ok / n
  return { tokens: out, score }
}
