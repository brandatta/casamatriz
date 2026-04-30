import os
import re
import io
import zipfile
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from docx import Document


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Organizador Casa Matriz",
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

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".tif", ".jp2"}
DOC_EXTENSIONS = {".docx", ".pdf", ".txt", ".md"}
OTHER_EXTENSIONS = {".ai", ".psd", ".indd", ".zip"}


CATEGORY_RULES = {
    "01_IDENTIDAD_MARCA_Y_ESTRATEGIA": {
        "keywords": [
            "casa matriz",
            "proyecto integral",
            "manifiesto",
            "fundamentos",
            "marca",
            "identidad",
            "estrategia",
            "nombres",
            "tagline",
            "landing",
            "web",
            "estructura",
            "talleres",
            "publicaciones",
            "matrices",
            "mediatrices",
            "editable marcas",
        ],
        "weight": 5,
    },
    "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES": {
        "keywords": [
            "ensayo",
            "cosmos",
            "core",
            "pliegues",
            "habitar",
            "venus",
            "buena astróloga",
            "ideas",
            "otros títulos",
            "varios",
            "adorno",
            "foucault",
            "hermeneutica",
            "mujeres",
            "giro copernicano",
            "criptozoología",
            "fragmento",
            "borrador",
            "dossier",
            "cuerpo",
            "metamorfosis",
            "oscuridad",
            "sirenas",
            "luna",
            "imagen",
        ],
        "weight": 4,
    },
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO": {
        "keywords": [
            "curso",
            "formación",
            "formacion",
            "certificación",
            "certificacion",
            "luminarias",
            "sol y luna",
            "intro curso",
            "preview",
            "material adicional",
            "seminario",
            "volver a la luna",
            "transcripcion",
            "transcripción",
            "horoscoño",
            "ernesto castro",
            "arquetipo",
            "lunar",
            "solar",
            "astrología",
            "astrologia",
            "carta natal",
            "zodiaco",
            "venus",
            "tauro",
            "libra",
        ],
        "weight": 4,
    },
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES": {
        "keywords": [
            "bibliografia",
            "bibliografía",
            "tesis",
            "thesis",
            "phd",
            "startup",
            "phillipson",
            "clynes",
            "von stuckrad",
            "astrology and truth",
            "internet on modern western astrology",
            "historia",
            "foucault",
            "borges",
            "seres imaginarios",
            "libro de los seres",
            "fuente",
            "paper",
            "research",
            "epistemology",
            "epistemología",
            "bibliography",
            "references",
        ],
        "weight": 5,
    },
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS": {
        "keywords": [
            "cabinet",
            "wonders",
            "collection",
            "colección ilustrada",
            "coleccion ilustrada",
            "links",
            "rawpixel",
            "dragon",
            "dragón",
            "utagawa",
            "kuniyoshi",
            "imagen",
            "visual",
            "referencia",
            "archivo visual",
            "public domain",
            "wellcome",
            "british library",
            "library of congress",
            "munch",
            "grabado",
            "manuscrito",
            "sketchbook",
            "stephan scriber",
            "ai",
            "jpg",
            "jpeg",
            "png",
            "jp2",
        ],
        "weight": 5,
    },
}


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value: str) -> str:
    if not value:
        return ""
    value = value.lower()
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def safe_filename(filename: str) -> str:
    """
    Sanitiza nombres para evitar problemas en filesystem.
    Mantiene bastante legibilidad.
    """
    name = filename.strip()
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    name = re.sub(r"\s+", " ", name)
    return name[:180]


def extract_text_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        # También intenta leer tablas
        table_texts = []
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    table_texts.append(" | ".join(cells))

        return "\n".join(paragraphs + table_texts).strip()
    except Exception as e:
        return f"[ERROR_DOCX] {e}"


