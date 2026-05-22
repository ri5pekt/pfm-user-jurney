export interface Attribution {
  source:      string;  // 'Google Ads', 'Facebook', 'Instagram', 'Klaviyo', etc.
  medium:      string;  // 'cpc', 'paid_social', 'email', 'organic', etc.
  channel:     string;  // 'paid_search', 'paid_shopping', 'paid_social', 'email', 'organic_shopping', 'organic_search', 'organic_social', 'referral', 'direct'
  placement:   string;  // 'Instagram Reels', 'Facebook Feed', etc.
  campaign_id: string;
  utm_source:  string;
  utm_medium:  string;
  utm_campaign: string;
}

const PLACEMENT_LABELS: Record<string, string> = {
  Facebook_Mobile_Feed:     'Facebook Feed',
  Facebook_Desktop_Feed:    'Facebook Feed',
  Facebook_Mobile_Reels:    'Facebook Reels',
  Facebook_Notification:    'Facebook Notification',
  Facebook_Marketplace:     'Facebook Marketplace',
  Facebook_Instream_Video:  'Facebook Video',
  Instagram_Reels:          'Instagram Reels',
  Instagram_Stories:        'Instagram Stories',
  Instagram_Feed:           'Instagram Feed',
  Threads_Feed:             'Threads',
  an:                       'Audience Network',
  Others:                   'Meta Other',
  others:                   'Meta Other',
};

