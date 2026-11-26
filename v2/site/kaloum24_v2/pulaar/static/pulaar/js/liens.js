/* Homonymes : sur un lien « … », une petite liste propose les autres entrées de même forme.
   Au survol et au clavier (le lien principal reste cliquable : aucun JavaScript n'est nécessaire pour lire). */
(function () {
  var ouverte = null;
  function fermer() { if (ouverte) { ouverte.remove(); ouverte = null; } }
  function ouvrir(a) {
    var alts;
    try { alts = JSON.parse(a.getAttribute("data-alternatives") || "[]"); } catch (e) { return; }
    if (!alts.length) return;
    fermer();
    var boite = document.createElement("div");
    boite.className = "tc-homonymes";
    boite.setAttribute("role", "group");
    boite.setAttribute("aria-label", "Autres entrées de même forme");
    var t = document.createElement("strong"); t.textContent = "Autres entrées"; boite.appendChild(t);
    alts.forEach(function (x) {
      var l = document.createElement("a"); l.href = x.url; l.textContent = x.lemma; l.setAttribute("lang", "ff");
      boite.appendChild(l);
    });
    a.insertAdjacentElement("afterend", boite);  // juste après dans le DOM : accessible au clavier (Tab)
    boite.style.left = a.offsetLeft + "px"; boite.style.top = (a.offsetTop + a.offsetHeight + 2) + "px";
    ouverte = boite;
    boite.addEventListener("mouseleave", fermer);
    boite.addEventListener("focusout", function (e) { if (!boite.contains(e.relatedTarget) && e.relatedTarget !== a) fermer(); });
  }
  document.addEventListener("mouseover", function (e) { var a = e.target.closest && e.target.closest("a.tc-lien[data-alternatives]"); if (a) ouvrir(a); });
  document.addEventListener("focusin", function (e) { var a = e.target.closest && e.target.closest("a.tc-lien[data-alternatives]"); if (a) ouvrir(a); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") fermer(); });
  document.addEventListener("click", function (e) { if (ouverte && !e.target.closest(".tc-homonymes, a.tc-lien")) fermer(); });
})();
