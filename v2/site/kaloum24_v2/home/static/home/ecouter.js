/* Écouter : lecture du texte de l'article par la synthèse vocale du navigateur (Web Speech). */
(function () {
  var racine = document.querySelector("[data-ecouter]");
  if (!racine || !("speechSynthesis" in window) || !window.SpeechSynthesisUtterance) return;
  var synth = window.speechSynthesis;
  var barre = racine.querySelector(".k24-ecouter__barre");
  var lire = racine.querySelector("[data-ecouter-lire]");
  var stop = racine.querySelector("[data-ecouter-stop]");
  var vitesse = racine.querySelector("[data-ecouter-vitesse]");
  var note = racine.querySelector("[data-ecouter-note]");
  if (!barre || !lire) return;
  barre.hidden = false;
  if (note) note.hidden = false;

  var morceaux = [], index = 0, actif = false, pause = false;

  function texte() {
    var t = [];
    var h1 = document.querySelector("h1");
    if (h1) t.push(h1.textContent.trim() + ".");
    var intro = document.querySelector(".rich-text");
    if (intro) t.push(intro.textContent.trim());
    var corps = document.getElementById("art-corps");
    if (corps) {
      corps.querySelectorAll("h2, h3, p, blockquote, li").forEach(function (n) {
        var x = n.textContent.replace(/\s+/g, " ").trim();
        if (x) t.push(x);
      });
    }
    return t.join("\n");
  }

  function decouper(s) {
    // Phrases de 200 caractères au plus : Chrome coupe les lectures trop longues.
    var phrases = s.replace(/\s+/g, " ").match(/[^.!?…]+[.!?…]*\s*/g) || [s];
    var res = [], cur = "";
    phrases.forEach(function (p) {
      if ((cur + p).length > 200 && cur) { res.push(cur); cur = p; } else { cur += p; }
    });
    if (cur.trim()) res.push(cur);
    return res;
  }

  function voixFr() {
    var v = synth.getVoices().filter(function (x) { return /^fr/i.test(x.lang); });
    return v[0] || null;
  }

  function dire() {
    if (!actif || index >= morceaux.length) { fin(); return; }
    var u = new SpeechSynthesisUtterance(morceaux[index]);
    u.lang = "fr-FR";
    var v = voixFr();
    if (v) u.voice = v;
    u.rate = parseFloat(vitesse.value) || 1;
    u.onend = function () { index += 1; dire(); };
    u.onerror = function () { fin(); };
    synth.speak(u);
  }

  function fin() {
    actif = false; pause = false; index = 0;
    synth.cancel();
    lire.textContent = "Écouter l'article";
    lire.setAttribute("aria-pressed", "false");
    stop.hidden = true;
  }

  lire.addEventListener("click", function () {
    if (!actif) {
      morceaux = decouper(texte());
      index = 0; actif = true; pause = false;
      lire.textContent = "Mettre en pause";
      lire.setAttribute("aria-pressed", "true");
      stop.hidden = false;
      dire();
    } else if (!pause) {
      synth.pause(); pause = true;
      lire.textContent = "Reprendre";
    } else {
      synth.resume(); pause = false;
      lire.textContent = "Mettre en pause";
    }
  });
  stop.addEventListener("click", fin);
  vitesse.addEventListener("change", function () {
    if (actif && !pause) { synth.cancel(); dire(); }
  });
  window.addEventListener("pagehide", function () { synth.cancel(); });
})();
