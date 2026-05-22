/**
 * PFM User Journey Tracker
 * Drop this snippet into WordPress <head> (child theme or Code Snippets plugin).
 * File name: app.js  — avoid "tracker", "analytics", "pixel" in the filename.
 */
(function () {
  'use strict';

  var SESSION_KEY     = 'pfm_sid';
  var SESSION_EXP_KEY = 'pfm_sid_exp';
  var SESSION_TTL_MS  = 2 * 60 * 60 * 1000; // 2 hours
  var COLLECTOR_URL   = 'https://uj.pfm-qa.com/p';

  function generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    // Fallback for older browsers
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function getSessionId() {
    try {
      var sid = localStorage.getItem(SESSION_KEY);
      var exp = parseInt(localStorage.getItem(SESSION_EXP_KEY) || '0', 10);
      var now = Date.now();

      if (!sid || now > exp) {
        sid = generateUUID();
        localStorage.setItem(SESSION_KEY, sid);
        localStorage.setItem(SESSION_EXP_KEY, String(now + SESSION_TTL_MS));
      }

      return sid;
    } catch (e) {
      // localStorage blocked (private browsing strict mode) — use ephemeral ID
      return generateUUID();
    }
  }

  function track() {
    try {
      var payload = JSON.stringify({
        session_id: getSessionId(),
        page_url:   window.location.href,
      });

      // sendBeacon is preferred: non-blocking, survives page unload
      if (typeof navigator.sendBeacon === 'function') {
        var blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(COLLECTOR_URL, blob);
      } else {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', COLLECTOR_URL, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(payload);
      }
    } catch (e) {
      // Never throw — tracking must never break the page
    }
  }

  track();
})();
