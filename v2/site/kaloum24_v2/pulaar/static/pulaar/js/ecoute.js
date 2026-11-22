/* Bouton « Écouter » d'une entrée : lit l'enregistrement, un seul à la fois. */
(function () {
  var courant = null;
  document.addEventListener("click", function (ev) {
    var bouton = ev.target.closest("[data-ecoute]");
    if (!bouton) return;
    var audio = document.getElementById(bouton.getAttribute("data-ecoute"));
    if (!audio) return;
    if (courant && courant !== audio) { courant.pause(); courant.currentTime = 0; }
    courant = audio;
    if (audio.paused) { audio.currentTime = 0; audio.play(); } else { audio.pause(); }
  });
  document.querySelectorAll("audio[data-ecoute-audio]").forEach(function (a) {
    a.addEventListener("play", function () {
      var b = document.querySelector('[data-ecoute="' + a.id + '"]');
      if (b) b.setAttribute("aria-pressed", "true");
    });
    a.addEventListener("pause", function () {
      var b = document.querySelector('[data-ecoute="' + a.id + '"]');
      if (b) b.setAttribute("aria-pressed", "false");
    });
  });
})();
