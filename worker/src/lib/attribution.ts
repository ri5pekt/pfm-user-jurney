export interface Attribution {
  source:       string;
  medium:       string;
  channel:      string;
  placement:    string;
  campaign_id:  string;
  utm_source:   string;
  utm_medium:   string;
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

// Domains that are email relay / proxy services — referrer means the user came from email
const EMAIL_RELAY_DOMAINS = [
  'deref-mail.com', 'pstmrk.it', 'track.pstmrk.it',
  'webmailb.netzero.net', 'webmail1.earthlink.net',
  // ISP webmail portals
  'mail3.spectrum.net', 'myemail.optimum.net', 'myemail.suddenlink.net',
  'webmail1.earthlink.net',
];

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

  attr.utm_source   = params.get('utm_source')   || '';
  attr.utm_medium   = params.get('utm_medium')   || '';
  attr.utm_campaign = params.get('utm_campaign') || '';

  // ── 1. nbt (Nextbee cross-platform ad tracking) ────────────────────
  // Format: nb:{network}:{platform}:{campaign_id}:{adset_id}:{ad_id}
  const nbt = params.get('nbt');
  if (nbt) {
    const parts      = nbt.split(':');
    const network    = parts[1] || '';
    const platform   = parts[2] || '';
    attr.campaign_id = parts[3] || '';

    if (network === 'adwords') {
      const adtype     = params.get('nb_adtype') || '';
      const isShopping = adtype.startsWith('pla');
      attr.source  = 'Google Ads';
      attr.medium  = 'cpc';
      attr.channel = isShopping ? 'paid_shopping' : 'paid_search';
      return attr;
    }

    if (network === 'fb') {
      const raw      = params.get('nb_placement') || '';
      attr.placement = PLACEMENT_LABELS[raw] || raw;
      if      (platform === 'ig') { attr.source = 'Instagram';        }
      else if (platform === 'an') { attr.source = 'Audience Network'; }
      else if (platform === 'th') { attr.source = 'Threads';          }
      else                        { attr.source = 'Facebook';         }
      attr.medium  = 'paid_social';
      attr.channel = 'paid_social';
      return attr;
    }

    if (network === 'microsoft') {
      attr.source  = 'Bing Ads';
      attr.medium  = 'cpc';
      attr.channel = 'paid_search';
      return attr;
    }
    // Unknown nbt network — fall through to other checks below
  }

  // ── 2. Google Ads — gad_source / gad_campaignid ────────────────────
  if (params.has('gad_source') || params.has('gad_campaignid')) {
    attr.campaign_id = params.get('gad_campaignid') || '';
    const adtype     = params.get('nb_adtype') || '';
    attr.source  = 'Google Ads';
    attr.medium  = 'cpc';
    attr.channel = adtype.startsWith('pla') ? 'paid_shopping' : 'paid_search';
    return attr;
  }

  // ── 3. Google click IDs (gclid / wbraid / gbraid) ──────────────────
  if (params.has('gclid') || params.has('wbraid') || params.has('gbraid')) {
    const adtype = params.get('nb_adtype') || params.get('utm_medium') || '';
    attr.source      = 'Google Ads';
    attr.medium      = 'cpc';
    attr.channel     = adtype.includes('pla') || adtype.includes('shopping') ? 'paid_shopping' : 'paid_search';
    attr.campaign_id = params.get('gad_campaignid') || '';
    return attr;
  }

  // ── 4. Microsoft / Bing click ID (msclkid) ─────────────────────────
  if (params.has('msclkid')) {
    attr.source  = 'Bing Ads';
    attr.medium  = 'cpc';
    attr.channel = 'paid_search';
    return attr;
  }

  // ── 4b. Bing Ads without nbt/msclkid — nb_bmt or nb_qs present ─────
  // nb_bmt = Bing match type (be=exact, bp=phrase, bb=broad)
  // nb_qs  = search query captured by Nextbee Bing pixel
  if (params.has('nb_bmt') || (params.has('nb_qs') && params.has('nb_oii'))) {
    attr.source  = 'Bing Ads';
    attr.medium  = 'cpc';
    attr.channel = 'paid_search';
    return attr;
  }

  // ── 5. Google Shopping surfaces (srsltid) ──────────────────────────
  if (params.has('srsltid')) {
    attr.source  = 'Google Shopping';
    attr.medium  = 'organic';
    attr.channel = 'organic_shopping';
    return attr;
  }

  // ── 6. Klaviyo email / SMS ─────────────────────────────────────────
  if (params.has('nb_klid') || params.has('_kx')) {
    attr.source  = 'Klaviyo';
    attr.medium  = params.get('utm_medium')?.toLowerCase() === 'sms' ? 'sms' : 'email';
    attr.channel = attr.medium === 'sms' ? 'sms' : 'email';
    return attr;
  }

  // ── 7. Beehiiv email ───────────────────────────────────────────────
  if (params.has('_bhiiv') || params.has('bhcl_id') || params.has('_bhlid')) {
    attr.source  = 'Beehiiv';
    attr.medium  = 'email';
    attr.channel = 'email';
    return attr;
  }

  // ── 8. Applov / AppsLovin (aleid / alart params) ───────────────────
  if (params.has('aleid') || params.has('alart')) {
    attr.source  = 'Applov';
    attr.medium  = 'paid';
    attr.channel = 'paid_other';
    return attr;
  }

  // ── 9. AdsSupply ───────────────────────────────────────────────────
  if (params.has('ads_id') || params.has('ads_site_id')) {
    attr.source  = 'AdsSupply';
    attr.medium  = 'paid';
    attr.channel = 'paid_other';
    return attr;
  }

  // ── 10. Snapchat ────────────────────────────────────────────────────
  if (params.has('ScCid') || params.has('_sc_p') || params.has('csatc')) {
    attr.source  = 'Snapchat';
    attr.medium  = 'paid_social';
    attr.channel = 'paid_social';
    return attr;
  }

  // ── 11. Facebook Click ID (fbclid) — Meta paid without nbt ─────────
  if (params.has('fbclid')) {
    attr.source    = 'Facebook';
    attr.medium    = 'paid_social';
    attr.channel   = 'paid_social';
    const raw      = params.get('nb_placement') || '';
    attr.placement = PLACEMENT_LABELS[raw] || raw;
    return attr;
  }

  // ── 12. UTM-based attribution ──────────────────────────────────────
  if (attr.utm_source) {
    const src = attr.utm_source.toLowerCase().replace(/\s+/g, '');
    const med = (attr.utm_medium || '').toLowerCase();

    // Meta / Facebook (utm_source=MetaAds without fbclid)
    if (src === 'metaads' || src === 'meta' || src === 'facebook' || src === 'fb') {
      attr.source  = 'Facebook';
      attr.medium  = 'paid_social';
      attr.channel = 'paid_social';
      return attr;
    }
    // Snapchat
    if (src === 'snapchat') {
      attr.source  = 'Snapchat';
      attr.medium  = 'paid_social';
      attr.channel = 'paid_social';
      return attr;
    }
    // Bing / Microsoft
    if (src === 'bing' || src === 'microsoft') {
      attr.source  = 'Bing Ads';
      attr.medium  = 'cpc';
      attr.channel = 'paid_search';
      return attr;
    }
    // Google (utm_source=google without gclid/gad)
    if (src === 'google') {
      attr.source  = med === 'cpc' ? 'Google Ads' : 'Google';
      attr.medium  = med || 'organic';
      attr.channel = med === 'cpc' ? 'paid_search' : 'organic_search';
      return attr;
    }
    // Beehiiv
    if (src === 'beehiiv') {
      attr.source  = 'Beehiiv';
      attr.medium  = 'email';
      attr.channel = 'email';
      return attr;
    }
    // Narvar (post-purchase shipping notifications)
    if (src.includes('narvar')) {
      attr.source  = 'Narvar';
      attr.medium  = 'email';
      attr.channel = 'email';
      return attr;
    }
    // Yotpo (loyalty / rewards emails)
    if (src.includes('yotpo') || src.includes('rewards') || src.includes('loyalty') || src.includes('points')) {
      attr.source  = 'Yotpo';
      attr.medium  = 'email';
      attr.channel = 'email';
      return attr;
    }
    // AppsLovin / Applov (utm_source=applovin or axon)
    if (src === 'applovin' || src === 'axon') {
      attr.source  = 'Applov';
      attr.medium  = 'paid';
      attr.channel = 'paid_other';
      return attr;
    }
    // Klaviyo flows/campaigns with utm_source names (no nb_klid)
    if (med === 'email' || med === 'sms') {
      // Keep utm_source as the platform name but normalise channel
      attr.source  = attr.utm_source;
      attr.medium  = med;
      attr.channel = med === 'sms' ? 'sms' : 'email';
      return attr;
    }

    // Generic UTM fallback
    attr.source  = attr.utm_source;
    attr.medium  = attr.utm_medium || 'referral';
    attr.channel = utmChannel(attr.utm_medium);
    return attr;
  }

  // ── 13. Referrer-based attribution ────────────────────────────────
  if (referrer) {
    // Android app scheme: android-app://com.google.android.gm/ etc.
    if (referrer.startsWith('android-app://')) {
      const appId = referrer.toLowerCase();
      if (appId.includes('.gm') || appId.includes('mail')) {
        attr.source = 'Email'; attr.medium = 'email'; attr.channel = 'email';
      } else if (appId.includes('google') || appId.includes('search')) {
        attr.source = 'Google'; attr.medium = 'organic'; attr.channel = 'organic_search';
      } else {
        attr.source = 'direct'; attr.medium = 'none'; attr.channel = 'direct';
      }
      return attr;
    }

    try {
      const host = new URL(referrer).hostname.replace(/^www\./, '');

      if      (/\bgoogle\b/.test(host))             { attr.source = 'Google';      attr.medium = 'organic'; attr.channel = 'organic_search';  }
      else if (/\bbing\b/.test(host))               { attr.source = 'Bing';        attr.medium = 'organic'; attr.channel = 'organic_search';  }
      else if (/\byahoo\b/.test(host))              { attr.source = 'Yahoo';       attr.medium = 'organic'; attr.channel = 'organic_search';  }
      else if (/\bduckduckgo\b/.test(host))         { attr.source = 'DuckDuckGo';  attr.medium = 'organic'; attr.channel = 'organic_search';  }
      else if (/\bbrave\b/.test(host))              { attr.source = 'Brave';       attr.medium = 'organic'; attr.channel = 'organic_search';  }
      else if (/\bfacebook\b|^fb\.com$|^l\.facebook|^m\.facebook|^lm\.facebook/.test(host)) {
        attr.source = 'Facebook';   attr.medium = 'social';  attr.channel = 'organic_social';
      }
      else if (/\binstagram\b/.test(host))          { attr.source = 'Instagram';   attr.medium = 'social';  attr.channel = 'organic_social';  }
      else if (/\bpinterest\b/.test(host))          { attr.source = 'Pinterest';   attr.medium = 'social';  attr.channel = 'organic_social';  }
      else if (/\byoutube\b/.test(host))            { attr.source = 'YouTube';     attr.medium = 'social';  attr.channel = 'organic_social';  }
      else if (/\bthreads\b/.test(host))            { attr.source = 'Threads';     attr.medium = 'social';  attr.channel = 'organic_social';  }
      else if (/\bsnapchat\b/.test(host))           { attr.source = 'Snapchat';    attr.medium = 'social';  attr.channel = 'organic_social';  }
      // Email relay / webmail services — user clicked email link
      else if (EMAIL_RELAY_DOMAINS.some(d => host.includes(d)))  {
        attr.source = 'Email'; attr.medium = 'email'; attr.channel = 'email';
      }
      else if (/\bmail\.google\b/.test(host))       { attr.source = 'Gmail';          attr.medium = 'email';    attr.channel = 'email';           }
      // Microsoft Edge news / content recommendation
      else if (/\bedgepilot\b/.test(host))          { attr.source = 'Microsoft Edge'; attr.medium = 'referral'; attr.channel = 'referral';        }
      // Email security URL scanner — pre-scans links, not a real user
      else if (/\besvalabs\b|\burlsand\b/.test(host)) { attr.source = 'direct'; attr.medium = 'none'; attr.channel = 'direct'; }
      // Afterpay / BNPL redirect back to site — treat as direct (mid-checkout)
      else if (/\bafterpay\b/.test(host))           { attr.source = 'direct';      attr.medium = 'none';    attr.channel = 'direct';          }
      // Same-site referrer on first event = session expired mid-browse → direct
      else if (/\bparticleformen\b/.test(host))     { attr.source = 'direct';      attr.medium = 'none';    attr.channel = 'direct';          }
      else { attr.source = host; attr.medium = 'referral'; attr.channel = 'referral'; }

    } catch { /* ignore malformed referrer */ }
    return attr;
  }

  // ── 14. Direct ────────────────────────────────────────────────────
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
