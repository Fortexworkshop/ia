// Validation des messages reçus du serveur (OWASP A08 : ne pas faire confiance aux données reçues ;
// A10 : un message malformé est ignoré, il ne fait pas planter l'écran de supervision).
const num = (v) => typeof v === 'number' && Number.isFinite(v)
const str = (v, max = 500) => typeof v === 'string' && v.length <= max
const opt = (v, check) => v === undefined || v === null || check(v)
const time = (v) => num(v) || (str(v, 40) && !Number.isNaN(Date.parse(v)))

const RULES = {
  reading: (m) => time(m.ts) && ['temp', 'hum', 'gas'].every((k) => num(m[k])) && opt(m.pir, (v) => v === 0 || v === 1 || typeof v === 'boolean'),
  alert: (m) =>
    time(m.ts) && str(m.kind, 60) && ['critical', 'warning'].includes(m.level) && opt(m.message, str) && opt(m.source, (v) => str(v, 40)) &&
    opt(m.id, (v) => num(v) || str(v, 80)) && opt(m.unit, (v) => str(v, 20)) && opt(m.value, (v) => num(v) || str(v, 40)),
  'command-ack': (m) => m.cmd && ['buzzer', 'led'].includes(m.cmd.actuator) && typeof m.cmd.state === 'boolean',
  presence: (m) => time(m.ts) && str(m.kind, 20) && opt(m.person, (v) => str(v, 80)),
  ack: (m) => num(m.id) || str(m.id, 80),
  status: (m) => typeof m.online === 'boolean',
  auth: (m) => typeof m.ok === 'boolean',
}

export function validMessage(m) {
  if (!m || typeof m !== 'object' || !(m.type in RULES)) return false
  try {
    return Boolean(RULES[m.type](m))
  } catch {
    return false
  }
}
