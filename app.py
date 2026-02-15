import streamlit as st
import fitz  # PyMuPDF
import re
import io
import zipfile

st.set_page_config(page_title="Divisor de Pólizas Triple A", page_icon="✂️")
st.title("✂️ Divisor Masivo de Actas Triple A")
st.write("Sube tu PDF combinado y el sistema creará un archivo individual por cada página con su número de póliza.")

uploaded_file = st.file_uploader("Sube el PDF con todas las órdenes aquí", type="pdf")

if uploaded_file:
    # Leemos el archivo completo
    pdf_data = uploaded_file.read()
    doc_original = fitz.open(stream=pdf_data, filetype="pdf")
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        progress_bar = st.progress(0)
        total_paginas = len(doc_original)
        
        for i in range(total_paginas):
            # 1. Extraer la página individual
            doc_pagina = fitz.open()
            doc_pagina.insert_pdf(doc_original, from_page=i, to_page=i)
            
            # 2. Leer el texto de esa página para buscar la póliza
            texto_pagina = doc_original[i].get_text()
            
            # Buscamos el patrón "Póliza No:" (ej: 235568, 980121, 745098)
            match = re.search(r"Póliza\s*No:?\s*(\d+)", texto_pagina, re.IGNORECASE)
            
            if match:
                nombre_archivo = f"Poliza_{match.group(1)}.pdf"
            else:
                # Si no encuentra el número, usa el número de página como respaldo
                nombre_archivo = f"Pagina_{i+1}_Sin_Poliza.pdf"
            
            # 3. Guardar la página individual en el ZIP
            pagina_bytes = doc_pagina.tobytes()
            zip_file.writestr(nombre_archivo, pagina_bytes)
            doc_pagina.close()
            
            # Actualizar progreso
            progress_bar.progress((i + 1) / total_paginas)

    st.success(f"¡Listo! Se dividieron {total_paginas} páginas correctamente.")
    st.download_button(
        label="⬇️ Descargar todas las pólizas separadas (ZIP)",
        data=zip_buffer.getvalue(),
        file_name="ordenes_divididas.zip",
        mime="application/zip"
    )
    doc_original.close()
