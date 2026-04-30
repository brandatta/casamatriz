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
# CONFIGURACIÓN GENERAL
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

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".jp2"
}

DESIGN_EXTENSIONS = {
    ".ai", ".psd", ".indd"
}


# ============================================================
# REGLAS DE CLASIFICACIÓN
# ============================================================

RULES = {
    "01_IDENTIDAD_MARCA_Y_ESTRATEGIA": [
        "casa matriz",
        "proyecto integral",
        "manifiesto",
        "fundamentos",
        "marca",
        "identidad",
        "estrategia",
        "nombres",
        "tagline",
        "estructura",
        "talleres",
        "publicaciones",
        "matrices",
        "mediatrices",
        "editable marcas",
        "landing",
        "web",
    ],
    "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES": [
        "ensayo",
        "cosmos",
        "core",
        "pliegues",
        "habitar",
        "venus",
        "buena astróloga",
        "buena astrologa",
        "ideas",
        "otros títulos",
        "otros titulos",
        "varios",
        "adorno",
        "foucault",
        "hermenéutica",
        "hermeneutica",
        "mujeres",
        "giro copernicano",
        "fragmento",
        "borrador",
        "dossier",
        "cuerpo",
        "metamorfosis",
        "oscuridad",
        "sirenas",
        "criptozoologia",
        "criptozoología",
    ],
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO": [
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
        "horoscono",
        "ernesto castro",
        "arquetipo",
        "lunar",
        "solar",
        "astrología",
        "astrologia",
        "carta natal",
        "zodiaco",
        "tauro",
        "libra",
        "luna astrológica",
        "luna astrologica",
    ],
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES": [
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
        "borges",
        "seres imaginarios",
        "libro de los seres",
        "fuente",
        "paper",
        "research",
        "epistemology",
        "epistemología",
        "references",
        "bibliography",
        "university",
        "submitted",
        "abstract",
        "table of contents",
    ],
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS": [
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
        "grabado",
        "manuscrito",
        "sketchbook",
        "stephan scriber",
        "ilustrada",
        "ilustrado",
        "editorial",
        "wunderkammer",
        "kunstkammer",
    ],
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def normalize(value: str) -> str:
    if not value:
        return ""

    value = value.lower()
    value = value.replace("_", " ")
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
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
                row_text = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        row_text.append(cell_text)
                if row_text:
                    parts.append(" | ".join(row_text))

        return "\n".join(parts)

    except Exception as error:
        return f"[ERROR_DOCX] {error}"


def extract_pdf(file_bytes: bytes, max_pages: int = 15) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts = []

        total_pages = min(len(reader.pages), max_pages)

        for index in range(total_pages):
            page = reader.pages[index]
            text = page.extract_text() or ""
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

    # Reglas fuertes por extensión
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

    # Reglas fuertes por PDF académico / fuente
    if extension == ".pdf":
        academic_terms = [
            "abstract",
            "thesis",
            "phd",
            "university",
            "bibliography",
            "references",
            "table of contents",
            "submitted",
        ]
        if any(term in searchable for term in academic_terms):
            scores["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"] += 12
            reasons["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"].append(
                "estructura de tesis/paper/libro académico"
            )

    # Reglas por keywords
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
        best_category = "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES"
        reason = "sin coincidencias fuertes; revisar manualmente"
    else:
        reason_items = reasons[best_category][:4]
        reason = "; ".join(reason_items)

    return best_category, best_score, reason


def build_inventory(uploaded_files) -> pd.DataFrame:
    rows = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        extension = Path(filename).suffix.lower()
        file_bytes = uploaded_file.getvalue()

        text = extract_text(filename, file_bytes)

        category, score, reason = classify_file(filename, text)

        combined_for_tags = f"{filename} {text[:4000]}"
        tags = detect_tags(combined_for_tags)

        rows.append(
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
            }
        )

    return pd.DataFrame(rows)


def generate_structure_text(df: pd.DataFrame) -> str:
    lines = []
    lines.append("CASA MATRIZ - ESTRUCTURA PROPUESTA")
    lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for category in CATEGORIES:
        lines.append(f"{category}/")
        subset = df[df["categoria_final"] == category]

        if subset.empty:
            lines.append("  [sin archivos]")
        else:
            for _, row in subset.iterrows():
                lines.append(f"  - {row['archivo']}")

        lines.append("")

    return "\n".join(lines)