export function parseAttribution(pageUrl: string, referrer: string): Attribution {
  const attr: Attribution = {
    source: '', medium: '', channel: '', placement: '',
    campaign_id: '', utm_source: '', utm_medium: '', utm_campaign: '',
  };

  let params: URLSearchParams;
  try {
    params = new URL(pageUrl).searchParams;
  } catch {
    return attr;
  }

  // Standard UTM — capture always, may be used as fallback
  attr.utm_source   = params.get('utm_source')   || '';
  attr.utm_medium   = params.get('utm_medium')   || '';
  attr.utm_campaign = params.get('utm_campaign') || '';

  // ── 1. nbt (Nextbee cross-platform ad tracking) ────────────────────
  // Format: nb:{network}:{platform}:{campaign_id}:{adset_id}:{ad_id}
  const nbt = params.get('nbt');
  if (nbt) {
    const parts    = nbt.split(':');
    const network  = parts[1] || '';
    const platform = parts[2] || '';
    attr.campaign_id = parts[3] || '';

    if (network === 'adwords') {
      const adtype    = params.get('nb_adtype') || '';
      const isShopping = adtype.startsWith('pla');
      attr.source  = 'Google Ads';
      attr.medium  = isShopping ? 'cpc' : 'cpc';
      attr.channel = isShopping ? 'paid_shopping' : 'paid_search';
    } else if (network === 'fb') {
      const raw   = params.get('nb_placement') || '';
      attr.placement = PLACEMENT_LABELS[raw] || raw;
      if (platform === 'ig') {
        attr.source = 'Instagram'; attr.medium = 'paid_social'; attr.channel = 'paid_social';
      } else if (platform === 'an') {
        attr.source = 'Audience Network'; attr.medium = 'paid_social'; attr.channel = 'paid_social';
      } else if (platform === 'th') {
        attr.source = 'Threads'; attr.medium = 'paid_social'; attr.channel = 'paid_social';
      } else {
        attr.source = 'Facebook'; attr.medium = 'paid_social'; attr.channel = 'paid_social';
      }
    }
    return attr;
  }

  // ── 2. Google Ads without nbt (gad_source / gad_campaignid) ────────
  if (params.has('gad_source') || params.has('gad_campaignid')) {
    attr.campaign_id = params.get('gad_campaignid') || '';
    attr.source  = 'Google Ads';
    attr.medium  = 'cpc';
    attr.channel = 'paid_search';
    return attr;
  }

  // ── 3. Google Shopping surfaces (srsltid) ──────────────────────────
  if (params.has('srsltid')) {
    attr.source  = 'Google Shopping';
    attr.medium  = 'organic';
    attr.channel = 'organic_shopping';
    return attr;
  }

  // ── 4. Klaviyo email ───────────────────────────────────────────────
  if (params.has('nb_klid') || params.has('_kx')) {
    attr.source  = 'Klaviyo';
    attr.medium  = 'email';
    attr.channel = 'email';
    return attr;
  }

  // ── 5. Beehiiv email ───────────────────────────────────────────────
  if (params.has('_bhiiv') || params.has('bhcl_id') || params.has('_bhlid')) {
    attr.source  = 'Beehiiv';
    attr.medium  = 'email';
    attr.channel = 'email';
    return attr;
  }

  // ── 6. Applov (mobile ad network) ─────────────────────────────────
  if (params.has('aleid') || params.has('alart')) {
    attr.source  = 'Applov';
    attr.medium  = 'paid';
    attr.channel = 'paid_other';
    return attr;
  }

  // ── 7. AdsSupply ───────────────────────────────────────────────────
  if (params.has('ads_id') || params.has('ads_site_id')) {
    attr.source  = 'AdsSupply';
    attr.medium  = 'paid';
    attr.channel = 'paid_other';
    return attr;
  }

  // ── 8. Snapchat click ID (ScCid) ───────────────────────────────────
  if (params.has('ScCid')) {
    attr.source  = 'Snapchat';
    attr.medium  = 'paid_social';
    attr.channel = 'paid_social';
    return attr;
  }

  // ── 9. Facebook Click ID (fbclid) — Meta paid without nbt ──────────
  // Catches utm_source=MetaAds campaigns and any other FB paid traffic
  // that uses fbclid but not nbt
  if (params.has('fbclid')) {
    attr.source  = 'Facebook';
    attr.medium  = 'paid_social';
    attr.channel = 'paid_social';
    const nbPlacement = params.get('nb_placement') || '';
    if (nbPlacement) attr.placement = PLACEMENT_LABELS[nbPlacement] || nbPlacement;
    return attr;
  }

  // ── 10. Google Click ID (gclid) — Google Ads without nbt ───────────
  if (params.has('gclid')) {
    const adtype    = params.get('nb_adtype') || params.get('utm_medium') || '';
    const isShopping = adtype.includes('pla') || adtype.includes('shopping');
    attr.source      = 'Google Ads';
    attr.medium      = 'cpc';
    attr.channel     = isShopping ? 'paid_shopping' : 'paid_search';
    attr.campaign_id = params.get('gad_campaignid') || '';
    return attr;
  }

  // ── 11. Standard UTM fallback ──────────────────────────────────────
  if (attr.utm_source) {
    attr.source  = attr.utm_source;
    attr.medium  = attr.utm_medium || 'referral';
    attr.channel = utmChannel(attr.utm_medium);
    return attr;
  }

  // ── 12. Referrer-based organic / social ───────────────────────────
  if (referrer) {
    try {
      const host = new URL(referrer).hostname.replace(/^www\./, '');
      if      (/\bgoogle\b/.test(host))           { attr.source = 'Google';    attr.medium = 'organic'; attr.channel = 'organic_search'; }
      else if (/\bbing\b/.test(host))             { attr.source = 'Bing';      attr.medium = 'organic'; attr.channel = 'organic_search'; }
      else if (/\byahoo\b/.test(host))            { attr.source = 'Yahoo';     attr.medium = 'organic'; attr.channel = 'organic_search'; }
      else if (/\bduckduckgo\b/.test(host))       { attr.source = 'DuckDuckGo'; attr.medium = 'organic'; attr.channel = 'organic_search'; }
      else if (/\bbrave\b/.test(host))            { attr.source = 'Brave';     attr.medium = 'organic'; attr.channel = 'organic_search'; }
      else if (/\bfacebook\b|fb\.com/.test(host)) { attr.source = 'Facebook';  attr.medium = 'social';  attr.channel = 'organic_social'; }
      else if (/\binstagram\b/.test(host))        { attr.source = 'Instagram'; attr.medium = 'social';  attr.channel = 'organic_social'; }
      else if (/\bpinterest\b/.test(host))        { attr.source = 'Pinterest'; attr.medium = 'social';  attr.channel = 'organic_social'; }
      // Same-site referrer on first event = session expired mid-browse or tab reload → direct
      else if (/\bparticleformen\b/.test(host))   { attr.source = 'direct';    attr.medium = 'none';    attr.channel = 'direct'; }
      else { attr.source = host; attr.medium = 'referral'; attr.channel = 'referral'; }
    } catch { /* ignore */ }
    return attr;
  }

  // ── 13. Direct ─────────────────────────────────────────────────────
  attr.source  = 'direct';
  attr.medium  = 'none';
  attr.channel = 'direct';
  return attr;
}

function utmChannel(medium: string): string {
  switch ((medium || '').toLowerCase()) {
    case 'cpc': case 'ppc': case 'paid_search': return 'paid_search';
    case 'paid_social': case 'social_paid':     return 'paid_social';
    case 'social':                              return 'organic_social';
    case 'email':                               return 'email';
    case 'sms':                                 return 'sms';
    case 'organic':                             return 'organic_search';
    case 'paid':                                return 'paid_other';
    default:                                    return 'referral';
  }
}
