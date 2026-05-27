// ── User-Agent bot detection ────────────────────────────────────────────────
// Patterns are grouped by category for maintainability.
// All patterns are case-insensitive.

const BOT_UA_PATTERNS: RegExp[] = [
  // ── Search engine crawlers ────────────────────────────────────────────────
  /googlebot/i,
  /google-inspectiontool/i,
  /adsbot-google/i,
  /apis-google/i,
  /google-read-aloud/i,
  /mediapartners-google/i,
  /bingbot/i,
  /bingpreview/i,
  /adidxbot/i,
  /msnbot/i,
  /yandexbot/i,
  /yandexdirect/i,
  /yandexmetrika/i,
  /yandexfavicons/i,
  /yandexwebmaster/i,
  /baiduspider/i,
  /duckduckbot/i,
  /duckduckgo-favicons-bot/i,
  /sogou/i,
  /exabot/i,
  /ia_archiver/i,          // Alexa
  /archive\.org_bot/i,
  /seznambot/i,
  /naverbot/i,
  /petalbot/i,             // Huawei
  /applebot/i,
  /coccocbot/i,
  /mojeekbot/i,
  /qwantify/i,
  /uptimebot/i,

  // ── Social / preview crawlers ─────────────────────────────────────────────
  /facebookexternalhit/i,
  /facebookbot/i,
  /twitterbot/i,
  /linkedinbot/i,
  /whatsapp/i,
  /slackbot/i,
  /slack-imgproxy/i,
  /telegrambot/i,
  /discordbot/i,
  /skypeuripreview/i,
  /iframely/i,
  /embedly/i,
  /outbrain/i,
  /pinterest/i,
  /redditbot/i,
  /rogerbot/i,             // Moz

  // ── SEO / analytics tools ─────────────────────────────────────────────────
  /ahrefsbot/i,
  /semrushbot/i,
  /mj12bot/i,              // Majestic
  /dotbot/i,
  /blexbot/i,
  /dataforseobot/i,
  /siteauditbot/i,
  /serpstatbot/i,
  /cognitiveseo/i,
  /seokicks/i,
  /seoscannerbot/i,
  /screaming frog/i,
  /sistrix/i,

  // ── Monitoring / uptime tools ─────────────────────────────────────────────
  /pingdom/i,
  /uptimerobot/i,
  /statuscake/i,
  /newrelicpinger/i,
  /datadoghq/i,
  /site24x7/i,
  /hetrix/i,
  /freshpingbot/i,
  /better uptime/i,

  // ── Security scanners ─────────────────────────────────────────────────────
  /qualys/i,
  /shodan/i,
  /masscan/i,
  /nmap/i,
  /nikto/i,
  /zmeu/i,
  /sqlmap/i,
  /wfuzz/i,
  /nuclei/i,
  /acunetix/i,
  /nessus/i,
  /openvas/i,
  /burpsuite/i,
  /zgrab/i,
  /censys/i,

  // ── Generic crawlers / scrapers ───────────────────────────────────────────
  /\bbot\b/i,
  /\bcrawl/i,
  /\bspider\b/i,
  /\bscraper\b/i,

  // ── Headless / automation browsers ───────────────────────────────────────
  /headlesschrome/i,
  /headless/i,
  /phantomjs/i,
  /puppeteer/i,
  /playwright/i,
  /selenium/i,
  /cypress/i,
  /nightwatch/i,
  /webdriver/i,
  /slimerjs/i,

  // ── Raw HTTP clients ──────────────────────────────────────────────────────
  /^curl\//i,
  /^wget\//i,
  /^python-requests\//i,
  /^python-urllib\//i,
  /^go-http-client\//i,
  /^java\//i,
  /^apache-httpclient\//i,
  /^libwww-perl\//i,
  /^lwp-trivial/i,
  /^okhttp\//i,
  /^node-fetch\//i,
  /^got\//i,
  /^axios\//i,
  /^node\/\d/i,
  /^undici/i,
  /^ruby\//i,
  /^php\//i,
  /\.net clr/i,
  /jakarta commons/i,
];

// ── IP-based blocklist ──────────────────────────────────────────────────────
// First two octets (x.y) of known scanner / datacenter IPs that generate
// bot traffic. Conservative list — only include ranges where real shoppers
// are extremely unlikely. Configurable via BOT_IP_PREFIXES env var
// (comma-separated, e.g. "198.20,71.6,82.221").

const DEFAULT_BOT_IP_PREFIXES: string[] = [
  // Shodan scanners
  '198.20',   // shodan.io primary scanner range
  '71.6',     // shodan.io
  '82.221',   // shodan.io
  '66.240',   // shodan.io
  '93.120',   // shodan.io
  '188.138',  // shodan.io

  // Censys scanners
  '162.142',  // censys.io
  '167.248',  // censys.io

  // Common automated scanning IPs
  '89.248',   // shadowserver.org
  '94.102',   // PacketSec
  '185.220',  // tor exit nodes / scanners
];

function buildIpPrefixes(): Set<string> {
  const extra = (process.env.BOT_IP_PREFIXES ?? '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  return new Set([...DEFAULT_BOT_IP_PREFIXES, ...extra]);
}

// Lazily built once on first call
let _ipPrefixes: Set<string> | null = null;
function getBotIpPrefixes(): Set<string> {
  if (!_ipPrefixes) _ipPrefixes = buildIpPrefixes();
  return _ipPrefixes;
}

// ── Exports ──────────────────────────────────────────────────────────────────

export function isBotUserAgent(userAgent: string | undefined): boolean {
  if (!userAgent || userAgent.trim() === '') return true;
  return BOT_UA_PATTERNS.some(p => p.test(userAgent));
}

/**
 * Returns true if the IP matches a known bot/scanner prefix (first two octets).
 * IPv6 and private/loopback addresses are never blocked.
 */
export function isBotIp(ip: string | null | undefined): boolean {
  if (!ip) return false;
  // Skip IPv6 and private ranges
  if (ip.includes(':')) return false;
  const parts = ip.split('.');
  if (parts.length !== 4) return false;
  const prefix = `${parts[0]}.${parts[1]}`;
  return getBotIpPrefixes().has(prefix);
}

// Legacy alias used by existing import in collect.ts
export const isBotRequest = isBotUserAgent;
