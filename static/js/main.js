/* Kaloum24 — interactions du site public */
(function () {
  "use strict";

  // ------------------------------------------------------------ thème
  // Le choix est appliqué très tôt (script inline dans <head>) pour éviter
  // le flash de thème clair au chargement. Ici on gère seulement la bascule.
  function initTheme() {
    var toggle = document.getElementById("themeToggle");
    if (!toggle) return;

    toggle.addEventListener("click", function () {
      var actuel = document.documentElement.getAttribute("data-theme");
      var nouveau = actuel === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", nouveau);
      try {
        localStorage.setItem("theme", nouveau);
      } catch (e) {
        /* navigation privée : le choix ne survivra pas au rechargement */
      }
      toggle.setAttribute(
        "aria-label",
        nouveau === "dark" ? "Passer en mode clair" : "Passer en mode sombre"
      );
    });
  }

  // ------------------------------------------------------ menu mobile
  function initNav() {
    var toggle = document.getElementById("navToggle");
    var nav = document.getElementById("primaryNav");
    if (!toggle || !nav) return;

    toggle.addEventListener("click", function () {
      var ouvert = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", ouvert ? "true" : "false");
    });
  }

  // ---------------------------------------------------------- bandeau
  function initTicker() {
    var track = document.querySelector(".ticker__track");
    if (track && track.children.length > 0) {
      track.innerHTML += track.innerHTML; // boucle sans coupure
    }
  }

  // ------------------------------------------------------------ météo
  function initWeather() {
    var box = document.getElementById("weather");
    if (!box) return;

    var CODES = {
      0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
      51: "🌦️", 53: "🌦️", 55: "🌦️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
      71: "🌨️", 73: "🌨️", 75: "🌨️", 80: "🌦️", 81: "🌧️", 82: "⛈️",
      95: "⛈️", 96: "⛈️", 99: "⛈️"
    };

    fetch("/api/meteo")
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (d) {
        if (!d.disponible) return;
        box.textContent = (CODES[d.code] || "🌡️") + " " + d.temperature + "°C · " + d.ville;
        box.hidden = false;
      })
      .catch(function () {
        /* météo indisponible : on laisse simplement le bloc masqué */
      });
  }

  // --------------------------------------------- lecture audio (TTS)
  // Utilise l'API de synthèse vocale du navigateur : gratuite, sans clé API
  // et sans coût récurrent. Sur Chrome et Android, ce sont les voix Google.
  function initTTS() {
    var bouton = document.getElementById("ttsButton");
    if (!bouton) return;

    if (!("speechSynthesis" in window)) {
      bouton.hidden = true;
      return;
    }

    var synth = window.speechSynthesis;
    var lang = bouton.dataset.lang || "fr-FR";
    var enCours = false;

    function texteArticle() {
      var titre = document.querySelector(".article-header h1");
      var corps = document.querySelector(".article-body");
      var morceaux = [];
      if (titre) morceaux.push(titre.textContent);
      if (corps) morceaux.push(corps.textContent);
      return morceaux.join(". ").replace(/\s+/g, " ").trim();
    }

    function choisirVoix() {
      var voix = synth.getVoices();
      // Priorité à une voix française ; à défaut, la voix par défaut du système.
      return voix.filter(function (v) { return v.lang.indexOf(lang.slice(0, 2)) === 0; })[0] || null;
    }

    function majBouton(actif) {
      enCours = actif;
      bouton.classList.toggle("is-playing", actif);
      bouton.querySelector(".tts-label").textContent = actif ? "Arrêter" : "Écouter";
      bouton.setAttribute("aria-pressed", actif ? "true" : "false");
    }

    bouton.addEventListener("click", function () {
      if (enCours) {
        synth.cancel();
        majBouton(false);
        return;
      }

      var texte = texteArticle();
      if (!texte) return;

      synth.cancel();
      // Les navigateurs coupent les énoncés très longs : on découpe par phrases.
      var phrases = texte.match(/[^.!?]+[.!?]*/g) || [texte];
      var blocs = [];
      var courant = "";
      phrases.forEach(function (p) {
        if ((courant + p).length > 200) { blocs.push(courant); courant = p; }
        else { courant += p; }
      });
      if (courant) blocs.push(courant);

      var voix = choisirVoix();
      blocs.forEach(function (bloc, i) {
        var u = new SpeechSynthesisUtterance(bloc);
        u.lang = lang;
        u.rate = 1;
        if (voix) u.voice = voix;
        if (i === blocs.length - 1) {
          u.onend = function () { majBouton(false); };
        }
        u.onerror = function () { majBouton(false); };
        synth.speak(u);
      });

      majBouton(true);
    });

    // Certains navigateurs chargent les voix de façon asynchrone.
    if (synth.onvoiceschanged !== undefined) {
      synth.onvoiceschanged = choisirVoix;
    }
    // Sécurité : couper la lecture si l'utilisateur quitte la page.
    window.addEventListener("beforeunload", function () { synth.cancel(); });
  }

  // ---------------------------------------------------------- partage
  function initPartage() {
    var boutons = document.querySelectorAll("[data-partage]");
    Array.prototype.forEach.call(boutons, function (b) {
      b.addEventListener("click", function () {
        var type = b.dataset.partage;
        var url = b.dataset.url || window.location.href;
        var titre = b.dataset.titre || document.title;

        if (type === "copier") {
          navigator.clipboard.writeText(url).then(function () {
            var initial = b.querySelector(".partage-label").textContent;
            b.querySelector(".partage-label").textContent = "Lien copié";
            setTimeout(function () {
              b.querySelector(".partage-label").textContent = initial;
            }, 2000);
          });
          return;
        }

        if (type === "natif" && navigator.share) {
          navigator.share({ title: titre, url: url });
          return;
        }

        var cibles = {
          whatsapp: "https://wa.me/?text=" + encodeURIComponent(titre + " " + url),
          x: "https://twitter.com/intent/tweet?text=" + encodeURIComponent(titre) +
             "&url=" + encodeURIComponent(url),
          facebook: "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url)
        };
        if (cibles[type]) window.open(cibles[type], "_blank", "noopener,width=600,height=500");
      });
    });
  }

  // ------------------------------------------- réponses aux commentaires
  function initReponses() {
    var boutons = document.querySelectorAll("[data-repondre]");
    Array.prototype.forEach.call(boutons, function (b) {
      b.addEventListener("click", function () {
        var form = document.getElementById("reply-" + b.dataset.repondre);
        if (!form) return;
        form.hidden = !form.hidden;
        if (!form.hidden) form.querySelector("textarea").focus();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initNav();
    initTicker();
    initWeather();
    initTTS();
    initPartage();
    initReponses();
  });
})();
