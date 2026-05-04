import base64
import io
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from docx import Document
from pypdf import PdfReader


# ============================================================
# CONFIG
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

NAV_ITEMS = {
    "🏠 Inicio / Subir archivos": "home",
    "📁 Identidad, marca y estrategia": "01_IDENTIDAD_MARCA_Y_ESTRATEGIA",
    "📁 Obra autoral, ensayos y borradores": "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES",
    "📁 Cursos, formación y archivo astrológico": "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO",
    "📁 Bibliografía, investigación y fuentes": "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES",
    "📁 Archivo visual, editorial y referencias": "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS",
    "📋 Inventario general": "inventory",
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
        "buena astrologa", "ideas", "otros titulos", "varios",
        "adorno", "foucault", "hermeneutica", "mujeres",
        "giro copernicano", "fragmento", "borrador", "dossier",
        "cuerpo", "metamorfosis", "oscuridad", "sirenas",
        "criptozoologia",
    ],
    "03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO": [
        "curso", "formacion", "certificacion", "luminarias",
        "sol y luna", "intro curso", "preview", "material adicional",
        "seminario", "volver a la luna", "transcripcion", "horoscono",
        "ernesto castro", "arquetipo", "lunar", "solar",
        "astrologia", "carta natal", "zodiaco", "tauro", "libra",
        "luna astrologica",
    ],
    "04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES": [
        "bibliografia", "tesis", "thesis", "phd", "startup",
        "phillipson", "clynes", "von stuckrad", "astrology and truth",
        "internet on modern western astrology", "historia", "borges",
        "seres imaginarios", "libro de los seres", "fuente", "paper",
        "research", "epistemology", "references", "bibliography",
        "university", "submitted", "abstract", "table of contents",
    ],
    "05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS": [
        "cabinet", "wonders", "collection", "coleccion ilustrada",
        "links", "rawpixel", "dragon", "utagawa", "kuniyoshi",
        "imagen", "visual", "referencia", "archivo visual",
        "public domain", "wellcome", "british library",
        "library of congress", "grabado", "manuscrito", "sketchbook",
        "stephan scriber", "ilustrada", "ilustrado", "editorial",
        "wunderkammer", "kunstkammer",
    ],
}


# ============================================================
# GITHUB CONFIG
# ============================================================

def get_github_config():
    token = st.secrets.get("GITHUB_TOKEN", "")
    repo = st.secrets.get("GITHUB_REPO", "")
    branch = st.secrets.get("GITHUB_BRANCH", "main")

    if not token or not repo:
        st.error(
            "Faltan secrets de GitHub. Configurá GITHUB_TOKEN, GITHUB_REPO y GITHUB_BRANCH en Streamlit Cloud."
        )
        st.stop()

    return token, repo, branch


def github_headers():
    token, _, _ = get_github_config()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_api_url(path: str) -> str:
    _, repo, _ = get_github_config()
    encoded_path = quote(path)
    return f"https://api.github.com/repos/{repo}/contents/{encoded_path}"