def build_zip(uploaded_files, df: pd.DataFrame) -> bytes:
    zip_buffer = io.BytesIO()
    file_bytes_by_name = {
        uploaded_file.name: uploaded_file.getvalue()
        for uploaded_file in uploaded_files
    }

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Inventario
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        zip_file.writestr("inventario_casa_matriz.csv", csv_data)

        # Estructura
        structure_text = generate_structure_text(df)
        zip_file.writestr(
            "estructura_propuesta_casa_matriz.txt",
            structure_text.encode("utf-8")
        )

        # Archivos
        for _, row in df.iterrows():
            filename = row["archivo"]
            category = row["categoria_final"]
            safe_name = clean_filename(filename)

            file_bytes = file_bytes_by_name.get(filename)

            if file_bytes is not None:
                zip_path = f"{category}/{safe_name}"
                zip_file.writestr(zip_path, file_bytes)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


# ============================================================
# UI
# ============================================================

st.title("🗂️ Organizador Casa Matriz")

st.write(
    "Clasificador simple para documentos, PDFs, imágenes y referencias editoriales. "
    "La app sugiere una categoría, permite corregirla manualmente y genera un ZIP organizado."
)

with st.sidebar:
    st.header("Categorías")

    for category in CATEGORIES:
        st.write(f"• {category}")

    st.divider()

    st.caption(
        "Versión liviana para Streamlit Cloud. "
        "Usa reglas locales, sin API externa y sin PyMuPDF."
    )

uploaded_files = st.file_uploader(
    "Subí archivos para clasificar",
    accept_multiple_files=True,
    type=[
        "docx",
        "pdf",
        "txt",
        "md",
        "odt",
        "jpg",
        "jpeg",
        "png",
        "webp",
        "gif",
        "tif",
        "tiff",
        "jp2",
        "ai",
        "psd",
        "indd",
    ],
)

if not uploaded_files:
    st.info("Subí uno o varios archivos para comenzar.")
    st.stop()

st.success(f"Archivos cargados: {len(uploaded_files)}")

if "inventory" not in st.session_state:
    st.session_state["inventory"] = None

if st.button("Generar inventario", type="primary"):
    with st.spinner("Leyendo y clasificando archivos..."):
        st.session_state["inventory"] = build_inventory(uploaded_files)

if st.session_state["inventory"] is None:
    st.stop()

df = st.session_state["inventory"]

# ============================================================
# RESUMEN
# ============================================================

st.subheader("Resumen")

cols = st.columns(len(CATEGORIES))

for index, category in enumerate(CATEGORIES):
    count = int((df["categoria_final"] == category).sum())
    cols[index].metric(category.replace("_", " "), count)

st.divider()


# ============================================================
# REVISIÓN MANUAL
# ============================================================

st.subheader("Revisión manual")

st.caption(
    "Podés modificar la columna `Categoría final`. "
    "El ZIP se arma usando esa categoría final, no la sugerida."
)

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
        "preview": st.column_config.TextColumn(
            "Preview",
            width="large",
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
        "preview",
    ],
)

st.session_state["inventory"] = edited_df

st.divider()


# ============================================================
# VISTA POR SECCIONES
# ============================================================

st.subheader("Archivos organizados por sección")

st.caption(
    "Esta es la vista final por categoría. "
    "Si cambiás una categoría arriba, se refleja acá."
)

for category in CATEGORIES:
    category_df = edited_df[edited_df["categoria_final"] == category]

    with st.expander(f"{category} ({len(category_df)} archivos)", expanded=True):
        if category_df.empty:
            st.caption("Sin archivos en esta sección.")
        else:
            for _, row in category_df.iterrows():
                tags_display = row["tags"] if row["tags"] else "sin tags"
                st.markdown(
                    f"""
**📄 {row['archivo']}**

Extensión: `{row['extension']}` · Tamaño: `{row['tamano_kb']} KB` · Score: `{row['score']}`  
Tags: `{tags_display}`  
Motivo: {row['motivo']}
"""
                )
                st.divider()

st.divider()


# ============================================================
# FILTRO
# ============================================================

st.subheader("Filtrar resultado")

selected_category = st.selectbox(
    "Categoría",
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
            "score",
            "tags",
            "motivo",
        ]
    ],
    use_container_width=True,
)

st.divider()


# ============================================================
# EXPORTACIÓN
# ============================================================

st.subheader("Exportar")

csv_bytes = edited_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Descargar inventario CSV",
    data=csv_bytes,
    file_name="inventario_casa_matriz.csv",
    mime="text/csv",
)

structure_text = generate_structure_text(edited_df)

st.download_button(
    "Descargar estructura TXT",
    data=structure_text.encode("utf-8"),
    file_name="estructura_propuesta_casa_matriz.txt",
    mime="text/plain",
)

zip_bytes = build_zip(uploaded_files, edited_df)

st.download_button(
    "Descargar ZIP organizado",
    data=zip_bytes,
    file_name="casa_matriz_organizado.zip",
    mime="application/zip",
)

with st.expander("Ver estructura propuesta"):
    st.code(structure_text, language="text")
