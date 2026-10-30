"""Spanish for the SubD panel (see subdiv/lang.py). Keys: the English text
as written in the code, placeholders included."""

ES = {
    # -- tools ---------------------------------------------------------------------
    "Create": "Crear",
    "New box cage (size in {unit}), with its lower corner on the origin.":
        "Nueva jaula en forma de caja (tamaño en {unit}), con su esquina inferior en el origen.",
    "Size": "Tamaño",
    "Edit cage": "Modificar",
    "Move the selected point, edge or face along an axis.":
        "Mueve el punto, la arista o la cara seleccionada a lo largo de un eje.",
    "Move by": "Mover",
    "Crease": "Pliegue",
    "Keep the selected edge (or the edges of a face) sharp for N levels; 0 clears. With nothing "
    "selected it applies to every edge; with several selected (Shift+click, or click an edge "
    "again for its contour) to all their edges. The value starts at the smoothing level, which "
    "keeps the edge crisp; a smaller one leaves a small radius.":
        "Mantiene viva la arista seleccionada (o las aristas de una cara) durante N niveles; 0 la "
        "borra. Sin selección se aplica a todas las aristas; con varias seleccionadas (Mayús+clic, "
        "o un nuevo clic en una arista para su contorno), a todas ellas. El valor parte del nivel "
        "de suavizado, que mantiene la arista nítida; uno menor deja un radio pequeño.",
    "Sharpness": "Nitidez",
    "Grow F": "Empujar C",
    "Push the selected face out along its normal.": "Empuja la cara seleccionada a lo largo de su normal.",
    "Height": "Altura",
    "Grow E": "Empujar A",
    "Extend the selected open edge into a new strip (Auto). With a whole contour selected "
    "(click an edge again for its contour) it is extruded outwards; with X, Y or Z chosen the "
    "whole contour of the edge goes along that axis (negative distance goes the other way).":
        "Prolonga la arista abierta seleccionada con una nueva banda (Auto). Con todo un contorno "
        "seleccionado (nuevo clic en una arista para su contorno) se extruye hacia fuera; con X, Y "
        "o Z, todo el contorno de la arista sigue ese eje (una distancia negativa va en sentido "
        "contrario).",
    "Distance": "Distancia",
    "Stretch": "Estirar",
    "Scale the selection along an axis. A face stretched along its own normal stretches the "
    "whole piece that way, the far side staying put.":
        "Escala la selección a lo largo de un eje. Una cara estirada a lo largo de su normal "
        "estira toda la pieza en ese sentido, y el lado opuesto se queda en su sitio.",
    "Factor": "Factor",
    "Offset F": "Desfasar C",
    "Add a smaller copy of the selected face inside it.":
        "Añade, en su interior, una copia más pequeña de la cara seleccionada.",
    "Inset (0-0.95)": "Retranqueo (0-0,95)",
    "Offset E": "Desfasar A",
    "Run a new loop inside the open border the selected edge belongs to.":
        "Traza un nuevo bucle dentro del borde abierto al que pertenece la arista seleccionada.",
    "Squeeze": "Pellizcar",
    "Pinch the selected face's ring (or the open contour of the selected edge, or the contour "
    "selected with repeated clicks) towards its axis.":
        "Estrecha el anillo de la cara seleccionada (o el contorno abierto de la arista "
        "seleccionada, o el contorno elegido con clics repetidos) hacia su eje.",
    "Divide": "Dividir",
    "Cut the selected face in four (each cut runs on round the piece as a loop, or this face "
    "only), or select an edge to cut across it (the whole loop, or only the faces touching "
    "that edge).":
        "Corta la cara seleccionada en cuatro (cada corte da la vuelta a la pieza en bucle, o "
        "solo esta cara), o selecciona una arista para cortar a través de ella (todo el bucle, o "
        "solo las caras que tocan esa arista).",
    "Delete F": "Eliminar C",
    "Remove the selected face, leaving an opening to Close or Bridge.":
        "Quita la cara seleccionada y deja una abertura para Cerrar o Unir con un puente.",
    "Close": "Cerrar",
    "Fill the open border the selected edge belongs to.": "Rellena el borde abierto al que pertenece la arista seleccionada.",
    "Bridge": "Puente",
    "Click a face (or an edge of an opening), then click the other one: the bridge is made at "
    "the second click, the faces removed and joined by a ring of quads. (Shift+click then "
    "Apply, or Apply after each, also work.) Twist turns the ring by that many points; set it "
    "before the second click.":
        "Haz clic en una cara (o en una arista de una abertura) y luego en la otra: el puente se "
        "hace en el segundo clic, las caras se quitan y se unen con un anillo de cuadriláteros. "
        "(Mayús+clic y luego Aplicar, o Aplicar tras cada clic, también funcionan.) Giro hace "
        "girar el anillo ese número de puntos; ajústalo antes del segundo clic.",
    "Twist": "Giro",
    "Shell": "Vaciado",
    "Give the whole piece a wall: choose Inside, Outside or Centred, then Apply. An open piece "
    "becomes a thick sheet, a closed one a hollow body.":
        "Da un grosor de pared a toda la pieza: elige Interior, Exterior o Centrado y luego "
        "Aplicar. Una pieza abierta se convierte en una lámina gruesa, una cerrada en un cuerpo "
        "hueco.",
    "Thickness": "Espesor",
    "metres": "metros", "centimetres": "centímetros", "millimetres": "milímetros",
    "inches": "pulgadas", "feet": "pies",
    "outside": "exterior", "inside": "interior", "center": "centrado",
    # -- panel ---------------------------------------------------------------------
    "SubD group": "Grupo SubD",
    "Auto": "Auto",
    "Direction for Edit, Stretch and Squeeze (Auto: the face's normal / ring)":
        "Dirección para Modificar, Estirar y Pellizcar (Auto: la normal de la cara / el anillo)",
    "Outside": "Exterior", "Inside": "Interior", "Centred": "Centrado",
    "Where the wall grows from the current surface": "Hacia qué lado de la superficie crece la pared",
    "Whole loop": "Todo el bucle", "Only this face": "Solo esta cara",
    "Divide a face or an edge. Whole loop: the cut runs on round the piece through the quads "
    "beyond (clean quads). Only this face: just the face (or the faces touching the edge) is "
    "cut; the neighbours get an extra point.":
        "Divide una cara o una arista. Todo el bucle: el corte da la vuelta a la pieza a través "
        "de los cuadriláteros siguientes (cuadriláteros limpios). Solo esta cara: solo se corta "
        "la cara (o las caras que tocan la arista); las vecinas reciben un punto más.",
    "Apply": "Aplicar",
    "Symmetry": "Simetría",
    "Repeat every edit on the other side of the plane.": "Repite cada modificación al otro lado del plano.",
    "Axis the plane is perpendicular to.": "Eje al que el plano es perpendicular.",
    "Centre": "Centrar",
    "Put the plane through the middle of the piece.": "Coloca el plano por el centro de la pieza.",
    "From face": "Desde la cara",
    "Use the plane of the selected face.": "Usa el plano de la cara seleccionada.",
    "Join with": "Unir con",
    "Another SubD group to merge into this one, so Bridge can link their openings.":
        "Otro grupo SubD que se fusiona con este, para que Puente pueda unir sus aberturas.",
    "Join": "Unir",
    "Split": "Separar",
    "Undo a Join: every separate piece of this group becomes its own SubD group again.":
        "Deshace una unión: cada pieza separada de este grupo vuelve a ser su propio grupo SubD.",
    "Convert group": "Convertir el grupo",
    "Groups not made by this plugin. Their faces become the cage, so use a coarse one (under "
    "7000 faces; editing gets slow above a few hundred).":
        "Grupos que no vienen de esta extensión. Sus caras pasan a ser la jaula: elige uno poco "
        "denso (menos de 7000 caras; la edición se ralentiza por encima de unos cientos).",
    "Crease edges over": "Aristas vivas a partir de",
    "Edges where two faces meet at more than this angle stay sharp. 0 = no automatic creases "
    "(everything rounds).":
        "Las aristas donde dos caras forman un ángulo mayor que este se quedan vivas. 0 = sin "
        "pliegues automáticos (todo se redondea).",
    "Convert to SubD": "Convertir a SubD",
    "Replace the chosen group by a SubD group built on its faces. Ctrl+Z brings the original back.":
        "Sustituye el grupo elegido por un grupo SubD construido sobre sus caras. Ctrl+Z recupera el original.",
    "Create with sharp edges (angle above)": "Crear con aristas vivas (ángulo de arriba)",
    "Create then gives a crisp box instead of a rounded block: the edges of the new box stay "
    "sharp when the angle above is below 90 degrees (30 is fine). Stretch, Grow and Shell then "
    "work on a rectilinear piece.":
        "Crear da entonces una caja nítida en lugar de un bloque redondeado: las aristas de la "
        "nueva caja se quedan vivas cuando el ángulo de arriba es inferior a 90 grados (30 va "
        "bien). Estirar, Empujar y Vaciado trabajan entonces sobre una pieza rectilínea.",
    "Smoothing": "Suavizado",
    "Subdivision steps: 0 is the cage itself.": "Pasos de subdivisión: 0 es la propia jaula.",
    "Smoothest level that keeps the surface under about 25 000 triangles; uncheck to choose it yourself.":
        "El nivel más suave que mantiene la superficie por debajo de unos 25 000 triángulos; "
        "desmarca para elegirlo tú.",
    "Cage lines": "Líneas de la jaula", "All edges": "Todas las aristas", "No lines": "Sin líneas",
    "Update look": "Actualizar el aspecto",
    "Rebuild the surface with this smoothing and these lines.":
        "Reconstruye la superficie con este suavizado y estas líneas.",
    "Flip faces": "Invertir las caras",
    "Blue faces are seen from behind. Flip turns the whole piece inside out so the front and "
    "the back swap.":
        "Las caras azules se ven por detrás. Invertir da la vuelta a toda la pieza: el anverso y "
        "el reverso se intercambian.",
    "Finish detail": "Detalle del acabado",
    "Automatic (light)": "Automático (ligero)",
    "Same as the view": "Igual que la vista",
    "Light (1)": "Ligero (1)", "Medium (2)": "Medio (2)", "Fine (3)": "Fino (3)",
    "How finely the curved parts are cut when the piece is finished. Automatic keeps the result "
    "under about %d faces so ordinary tools stay fast (the smoothest level that fits). Each "
    "step up multiplies the triangles by four. Flat faces are always single polygons, whatever "
    "you choose.":
        "Con qué finura se cortan las partes curvas al terminar la pieza. Automático mantiene el "
        "resultado por debajo de unas %d caras para que las herramientas habituales sigan siendo "
        "rápidas (el nivel más suave que cabe). Cada nivel más multiplica los triángulos por "
        "cuatro. Las caras planas son siempre un único polígono, elijas lo que elijas.",
    "Finish": "Terminar",
    "Finish (no longer SubD): keep the smooth surface as an ordinary group and drop the cage. "
    "If the cage is closed and sound, the result is a Solid Group (usable with Solid Tools) and "
    "its volume is reported; if it is still open, you get the surface and the reason. Undo "
    "brings the SubD group back.":
        "Terminar (deja de ser SubD): conserva la superficie suave como un grupo normal y "
        "descarta la jaula. Si la jaula está cerrada y sana, el resultado es un Grupo sólido "
        "(utilizable con las Herramientas de sólidos) y se indica su volumen; si sigue abierta, "
        "obtienes la superficie y el motivo. Deshacer devuelve el grupo SubD.",
    "Handles": "Tiradores",
    "Move + Rotate": "Mover + Girar", "Move only": "Solo mover",
    "Rotate only (protractor)": "Solo girar (transportador)",
    "Move: drag a coloured tip to slide the selection along that axis.\nRotate: drag a coloured "
    "ring to turn the selection around that axis (hold Ctrl to snap to 15 degrees).\nBoth are "
    "shown by default; pick one to keep the view clear.":
        "Mover: arrastra una punta de color para deslizar la selección a lo largo de ese eje.\n"
        "Girar: arrastra un anillo de color para girar la selección alrededor de ese eje (Ctrl: "
        "pasos de 15 grados).\nAmbos se muestran por defecto; elige uno para despejar la vista.",
    "Show cage": "Mostrar la jaula",
    "SubD panel": "Panel SubD",
    "Show the subdivision-modelling panel.": "Muestra el panel de modelado por subdivisión.",
    # -- messages ------------------------------------------------------------------
    "  (waiting for the second opening)": "  (esperando la segunda abertura)",
    "Could not apply: {err}": "No se pudo aplicar: {err}",
    "Several items are selected: use Edit cage or Crease on them, or click one item for this tool":
        "Hay varios elementos seleccionados: usa Modificar o Pliegue con ellos, o haz clic en un "
        "solo elemento para esta herramienta",
    "Choose X, Y or Z to move several items together": "Elige X, Y o Z para mover varios elementos a la vez",
    "Sharp-edged SubD box created — click a point, edge or face of the cage":
        "Caja SubD de aristas vivas creada — haz clic en un punto, una arista o una cara de la jaula",
    "SubD box created — click a point, edge or face of the cage":
        "Caja SubD creada — haz clic en un punto, una arista o una cara de la jaula",
    "Create or choose a SubD group first": "Primero crea o elige un grupo SubD",
    "Symmetry on": "Simetría activada", "Symmetry off": "Simetría desactivada",
    "Plane set through the centre": "Plano colocado en el centro",
    "Plane set from the face": "Plano tomado de la cara",
    "Select a face first: its plane becomes the symmetry plane":
        "Selecciona primero una cara: su plano pasa a ser el plano de simetría",
    "Choose a second SubD group under \"Join with\"": "Elige un segundo grupo SubD en «Unir con»",
    "Could not join: {err}": "No se pudo unir: {err}",
    "Joined. Choose Bridge, then click a face on each piece (Apply after each)":
        "Unido. Elige Puente y haz clic en una cara de cada pieza (Aplicar tras cada una)",
    "No SubD group to split": "No hay ningún grupo SubD que separar",
    "Nothing to split: this is one connected piece. After a Bridge, delete the bridge's faces "
    "(Delete F) to separate the pieces first":
        "Nada que separar: es una sola pieza conectada. Tras un Puente, elimina primero las caras "
        "del puente (Eliminar C) para separar las piezas",
    "Could not split: {err}": "No se pudo separar: {err}",
    "Split into {n} separate SubD groups (Ctrl+Z to join them back)":
        "Separado en {n} grupos SubD (Ctrl+Z para volver a unirlos)",
    "No group to convert: make or import one first": "No hay ningún grupo que convertir: crea o importa uno primero",
    " ({n} faces lost their holes)": " ({n} caras han perdido sus agujeros)",
    "Converted: {n} faces, {k} sharp edges": "Convertido: {n} caras, {k} aristas vivas",
    "No SubD group to update": "No hay ningún grupo SubD que actualizar",
    "Look updated": "Aspecto actualizado",
    "No SubD group to flip": "No hay ningún grupo SubD que invertir",
    "Faces flipped": "Caras invertidas",
    "No SubD group to finish": "No hay ningún grupo SubD que terminar",
    "Could not finish: {err}": "No se pudo terminar: {err}",
    "Finished, solid group ({n} faces): volume {v} {u}³": "Terminado, grupo sólido ({n} caras): volumen {v} {u}³",
    " — not counted as a solid by Solid Tools; check for coincident points":
        " — las Herramientas de sólidos no lo cuentan como sólido; comprueba si hay puntos coincidentes",
    "Finished, surface only ({n} faces), not a solid: {why}":
        "Terminado, solo superficie ({n} caras), no es un sólido: {why}",
    " (Ctrl+Z to edit the cage again)": " (Ctrl+Z para retomar la jaula)",
    "Rotated {a}° around {axis}": "Girado {a}° alrededor de {axis}",
    "Bridge: now click the other face (or an edge of the other opening)":
        "Puente: haz clic ahora en la otra cara (o en una arista de la otra abertura)",
    "Bridge: select two faces (click one, Shift+click the other)":
        "Puente: selecciona dos caras (clic en una, Mayús+clic en la otra)",
    "Create a SubD box first, or choose a SubD group": "Primero crea una caja SubD, o elige un grupo SubD",
    "{note} ({n} edges) - click again for the next contour":
        "{note} ({n} aristas) - haz clic de nuevo para el contorno siguiente",
    "{note} ({n} edge) - click again for the next contour":
        "{note} ({n} arista) - haz clic de nuevo para el contorno siguiente",
    "SubD drag failed": "Falló el arrastre SubD",
    "Loop": "Bucle", "Face outline": "Contorno de la cara",
    # -- tool results ------------------------------------------------------------------
    "{n} items selected (Shift+click adds or removes one)":
        "{n} elementos seleccionados (Mayús+clic añade o quita uno)",
    "Nothing selected": "Nada seleccionado",
    "Point {i}": "Punto {i}", "Edge {a}-{b}": "Arista {a}-{b}", "Face {i}": "Cara {i}",
    "Select {what} first": "Selecciona primero {what}",
    "an open edge": "una arista abierta",
    "a point, edge or face": "un punto, una arista o una cara",
    "an edge or a face": "una arista o una cara",
    "a face": "una cara",
    "a face, or an edge of an open contour": "una cara, o una arista de un contorno abierto",
    "a face or an edge": "una cara o una arista",
    "That edge is not on an open border": "Esa arista no está en un borde abierto",
    "All creases cleared": "Todos los pliegues borrados",
    "Every edge creased {value}": "Todas las aristas plegadas {value}",
    "Crease cleared": "Pliegue borrado",
    "Crease {value}": "Pliegue {value}",
    "Select edges or faces first": "Selecciona primero aristas o caras",
    "{n} edges rounded off": "{n} aristas redondeadas",
    "{n} edge rounded off": "{n} arista redondeada",
    "{n} edges creased {value}": "{n} aristas plegadas {value}",
    "{n} edge creased {value}": "{n} arista plegada {value}",
    "Face grown": "Cara empujada",
    "along {v0}": "a lo largo de {v0}",
    "Cannot tell which way is outward for that contour: choose X, Y or Z":
        "No se puede saber dónde está el exterior para ese contorno: elige X, Y o Z",
    "Open contour of {v0} edges extruded {where}": "Contorno abierto de {v0} aristas extruido {where}",
    "Cannot tell which way is outward for that edge": "No se puede saber dónde está el exterior para esa arista",
    "Edge grown": "Arista empujada",
    "Grow E: select edges of an open contour": "Empujar A: selecciona aristas de un contorno abierto",
    "Select the whole open contour (click an edge again for its contour), or a single edge":
        "Selecciona todo el contorno abierto (nuevo clic en una arista para su contorno), o una "
        "sola arista",
    "Whole piece stretched (the selection alone has no length along that direction)":
        "Toda la pieza estirada (la selección sola no tiene longitud en esa dirección)",
    "Face offset": "Cara desfasada",
    "Border offset": "Borde desfasado",
    "Open contour squeezed": "Contorno abierto pellizcado",
    "Select a face or the edges of a contour first": "Selecciona primero una cara o las aristas de un contorno",
    "Select at least three points to squeeze": "Selecciona al menos tres puntos que pellizcar",
    "Loop cut": "Bucle cortado",
    "Cut across the face": "Corte a través de la cara",
    "Face divided": "Cara dividida",
    "A cage needs at least one face": "Una jaula necesita al menos una cara",
    "Face deleted — Close it again or Bridge it to another opening":
        "Cara eliminada — vuelve a Cerrarla o únela con un Puente a otra abertura",
    "Hole closed": "Agujero cerrado",
    "Now select the other {what} (a face or an edge of an opening) and press Apply again":
        "Selecciona ahora la otra {what} (una cara o una arista de una abertura) y pulsa "
        "Aplicar de nuevo",
    "Pick a different face": "Elige otra cara",
    "Pick an edge of a different opening": "Elige una arista de otra abertura",
    "Both ends need the same number of sides ({v0} and {v1})":
        "Ambos extremos necesitan el mismo número de lados ({v0} y {v1})",
    "The two ends touch each other: pick faces that do not share a point":
        "Los dos extremos se tocan: elige caras que no compartan ningún punto",
    "The cage changed since the first click: start the Bridge again":
        "La jaula ha cambiado desde el primer clic: empieza el Puente de nuevo",
    "face": "cara", "opening": "abertura",
    "Bridged": "Puenteado",
    "Openings bridged": "Aberturas unidas con un puente",
    "Wall added ({mode}). Smooth it, or use Finish": "Pared añadida ({mode}). Suavízala, o usa Terminar",
    "Unknown tool {tool}": "Herramienta desconocida {tool}",
    "The selection no longer exists": "La selección ya no existe",
    "That is not an edge of the cage": "Eso no es una arista de la jaula",
    # -- checks before Finish ------------------------------------------------------------
    "fewer than 4 faces": "menos de 4 caras",
    "{v0} opening(s) left ({open_edges} open edges): Close or Bridge them":
        "quedan {v0} abertura(s) ({open_edges} aristas abiertas): ciérralas o únelas con un Puente",
    "{bad_edges} edge(s) shared by more than two faces": "{bad_edges} arista(s) compartida(s) por más de dos caras",
    "faces wind in mixed directions (they will be re-oriented)":
        "caras orientadas en sentidos distintos (se reorientarán)",
    "{twins} point(s) sit exactly on another point": "{twins} punto(s) exactamente sobre otro punto",
    "{flat} face(s) have no area": "{flat} cara(s) sin área",
    "the cage encloses no volume": "la jaula no encierra ningún volumen",
    "Shell side must be outside, inside or centred": "El lado del vaciado debe ser exterior, interior o centrado",
    "The wall thickness must be above zero": "El espesor de la pared debe ser mayor que cero",
    "Nothing to shell": "Nada que vaciar",
    "That group has no faces to convert": "Ese grupo no tiene caras que convertir",
    "That group has {v0} faces: a cage should be coarse (under {max_faces}). Simplify it first.":
        "Ese grupo tiene {v0} caras: una jaula debe ser poco densa (menos de {max_faces}). "
        "Simplifícala primero.",
}
