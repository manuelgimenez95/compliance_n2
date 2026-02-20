import streamlit as st
from engine import process_files, generate_final_csv, FINALIDAD_MAP
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


st.set_page_config(layout="wide")
st.title("Unifica todas tus reservas en formato válido para N2")

nrua_input = st.text_input("Introduce NRUA (si varios separados por coma)")
year_target = st.number_input("Año a generar", min_value=2000, max_value=2100, value=2025)

uploaded_files = st.file_uploader(
    "Sube archivos CSV o XLS/XLSX",
    type=["csv","xls","xlsx"],
    accept_multiple_files=True
)

finalidad_mode = st.radio(
    "Asignación de finalidad",
    ["Asignar una finalidad a todas", "Asignar manualmente"]
)

finalidad_global = None

if finalidad_mode == "¿Quieres asignar una misma finalidad a todas las reservas? (Puedes editar posteriormente).":
    finalidad_global = st.selectbox(
        "Selecciona la finalidad por defecto",
        list(FINALIDAD_MAP.keys()),
        format_func=lambda x: f"{x} - {FINALIDAD_MAP[x]}"
    )

if uploaded_files and nrua_input:

    nruas = [x.strip() for x in nrua_input.split(",")]

    df, errors, overlaps = process_files(uploaded_files, nruas, year_target)

    if errors:
        st.error("Errores detectados:")
        for e in errors:
            st.write("•", e)

    if overlaps:
        st.warning("Posibles solapamientos detectados:")
        for o in overlaps:
            st.write("•", o)

    if not df.empty:

        if finalidad_mode == "Asignar manualmente":
            df["finalidad"] = st.selectbox(
                "Finalidad para todas las filas",
                list(FINALIDAD_MAP.keys()),
                format_func=lambda x: f"{x} - {FINALIDAD_MAP[x]}"
            )

        st.subheader("Vista previa editable")
        edited_df = st.data_editor(df, num_rows="dynamic")

        if st.button("Validar y Generar CSV"):

            final_csv, validation_errors = generate_final_csv(
                edited_df,
                finalidad_global
            )

            if validation_errors:
                st.error("Errores en validación:")
                for e in validation_errors:
                    st.write("•", e)
            else:
                st.success("CSV generado correctamente")

                st.download_button(
                    "Descargar CSV",
                    final_csv,
                    file_name="reservas_nrua.csv",
                    mime="text/csv"
                )
# -------- FUNCIÓN PARA GUARDAR EN GOOGLE SHEETS --------

def save_lead(email, tipo_analisis):
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
        tipo_analisis
    ])

# -------- INTERFAZ --------

st.subheader("Vista preliminar completada")

st.info("Para descargar el informe completo necesitamos tus datos.")

email = st.text_input("Correo electrónico")
consent = st.checkbox("Acepto la política de privacidad")

if st.button("Descargar informe completo"):
    if email and consent:
        save_lead(email, "Deposito N2")

        st.success("Informe listo para descarga")

        with open("informe_generado.pdf", "rb") as f:
            st.download_button(
                label="Descargar PDF",
                data=f,
                file_name="informe_deposito_n2.pdf",
                mime="application/pdf"
            )
    else:
        st.error("Debes completar el formulario y aceptar la política.")








