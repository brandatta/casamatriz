import io
import re
import zipfile
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from docx import Document
from pypdf import PdfReader


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Casa Matriz | Archivo organizado",
    page_icon="🗂️",
    layout="wide",
)

CATEGORIES = [
    "01_IDENTIDAD_MARCA_Y_ESTRATEGIA",
    "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES",
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO",
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES",
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS",
]

CATEGORY_LABELS = {
    "01_IDENTIDAD_MARCA_Y_ESTRATEGIA": "Identidad, marca y estrategia",
    "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES": "Obra autoral, ensayos y borradores",
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO": "Cursos, formación y archivo astrológico",
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES": "Bibliografía, investigación y fuentes",
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS": "Archivo visual, editorial y referencias",
}

CATEGORY_DESCRIPTIONS = {
    "01_IDENTIDAD_MARCA_Y_ESTRATEGIA": "Material fundacional, marca, manifiestos, nombres, estructura y posicionamiento.",
    "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES": "Textos propios, ensayos, fragmentos, ideas y materiales publicables.",
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO": "Cursos, certificaciones, seminarios, material pedagógico y archivo histórico astrológico.",
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES": "Tesis, PDFs académicos, libros de referencia, papers y bibliografía.",
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS": "Imágenes, recursos visuales, links, referencias editoriales y diseño.",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".jp2"
}

DESIGN_EXTENSIONS = {
    ".ai", ".psd", ".indd"
}


RULES = {
    "01_IDENTIDAD_MARCA_Y_ESTRATEGIA": [
        "casa matriz", "proyecto integral", "manifiesto", "fundamentos",
        "marca", "identidad", "estrategia", "nombres", "tagline",
        "estructura", "talleres", "publicaciones", "matrices",
        "mediatrices", "editable marcas", "landing", "web",
    ],
    "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES": [
        "ensayo", "cosmos", "core", "pliegues", "habitar", "venus",
        "buena astróloga", "buena astrologa", "ideas", "otros títulos",
        "otros titulos", "varios", "adorno", "foucault", "hermenéutica",
        "hermeneutica", "mujeres", "giro copernicano", "fragmento",
        "borrador", "dossier", "cuerpo", "metamorfosis", "oscuridad",
        "sirenas", "criptozoologia", "criptozoología",
    ],
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO": [
        "curso", "formación", "formacion", "certificación", "certificacion",
        "luminarias", "sol y luna", "intro curso", "preview",
        "material adicional", "seminario", "volver a la luna",
        "transcripcion", "transcripción", "horoscoño", "horoscono",
        "ernesto castro", "arquetipo", "lunar", "solar", "astrología",
        "astrologia", "carta natal", "zodiaco", "tauro", "libra",
        "luna astrológica", "luna astrologica",
    ],
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES": [
        "bibliografia", "bibliografía", "tesis", "thesis", "phd",
        "startup", "phillipson", "clynes", "von stuckrad",
        "astrology and truth", "internet on modern western astrology",
        "historia", "borges", "seres imaginarios", "libro de los seres",
        "fuente", "paper", "research", "epistemology", "epistemología",
        "references", "bibliography", "university", "submitted",
        "abstract", "table of contents",
    ],
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS": [
        "cabinet", "wonders", "collection", "colección ilustrada",
        "coleccion ilustrada", "links", "rawpixel", "dragon", "dragón",
        "utagawa", "kuniyoshi", "imagen", "visual", "referencia",
        "archivo visual", "public domain", "wellcome", "british library",
        "library of congress", "grabado", "manuscrito", "sketchbook",
        "stephan scriber", "ilustrada", "ilustrado", "editorial",
        "wunderkammer", "kunstkammer",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def normalize(value: str) -> str:
    if not value:
        return ""

    value = value.lower()
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)

    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o",
        "ú": "u", "ü": "u", "ñ": "n",
    }

    for original, replacement in replacements.items():
        value = value.replace(original, replacement)

    return value.strip()


def clean_filename(filename: str) -> str:
    filename = filename.strip()
    filename = re.sub(r'[<>:"/\\|?*]', "-", filename)
    filename = re.sub(r"\s+", " ", filename)
    return filename[:180]


