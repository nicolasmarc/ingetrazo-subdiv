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
    "Keep the selected edge (or the edges of a face) sharp for N levels; 0 clears. A fraction (1.5, 0.5...) gives a softer edge, and a selected point becomes a corner. With nothing selected it applies to every edge; with several selected (Shift+click, or click an edge again for its contour) to all their edges. The value starts at the smoothing level, which keeps the edge crisp; a smaller one leaves a small radius.":
        "Garde l'arête sélectionnée (ou les arêtes d'une face) vive sur N niveaux ; 0 l'efface. Une fraction (1,5 ; 0,5...) donne une arête plus douce, et un point sélectionné devient un coin. Sans sélection, s'applique à toutes les arêtes ; avec plusieurs (Maj+clic, ou un nouveau clic sur une arête pour son contour), à toutes leurs arêtes. La valeur part du niveau de lissage, qui garde l'arête nette ; une plus petite laisse un petit rayon.",
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
    "Several items are selected: use Edit cage, Crease, Bevel, Slide, Loft or Sweep on them, or click one item for this tool":
        "Plusieurs éléments sont sélectionnés : utiliser Modifier, Pli, Chanfrein, Glisser, Loft ou Balayage, ou cliquer un seul élément pour cet outil",
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
    "face": "face", "opening": "ouverture",
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
    # -- Revolve, Bevel, Loft, Sweep, Slice, Merge, Dissolve, Slide, soft selection --
    "Segments":
        "Segments",
    "Revolve":
        "Révolution",
    "Bevel":
        "Chanfrein",
    "Replace the selected edge by a narrow flat strip, to give a corner a support or a chamfer. Click an edge again for its loop to bevel the whole loop.":
        "Remplace l'arête sélectionnée par une bande plate étroite, pour donner un appui à un angle ou un chanfrein. Cliquer à nouveau sur une arête pour sa boucle chanfreine toute la boucle.",
    "Width":
        "Largeur",
    "Loft":
        "Loft",
    "Sweep":
        "Balayage",
    "Twist (deg)":
        "Torsion (°)",
    "Slice":
        "Trancher",
    "Cut the cage with a plane perpendicular to X, Y or Z through the selected item (or the middle of the piece), moved by the value.":
        "Coupe la cage par un plan perpendiculaire à X, Y ou Z passant par l'élément sélectionné (ou le milieu de la pièce), décalé de la valeur.",
    "Offset":
        "Décalage",
    "Merge":
        "Fusionner",
    "Select an edge or a face to merge its points at the middle, or a point to merge every point within the distance into it.":
        "Sélectionner une arête ou une face pour fusionner ses points en leur milieu, ou un point pour y fusionner tous les points situés à moins de la distance.",
    "Dissolve":
        "Dissoudre",
    "Remove the selected edge (its two faces become one) or point, keeping the surface closed.":
        "Supprime l'arête sélectionnée (ses deux faces n'en font plus qu'une) ou le point, en gardant la surface fermée.",
    "Slide":
        "Glisser",
    "Slide the loop through the selected edge sideways, by a fraction of the way to its neighbour (negative goes the other way). Click an edge again for its loop.":
        "Fait glisser latéralement la boucle passant par l'arête sélectionnée, d'une fraction du chemin vers sa voisine (négatif : dans l'autre sens). Cliquer à nouveau sur une arête pour sa boucle.",
    "Slide (-0.9..0.9)":
        "Glissement (-0,9..0,9)",
    "Loft and Sweep: close the two ends with a face, or leave the surface open.":
        "Loft et Balayage : fermer les deux extrémités par une face, ou laisser la surface ouverte.",
    "Soft":
        "Doux",
    "Soft selection: moving a point also drags the points around it, fading out at the radius.":
        "Sélection douce : déplacer un point entraîne aussi les points autour, de moins en moins jusqu'au rayon.",
    "Radius of the soft selection.":
        "Rayon de la sélection douce.",
    "Closed ends":
        "Extrémités fermées",
    "Open ends":
        "Extrémités ouvertes",
    "a point, an edge or a face":
        "un point, une arête ou une face",
    "a face (the profile)":
        "une face (le profil)",
    "Revolved: {n} faces added":
        "Révolution : {n} faces ajoutées",
    "an edge":
        "une arête",
    "Bevelled: {n} faces added":
        "Chanfrein : {n} faces ajoutées",
    "Lofted through {k} sections: {n} faces added":
        "Loft par {k} sections : {n} faces ajoutées",
    "Swept along {k} points: {n} faces added":
        "Balayage le long de {k} points : {n} faces ajoutées",
    "Loft: select two or more faces (click one, Shift+click the others)":
        "Loft : sélectionner deux faces ou plus (cliquer l'une, Maj+clic sur les autres)",
    "Sweep: select one face (the profile), then Shift+click the edges of the path":
        "Balayage : sélectionner une face (le profil), puis Maj+clic sur les arêtes du chemin",
    "Sliced: {n} edges in the cut":
        "Tranché : {n} arêtes dans la coupe",
    "{n} points merged":
        "{n} points fusionnés",
    "an edge or a point":
        "une arête ou un point",
    "Point dissolved":
        "Point dissous",
    "Loop slid: {n} points":
        "Boucle glissée : {n} points",
    "Select edges to bevel":
        "Sélectionner les arêtes à chanfreiner",
    "Choose X, Y or Z: the plane is perpendicular to that axis":
        "Choisir X, Y ou Z : le plan est perpendiculaire à cet axe",
    "The plane does not cut the cage":
        "Le plan ne coupe pas la cage",
    "Edge merged at its middle":
        "Arête fusionnée en son milieu",
    "Face merged into one point":
        "Face fusionnée en un point",
    "Edge dissolved":
        "Arête dissoute",
    "Select the edges of a loop to slide":
        "Sélectionner les arêtes d'une boucle à faire glisser",
    "Ring":
        "Anneau",
    "Corner cleared":
        "Coin effacé",
    "Corner {value}":
        "Coin {value}",
    "{n} corners rounded off":
        "{n} coins arrondis",
    "{n} corners creased {value}":
        "{n} coins marqués {value}",
    "An edge section must be a closed loop":
        "Une section en arêtes doit être une boucle fermée",
    "Choose X, Y or Z: the axis the profile turns around":
        "Choisir X, Y ou Z : l'axe autour duquel le profil tourne",
    "A revolution needs at least 3 segments":
        "Une révolution demande au moins 3 segments",
    "The angle must be between 0 and 360 degrees":
        "L'angle doit être compris entre 0 et 360 degrés",
    "The profile lies on the axis: move it away first":
        "Le profil est sur l'axe : l'éloigner d'abord",
    "The bevel width must be above zero":
        "La largeur du chanfrein doit être supérieure à zéro",
    "Select an edge to bevel":
        "Sélectionner une arête à chanfreiner",
    "The distance must be above zero":
        "La distance doit être supérieure à zéro",
    "No other point lies within that distance":
        "Aucun autre point à moins de cette distance",
    "Dissolve needs an edge between two faces":
        "Dissoudre demande une arête entre deux faces",
    "Dissolving that edge would pinch the face":
        "Dissoudre cette arête pincerait la face",
    "That point belongs to no face":
        "Ce point n'appartient à aucune face",
    "Slide by a fraction between -1 and 1":
        "Glisser d'une fraction entre -1 et 1",
    "Loft needs at least two sections":
        "Le loft demande au moins deux sections",
    "Segments between sections must be at least 1":
        "Il faut au moins 1 segment entre les sections",
    "A section needs at least 3 points":
        "Une section demande au moins 3 points",
    "The path must be one chain of edges, without branches":
        "Le chemin doit être une seule chaîne d'arêtes, sans branches",
    "The path needs at least two points":
        "Le chemin demande au moins deux points",
    "The profile needs at least 3 points":
        "Le profil demande au moins 3 points",
    "The path has two points in the same place":
        "Le chemin a deux points au même endroit",
    "Bevel needs an edge inside the surface, not on a border":
        "Le chanfrein demande une arête à l'intérieur de la surface, pas sur un bord",
    "Bevel needs the edge's end points to be inside the surface":
        "Le chanfrein demande que les extrémités de l'arête soient à l'intérieur de la surface",
    "The bevel is too wide for this edge: use a smaller width":
        "Le chanfrein est trop large pour cette arête : prendre une largeur plus petite",
    "Dissolve a point inside the surface (not on a border)":
        "Dissoudre un point à l'intérieur de la surface (pas sur un bord)",
    "Dissolving that point would pinch the face":
        "Dissoudre ce point pincerait la face",
    "Slide needs a loop inside the surface, not on a border":
        "Glisser demande une boucle à l'intérieur de la surface, pas sur un bord",
    "A face is not convex where the plane cuts it: divide it first":
        "Une face n'est pas convexe là où le plan la coupe : la diviser d'abord",
    "Dissolving that point would leave a face with two sides":
        "Dissoudre ce point laisserait une face à deux côtés",
    # -- picking on the skin --
    "Pick on the skin":
        "Sélection sur la peau",
    "Click the smooth surface itself: the point, edge or face of the cage that shapes the spot you click is selected, even with the cage hidden.":
        "Cliquer sur la surface lissée elle-même : le point, l'arête ou la face de la cage qui façonne l'endroit cliqué est sélectionné, même avec la cage cachée.",
    "Join, split, convert":
        "Joindre, séparer, convertir",
    "Smoothing, finish, handles":
        "Lissage, finition, poignées",
    "Hide cage":
        "Masquer la cage",
    "Pass a surface through several faces used as sections: SubD faces (click one, Shift+click the others) or plain faces from your drawing (select them, then Apply). They are taken in the order they lie along the piece. The sections stay where they are. Choose whether the ends are closed.":
        "Fait passer une surface par plusieurs faces servant de sections : faces SubD (cliquer l'une, Maj+clic sur les autres) ou faces simples de votre dessin (les sélectionner, puis Appliquer). Elles sont prises dans l'ordre où elles se suivent. Les sections restent en place. Choisir si les extrémités sont fermées.",
    "Carry a face (the profile) along a path: select the face, then Shift+click the edges of the path, which must be one chain. The profile turns to follow the path. The profile and the path can also be a plain face and plain lines from your drawing (select them in the model, then Apply).":
        "Fait avancer une face (le profil) le long d'un chemin : sélectionner la face, puis Maj+clic sur les arêtes du chemin, qui doivent former une seule chaîne. Le profil tourne pour suivre le chemin. Le profil et le chemin peuvent aussi être une face simple et des lignes simples de votre dessin (les sélectionner dans le modèle, puis Appliquer).",
    "Copy faces":
        "Copier les faces",
    "Paste faces":
        "Coller les faces",
    "Copied {n} faces: Ctrl+V pastes them as a new SubD piece":
        "{n} faces copiées : Ctrl+V les colle comme une nouvelle pièce SubD",
    "Nothing to paste: select SubD faces and press Ctrl+C first":
        "Rien à coller : sélectionner des faces SubD et appuyer sur Ctrl+C d'abord",
    "Pasted {n} faces as a new SubD piece: move it with the handles":
        "{n} faces collées en nouvelle pièce SubD : la déplacer avec les poignées",
    "Turn the selected face (the profile, drawn away from the axis) round the X, Y or Z axis through the origin into a body of revolution. Points on the axis become poles. The profile can also be a plain face or plain lines from your drawing (select them in the model, then Apply).":
        "Fait tourner la face sélectionnée (le profil, dessiné à l'écart de l'axe) autour de l'axe X, Y ou Z passant par l'origine pour en faire un corps de révolution. Les points sur l'axe deviennent des pôles. Le profil peut aussi être une face simple ou des lignes simples de votre dessin (les sélectionner dans le modèle, puis Appliquer).",
    "Right-click: SubD tools only":
        "Clic droit : outils SubD seulement",
    "Right-click on the SubD piece shows a menu of SubD tools only (smoothing 0 to 4, cage, copy, paste). Untick to get the model's usual menu with the SubD tools inside.":
        "Un clic droit sur la pièce SubD n'affiche que les outils SubD (lissage de 0 à 4, cage, copier, coller). Décocher pour retrouver le menu habituel du modèle, avec les outils SubD à l'intérieur.",
    "Move the mouse to set the value. Click to apply, Enter for an exact value, Esc to cancel":
        "Bouger la souris pour régler la valeur. Clic pour appliquer, Entrée pour une valeur exacte, Échap pour annuler",
    "Cancelled":
        "Annulé",
    "Right-click tools: adjust with the mouse":
        "Outils du clic droit : régler à la souris",
    "A tool chosen from the right-click menu follows the mouse: move to set the value and see the result, click to apply, Enter to type an exact value, Esc to cancel. Shift = finer, Ctrl = snap to steps. Untick to always get the value box.":
        "Un outil choisi dans le menu clic droit suit la souris : bouger pour régler la valeur et voir le résultat, cliquer pour appliquer, Entrée pour saisir une valeur exacte, Échap pour annuler. Maj = plus fin, Ctrl = par pas. Décocher pour toujours avoir la boîte de saisie.",
    "Ctrl: dragging a copy":
        "Ctrl : copie en cours de déplacement",
    "Copy made: {n} faces":
        "Copie faite : {n} faces",
    "Enter applies, Esc cancels":
        "Entrée applique, Échap annule",
    "Select all faces":
        "Tout sélectionner",
    "All {n} faces selected: Ctrl + drag a move handle copies the piece":
        "Les {n} faces sont sélectionnées : Ctrl + tirer une poignée de déplacement copie la pièce",
    "Whole piece selected: move it, copy it, or press Delete to remove it":
        "Pièce entière sélectionnée : la déplacer, la copier, ou appuyer sur Suppr pour l'effacer",
    "Deleted — Ctrl+Z brings it back":
        "Supprimé — Ctrl+Z pour annuler",
    "Drawing: {f} face(s), {l} line(s)":
        "Dessin : {f} face(s), {l} ligne(s)",
    "Selected faces flipped":
        "Faces sélectionnées retournées",
    "Whole piece flipped (select faces to flip only those)":
        "Pièce entière retournée (sélectionne des faces pour ne retourner qu'elles)",
    "Loft: turn each section against the one before, in steps of one point of the section (a 4-point section turns by 90°).":
        "Loft : tourne chaque section par rapport à la précédente, par pas d'un point de la section (une section à 4 points tourne de 90°).",
    "Blue faces are seen from behind. Flip turns the selected faces over; with no face selected it turns the whole piece inside out.":
        "Les faces bleues sont vues de dos. Retourner inverse les faces sélectionnées ; sans face sélectionnée, toute la pièce est retournée.",
    "Cancelled — nothing made":
        "Annulé — rien n'a été créé",
    "Flipped the connected part of the selected face(s): {n} faces":
        "Partie connectée de la face sélectionnée retournée : {n} faces",
    "Whole piece flipped (select a face to flip only its part)":
        "Groupe entier retourné (sélectionne une face pour ne retourner que sa partie)",
    "Blue faces are seen from behind. Flip turns over the connected part that holds the selected face; with nothing selected, the whole group.":
        "Les faces bleues sont vues de dos. Retourner inverse la partie connectée qui contient la face sélectionnée ; sans sélection, tout le groupe.",
}