def extract_text_pdf(file_bytes: bytes, max_pages: int = 20) -> str:
    """
    Extrae texto de PDFs. Limita páginas para MVP y performance.
    """
    try:
        text_parts = []
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        pages_to_read = min(len(pdf), max_pages)

        for page_index in range(pages_to_read):
            page = pdf[page_index]
            text = page.get_text("text")
            if text.strip():
                text_parts.append(text)

        pdf.close()
        return "\n".join(text_parts).strip()
    except Exception as e:
        return f"[ERROR_PDF] {e}"


def extract_text_plain(file_bytes: bytes) -> str:
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return file_bytes.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return "[ERROR_TEXT] No se pudo decodificar el archivo de texto."


def extract_text(filename: str, file_bytes: bytes) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".docx":
        return extract_text_docx(file_bytes)

    if ext == ".pdf":
        return extract_text_pdf(file_bytes)

    if ext in [".txt", ".md"]:
        return extract_text_plain(file_bytes)

    if ext in IMAGE_EXTENSIONS:
        return "[IMAGE_FILE] Archivo visual sin extracción de texto."

    if ext == ".ai":
        return "[DESIGN_FILE] Archivo Adobe Illustrator / marca / diseño."

    return "[UNSUPPORTED] Tipo de archivo no soportado para extracción de texto."


def count_words(text: str) -> int:
    if not text or text.startswith("["):
        return 0
    return len(re.findall(r"\b\w+\b", text))