def extract_docx(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
        parts = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)

        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        return "\n".join(parts)

    except Exception as error:
        return f"[ERROR_DOCX] {error}"


def extract_pdf(file_bytes: bytes, max_pages: int = 15) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts = []

        total_pages = min(len(reader.pages), max_pages)

        for index in range(total_pages):
            text = reader.pages[index].extract_text() or ""
            if text.strip():
                parts.append(text.strip())

        return "\n".join(parts)

    except Exception as error:
        return f"[ERROR_PDF] {error}"


def extract_txt(file_bytes: bytes) -> str:
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return "[ERROR_TXT] No se pudo leer el archivo de texto."


def extract_text(filename: str, file_bytes: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".docx":
        return extract_docx(file_bytes)

    if extension == ".pdf":
        return extract_pdf(file_bytes)

    if extension in [".txt", ".md", ".odt"]:
        return extract_txt(file_bytes)

    if extension in IMAGE_EXTENSIONS:
        return "[IMAGEN] Archivo visual."

    if extension in DESIGN_EXTENSIONS:
        return "[DISEÑO] Archivo de diseño."

    return "[SIN_TEXTO] No se extrajo texto para este tipo de archivo."


def word_count(text: str) -> int:
    if not text or text.startswith("["):
        return 0

    return len(re.findall(r"\b\w+\b", text))


def detect_tags(text: str) -> str:
    normalized = normalize(text)

    tag_rules = {
        "astrologia": ["astrologia", "zodiaco", "carta natal", "horoscopo"],
        "cine": ["cine", "pelicula", "pantalla", "fotograma"],
        "luna": ["luna", "lunar", "selene", "artemisa"],
        "sol": ["sol", "solar"],
        "mitologia": ["mitologia", "dioses", "diosa", "arquetipo"],
        "bestiario": ["bestiario", "grifo", "fenix", "salamandra", "unicornio", "dragon"],
        "imagen": ["imagen", "visual", "grabado", "manuscrito", "ilustracion"],
        "marca": ["marca", "identidad", "logo", "tagline"],
        "curso": ["curso", "clase", "certificacion", "material adicional"],
        "bibliografia": ["bibliografia", "references", "bibliography"],
        "tesis": ["tesis", "thesis", "phd"],
        "ensayo": ["ensayo", "dossier", "texto"],
        "editorial": ["editorial", "coleccion", "cabinet", "wonders"],
    }

    tags = []

    for tag, keywords in tag_rules.items():
        for keyword in keywords:
            if keyword in normalized:
                tags.append(tag)
                break

    return ", ".join(sorted(set(tags)))


def classify_file(filename: str, text: str) -> tuple[str, int, str]:
    extension = Path(filename).suffix.lower()

    normalized_name = normalize(filename)
    normalized_text = normalize(text[:6000])
    searchable = f"{normalized_name} {normalized_text}"

    scores = {category: 0 for category in CATEGORIES}
    reasons = {category: [] for category in CATEGORIES}

    if extension in IMAGE_EXTENSIONS:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 20
        reasons["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(
            f"archivo visual {extension}"
        )

    if extension in DESIGN_EXTENSIONS:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 18
        reasons["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(
            f"archivo de diseño {extension}"
        )

    if extension == ".pdf":
        academic_terms = [
            "abstract", "thesis", "phd", "university",
            "bibliography", "references", "table of contents", "submitted",
        ]
        if any(term in searchable for term in academic_terms):
            scores["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"] += 12
            reasons["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"].append(
                "estructura de tesis/paper/libro académico"
            )

    for category, keywords in RULES.items():
        for keyword in keywords:
            keyword_normalized = normalize(keyword)

            if keyword_normalized in normalized_name:
                scores[category] += 6
                reasons[category].append(f"nombre contiene '{keyword}'")

            elif keyword_normalized in normalized_text:
                scores[category] += 3
                reasons[category].append(f"contenido contiene '{keyword}'")

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score == 0:
        return (
            "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES",
            0,
            "sin coincidencias fuertes; revisar manualmente",
        )

    return best_category, best_score, "; ".join(reasons[best_category][:4])


def file_icon(extension: str) -> str:
    if extension in IMAGE_EXTENSIONS:
        return "🖼️"
    if extension == ".pdf":
        return "📕"
    if extension == ".docx":
        return "📄"
    if extension in [".txt", ".md"]:
        return "📝"
    if extension in DESIGN_EXTENSIONS:
        return "🎨"
    return "📎"


def add_files_to_session(uploaded_files) -> None:
    existing_names = {item["archivo"] for item in st.session_state["files"]}

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name

        if filename in existing_names:
            continue

        file_bytes = uploaded_file.getvalue()
        extension = Path(filename).suffix.lower()
        text = extract_text(filename, file_bytes)
        category, score, reason = classify_file(filename, text)
        tags = detect_tags(f"{filename} {text[:4000]}")

        st.session_state["files"].append(
            {
                "archivo": filename,
                "extension": extension,
                "tamano_kb": round(len(file_bytes) / 1024, 2),
                "palabras_extraidas": word_count(text),
                "categoria_sugerida": category,
                "categoria_final": category,
                "score": score,
                "tags": tags,
                "motivo": reason,
                "preview": text[:900].replace("\n", " ").strip(),
                "bytes": file_bytes,
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )


def files_to_dataframe() -> pd.DataFrame:
    rows = []

    for item in st.session_state["files"]:
        rows.append(
            {
                "archivo": item["archivo"],
                "extension": item["extension"],
                "tamano_kb": item["tamano_kb"],
                "palabras_extraidas": item["palabras_extraidas"],
                "categoria_sugerida": item["categoria_sugerida"],
                "categoria_final": item["categoria_final"],
                "score": item["score"],
                "tags": item["tags"],
                "motivo": item["motivo"],
                "preview": item["preview"],
                "uploaded_at": item["uploaded_at"],
            }
        )

    return pd.DataFrame(rows)


def apply_category_edits(edited_df: pd.DataFrame) -> None:
    category_by_file = dict(zip(edited_df["archivo"], edited_df["categoria_final"]))

    for item in st.session_state["files"]:
        filename = item["archivo"]
        if filename in category_by_file:
            item["categoria_final"] = category_by_file[filename]


def generate_structure_text() -> str:
    lines = []
    lines.append("CASA MATRIZ - ESTRUCTURA PROPUESTA")
    lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for category in CATEGORIES:
        lines.append(f"{category}/")
        items = [
            item for item in st.session_state["files"]
            if item["categoria_final"] == category
        ]

        if not items:
            lines.append("  [sin archivos]")
        else:
            for item in items:
                lines.append(f"  - {item['archivo']}")

        lines.append("")

    return "\n".join(lines)


def build_zip() -> bytes:
    zip_buffer = io.BytesIO()

    df = files_to_dataframe()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        zip_file.writestr("inventario_casa_matriz.csv", csv_data)

        structure_text = generate_structure_text()
        zip_file.writestr(
            "estructura_propuesta_casa_matriz.txt",
            structure_text.encode("utf-8"),
        )

        for item in st.session_state["files"]:
            category = item["categoria_final"]
            filename = clean_filename(item["archivo"])
            zip_path = f"{category}/{filename}"
            zip_file.writestr(zip_path, item["bytes"])

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def remove_file(filename: str) -> None:
    st.session_state["files"] = [
        item for item in st.session_state["files"]
        if item["archivo"] != filename
    ]


def clear_all_files() -> None:
    st.session_state["files"] = []


# ============================================================
# SESSION STATE
# ============================================================

if "files" not in st.session_state:
    st.session_state["files"] = []


# ============================================================
# UI
# ============================================================

st.title("🗂️ Casa Matriz | Archivo organizado")

st.write(
    "Subí archivos y la app los va ubicando automáticamente en sus secciones. "
    "Podés corregir la categoría final y descargar el archivo organizado."
)

with st.sidebar:
    st.header("Secciones")

    for category in CATEGORIES:
        st.markdown(f"**{CATEGORY_LABELS[category]}**")
        st.caption(CATEGORY_DESCRIPTIONS[category])

    st.divider()

    if st.button("Vaciar archivos cargados"):
        clear_all_files()
        st.rerun()

uploaded_files = st.file_uploader(
    "Subir archivos",
    accept_multiple_files=True,
    type=[
        "docx", "pdf", "txt", "md", "odt",
        "jpg", "jpeg", "png", "webp", "gif", "tif", "tiff", "jp2",
        "ai", "psd", "indd",
    ],
)

if uploaded_files:
    add_files_to_session(uploaded_files)
    st.success(f"Archivos cargados en esta sesión: {len(st.session_state['files'])}")

if not st.session_state["files"]:
    st.info("Todavía no hay archivos cargados.")
    st.stop()


# ============================================================
# RESUMEN
# ============================================================

st.subheader("Resumen general")

summary_cols = st.columns(len(CATEGORIES))

for index, category in enumerate(CATEGORIES):
    count = sum(
        1 for item in st.session_state["files"]
        if item["categoria_final"] == category
    )
    summary_cols[index].metric(CATEGORY_LABELS[category], count)

st.divider()


# ============================================================
# EDICIÓN GLOBAL
# ============================================================

st.subheader("Revisión y corrección")

df = files_to_dataframe()

edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "categoria_final": st.column_config.SelectboxColumn(
            "Categoría final",
            options=CATEGORIES,
            required=True,
        ),
        "preview": st.column_config.TextColumn("Preview", width="large"),
    },
    disabled=[
        "archivo",
        "extension",
        "tamano_kb",
        "palabras_extraidas",
        "categoria_sugerida",
        "score",
        "tags",
        "motivo",
        "preview",
        "uploaded_at",
    ],
)

