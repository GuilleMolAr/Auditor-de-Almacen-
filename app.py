# streamlit run core/app.py
# app.py
# Auditor de Almacén – Streamlit
# Auditoría Normativa + Auditoría Operativa
# Versión estable + futura compatible

import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from io import StringIO

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------

st.set_page_config(
    page_title="Auditor de Almacén",
    layout="wide"
)

BASE_PATH = Path(__file__).parent
TABLAS_CONTROL_PATH = BASE_PATH / "tablas_control.xlsx"
MHTML_DEFAULT_PATH = BASE_PATH / "auditor de posiciones.MHTML"

# --------------------------------------------------
# UTILIDADES
# --------------------------------------------------

def normalizar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
        .str.replace("°", "", regex=False)
    )
    return df

# --------------------------------------------------
# CARGA TABLAS DE CONTROL
# --------------------------------------------------

@st.cache_data
def cargar_tablas_control():
    tp_almacen = pd.read_excel(
        TABLAS_CONTROL_PATH,
        sheet_name="TP_ALMACEN",
        dtype=str
    )

    jerarquia = pd.read_excel(
        TABLAS_CONTROL_PATH,
        sheet_name="JERARQUIA",
        dtype=str
    )

    tp_almacen = normalizar_columnas(tp_almacen)
    jerarquia = normalizar_columnas(jerarquia)

    tp_almacen["N_ALMACEN"] = tp_almacen["N_ALMACEN"].astype(str).str.zfill(3)
    jerarquia["JERARQUIA_N"] = jerarquia["JERARQUIA_N"].astype(str).str.zfill(2)

    return tp_almacen, jerarquia

# --------------------------------------------------
# LECTURA MHTML SAP
# --------------------------------------------------

def leer_mhtml(path_or_file):
    if hasattr(path_or_file, "read"):
        content = path_or_file.read().decode("utf-8", errors="ignore")
    else:
        with open(path_or_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    raw = StringIO(str(soup))
    tablas = pd.read_html(raw, header=0)

    for t in tablas:
        t.columns = t.columns.astype(str).str.strip()

        if (
            any("material" in c.lower() for c in t.columns)
            and any("ubic" in c.lower() for c in t.columns)
            and any("almac" in c.lower() for c in t.columns)
        ):
            df = t.copy()
            break
    else:
        raise ValueError("No se encontró una tabla válida SAP")

    col_material = next(c for c in df.columns if "material" in c.lower())
    col_ubicacion = next(c for c in df.columns if "ubic" in c.lower())
    col_tipo = next(c for c in df.columns if "almac" in c.lower())

    df = df.rename(columns={
        col_material: "MATERIAL",
        col_ubicacion: "UBICACION",
        col_tipo: "TIPO_ALMACEN"
    })

    df["MATERIAL"] = df["MATERIAL"].astype(str).str.strip()
    df["TIPO_ALMACEN"] = df["TIPO_ALMACEN"].astype(str).str.zfill(3)

    return df

# --------------------------------------------------
# UI
# --------------------------------------------------

st.title("Auditor de Almacenamiento – SAP")
st.caption("Auditoría normativa y operativa")

with st.sidebar:
    st.header("📂 Fuente de datos")

    archivo_subido = st.file_uploader(
        "Subir archivo SAP (.MHTML)",
        type=["mhtml", "MHTML"]
    )

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------

tp_almacen, jerarquia = cargar_tablas_control()

if archivo_subido:
    df = leer_mhtml(archivo_subido)
    st.info("Usando archivo subido por el usuario")
elif MHTML_DEFAULT_PATH.exists():
    df = leer_mhtml(MHTML_DEFAULT_PATH)
    st.info("Usando archivo MHTML por defecto del proyecto")
else:
    st.warning("No hay archivo MHTML disponible")
    st.stop()

# --------------------------------------------------
# ENRIQUECIMIENTO DE DATOS
# --------------------------------------------------

# Tipo de almacén → nombre
df = df.merge(
    tp_almacen,
    how="left",
    left_on="TIPO_ALMACEN",
    right_on="N_ALMACEN"
)

df.rename(columns={"NOMBRE": "TIPO_ALMACEN_NOMBRE"}, inplace=True)
df.drop(columns=["N_ALMACEN"], inplace=True)

# Jerarquía (ejemplo: derivada del material si ya la tenés)
if "JERARQUIA" in df.columns:
    df["JERARQUIA"] = df["JERARQUIA"].astype(str).str.zfill(2)

    df = df.merge(
        jerarquia,
        how="left",
        left_on="JERARQUIA",
        right_on="JERARQUIA_N"
    )

    df.rename(columns={"NOMBRE": "JERARQUIA_NOMBRE"}, inplace=True)
    df.drop(columns=["JERARQUIA_N"], inplace=True)
else:
    df["JERARQUIA_NOMBRE"] = "No informada"

# --------------------------------------------------
# RESULTADO SIMULADO (placeholder de auditoría)
# --------------------------------------------------

df["ESTADO"] = "🟢"
df["OBSERVACION"] = "Ubicación correcta según normativa"
df["POSIBLE_CORRECCION"] = "-"

# --------------------------------------------------
# VISUALIZACIÓN
# --------------------------------------------------

st.dataframe(
    df[
        [
            "MATERIAL",
            "UBICACION",
            "TIPO_ALMACEN",
            "TIPO_ALMACEN_NOMBRE",
            "JERARQUIA_NOMBRE",
            "ESTADO",
            "OBSERVACION",
            "POSIBLE_CORRECCION"
        ]
    ],
    width="stretch"
)








