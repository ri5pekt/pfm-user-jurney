const BOT_PATTERNS = [
  /bot/i,
  /crawl/i,
  /spider/i,
  /slurp/i,
  /facebookexternalhit/i,
  /LinkedInBot/i,
  /Twitterbot/i,
  /curl/i,
  /wget/i,
  /python-requests/i,
  /Go-http-client/i,
  /axios/i,
  /Googlebot/i,
  /bingbot/i,
  /YandexBot/i,
  /DuckDuckBot/i,
  /Baiduspider/i,
  /HeadlessChrome/i,
  /PhantomJS/i,
];

export function isBotRequest(userAgent: string | undefined): boolean {
  if (!userAgent || userAgent.trim() === '') return true;
  return BOT_PATTERNS.some((pattern) => pattern.test(userAgent));
}
