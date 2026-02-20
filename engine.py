import pandas as pd
import numpy as np
import re
from datetime import datetime

FINALIDAD_MAP = {
    1: "Vacacional/Turístico",
    2: "Laboral",
    3: "Estudios",
    4: "Causas médicas",
    5: "Otros"
}

# ---------------------------------------------------
# Normalización
# ---------------------------------------------------

def clean_header(col):
    col = str(col).lower()
    col = re.sub(r"[^a-z0-9ñáéíóú ]", "", col)
    return col.strip()

def detect_column(df, keywords):
    for col in df.columns:
        clean = clean_header(col)
        for k in keywords:
            if k in clean:
                return col
    return None

# ---------------------------------------------------
# Fechas robustas
# ---------------------------------------------------

def robust_parse_column(series):
    return pd.to_datetime(series, dayfirst=True, errors="coerce")

# ---------------------------------------------------
# Filtro canceladas
# ---------------------------------------------------

def remove_cancelled(df):

    status_col = detect_column(df, ["status"])
    estado_col = detect_column(df, ["estado"])

    if status_col:
        df = df[
            ~df[status_col]
            .astype(str)
            .str.lower()
            .str.strip()
            .eq("cancelled")
        ]

    if estado_col:
        df = df[
            ~df[estado_col]
            .astype(str)
            .str.lower()
            .str.contains("cancelación|cancelada|antiguo", regex=True)
        ]

    return df

# ---------------------------------------------------
# Procesamiento principal
# ---------------------------------------------------

def process_files(files, nruas, year_target):

    all_rows = []
    errors = []
    overlaps = []

    for file in files:

        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file, engine="openpyxl")
            elif file.name.endswith(".xls"):
                df = pd.read_excel(file, engine="xlrd")
            else:
                errors.append(f"{file.name}: Formato no soportado")
                continue
        except Exception as e:
            errors.append(f"{file.name}: No se pudo leer el archivo")
            continue

        df = remove_cancelled(df)

        checkin_col = detect_column(df, ["entrada","checkin","inicio"])
        checkout_col = detect_column(df, ["salida","checkout","final"])

        guests_col = detect_column(df, ["personas","guests"])
        adults_col = detect_column(df, ["adult"])
        children_col = detect_column(df, ["niñ","child"])
        babies_col = detect_column(df, ["beb","infant"])

        if not checkin_col or not checkout_col:
            errors.append(f"{file.name}: No se detectaron columnas de fechas")
            continue

        df["checkin"] = robust_parse_column(df[checkin_col])
        df["checkout"] = robust_parse_column(df[checkout_col])

        df = df.dropna(subset=["checkin","checkout"])
        df = df[df["checkout"] > df["checkin"]]

        df = df[
            (df["checkin"].dt.year == year_target)
        ]

        if guests_col:
            df["guests"] = pd.to_numeric(df[guests_col], errors="coerce")
        else:
            total = 0
            if adults_col:
                total += pd.to_numeric(df[adults_col], errors="coerce").fillna(0)
            if children_col:
                total += pd.to_numeric(df[children_col], errors="coerce").fillna(0)
            if babies_col:
                total += pd.to_numeric(df[babies_col], errors="coerce").fillna(0)
            df["guests"] = total

        df["NRUA"] = nruas[0] if len(nruas)==1 else None

        all_rows.append(df[["NRUA","checkin","checkout","guests"]])

    if not all_rows:
        return pd.DataFrame(), errors, overlaps

    final_df = pd.concat(all_rows).sort_values("checkin").reset_index(drop=True)

    # Solapamientos reales (checkout NO cuenta como solape)
    for i in range(len(final_df)-1):
        if final_df.loc[i,"checkout"] > final_df.loc[i+1,"checkin"]:
            overlaps.append(
                f"Solapamiento entre {final_df.loc[i,'checkin'].date()} y {final_df.loc[i+1,'checkin'].date()}"
            )

    return final_df, errors, overlaps

# ---------------------------------------------------
# Generación CSV final
# ---------------------------------------------------

def generate_final_csv(df, finalidad_global):

    errors = []

    if finalidad_global:
        df["finalidad"] = finalidad_global

    required = ["NRUA","checkin","checkout","guests","finalidad"]

    for col in required:
        if col not in df.columns:
            errors.append(f"Falta columna {col}")

    if df["guests"].isnull().any():
        errors.append("Existen huéspedes no definidos")

    if errors:
        return None, errors

    df["checkin"] = pd.to_datetime(df["checkin"]).dt.strftime("%d/%m/%Y")
    df["checkout"] = pd.to_datetime(df["checkout"]).dt.strftime("%d/%m/%Y")

    output = df[required]

    return output.to_csv(sep=";", index=False, header=False), []
