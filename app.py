import streamlit as st
import fitz  # PyMuPDF
import re
import io
import zipfile

st.set_page_config(page_title="Renombrador Triple A", page_icon="💧")
st.title("🚀 Procesador Masivo de Pólizas")
st.write("Sube tus 400 archivos y descárgalos renombrados en segundos.")

# Componente para subir archivos masivos
files = st.file_uploader("Arrastra aquí tus PDFs", accept_multiple_files=True, type="pdf")

if files:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        progress_bar = st.progress(0)
        for i, file in enumerate(files):
            data = file.read()
            # Leemos el PDF a toda velocidad con PyMuPDF
            doc = fitz.open(stream=data, filetype="pdf")
            text = "".join([page.get_text() for page in doc])
            
            # Buscamos el patrón "Póliza No:" de tus actas
            match = re.search(r"Póliza\s*No:?\s*(\d+)", text, re.IGNORECASE)
            num_poliza = match.group(1) if match else f"Desconocida_{i}"
            
            # Lo metemos en el ZIP con el nombre nuevo
            zip_file.writestr(f"Poliza_{num_poliza}.pdf", data)
            progress_bar.progress((i + 1) / len(files))

    st.success("¡Proceso completado!")
    st.download_button(
        label="⬇️ Descargar todo en un ZIP",
        data=zip_buffer.getvalue(),
        file_name="polizas_listas.zip",
        mime="application/zip"
    )