def github_get_file(path: str):
    _, _, branch = get_github_config()

    response = requests.get(
        github_api_url(path),
        headers=github_headers(),
        params={"ref": branch},
        timeout=30,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def github_list_dir(path: str):
    _, _, branch = get_github_config()

    response = requests.get(
        github_api_url(path),
        headers=github_headers(),
        params={"ref": branch},
        timeout=30,
    )

    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()

    if isinstance(data, list):
        return data

    return []


def github_put_file(path: str, file_bytes: bytes, message: str):
    _, _, branch = get_github_config()

    existing = github_get_file(path)

    payload = {
        "message": message,
        "content": base64.b64encode(file_bytes).decode("utf-8"),
        "branch": branch,
    }

    if existing and existing.get("sha"):
        payload["sha"] = existing["sha"]

    response = requests.put(
        github_api_url(path),
        headers=github_headers(),
        json=payload,
        timeout=60,
    )

    response.raise_for_status()
    return response.json()


def github_delete_file(path: str, message: str):
    _, _, branch = get_github_config()

    existing = github_get_file(path)

    if not existing:
        return None

    payload = {
        "message": message,
        "sha": existing["sha"],
        "branch": branch,
    }

    response = requests.delete(
        github_api_url(path),
        headers=github_headers(),
        json=payload,
        timeout=60,
    )

    response.raise_for_status()
    return response.json()


def github_download_file(path: str) -> bytes:
    data = github_get_file(path)

    if not data:
        raise FileNotFoundError(path)

    content = data.get("content", "")
    encoding = data.get("encoding", "")

    if encoding == "base64":
        return base64.b64decode(content)

    raise ValueError(f"No se pudo decodificar {path}")


# ============================================================
# TEXT / CLASSIFICATION HELPERS
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


def extract_pdf(file_bytes: bytes, max_pages: int = 10) -> str:
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

    if extension in [".txt", ".md"]:
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


def classify_file(filename: str, text: str):
    extension = Path(filename).suffix.lower()

    normalized_name = normalize(filename)
    normalized_text = normalize(text[:6000])
    searchable = f"{normalized_name} {normalized_text}"

    scores = {category: 0 for category in CATEGORIES}
    reasons = {category: [] for category in CATEGORIES}

    # ------------------------------------------------------------
    # DEFAULTS FUERTES POR EXTENSIÓN
    # ------------------------------------------------------------

    # Imágenes y archivos de diseño: por defecto a archivo visual.
    if extension in IMAGE_EXTENSIONS:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 25
        reasons["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(
            f"archivo visual {extension}"
        )

    if extension in DESIGN_EXTENSIONS:
        scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 25
        reasons["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(
            f"archivo de diseño {extension}"
        )

    # PDFs: por defecto a bibliografía/fuentes.
    # Solo se moverán a otra categoría si hay señales muy claras.
    if extension == ".pdf":
        scores["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"] += 18
        reasons["04_BIBLIOGRAFIA_INVESTIGACION_Y_FUENTES"].append(
            "PDF por defecto clasificado como bibliografía/fuente"
        )

    # ------------------------------------------------------------
    # REGLAS POR KEYWORDS
    # ------------------------------------------------------------

    for category, keywords in RULES.items():
        for keyword in keywords:
            keyword_normalized = normalize(keyword)

            if keyword_normalized in normalized_name:
                # El nombre pesa más que el contenido.
                scores[category] += 8
                reasons[category].append(f"nombre contiene '{keyword}'")

            elif keyword_normalized in normalized_text:
                scores[category] += 3
                reasons[category].append(f"contenido contiene '{keyword}'")

    # ------------------------------------------------------------
    # OVERRIDES MUY OBVIOS PARA PDFs
    # ------------------------------------------------------------
    # Estos casos fuerzan una categoría distinta a bibliografía
    # cuando el nombre del PDF es claramente pedagógico, visual,
    # estratégico o autoral.

    if extension == ".pdf":
        obvious_course_terms = [
            "seminario",
            "curso",
            "certificacion",
            "certificación",
            "material adicional",
            "preview",
            "luminarias",
            "sol y luna",
            "volver a la luna",
            "clase",
        ]

        obvious_visual_terms = [
            "cabinet",
            "wonders",
            "sketchbook",
            "catalogo",
            "catálogo",
            "imagen",
            "visual",
            "ilustrado",
            "ilustrada",
            "manuscrito",
            "dragon",
            "dragón",
            "grabado",
        ]

        obvious_identity_terms = [
            "manifiesto",
            "fundamentos",
            "marca",
            "identidad",
            "proyecto integral",
            "casa matriz",
        ]

        obvious_author_terms = [
            "cosmos",
            "core",
            "pliegues",
            "habitar",
            "venus",
            "buena astrologa",
            "buena astróloga",
            "ensayo",
        ]

        if any(term in normalized_name for term in [normalize(t) for t in obvious_course_terms]):
            scores["03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO"] += 30
            reasons["03_CURSOS_FORMACION_Y_ARCHIVO_ASTROLOGICO"].append(
                "PDF con nombre claramente asociado a curso/formación"
            )

        if any(term in normalized_name for term in [normalize(t) for t in obvious_visual_terms]):
            scores["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"] += 30
            reasons["05_ARCHIVO_VISUAL_EDITORIAL_Y_REFERENCIAS"].append(
                "PDF con nombre claramente asociado a archivo visual/editorial"
            )

        if any(term in normalized_name for term in [normalize(t) for t in obvious_identity_terms]):
            scores["01_IDENTIDAD_MARCA_Y_ESTRATEGIA"] += 30
            reasons["01_IDENTIDAD_MARCA_Y_ESTRATEGIA"].append(
                "PDF con nombre claramente asociado a identidad/marca"
            )

        if any(term in normalized_name for term in [normalize(t) for t in obvious_author_terms]):
            scores["02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES"] += 30
            reasons["02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES"].append(
                "PDF con nombre claramente asociado a obra autoral"
            )

    # ------------------------------------------------------------
    # SELECCIÓN FINAL
    # ------------------------------------------------------------

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score == 0:
        return (
            "02_OBRA_AUTORAL_ENSAYOS_Y_BORRADORES",
            0,
            "sin coincidencias fuertes; revisar manualmente",
        )

    return best_category, best_score, "; ".join(reasons[best_category][:4])

# ============================================================
# INVENTORY
# ============================================================

INVENTORY_PATH = "data/inventory.csv"


def load_inventory() -> pd.DataFrame:
    try:
        file_bytes = github_download_file(INVENTORY_PATH)
        return pd.read_csv(io.BytesIO(file_bytes))
    except Exception:
        return pd.DataFrame(
            columns=[
                "archivo",
                "extension",
                "tamano_kb",
                "categoria",
                "path",
                "score",
                "tags",
                "motivo",
                "palabras_extraidas",
                "uploaded_at",
            ]
        )


def save_inventory(df: pd.DataFrame):
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    github_put_file(
        INVENTORY_PATH,
        csv_bytes,
        "Actualizar inventario Casa Matriz",
    )


def add_inventory_row(row: dict):
    df = load_inventory()

    # Evita duplicados por path
    df = df[df["path"] != row["path"]]

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    save_inventory(df)


def remove_inventory_path(path: str):
    df = load_inventory()

    if df.empty:
        return

    df = df[df["path"] != path]

    save_inventory(df)


def rebuild_inventory_from_storage() -> pd.DataFrame:
    rows = []

    for category in CATEGORIES:
        contents = github_list_dir(f"storage/{category}")

        for item in contents:
            if item.get("type") != "file":
                continue

            filename = item["name"]
            extension = Path(filename).suffix.lower()
            path = item["path"]

            rows.append(
                {
                    "archivo": filename,
                    "extension": extension,
                    "tamano_kb": round(item.get("size", 0) / 1024, 2),
                    "categoria": category,
                    "path": path,
                    "score": "",
                    "tags": "",
                    "motivo": "detectado desde GitHub storage",
                    "palabras_extraidas": "",
                    "uploaded_at": "",
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        df = load_inventory()

    return df


# ============================================================
# UI HELPERS
# ============================================================

def render_file_card(row):
    extension = row.get("extension", "")
    icon = file_icon(extension)
    filename = row.get("archivo", "")
    path = row.get("path", "")

    with st.container(border=True):
        st.markdown(f"### {icon} {filename}")

        st.caption(
            f"{extension} · {row.get('tamano_kb', '')} KB · "
            f"{row.get('palabras_extraidas', '')} palabras"
        )

        if row.get("tags"):
            st.markdown(f"**Tags:** `{row.get('tags')}`")

        if row.get("motivo"):
            st.markdown(f"**Motivo:** {row.get('motivo')}")

        if row.get("uploaded_at"):
            st.caption(f"Subido: {row.get('uploaded_at')}")

        try:
            file_bytes = github_download_file(path)

            st.download_button(
                "Descargar",
                data=file_bytes,
                file_name=filename,
                key=f"download_{path}",
            )
        except Exception as error:
            st.warning(f"No se pudo preparar la descarga: {error}")

        if st.button("Eliminar del sitio", key=f"delete_{path}"):
            try:
                github_delete_file(path, f"Eliminar {filename}")
                remove_inventory_path(path)
                st.success("Archivo eliminado.")
                st.rerun()
            except Exception as error:
                st.error(f"No se pudo eliminar: {error}")


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🗂️ Casa Matriz")
st.sidebar.caption("Archivo persistente en GitHub")

selected_nav_label = st.sidebar.radio(
    "Navegación",
    list(NAV_ITEMS.keys()),
)

selected_page = NAV_ITEMS[selected_nav_label]

st.sidebar.divider()

inventory_df = load_inventory()

for category in CATEGORIES:
    count = int((inventory_df["categoria"] == category).sum()) if not inventory_df.empty else 0
    st.sidebar.caption(f"{CATEGORY_LABELS[category]}: {count}")


# ============================================================
# HOME
# ============================================================

if selected_page == "home":
    st.title("🗂️ Casa Matriz | Archivo organizado")

    st.write(
        "Subí archivos y la app los guarda permanentemente en GitHub, "
        "dentro de su categoría correspondiente."
    )

    st.info(
        "Los archivos se guardan en el repo, dentro de `/storage/<categoria>/`. "
        "Luego quedan visibles en cada sección del sitio."
    )

    uploaded_files = st.file_uploader(
        "Subir archivos",
        accept_multiple_files=True,
        type=[
            "docx", "pdf", "txt", "md",
            "jpg", "jpeg", "png", "webp", "gif", "tif", "tiff", "jp2",
            "ai", "psd", "indd",
        ],
    )

    if uploaded_files:
        if st.button("Guardar archivos en el sitio", type="primary"):
            with st.spinner("Clasificando y guardando en GitHub..."):
                for uploaded_file in uploaded_files:
                    filename = clean_filename(uploaded_file.name)
                    extension = Path(filename).suffix.lower()
                    file_bytes = uploaded_file.getvalue()

                    text = extract_text(filename, file_bytes)
                    category, score, reason = classify_file(filename, text)
                    tags = detect_tags(f"{filename} {text[:4000]}")

                    github_path = f"storage/{category}/{filename}"

                    github_put_file(
                        github_path,
                        file_bytes,
                        f"Subir archivo {filename} a {category}",
                    )

                    row = {
                        "archivo": filename,
                        "extension": extension,
                        "tamano_kb": round(len(file_bytes) / 1024, 2),
                        "categoria": category,
                        "path": github_path,
                        "score": score,
                        "tags": tags,
                        "motivo": reason,
                        "palabras_extraidas": word_count(text),
                        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

                    add_inventory_row(row)

            st.success("Archivos guardados en el sitio.")
            st.rerun()

    st.subheader("Secciones")

    inventory_df = load_inventory()

    cols = st.columns(5)

    for idx, category in enumerate(CATEGORIES):
        with cols[idx]:
            count = int((inventory_df["categoria"] == category).sum()) if not inventory_df.empty else 0
            st.metric(CATEGORY_LABELS[category], count)
            st.caption(CATEGORY_DESCRIPTIONS[category])

    st.stop()


# ============================================================
# CATEGORY PAGES
# ============================================================

if selected_page in CATEGORIES:
    category = selected_page

    st.title(f"📁 {CATEGORY_LABELS[category]}")
    st.caption(CATEGORY_DESCRIPTIONS[category])

    inventory_df = load_inventory()

    if inventory_df.empty:
        st.info("Todavía no hay archivos guardados.")
        st.stop()

    category_df = inventory_df[inventory_df["categoria"] == category].copy()

    st.metric("Archivos en esta sección", len(category_df))

    if category_df.empty:
        st.info("Todavía no hay archivos en esta sección.")
        st.stop()

    search = st.text_input("Buscar dentro de esta sección", "")

    if search:
        search_norm = normalize(search)
        category_df = category_df[
            category_df.apply(
                lambda row: search_norm in normalize(str(row.get("archivo", "")))
                or search_norm in normalize(str(row.get("tags", "")))
                or search_norm in normalize(str(row.get("motivo", ""))),
                axis=1,
            )
        ]

    cols = st.columns(3)

    for index, row in category_df.reset_index(drop=True).iterrows():
        with cols[index % 3]:
            render_file_card(row)

    st.stop()


# ============================================================
# INVENTORY
# ============================================================

if selected_page == "inventory":
    st.title("📋 Inventario general")

    col_a, col_b = st.columns([1, 3])

    with col_a:
        if st.button("Reconstruir inventario desde GitHub"):
            with st.spinner("Leyendo storage desde GitHub..."):
                rebuilt = rebuild_inventory_from_storage()
                save_inventory(rebuilt)
                st.success("Inventario reconstruido.")
                st.rerun()

    inventory_df = load_inventory()

    if inventory_df.empty:
        st.info("Todavía no hay archivos guardados.")
        st.stop()

    st.dataframe(inventory_df, use_container_width=True)

    csv_bytes = inventory_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "Descargar inventario CSV",
        data=csv_bytes,
        file_name="inventario_casa_matriz.csv",
        mime="text/csv",
    )

    st.stop()
