/* PFM User Journey Tracker — drop into WordPress <head> */
(function () {
  var K = 'pfm_sid', E = 'pfm_sid_exp', TTL = 864e5, URL = 'https://uj.pfm-qa.com/p';

  function uid() {
    return crypto.randomUUID ? crypto.randomUUID()
      : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
          var r = Math.random() * 16 | 0;
          return (c === 'x' ? r : r & 3 | 8).toString(16);
        });
  }

  function sid() {
    try {
      var n = Date.now(), v = localStorage.getItem(K), x = +localStorage.getItem(E);
      if (!v || n > x) { v = uid(); localStorage.setItem(K, v); localStorage.setItem(E, n + TTL); }
      return v;
    } catch (e) { return uid(); }
  }

  function send(eventType, pageUrl, referrer, metadata) {
    try {
      var payload = {
        session_id: sid(),
        event_type: eventType || 'page_view',
        page_url:   pageUrl   || location.href,
        referrer:   referrer  !== undefined ? referrer : document.referrer,
      };
      if (metadata && typeof metadata === 'object' && !Array.isArray(metadata)) {
        payload.metadata = metadata;
      }
      var p = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(URL, new Blob([p], { type: 'application/json' }));
      } else {
        var x = new XMLHttpRequest();
        x.open('POST', URL, true);
        x.setRequestHeader('Content-Type', 'application/json');
        x.send(p);
      }
    } catch (e) {}
  }

  // Auto-fire page_view on every page load
  send('page_view', location.href, document.referrer);

  // Global API for custom events.
  // Supports a pre-load queue: if code runs before this script (e.g. header vs footer),
  // callers push to window.pfmTrack.q and we drain it here on init.
  // Usage: window.pfmTrack('order_completed', { order_id: '123', value: 89.99, currency: 'USD' })
  function track(eventType, metadata) {
    send(eventType, location.href, '', metadata || null);
  }

  var q = window.pfmTrack && window.pfmTrack.q;
  if (q) {
    for (var i = 0; i < q.length; i++) track(q[i][0], q[i][1]);
  }

  window.pfmTrack = track;

  // Fingerprint collection — once per pfm session, fired in idle time after page load.
  // Loads thumbmark.min.js async, collects a browser fingerprint hash, and sends it
  // as a custom fp_collected event. Used server-side for session stitching only.
  // Triple-wrapped in try/catch — any failure is silent and never affects page load.
  (function () {
    var FP_KEY = 'pfm_fp_sid';
    try {
      if (localStorage.getItem(FP_KEY) === sid()) return;
    } catch (e) {}

    function collectFp() {
      try {
        var s = document.createElement('script');
        s.src = 'https://uj.pfm-qa.com/thumbmark.min.js';
        s.onload = function () {
          try {
            // ThumbmarkJS.getFingerprint() returns the hash string directly (v1.9.1+)
            ThumbmarkJS.getFingerprint().then(function (fp) {
              if (!fp) return;
              send('fp_collected', location.href, '', { fp: String(fp) });
              try { localStorage.setItem(FP_KEY, sid()); } catch (e) {}
            }).catch(function () {});
          } catch (e) {}
        };
        s.onerror = function () {};
        document.head.appendChild(s);
      } catch (e) {}
    }

    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(collectFp, { timeout: 5000 });
    } else {
      setTimeout(collectFp, 2000);
    }
  })();
})();
