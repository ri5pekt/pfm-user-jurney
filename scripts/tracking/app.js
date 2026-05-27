/* PFM User Journey Tracker — drop into WordPress <head> */
(function () {
  var K = 'pfm_sid', E = 'pfm_sid_exp', CK = 'pfm_sid', TTL = 864e5, URL = 'https://uj.pfm-qa.com/p';

  function uid() {
    return crypto.randomUUID ? crypto.randomUUID()
      : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
          var r = Math.random() * 16 | 0;
          return (c === 'x' ? r : r & 3 | 8).toString(16);
        });
  }

  // ── Cookie helpers ────────────────────────────────────────────────
  function setCookie(val, ttlMs) {
    try {
      var exp = new Date(Date.now() + ttlMs).toUTCString();
      document.cookie = CK + '=' + val + '; expires=' + exp + '; path=/; SameSite=Lax';
    } catch (e) {}
  }

  function getCookie() {
    try {
      var m = document.cookie.match(/(?:^|;\s*)pfm_sid=([^;]+)/);
      return m ? m[1] : null;
    } catch (e) { return null; }
  }

  // ── Session ID — stored in both localStorage and cookie ───────────
  // Priority: localStorage (if not expired) → cookie → new UUID.
  // Whichever wins, both storages are kept in sync for resilience:
  //   - If localStorage is wiped by a privacy tool, the cookie restores it.
  //   - If cookies are blocked, localStorage still works.
  function sid() {
    try {
      var n = Date.now();
      var lsVal = localStorage.getItem(K);
      var lsExp = +localStorage.getItem(E);
      var ckVal = getCookie();

      if (lsVal && n < lsExp) {
        // localStorage is valid — sync cookie if it drifted
        if (ckVal !== lsVal) setCookie(lsVal, lsExp - n);
        return lsVal;
      }

      if (ckVal) {
        // localStorage expired/cleared — restore from cookie
        var restoredExp = n + TTL;
        localStorage.setItem(K, ckVal);
        localStorage.setItem(E, restoredExp);
        setCookie(ckVal, TTL);
        return ckVal;
      }

      // Neither is available — create a new session ID
      var v = uid();
      localStorage.setItem(K, v);
      localStorage.setItem(E, n + TTL);
      setCookie(v, TTL);
      return v;
    } catch (e) {
      // localStorage blocked (e.g. private mode strict) — try cookie only
      var ck = getCookie();
      if (ck) return ck;
      var newId = uid();
      setCookie(newId, TTL);
      return newId;
    }
  }

  // ── Send ──────────────────────────────────────────────────────────
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

  // ── Auto-fire page_view, including raw ls/cookie diagnostic ──────
  // Capture the raw values BEFORE sid() normalises/syncs them so we
  // can see in the admin whether they were present and whether they matched.
  var rawLs = null, rawCk = getCookie();
  try { rawLs = localStorage.getItem(K); } catch (e) {}
  send('page_view', location.href, document.referrer, { ls_sid: rawLs, cookie_sid: rawCk });

  // ── Global API for custom events ──────────────────────────────────
  function track(eventType, metadata) {
    send(eventType, location.href, '', metadata || null);
  }

  var q = window.pfmTrack && window.pfmTrack.q;
  if (q) {
    for (var i = 0; i < q.length; i++) track(q[i][0], q[i][1]);
  }

  window.pfmTrack = track;
})();