apply_category_edits(edited_df)

st.divider()


# ============================================================
# SITIO ORGANIZADO POR CATEGORÍAS
# ============================================================

st.subheader("Archivo organizado por secciones")

for category in CATEGORIES:
    items = [
        item for item in st.session_state["files"]
        if item["categoria_final"] == category
    ]

    st.markdown(f"## {CATEGORY_LABELS[category]}")
    st.caption(CATEGORY_DESCRIPTIONS[category])

    if not items:
        st.info("Sin archivos en esta sección.")
        st.divider()
        continue

    cols = st.columns(3)

    for index, item in enumerate(items):
        col = cols[index % 3]

        with col:
            icon = file_icon(item["extension"])

            with st.container(border=True):
                st.markdown(f"### {icon} {item['archivo']}")
                st.caption(
                    f"{item['extension']} · {item['tamano_kb']} KB · "
                    f"{item['palabras_extraidas']} palabras"
                )

                if item["tags"]:
                    st.markdown(f"**Tags:** `{item['tags']}`")

                st.markdown(f"**Motivo:** {item['motivo']}")

                if item["preview"] and not item["preview"].startswith("[IMAGEN]"):
                    with st.expander("Preview"):
                        st.write(item["preview"])

                st.download_button(
                    "Descargar archivo",
                    data=item["bytes"],
                    file_name=item["archivo"],
                    key=f"download_{category}_{index}_{item['archivo']}",
                )

                if st.button(
                    "Quitar",
                    key=f"remove_{category}_{index}_{item['archivo']}",
                ):
                    remove_file(item["archivo"])
                    st.rerun()

    st.divider()


# ============================================================
# EXPORTACIÓN
# ============================================================

st.subheader("Exportar archivo organizado")

final_df = files_to_dataframe()

csv_bytes = final_df.to_csv(index=False).encode("utf-8-sig")
structure_text = generate_structure_text()
zip_bytes = build_zip()

export_cols = st.columns(3)

with export_cols[0]:
    st.download_button(
        "Descargar inventario CSV",
        data=csv_bytes,
        file_name="inventario_casa_matriz.csv",
        mime="text/csv",
    )

with export_cols[1]:
    st.download_button(
        "Descargar estructura TXT",
        data=structure_text.encode("utf-8"),
        file_name="estructura_propuesta_casa_matriz.txt",
        mime="text/plain",
    )

with export_cols[2]:
    st.download_button(
        "Descargar ZIP organizado",
        data=zip_bytes,
        file_name="casa_matriz_organizado.zip",
        mime="application/zip",
    )

with st.expander("Ver estructura propuesta"):
    st.code(structure_text, language="text")
