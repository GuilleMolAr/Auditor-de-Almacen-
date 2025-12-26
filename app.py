# streamlit run core/app.py
# app.py
# Auditor de Almacén – Streamlit
# Auditoría Normativa + Auditoría Operativa
# Versión estable + futura compatible

import streamlit as st
import pandas as pd
import os
from bs4 import BeautifulSoup

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(page_title="Auditor de Almacén", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TABLAS_CONTROL_PATH = os.path.join(BASE_DIR, "tablas_control.xlsx")

# Buscar automáticamente el MHTML en la carpeta
def buscar_mhtml_en_directorio(base_dir):
    for file in os.listdir(base_dir):
        if file.lower().endswith(".mhtml"):
            return os.path.join(base_dir, file)
    return None

MHTML_DEFAULT_PATH = buscar_mhtml_en_directorio(BASE_DIR)

# ----------------------------------
# FUNCIONES
# ----------------------------------
def leer_mhtml(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        st.error("No se encontraron tablas en el archivo MHTML")
        st.stop()

    return pd.read_html(str(tables[0]))[0]


def cargar_tablas_control():
    tp_almacen = pd.read_excel(
        TABLAS_CONTROL_PATH,
        sheet_name="TP_ALMACEN"
    )

    jerarquia = pd.read_excel(
        TABLAS_CONTROL_PATH,
        sheet_name="JERARQUIA"
    )

    tp_almacen["Tipo almacén"] = tp_almacen["Tipo almacén"].astype(str).str.zfill(3)
    jerarquia["Jerarquia"] = jerarquia["Jerarquia"].astype(str).str.zfill(2)

    return tp_almacen, jerarquia


def evaluar_normativa(row):
    if row["ESTADO"] == 1:
        return "Ubicación correcta según normativa"
    if row["ESTADO"] == 6:
        return "Ubicación válida pero no permitida para este material"
    return "Ubicación no permitida según normativa"


def sugerencia_correccion(row):
    if row["ESTADO"] == 1:
        return "No requiere corrección"
    if row["ESTADO"] == 6:
        return "Reubicar en posición compatible con el tipo de almacén"
    return "Revisar jerarquía y tipo de almacén asignado"


# ----------------------------------
# SIDEBAR
# ----------------------------------
st.sidebar.title("📂 Fuente de datos")

uploaded_file = st.sidebar.file_uploader(
    "Subir archivo MHTML actualizado",
    type=["mhtml"]
)

# ----------------------------------
# CARGA DE DATOS
# ----------------------------------
if uploaded_file:
    df = leer_mhtml(uploaded_file)
elif MHTML_DEFAULT_PATH:
    df = leer_mhtml(MHTML_DEFAULT_PATH)
else:
    st.error("No se encontró ningún archivo MHTML en el proyecto.")
    st.stop()

tp_almacen, jerarquia = cargar_tablas_control()

# ----------------------------------
# TRANSFORMACIONES
# ----------------------------------
df["Tipo almacén"] = df["Tipo almacén"].astype(str).str.zfill(3)
df["Jerarquia"] = df["Jerarquia"].astype(str).str.zfill(2)

df = df.merge(tp_almacen, how="left", on="Tipo almacén")
df = df.merge(jerarquia, how="left", on="Jerarquia")

df["OBSERVACION"] = df.apply(evaluar_normativa, axis=1)
df["POSIBLE_CORRECCION"] = df.apply(sugerencia_correccion, axis=1)

# ----------------------------------
# COLUMNAS FINALES
# ----------------------------------
COLUMNAS_FINALES = [
    "Texto breve de material",
    "Ubicacion",
    "Tipo almacén",
    "Tipo_Almacen",
    "Jerarquia",
    "Jerarquía nombre",
    "ESTADO",
    "OBSERVACION",
    "POSIBLE_CORRECCION"
]

df_final = df[COLUMNAS_FINALES]

# ----------------------------------
# UI
# ----------------------------------
st.title("📊 Auditoría normativa de almacén")
st.dataframe(df_final, use_container_width=True)



