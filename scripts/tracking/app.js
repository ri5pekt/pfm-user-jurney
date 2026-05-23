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

  function send(eventType, pageUrl, referrer) {
    try {
      var p = JSON.stringify({
        session_id: sid(),
        event_type: eventType || 'page_view',
        page_url:   pageUrl   || location.href,
        referrer:   referrer  !== undefined ? referrer : document.referrer,
      });
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

  // Global API for custom events
  // Usage: window.pfmTrack('order_completed')
  window.pfmTrack = function (eventType) {
    send(eventType, location.href, '');
  };
})();
