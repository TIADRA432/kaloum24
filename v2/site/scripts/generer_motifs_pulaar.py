"""Génère les motifs et pictogrammes décoratifs de /pulaar/ (SVG originaux, dessinés pour Kaloum24).

Inspirations (formes seulement, aucun sens inventé) : anneaux concentriques à frise en zigzag,
vannerie en chevrons, bandes tissées en losanges (leppi), pictogrammes de vache, calebasse, gourde.
Palette Tiadra Consortium. Angles de 30/60° pour les éléments structurels.
Usage : python scripts/generer_motifs_pulaar.py
"""
import math
import pathlib

SORTIE = pathlib.Path(__file__).resolve().parent.parent / "kaloum24_v2/pulaar/static/pulaar/img/decor"
OR, BORDEAUX, SABLE, BRONZE, MAUVE, NOIR, IVOIRE = "#D19F5E", "#5D2E38", "#DCB786", "#C48738", "#7F3F4D", "#3B1D23", "#F7F3EF"


def ecrire(nom, contenu):
    (SORTIE / nom).write_text(contenu.strip() + "\n", encoding="utf-8")


def pts(liste):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in liste)


# ---------------------------------------------------------------- bande leppi (losanges 60°) ---
def bande_leppi(vertical=False):
    L, H = 120, 40  # tuile : longueur, hauteur
    h = 40
    e = []
    # fond bordeaux
    e.append(f'<rect width="{L}" height="{H}" fill="{BORDEAUX}"/>')
    # filets haut et bas
    for y in (3, H - 5):
        e.append(f'<rect y="{y}" width="{L}" height="2" fill="{OR}"/>')
    # grand losange (angles 60/120) : demi-largeur a, demi-hauteur b avec b = a*tan(60°)
    cx, cy = L / 2, H / 2
    b = 15
    a = b / math.tan(math.radians(60))
    a *= 1.9  # losange un peu plus large, lisible
    e.append(f'<polygon points="{pts([(cx, cy-b), (cx+a, cy), (cx, cy+b), (cx-a, cy)])}" fill="{OR}"/>')
    e.append(f'<polygon points="{pts([(cx, cy-b+5), (cx+a-5, cy), (cx, cy+b-5), (cx-a+5, cy)])}" fill="{BORDEAUX}"/>')
    e.append(f'<polygon points="{pts([(cx, cy-4), (cx+4, cy), (cx, cy+4), (cx-4, cy)])}" fill="{SABLE}"/>')
    # triangles dentelés de part et d'autre (entre les losanges)
    for x0 in (0, L):
        for k in range(3):
            y = 9 + k * 8
            e.append(f'<polygon points="{pts([(x0-5, y), (x0, y+4), (x0-5, y+8)])}" fill="{SABLE}" opacity=".9"/>')
            e.append(f'<polygon points="{pts([(x0+5, y), (x0, y+4), (x0+5, y+8)])}" fill="{SABLE}" opacity=".9"/>')
    # petits points entre losanges
    for x in (cx - 30, cx + 30):
        e.append(f'<polygon points="{pts([(x, cy-5), (x+3.5, cy), (x, cy+5), (x-3.5, cy)])}" fill="{BRONZE}"/>')
    corps = "".join(e)
    if vertical:  # même motif tourné de 90° (tuile H x L)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{H}" height="{L}" viewBox="0 0 {H} {L}">'
                f'<g transform="translate({H},0) rotate(90)">{corps}</g></svg>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" viewBox="0 0 {L} {H}">{corps}</svg>'


