# streamlit run core/app.py
# app.py
# Auditor de Almacén – Streamlit
# Auditoría Normativa + Auditoría Operativa
# Versión estable + futura compatible

import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from pathlib import Path

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(page_title="Auditor de Almacén", layout="wide")

RUTA_TABLAS_CONTROL = Path("tablas_control.xlsx")
#(r"C:/Users/gmolar/Documents/Python/Auditor_de_almacen/control_data/tablas_control.xlsx")

# --------------------------------------------------
# CARGA TABLAS DE CONTROL
# --------------------------------------------------

@st.cache_data
def cargar_tablas_control():
    maestro = pd.read_excel(
        RUTA_TABLAS_CONTROL,
        sheet_name="MAESTRO_MATERIALES",
        dtype=str
    )

    combinaciones = pd.read_excel(
        RUTA_TABLAS_CONTROL,
        sheet_name="COMBINACIONES",
        dtype=str
    )

    mapeo = pd.read_excel(
        RUTA_TABLAS_CONTROL,
        sheet_name="MAPEO_POSICIONES",
        dtype=str
    )

    maestro["MATERIAL"] = maestro["MATERIAL"].astype(str).str.strip()
    maestro["JERARQUIA"] = maestro["JERARQUIA"].astype(str).str.zfill(15)
    maestro["IND TP ALM ENTRADA"] = maestro["IND TP ALM ENTRADA"].astype(str).str.zfill(3)

    combinaciones["TP_ALMACEN"] = combinaciones["TP_ALMACEN"].astype(str).str.zfill(3)
    combinaciones["JERRARQUIA"] = combinaciones["JERRARQUIA"].astype(str).str.zfill(15)

    # Crear mapeo de Tipo_Almacen -> NOMBRE_ALMACEN
    mapeo_almacenes = {}
    if "TP_ALMACEN" in combinaciones.columns and "NOMBRE_ALMACEN" in combinaciones.columns:
        mapeo_almacenes = dict(zip(
            combinaciones["TP_ALMACEN"].str.zfill(3),
            combinaciones["NOMBRE_ALMACEN"]
        ))

    return maestro, combinaciones, mapeo, mapeo_almacenes

# --------------------------------------------------
# LECTURA ARCHIVO SAP
# --------------------------------------------------

def cargar_mhtml(file):
    content = file.read().decode("utf-8", errors="ignore")
    soup = BeautifulSoup(content, "html.parser")

    raw = StringIO(str(soup))
    tablas = pd.read_html(raw, header=0)

    def buscar_columna(cols, keywords):
        cols_l = [str(c).lower() for c in cols]
        for kw in keywords:
            for i, c in enumerate(cols_l):
                if kw in c:
                    return cols[i]
        return None

    kw_material = ["material", "matnr"]
    kw_ubicacion = ["ubic", "posición", "posicion", "location"]
    kw_tipo = ["tipo", "almac"]

    candidata = None

    for t in tablas:
        if isinstance(t.columns, pd.MultiIndex):
            t.columns = [
                " ".join([str(x) for x in col if x]).strip()
                for col in t.columns.values
            ]
        else:
            t.columns = t.columns.astype(str).str.strip()

        cols = list(t.columns)

        if (
            buscar_columna(cols, kw_material)
            and buscar_columna(cols, kw_ubicacion)
            and buscar_columna(cols, kw_tipo)
        ):
            candidata = t.copy()
            break

    if candidata is None:
        raise ValueError("No se encontró una tabla SAP válida")

    cols = list(candidata.columns)
    col_material = buscar_columna(cols, kw_material)
    col_ubicacion = buscar_columna(cols, kw_ubicacion)
    col_tipo = buscar_columna(cols, kw_tipo)

    candidata = candidata.rename(columns={
        col_material: "Material",
        col_ubicacion: "Ubicacion",
        col_tipo: "Tipo_Almacen"
    })

    candidata["Material"] = candidata["Material"].astype(str).str.strip()
    candidata["Tipo_Almacen"] = candidata["Tipo_Almacen"].astype(str).str.zfill(3)

    return candidata

# --------------------------------------------------
# UTILIDADES
# --------------------------------------------------

def ubicacion_en_rango(ubicacion, desde, hasta):
    if pd.isna(ubicacion) or pd.isna(desde) or pd.isna(hasta):
        return False
    try:
        return float(desde) <= float(ubicacion) <= float(hasta)
    except Exception:
        return str(desde) <= str(ubicacion) <= str(hasta)


def zonas_por_ubicacion(ubicacion, mapeo):
    zonas = []
    for _, r in mapeo.iterrows():
        if ubicacion_en_rango(ubicacion, r["Posición Desde"], r["Posición Hasta"]):
            zonas.append(str(r["ZONA"]).strip())
    return zonas

