/* PFM User Journey Tracker — drop into WordPress <head> */
(function () {
  var K = 'pfm_sid', E = 'pfm_sid_exp', TTL = 72e5, URL = 'https://uj.pfm-qa.com/p';

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

  try {
    var p = JSON.stringify({ session_id: sid(), page_url: location.href, referrer: document.referrer });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(URL, new Blob([p], { type: 'application/json' }));
    } else {
      var x = new XMLHttpRequest();
      x.open('POST', URL, true);
      x.setRequestHeader('Content-Type', 'application/json');
      x.send(p);
    }
  } catch (e) {}
})();