def score_category(filename: str, text: str, ext: str) -> tuple[str, int, str, list[str]]:
    """
    Clasificador simple por reglas.
    Devuelve:
    - categoría sugerida
    - score
    - motivo
    - tags detectados
    """

    searchable_name = normalize_text(filename)
    searchable_text = normalize_text(text[:8000])
    combined = f"{searchable_name} {searchable_text}"

    scores = {cat: 0 for cat in CATEGORIES}
    hits = {cat: [] for cat in CATEGORIES}

    # Regla fuerte por tipo de archivo visual
    if ext in IMAGE_EXTENSIONS:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 12
        hits["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(f"extensión visual {ext}")

    if ext in {".ai", ".psd", ".indd"}:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 10
        hits["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(f"archivo de diseño {ext}")

    # Regla fuerte por PDFs académicos
    if ext == ".pdf":
        pdf_source_terms = [
            "thesis",
            "phd",
            "bibliography",
            "abstract",
            "university",
            "submitted",
            "references",
            "table of contents",
        ]
        if any(term in searchable_text for term in pdf_source_terms):
            scores["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"] += 8
            hits["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"].append("estructura de tesis/paper/pdf académico")

    # Keywords por categoría
    for category, config in CATEGORY_RULES.items():
        weight = config["weight"]
        for kw in config["keywords"]:
            kw_norm = normalize_text(kw)
            if kw_norm and kw_norm in combined:
                # Más peso si aparece en nombre de archivo
                if kw_norm in searchable_name:
                    scores[category] += weight * 2
                    hits[category].append(f"nombre contiene '{kw}'")
                else:
                    scores[category] += weight
                    hits[category].append(f"contenido contiene '{kw}'")

    # Ajustes específicos
    if "seminario" in searchable_name and "luna" in searchable_name:
        scores["03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO"] += 8
        hits["03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO"].append("seminario lunar")

    if "cabinet" in searchable_name or "wonders" in searchable_name:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 8
        hits["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append("proyecto editorial visual")

    if "proyecto integral" in searchable_name or "fundamentos" in searchable_name:
        scores["01_IDENTIDAD_MARCA_Y_ESTRATEGIA"] += 10
        hits["01_IDENTIDAD_MARCA_Y_ESTRATEGIA"].append("documento estratégico/fundacional")

    # Selección final
    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score == 0:
        best_category = "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES"
        reason = "No hubo coincidencias fuertes; se clasifica provisoriamente como borrador/obra autoral."
        detected_tags = []
    else:
        reason = "; ".join(hits[best_category][:5])
        detected_tags = extract_tags(combined)

    return best_category, best_score, reason, detected_tags


def extract_tags(combined_text: str) -> list[str]:
    tag_map = {
        "astrologia": ["astrología", "astrologia", "zodiaco", "carta natal", "horóscopo", "horoscopo"],
        "cine": ["cine", "película", "pelicula", "pantalla", "fotograma", "kubrick"],
        "luna": ["luna", "lunar", "selene", "artemisa", "hecate"],
        "sol": ["sol", "solar"],
        "mitologia": ["mitología", "mitologia", "dioses", "diosa", "arquetipo"],
        "bestiario": ["bestiario", "grifo", "fénix", "fenix", "salamandra", "unicornio", "dragón", "dragon"],
        "imagen": ["imagen", "visual", "grabado", "manuscrito", "ilustración", "ilustracion"],
        "marca": ["marca", "identidad", "logo", "tagline"],
        "curso": ["curso", "clase", "certificación", "certificacion", "material adicional"],
        "bibliografia": ["bibliografía", "bibliografia", "references", "bibliography"],
        "tesis": ["tesis", "thesis", "phd", "submitted"],
        "ensayo": ["ensayo", "dossier", "texto"],
        "editorial": ["editorial", "colección", "coleccion", "cabinet", "wonders"],
    }

    tags = []
    for tag, terms in tag_map.items():
        for term in terms:
            if normalize_text(term) in combined_text:
                tags.append(tag)
                break

    return sorted(set(tags))


def create_inventory(uploaded_files) -> pd.DataFrame:
    rows = []

    for file in uploaded_files:
        filename = file.name
        ext = Path(filename).suffix.lower()
        file_bytes = file.getvalue()
        size_kb = round(len(file_bytes) / 1024, 2)

        text = extract_text(filename, file_bytes)
        words = count_words(text)

        suggested_category, score, reason, tags = score_category(
            filename=filename,
            text=text,
            ext=ext,
        )

        preview = text[:1000].replace("\n", " ").strip()

        rows.append(
            {
                "archivo": filename,
                "extension": ext,
                "tamano_kb": size_kb,
                "palabras_extraidas": words,
                "categoria_sugerida": suggested_category,
                "categoria_final": suggested_category,
                "score": score,
                "tags": ", ".join(tags),
                "motivo": reason,
                "preview_texto": preview,
            }
        )

    return pd.DataFrame(rows)


def build_zip_from_inventory(uploaded_files, inventory_df: pd.DataFrame) -> bytes:
    """
    Crea ZIP con carpetas por categoria_final y copia los archivos.
    """
    file_map = {file.name: file.getvalue() for file in uploaded_files}

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Agrega inventario CSV dentro del zip
        csv_bytes = inventory_df.to_csv(index=False).encode("utf-8-sig")
        zipf.writestr("inventario_casa_matriz.csv", csv_bytes)

        # Agrega estructura TXT
        structure_txt = generate_structure_txt(inventory_df)
        zipf.writestr("estructura_propuesta.txt", structure_txt.encode("utf-8"))

        # Agrega archivos clasificados
        for _, row in inventory_df.iterrows():
            filename = row["archivo"]
            category = row["categoria_final"]
            safe_name = safe_filename(filename)

            if filename in file_map:
                zip_path = f"{category}/{safe_name}"
                zipf.writestr(zip_path, file_map[filename])

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def generate_structure_txt(inventory_df: pd.DataFrame) -> str:
    lines = []
    lines.append("CASA MATRIZ - ESTRUCTURA PROPUESTA")
    lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for category in CATEGORIES:
        lines.append(f"{category}/")
        subset = inventory_df[inventory_df["categoria_final"] == category]
        for _, row in subset.iterrows():
            lines.append(f"  - {row['archivo']}")
        lines.append("")

    return "\n".join(lines)


def make_csv_download(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# ============================================================
# UI
# ============================================================

st.title("🗂️ Organizador Casa Matriz")
st.caption("MVP para clasificar documentos, bibliografía, cursos, obra autoral y archivo visual.")

with st.sidebar:
    st.header("Categorías")
    for category in CATEGORIES:
        st.markdown(f"- `{category}`")

    st.divider()

    st.markdown(
        """
        **Flujo sugerido**
        1. Subir archivos  
        2. Generar inventario  
        3. Revisar categorías  
        4. Exportar CSV o ZIP organizado  
        """
    )

uploaded_files = st.file_uploader(
    "Subí archivos para clasificar",
    accept_multiple_files=True,
    type=[
        "docx",
        "pdf",
        "txt",
        "md",
        "jpg",
        "jpeg",
        "png",
        "webp",
        "gif",
        "tiff",
        "tif",
        "jp2",
        "ai",
    ],
)

if not uploaded_files:
    st.info("Subí uno o varios archivos para empezar.")
    st.stop()

st.success(f"Archivos cargados: {len(uploaded_files)}")

if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = None

col_a, col_b = st.columns([1, 3])

with col_a:
    if st.button("Generar inventario", type="primary"):
        with st.spinner("Leyendo archivos y clasificando..."):
            st.session_state.inventory_df = create_inventory(uploaded_files)

with col_b:
    st.markdown(
        "La clasificación es automática por reglas. Después podés corregir la columna `categoria_final`."
    )

if st.session_state.inventory_df is None:
    st.stop()

df = st.session_state.inventory_df.copy()

# Métricas
st.subheader("Resumen")

summary = (
    df.groupby("categoria_final")
    .size()
    .reset_index(name="cantidad")
    .sort_values("categoria_final")
)

metric_cols = st.columns(len(CATEGORIES))
for idx, category in enumerate(CATEGORIES):
    count = int(summary.loc[summary["categoria_final"] == category, "cantidad"].sum())
    metric_cols[idx].metric(category.replace("_", " "), count)

st.divider()

# Tabla editable
st.subheader("Revisión manual")

edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "categoria_final": st.column_config.SelectboxColumn(
            "categoria_final",
            options=CATEGORIES,
            required=True,
        ),
        "preview_texto": st.column_config.TextColumn(
            "preview_texto",
            width="large",
        ),
        "motivo": st.column_config.TextColumn(
            "motivo",
            width="medium",
        ),
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
        "preview_texto",
    ],
)

st.session_state.inventory_df = edited_df

st.divider()

# Filtros y preview
st.subheader("Explorar por categoría")

selected_category = st.selectbox(
    "Filtrar categoría",
    ["Todas"] + CATEGORIES,
)

if selected_category == "Todas":
    filtered_df = edited_df
else:
    filtered_df = edited_df[edited_df["categoria_final"] == selected_category]

st.dataframe(
    filtered_df[
        [
            "archivo",
            "extension",
            "categoria_sugerida",
            "categoria_final",
            "tags",
            "motivo",
        ]
    ],
    use_container_width=True,
)

st.divider()

# Exportaciones
st.subheader("Exportar")

csv_bytes = make_csv_download(edited_df)
st.download_button(
    label="Descargar inventario CSV",
    data=csv_bytes,
    file_name="inventario_casa_matriz.csv",
    mime="text/csv",
)

structure_txt = generate_structure_txt(edited_df)
st.download_button(
    label="Descargar estructura TXT",
    data=structure_txt.encode("utf-8"),
    file_name="estructura_propuesta_casa_matriz.txt",
    mime="text/plain",
)

zip_bytes = build_zip_from_inventory(uploaded_files, edited_df)
st.download_button(
    label="Descargar ZIP organizado",
    data=zip_bytes,
    file_name="casa_matriz_organizado.zip",
    mime="application/zip",
)

st.divider()

with st.expander("Ver estructura propuesta"):
    st.code(structure_txt, language="text")