# --------------------------------------------------
# AUDITORÍA NORMATIVA
# --------------------------------------------------

def auditar_calidad(df_sap, maestro, combinaciones, mapeo, mapeo_almacenes):
    resultados = []

    for _, row in df_sap.iterrows():
        material = row["Material"]
        ubicacion = row["Ubicacion"]

        fila_maestro = maestro[maestro["MATERIAL"] == material]

        if fila_maestro.empty:
            resultados.append(("🔴", "Material no existe en Maestro"))
            continue

        jerarquia = fila_maestro.iloc[0]["JERARQUIA"]
        tp_alm_ctrl = fila_maestro.iloc[0]["IND TP ALM ENTRADA"]

        comb = combinaciones[
            (combinaciones["TP_ALMACEN"] == tp_alm_ctrl) &
            (combinaciones["JERRARQUIA"] == jerarquia)
        ]

        if comb.empty:
            resultados.append(("🔴", "No existe combinación válida Almacén + Jerarquía"))
            continue

        zonas_validas = set()
        for z in comb["MAPEO_POSICIONES"]:
            zonas_validas.update(x.strip() for x in str(z).split(","))

        zonas_ubic = set(zonas_por_ubicacion(ubicacion, mapeo))

        if zonas_validas & zonas_ubic:
            resultados.append(("🟢", "Ubicación correcta según normativa"))
        elif zonas_ubic:
            resultados.append(("🟡", "Ubicación válida pero no para esta combinación"))
        else:
            resultados.append(("🔴", "Ubicación fuera de zonas permitidas"))

    df_out = df_sap.copy()
    df_out[["ESTADO", "OBSERVACION"]] = resultados
    
    # Añadir nombre descriptivo de almacén
    if mapeo_almacenes:
        df_out["NOMBRE_ALMACEN"] = df_out["Tipo_Almacen"].map(mapeo_almacenes)
        cols = [c for c in df_out.columns if c != "Tipo_Almacen"] + ["Tipo_Almacen"]
        df_out = df_out[cols]
    
    return df_out

# --------------------------------------------------
# AUDITORÍA OPERATIVA
# --------------------------------------------------

def auditar_operaciones(df_sap, maestro, mapeo_almacenes):
    resultados = []

    for _, row in df_sap.iterrows():
        material = row["Material"]
        tp_sap = row["Tipo_Almacen"]

        fila_maestro = maestro[maestro["MATERIAL"] == material]

        if fila_maestro.empty:
            resultados.append(("🔴", "Material no existe en Maestro"))
            continue

        tp_maestro = fila_maestro.iloc[0]["IND TP ALM ENTRADA"]

        if tp_sap != tp_maestro:
            resultados.append(("🔴", f"Tipo almacén SAP ({tp_sap}) ≠ Maestro ({tp_maestro})"))
        else:
            resultados.append(("🟢", "Datos operativos correctos"))

    df_out = df_sap.copy()
    df_out[["ESTADO_OP", "OBSERVACION_OP"]] = resultados
    
    # Añadir nombre descriptivo de almacén
    if mapeo_almacenes:
        df_out["NOMBRE_ALMACEN"] = df_out["Tipo_Almacen"].map(mapeo_almacenes)
        cols = [c for c in df_out.columns if c != "Tipo_Almacen"] + ["Tipo_Almacen"]
        df_out = df_out[cols]
    
    return df_out

# --------------------------------------------------
# UI
# --------------------------------------------------

st.title("Auditor de Almacenamiento – SAP")
st.caption("Ley Prov. 8302 · Normativa ANMAT")

maestro, combinaciones, mapeo, mapeo_almacenes = cargar_tablas_control()

archivo = st.file_uploader("Subir archivo SAP (.MHTML)", type=["mhtml"])

if archivo:
    df_sap = cargar_mhtml(archivo)

    tab1, tab2 = st.tabs(["🧪 Auditoría Normativa", "🛠 Auditoría Operaciones"])

    with tab1:
        df_calidad = auditar_calidad(df_sap, maestro, combinaciones, mapeo, mapeo_almacenes)
        st.dataframe(df_calidad, use_container_width=True)
        st.markdown("### Resumen")
        st.write(df_calidad["ESTADO"].value_counts())

    with tab2:
        if st.button("Ejecutar auditoría operativa"):
            df_op = auditar_operaciones(df_sap, maestro, mapeo_almacenes)
            st.dataframe(df_op, use_container_width=True)
            st.markdown("### Resumen operativo")
            st.write(df_op["ESTADO_OP"].value_counts())