# ---------------------------------------------------------------- médaillon : anneaux + zigzag ---
def medaillon(couleur=OR):
    S = 400
    c = S / 2
    e = []

    def cercle(r, w=2, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        e.append(f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{couleur}" stroke-width="{w}"{d} opacity="{op}"/>')

    def zigzag(r1, r2, n, w=2):
        p = []
        for i in range(2 * n):
            a = math.pi * i / n
            r = r2 if i % 2 == 0 else r1
            p.append((c + r * math.cos(a), c + r * math.sin(a)))
        e.append(f'<polygon points="{pts(p)}" fill="none" stroke="{couleur}" stroke-width="{w}" stroke-linejoin="miter"/>')

    cercle(196, 3)
    cercle(188, 1.5)
    zigzag(168, 186, 48)
    cercle(164, 2)
    cercle(156, 1.5)
    # clé grecque simplifiée : petits carrés sur un anneau
    for i in range(36):
        a = 2 * math.pi * i / 36
        x, y = c + 142 * math.cos(a), c + 142 * math.sin(a)
        e.append(f'<rect x="{x-4:.1f}" y="{y-4:.1f}" width="8" height="8" fill="none" stroke="{couleur}" stroke-width="1.6" '
                 f'transform="rotate({math.degrees(a):.1f} {x:.1f} {y:.1f})"/>')
    cercle(128, 1.5)
    cercle(120, 2)
    zigzag(96, 116, 30, 1.8)
    cercle(92, 1.5)
    cercle(80, 1.5, "2 5")
    zigzag(52, 76, 12, 2)
    cercle(46, 2)
    # étoile centrale à 12 branches
    p = []
    for i in range(24):
        a = math.pi * i / 12
        r = 40 if i % 2 == 0 else 24
        p.append((c + r * math.cos(a), c + r * math.sin(a)))
    e.append(f'<polygon points="{pts(p)}" fill="{couleur}" opacity=".9"/>')
    cercle(12, 2)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">{"".join(e)}</svg>'


# ---------------------------------------------------------------- vannerie (chevrons) ---
def vannerie(couleur=OR, fond=None):
    L, H = 48, 28
    f = f'<rect width="{L}" height="{H}" fill="{fond}"/>' if fond else ""
    lignes = "".join(
        f'<polyline points="0,{y+8} {L/2},{y} {L},{y+8}" fill="none" stroke="{couleur}" stroke-width="2" stroke-linejoin="miter"/>'
        for y in (4, 14))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" viewBox="0 0 {L} {H}">{f}{lignes}</svg>'


# ---------------------------------------------------------------- pictogrammes ---
def vache(couleur=OR, accent=BORDEAUX):
    """Zébu de profil, silhouette à facettes (angles nets), cornes en lyre, bosse, queue à touffe."""
    corps = [(16, 38), (44, 34), (62, 32), (76, 18), (92, 30), (108, 32), (124, 30), (134, 36), (148, 54),
             (150, 62), (140, 66), (130, 60), (118, 62), (110, 68), (100, 66), (70, 64), (52, 64), (32, 64), (20, 54)]
    pattes = [(98, 62, 110, 62, 108, 95, 101, 95), (84, 62, 96, 62, 95, 95, 88, 95),
              (40, 62, 54, 62, 52, 95, 45, 95), (26, 60, 40, 62, 38, 95, 31, 95)]
    e = [f'<polygon points="{pts(corps)}" fill="{couleur}"/>']
    for p in pattes:
        e.append(f'<polygon points="{pts([(p[0], p[1]), (p[2], p[3]), (p[4], p[5]), (p[6], p[7])])}" fill="{couleur}"/>')
        e.append(f'<rect x="{min(p[4], p[6])-1:.1f}" y="93" width="{abs(p[4]-p[6])+2:.1f}" height="5" fill="{couleur}"/>')
    # queue
    e.append(f'<polyline points="17,40 8,56 9,72" fill="none" stroke="{couleur}" stroke-width="3" stroke-linejoin="miter"/>')
    e.append(f'<polygon points="{pts([(9, 70), (4, 80), (9, 85), (14, 80)])}" fill="{couleur}"/>')
    # cornes en lyre (traits épais, extrémités effilées par la forme)
    e.append(f'<path d="M124,30 C108,22 110,6 124,0" fill="none" stroke="{couleur}" stroke-width="5" stroke-linecap="butt"/>')
    e.append(f'<path d="M132,32 C148,24 150,8 138,0" fill="none" stroke="{couleur}" stroke-width="5" stroke-linecap="butt"/>')
    # oreille et œil
    e.append(f'<polygon points="{pts([(124, 38), (112, 40), (120, 47)])}" fill="{couleur}"/>')
    e.append(f'<circle cx="136" cy="44" r="2.2" fill="{accent}"/>')
    # accent hexagonal (clin d'œil à la marque) sur le flanc
    cx, cy, r = 66, 48, 9
    e.append(f'<polygon points="{pts([(cx + r*math.cos(math.radians(60*i)), cy + r*math.sin(math.radians(60*i))) for i in range(6)])}" fill="{accent}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -6 160 106" width="160" height="106">{"".join(e)}</svg>'


def calebasse(couleur=OR, accent=BORDEAUX):
    """Calebasse-bol vue de côté, frise en zigzag."""
    e = [f'<path d="M6,26 H94 C94,52 74,64 50,64 C26,64 6,52 6,26 Z" fill="{couleur}"/>',
         f'<rect x="3" y="22" width="94" height="6" fill="{couleur}"/>']
    zz = [(14 + i * 8.6, 36 if i % 2 == 0 else 46) for i in range(10)]
    e.append(f'<polyline points="{pts(zz)}" fill="none" stroke="{accent}" stroke-width="2.6" stroke-linejoin="miter"/>')
    e.append(f'<polyline points="{pts([(x, y+8) for x, y in zz[1:-1]])}" fill="none" stroke="{accent}" stroke-width="2" stroke-linejoin="miter" opacity=".8"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 70" width="100" height="70">{"".join(e)}</svg>'


def gourde(couleur=OR, accent=BORDEAUX):
    """Calebasse-bouteille (corps rond, long col), bouchon et losanges."""
    e = [f'<path d="M30,4 H40 V14 C40,26 62,34 62,60 C62,80 50,94 35,94 C20,94 8,80 8,60 C8,34 30,26 30,14 Z" fill="{couleur}"/>',
         f'<rect x="27" y="0" width="16" height="7" fill="{accent}"/>']
    for k, (cx, cy) in enumerate(((35, 52), (35, 68), (35, 84))):
        r = 6 if k == 1 else 5
        e.append(f'<polygon points="{pts([(cx, cy-r), (cx+r*1.2, cy), (cx, cy+r), (cx-r*1.2, cy)])}" fill="{accent}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 70 100" width="70" height="100">{"".join(e)}</svg>'


if __name__ == "__main__":
    SORTIE.mkdir(parents=True, exist_ok=True)
    ecrire("leppi-h.svg", bande_leppi(False))
    ecrire("leppi-v.svg", bande_leppi(True))
    ecrire("anneaux-or.svg", medaillon(OR))
    ecrire("anneaux-bordeaux.svg", medaillon(BORDEAUX))
    ecrire("vannerie-or.svg", vannerie(OR))
    ecrire("vannerie-bordeaux.svg", vannerie(BORDEAUX))
    ecrire("vache-or.svg", vache(OR, BORDEAUX))
    ecrire("vache-bordeaux.svg", vache(BORDEAUX, OR))
    ecrire("calebasse-or.svg", calebasse(OR, BORDEAUX))
    ecrire("calebasse-bordeaux.svg", calebasse(BORDEAUX, OR))
    ecrire("gourde-or.svg", gourde(OR, BORDEAUX))
    ecrire("gourde-bordeaux.svg", gourde(BORDEAUX, OR))
    print("motifs écrits dans", SORTIE)
