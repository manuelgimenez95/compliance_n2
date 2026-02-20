import streamlit as st
import gspread
import json
import os
import re
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from engine import process_files, generate_final_csv, FINALIDAD_MAP

st.set_page_config(layout="wide")
st.title("Generador oficial CSV NRUA")

# ---------------------------------------------------
# GUARDAR LEAD
# ---------------------------------------------------

def save_lead(email):

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False

    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_dict, scope
        )

        client = gspread.authorize(credentials)
        sheet = client.open("Leads DepositoN2").sheet1

        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            email,
            "Generador CSV NRUA"
        ])

        return True

    except:
        st.error("Error guardando lead.")
        return False

# ---------------------------------------------------
# FORMULARIO PRINCIPAL
# ---------------------------------------------------

nrua_input = st.text_input("Introduce NRUA")
year_target = st.number_input("Año", 2000, 2100, 2025)

uploaded_files = st.file_uploader(
    "Sube archivos CSV, XLS o XLSX",
    type=["csv","xls","xlsx"],
    accept_multiple_files=True
)

finalidad_global = st.selectbox(
    "Finalidad",
    list(FINALIDAD_MAP.keys()),
    format_func=lambda x: f"{x} - {FINALIDAD_MAP[x]}"
)

# ---------------------------------------------------
# PROCESAR ARCHIVOS
# ---------------------------------------------------

if uploaded_files and nrua_input:

    nruas = [x.strip() for x in nrua_input.split(",")]

    df, errors, overlaps = process_files(uploaded_files, nruas, year_target)

    if errors:
        st.error("Errores detectados:")
        for e in errors:
            st.write("•", e)

    if overlaps:
        st.warning("Posibles solapamientos:")
        for o in overlaps:
            st.write("•", o)

    if not df.empty:

        st.subheader("Vista previa")
        edited_df = st.data_editor(df, num_rows="dynamic")

        if st.button("Validar y Generar CSV"):

            final_csv, validation_errors = generate_final_csv(
                edited_df,
                finalidad_global
            )

            if validation_errors:
                st.error("Errores:")
                for e in validation_errors:
                    st.write("•", e)
            else:
                st.session_state["csv_ready"] = final_csv
                st.success("CSV generado correctamente")

# ---------------------------------------------------
# DESCARGA (SOLO SI CSV LISTO)
# ---------------------------------------------------

if "csv_ready" in st.session_state:

    st.markdown("---")
    st.subheader("Introduce tu correo para descargar")

    email = st.text_input("Correo electrónico")

    if st.button("Descargar CSV"):

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            st.error("Correo electrónico no válido.")
        else:
            if save_lead(email):
                st.download_button(
                    "Descargar archivo",
                    st.session_state["csv_ready"],
                    file_name="reservas_nrua.csv",
                    mime="text/csv"
                )
