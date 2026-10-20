"""French for the SubD panel (see subdiv/lang.py). Keys: the English text
as written in the code, placeholders included."""

FR = {
    # -- tools ---------------------------------------------------------------------
    "Create": "Créer",
    "New box cage (size in {unit}), with its lower corner on the origin.":
        "Nouvelle cage en boîte (taille en {unit}), son coin inférieur sur l'origine.",
    "Size": "Taille",
    "Edit cage": "Modifier",
    "Move the selected point, edge or face along an axis.":
        "Déplace le point, l'arête ou la face sélectionnée le long d'un axe.",
    "Move by": "Déplacer de",
    "Crease": "Pli",
    "Keep the selected edge (or the edges of a face) sharp for N levels; 0 clears. With nothing "
    "selected it applies to every edge; with several selected (Shift+click, or click an edge "
    "again for its contour) to all their edges. The value starts at the smoothing level, which "
    "keeps the edge crisp; a smaller one leaves a small radius.":
        "Garde l'arête sélectionnée (ou les arêtes d'une face) vive sur N niveaux ; 0 l'efface. "
        "Sans sélection, s'applique à toutes les arêtes ; avec plusieurs (Maj+clic, ou un "
        "nouveau clic sur une arête pour son contour), à toutes leurs arêtes. La valeur part du "
        "niveau de lissage, qui garde l'arête nette ; une plus petite laisse un petit rayon.",
    "Sharpness": "Netteté",
    "Grow F": "Pousser F",
    "Push the selected face out along its normal.": "Pousse la face sélectionnée le long de sa normale.",
    "Height": "Hauteur",
    "Grow E": "Pousser A",
    "Extend the selected open edge into a new strip (Auto). With a whole contour selected "
    "(click an edge again for its contour) it is extruded outwards; with X, Y or Z chosen the "
    "whole contour of the edge goes along that axis (negative distance goes the other way).":
        "Prolonge l'arête ouverte sélectionnée par une nouvelle bande (Auto). Avec tout un "
        "contour sélectionné (nouveau clic sur une arête pour son contour), il est extrudé vers "
        "l'extérieur ; avec X, Y ou Z, tout le contour de l'arête part le long de cet axe (une "
        "distance négative va dans l'autre sens).",
    "Distance": "Distance",
    "Stretch": "Étirer",
    "Scale the selection along an axis. A face stretched along its own normal stretches the "
    "whole piece that way, the far side staying put.":
        "Met la sélection à l'échelle le long d'un axe. Une face étirée le long de sa normale "
        "étire toute la pièce dans ce sens, le côté opposé restant en place.",
    "Factor": "Facteur",
    "Offset F": "Décaler F",
    "Add a smaller copy of the selected face inside it.":
        "Ajoute une copie plus petite de la face sélectionnée, à l'intérieur.",
    "Inset (0-0.95)": "Retrait (0-0,95)",
    "Offset E": "Décaler A",
    "Run a new loop inside the open border the selected edge belongs to.":
        "Trace une nouvelle boucle à l'intérieur du bord ouvert de l'arête sélectionnée.",
    "Squeeze": "Pincer",
    "Pinch the selected face's ring (or the open contour of the selected edge, or the contour "
    "selected with repeated clicks) towards its axis.":
        "Resserre l'anneau de la face sélectionnée (ou le contour ouvert de l'arête "
        "sélectionnée, ou le contour choisi par clics répétés) vers son axe.",
    "Divide": "Diviser",
    "Cut the selected face in four (each cut runs on round the piece as a loop, or this face "
    "only), or select an edge to cut across it (the whole loop, or only the faces touching "
    "that edge).":
        "Coupe la face sélectionnée en quatre (chaque coupe fait le tour de la pièce en boucle, "
        "ou cette face seule), ou sélectionner une arête pour couper en travers (toute la "
        "boucle, ou seulement les faces qui touchent cette arête).",
    "Delete F": "Supprimer F",
    "Remove the selected face, leaving an opening to Close or Bridge.":
        "Retire la face sélectionnée et laisse une ouverture à Fermer ou à Relier.",
    "Close": "Fermer",
    "Fill the open border the selected edge belongs to.": "Bouche le bord ouvert de l'arête sélectionnée.",
    "Bridge": "Relier",
    "Click a face (or an edge of an opening), then click the other one: the bridge is made at "
    "the second click, the faces removed and joined by a ring of quads. (Shift+click then "
    "Apply, or Apply after each, also work.) Twist turns the ring by that many points; set it "
    "before the second click.":
        "Cliquer une face (ou une arête d'une ouverture), puis l'autre : le pont se fait au "
        "second clic, les faces sont retirées et reliées par un anneau de quadrangles. (Maj+clic "
        "puis Appliquer, ou Appliquer après chaque clic, marchent aussi.) Torsion tourne "
        "l'anneau d'autant de points ; à régler avant le second clic.",
    "Twist": "Torsion",
    "Shell": "Coque",
    "Give the whole piece a wall: choose Inside, Outside or Centred, then Apply. An open piece "
    "becomes a thick sheet, a closed one a hollow body.":
        "Donne une paroi à toute la pièce : choisir Intérieur, Extérieur ou Centré, puis "
        "Appliquer. Une pièce ouverte devient une plaque épaisse, une pièce fermée un corps creux.",
    "Thickness": "Épaisseur",
    "metres": "mètres", "centimetres": "centimètres", "millimetres": "millimètres",
    "inches": "pouces", "feet": "pieds",
    "outside": "extérieur", "inside": "intérieur", "center": "centré",
    # -- panel ---------------------------------------------------------------------
    "SubD group": "Groupe SubD",
    "Auto": "Auto",
    "Direction for Edit, Stretch and Squeeze (Auto: the face's normal / ring)":
        "Direction pour Modifier, Étirer et Pincer (Auto : la normale de la face / l'anneau)",
    "Outside": "Extérieur", "Inside": "Intérieur", "Centred": "Centré",
    "Where the wall grows from the current surface": "De quel côté de la surface la paroi pousse",
    "Whole loop": "Toute la boucle", "Only this face": "Cette face seule",
    "Divide a face or an edge. Whole loop: the cut runs on round the piece through the quads "
    "beyond (clean quads). Only this face: just the face (or the faces touching the edge) is "
    "cut; the neighbours get an extra point.":
        "Diviser une face ou une arête. Toute la boucle : la coupe fait le tour de la pièce à "
        "travers les quadrangles suivants (quadrangles propres). Cette face seule : seule la "
        "face (ou les faces qui touchent l'arête) est coupée ; les voisines reçoivent un point "
        "de plus.",
    "Apply": "Appliquer",
    "Symmetry": "Symétrie",
    "Repeat every edit on the other side of the plane.": "Répète chaque modification de l'autre côté du plan.",
    "Axis the plane is perpendicular to.": "Axe perpendiculaire au plan.",
    "Centre": "Centrer",
    "Put the plane through the middle of the piece.": "Place le plan au milieu de la pièce.",
    "From face": "Depuis la face",
    "Use the plane of the selected face.": "Prend le plan de la face sélectionnée.",
    "Join with": "Joindre à",
    "Another SubD group to merge into this one, so Bridge can link their openings.":
        "Un autre groupe SubD à fusionner avec celui-ci, pour que Relier puisse joindre leurs ouvertures.",
    "Join": "Joindre",
    "Split": "Séparer",
    "Undo a Join: every separate piece of this group becomes its own SubD group again.":
        "Défait une jonction : chaque morceau séparé de ce groupe redevient un groupe SubD.",
    "Convert group": "Convertir le groupe",
    "Groups not made by this plugin. Their faces become the cage, so use a coarse one (under "
    "7000 faces; editing gets slow above a few hundred).":
        "Groupes qui ne viennent pas de cette extension. Leurs faces deviennent la cage : en "
        "choisir un grossier (moins de 7000 faces ; l'édition ralentit au-delà de quelques centaines).",
    "Crease edges over": "Arêtes vives au-delà de",
    "Edges where two faces meet at more than this angle stay sharp. 0 = no automatic creases "
    "(everything rounds).":
        "Les arêtes où deux faces font plus que cet angle restent vives. 0 = pas de pli "
        "automatique (tout s'arrondit).",
    "Convert to SubD": "Convertir en SubD",
    "Replace the chosen group by a SubD group built on its faces. Ctrl+Z brings the original back.":
        "Remplace le groupe choisi par un groupe SubD construit sur ses faces. Ctrl+Z rend l'original.",
    "Create with sharp edges (angle above)": "Créer à arêtes vives (angle ci-dessus)",
    "Create then gives a crisp box instead of a rounded block: the edges of the new box stay "
    "sharp when the angle above is below 90 degrees (30 is fine). Stretch, Grow and Shell then "
    "work on a rectilinear piece.":
        "Créer donne alors une boîte nette au lieu d'un bloc arrondi : les arêtes de la nouvelle "
        "boîte restent vives quand l'angle ci-dessus est sous 90 degrés (30 convient). Étirer, "
        "Pousser et Coque travaillent alors sur une pièce rectiligne.",
    "Smoothing": "Lissage",
    "Subdivision steps: 0 is the cage itself.": "Pas de subdivision : 0 est la cage elle-même.",
    "Smoothest level that keeps the surface under about 25 000 triangles; uncheck to choose it yourself.":
        "Le niveau le plus lisse qui garde la surface sous environ 25 000 triangles ; décocher "
        "pour le choisir soi-même.",
    "Cage lines": "Lignes de la cage", "All edges": "Toutes les arêtes", "No lines": "Aucune ligne",
    "Update look": "Mettre à jour l'aspect",
    "Rebuild the surface with this smoothing and these lines.":
        "Reconstruit la surface avec ce lissage et ces lignes.",
    "Flip faces": "Retourner les faces",
    "Blue faces are seen from behind. Flip turns the whole piece inside out so the front and "
    "the back swap.":
        "Les faces bleues sont vues de dos. Retourner inverse toute la pièce : l'endroit et "
        "l'envers s'échangent.",
    "Finish detail": "Finesse de la finition",
    "Automatic (light)": "Automatique (léger)",
    "Same as the view": "Comme la vue",
    "Light (1)": "Léger (1)", "Medium (2)": "Moyen (2)", "Fine (3)": "Fin (3)",
    "How finely the curved parts are cut when the piece is finished. Automatic keeps the result "
    "under about %d faces so ordinary tools stay fast (the smoothest level that fits). Each "
    "step up multiplies the triangles by four. Flat faces are always single polygons, whatever "
    "you choose.":
        "Finesse du découpage des parties courbes à la finition. Automatique garde le résultat "
        "sous environ %d faces pour que les outils ordinaires restent rapides (le niveau le plus "
        "lisse qui tient). Chaque niveau de plus multiplie les triangles par quatre. Les faces "
        "planes restent toujours des polygones uniques, quel que soit le choix.",
    "Finish": "Terminer",
    "Finish (no longer SubD): keep the smooth surface as an ordinary group and drop the cage. "
    "If the cage is closed and sound, the result is a Solid Group (usable with Solid Tools) and "
    "its volume is reported; if it is still open, you get the surface and the reason. Undo "
    "brings the SubD group back.":
        "Terminer (ce n'est plus du SubD) : garde la surface lisse comme un groupe ordinaire et "
        "abandonne la cage. Si la cage est fermée et saine, le résultat est un Groupe solide "
        "(utilisable avec les Outils de solides) et son volume est donné ; si elle est encore "
        "ouverte, on obtient la surface et la raison. Annuler rend le groupe SubD.",
    "Handles": "Poignées",
    "Move + Rotate": "Déplacer + Tourner", "Move only": "Déplacer seulement",
    "Rotate only (protractor)": "Tourner seulement (rapporteur)",
    "Move: drag a coloured tip to slide the selection along that axis.\nRotate: drag a coloured "
    "ring to turn the selection around that axis (hold Ctrl to snap to 15 degrees).\nBoth are "
    "shown by default; pick one to keep the view clear.":
        "Déplacer : tirer une pointe colorée pour faire glisser la sélection le long de cet axe.\n"
        "Tourner : tirer un anneau coloré pour tourner la sélection autour de cet axe (Ctrl : "
        "pas de 15 degrés).\nLes deux sont affichés par défaut ; en choisir un pour dégager la vue.",
    "Show cage": "Afficher la cage",
    "SubD panel": "Panneau SubD",
    "Show the subdivision-modelling panel.": "Affiche le panneau de modélisation par subdivision.",
    # -- messages ------------------------------------------------------------------
    "  (waiting for the second opening)": "  (en attente de la seconde ouverture)",
    "Could not apply: {err}": "Impossible d'appliquer : {err}",
    "Several items are selected: use Edit cage or Crease on them, or click one item for this tool":
        "Plusieurs éléments sont sélectionnés : utiliser Modifier ou Pli, ou cliquer un seul "
        "élément pour cet outil",
    "Choose X, Y or Z to move several items together": "Choisir X, Y ou Z pour déplacer plusieurs éléments ensemble",
    "Sharp-edged SubD box created — click a point, edge or face of the cage":
        "Boîte SubD à arêtes vives créée — cliquer un point, une arête ou une face de la cage",
    "SubD box created — click a point, edge or face of the cage":
        "Boîte SubD créée — cliquer un point, une arête ou une face de la cage",
    "Create or choose a SubD group first": "Créer ou choisir d'abord un groupe SubD",
    "Symmetry on": "Symétrie activée", "Symmetry off": "Symétrie désactivée",
    "Plane set through the centre": "Plan placé au centre",
    "Plane set from the face": "Plan pris sur la face",
    "Select a face first: its plane becomes the symmetry plane":
        "Sélectionner d'abord une face : son plan devient le plan de symétrie",
    "Choose a second SubD group under \"Join with\"": "Choisir un second groupe SubD dans « Joindre à »",
    "Could not join: {err}": "Impossible de joindre : {err}",
    "Joined. Choose Bridge, then click a face on each piece (Apply after each)":
        "Joint. Choisir Relier, puis cliquer une face sur chaque morceau (Appliquer après chacune)",
    "No SubD group to split": "Aucun groupe SubD à séparer",
    "Nothing to split: this is one connected piece. After a Bridge, delete the bridge's faces "
    "(Delete F) to separate the pieces first":
        "Rien à séparer : c'est une seule pièce. Après un Relier, supprimer d'abord les faces "
        "du pont (Supprimer F) pour séparer les morceaux",
    "Could not split: {err}": "Impossible de séparer : {err}",
    "Split into {n} separate SubD groups (Ctrl+Z to join them back)":
        "Séparé en {n} groupes SubD (Ctrl+Z pour les rejoindre)",
    "No group to convert: make or import one first": "Aucun groupe à convertir : en créer ou en importer un d'abord",
    " ({n} faces lost their holes)": " ({n} faces ont perdu leurs trous)",
    "Converted: {n} faces, {k} sharp edges": "Converti : {n} faces, {k} arêtes vives",
    "No SubD group to update": "Aucun groupe SubD à mettre à jour",
    "Look updated": "Aspect mis à jour",
    "No SubD group to flip": "Aucun groupe SubD à retourner",
    "Faces flipped": "Faces retournées",
    "No SubD group to finish": "Aucun groupe SubD à terminer",
    "Could not finish: {err}": "Impossible de terminer : {err}",
    "Finished, solid group ({n} faces): volume {v} {u}³": "Terminé, groupe solide ({n} faces) : volume {v} {u}³",
    " — not counted as a solid by Solid Tools; check for coincident points":
        " — non compté comme solide par les Outils de solides ; vérifier les points confondus",
    "Finished, surface only ({n} faces), not a solid: {why}":
        "Terminé, surface seule ({n} faces), pas un solide : {why}",
    " (Ctrl+Z to edit the cage again)": " (Ctrl+Z pour reprendre la cage)",
    "Rotated {a}° around {axis}": "Tourné de {a}° autour de {axis}",
    "Bridge: now click the other face (or an edge of the other opening)":
        "Relier : cliquer maintenant l'autre face (ou une arête de l'autre ouverture)",
    "Bridge: select two faces (click one, Shift+click the other)":
        "Relier : sélectionner deux faces (cliquer l'une, Maj+clic sur l'autre)",
    "Create a SubD box first, or choose a SubD group": "Créer d'abord une boîte SubD, ou choisir un groupe SubD",
    "{note} ({n} edges) - click again for the next contour":
        "{note} ({n} arêtes) - cliquer de nouveau pour le contour suivant",
    "{note} ({n} edge) - click again for the next contour":
        "{note} ({n} arête) - cliquer de nouveau pour le contour suivant",
    "SubD drag failed": "Échec du glisser SubD",
    "Loop": "Boucle", "Face outline": "Contour de la face",
    # -- tool results ------------------------------------------------------------------
    "{n} items selected (Shift+click adds or removes one)":
        "{n} éléments sélectionnés (Maj+clic en ajoute ou en retire un)",
    "Nothing selected": "Rien de sélectionné",
    "Point {i}": "Point {i}", "Edge {a}-{b}": "Arête {a}-{b}", "Face {i}": "Face {i}",
    "Select {what} first": "Sélectionner d'abord {what}",
    "an open edge": "une arête ouverte",
    "a point, edge or face": "un point, une arête ou une face",
    "an edge or a face": "une arête ou une face",
    "a face": "une face",
    "a face, or an edge of an open contour": "une face, ou une arête d'un contour ouvert",
    "a face or an edge": "une face ou une arête",
    "That edge is not on an open border": "Cette arête n'est pas sur un bord ouvert",
    "All creases cleared": "Tous les plis effacés",
    "Every edge creased {value}": "Toutes les arêtes pliées {value}",
    "Crease cleared": "Pli effacé",
    "Crease {value}": "Pli {value}",
    "Select edges or faces first": "Sélectionner d'abord des arêtes ou des faces",
    "{n} edges rounded off": "{n} arêtes arrondies",
    "{n} edge rounded off": "{n} arête arrondie",
    "{n} edges creased {value}": "{n} arêtes pliées {value}",
    "{n} edge creased {value}": "{n} arête pliée {value}",
    "Face grown": "Face poussée",
    "along {v0}": "le long de {v0}",
    "Cannot tell which way is outward for that contour: choose X, Y or Z":
        "Impossible de savoir où est l'extérieur pour ce contour : choisir X, Y ou Z",
    "Open contour of {v0} edges extruded {where}": "Contour ouvert de {v0} arêtes extrudé {where}",
    "Cannot tell which way is outward for that edge": "Impossible de savoir où est l'extérieur pour cette arête",
    "Edge grown": "Arête poussée",
    "Grow E: select edges of an open contour": "Pousser A : sélectionner des arêtes d'un contour ouvert",
    "Select the whole open contour (click an edge again for its contour), or a single edge":
        "Sélectionner tout le contour ouvert (nouveau clic sur une arête pour son contour), "
        "ou une seule arête",
    "Whole piece stretched (the selection alone has no length along that direction)":
        "Toute la pièce étirée (la sélection seule n'a pas de longueur dans cette direction)",
    "Face offset": "Face décalée",
    "Border offset": "Bord décalé",
    "Open contour squeezed": "Contour ouvert pincé",
    "Select a face or the edges of a contour first": "Sélectionner d'abord une face ou les arêtes d'un contour",
    "Select at least three points to squeeze": "Sélectionner au moins trois points à pincer",
    "Loop cut": "Boucle coupée",
    "Cut across the face": "Coupe en travers de la face",
    "Face divided": "Face divisée",
    "A cage needs at least one face": "Une cage a besoin d'au moins une face",
    "Face deleted — Close it again or Bridge it to another opening":
        "Face supprimée — la Fermer de nouveau ou la Relier à une autre ouverture",
    "Hole closed": "Trou fermé",
    "Now select the other {what} (a face or an edge of an opening) and press Apply again":
        "Sélectionner maintenant l'autre {what} (une face ou une arête d'une ouverture) et "
        "Appliquer de nouveau",
    "Pick a different face": "Choisir une autre face",
    "Pick an edge of a different opening": "Choisir une arête d'une autre ouverture",
    "Both ends need the same number of sides ({v0} and {v1})":
        "Les deux bouts doivent avoir le même nombre de côtés ({v0} et {v1})",
    "The two ends touch each other: pick faces that do not share a point":
        "Les deux bouts se touchent : choisir des faces sans point commun",
    "The cage changed since the first click: start the Bridge again":
        "La cage a changé depuis le premier clic : recommencer le Relier",
    "Bridged": "Relié",
    "Openings bridged": "Ouvertures reliées",
    "Wall added ({mode}). Smooth it, or use Finish": "Paroi ajoutée ({mode}). La lisser, ou Terminer",
    "Unknown tool {tool}": "Outil inconnu {tool}",
    "The selection no longer exists": "La sélection n'existe plus",
    "That is not an edge of the cage": "Ce n'est pas une arête de la cage",
    # -- checks before Finish ------------------------------------------------------------
    "fewer than 4 faces": "moins de 4 faces",
    "{v0} opening(s) left ({open_edges} open edges): Close or Bridge them":
        "{v0} ouverture(s) restante(s) ({open_edges} arêtes ouvertes) : les Fermer ou les Relier",
    "{bad_edges} edge(s) shared by more than two faces": "{bad_edges} arête(s) partagée(s) par plus de deux faces",
    "faces wind in mixed directions (they will be re-oriented)":
        "faces orientées dans des sens différents (elles seront réorientées)",
    "{twins} point(s) sit exactly on another point": "{twins} point(s) exactement sur un autre point",
    "{flat} face(s) have no area": "{flat} face(s) sans aire",
    "the cage encloses no volume": "la cage n'enferme aucun volume",
    "Shell side must be outside, inside or centred": "Le côté de la coque doit être extérieur, intérieur ou centré",
    "The wall thickness must be above zero": "L'épaisseur de paroi doit être supérieure à zéro",
    "Nothing to shell": "Rien à mettre en coque",
    "That group has no faces to convert": "Ce groupe n'a aucune face à convertir",
    "That group has {v0} faces: a cage should be coarse (under {max_faces}). Simplify it first.":
        "Ce groupe a {v0} faces : une cage doit rester grossière (moins de {max_faces}). Le "
        "simplifier d'abord.",
}
