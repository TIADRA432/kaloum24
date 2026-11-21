/* Date et heure de Conakry, mises à jour chaque seconde (aucun appel réseau). */
(function () {
  var d = document.querySelector("[data-vie-date]"), h = document.querySelector("[data-vie-heure]");
  if (!d || !h || !window.Intl) return;
  var opt = { timeZone: "Africa/Conakry" };
  var fd = new Intl.DateTimeFormat("fr-FR", Object.assign({ weekday: "long", day: "numeric", month: "long" }, opt));
  var fh = new Intl.DateTimeFormat("fr-FR", Object.assign({ hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }, opt));
  function tick() { var n = new Date(); d.textContent = fd.format(n); h.textContent = fh.format(n); }
  tick(); setInterval(tick, 1000);
})();
