import streamlit as st
import fitz  # PyMuPDF
import re
import io
import zipfile

st.set_page_config(page_title="Divisor Inteligente Triple A", page_icon="✂️")
st.title("✂️ Divisor de Actas Multipágina")
st.write("Este código une automáticamente las páginas de firmas (como la 20) con su póliza principal (como la 19).")

uploaded_file = st.file_uploader("Sube el PDF de Triple A", type="pdf")

if uploaded_file:
    pdf_data = uploaded_file.read()
    doc_original = fitz.open(stream=pdf_data, filetype="pdf")
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        progress_bar = st.progress(0)
        total_paginas = len(doc_original)
        
        # Variables para controlar la unión de páginas
        paginas_por_documento = []
        ultimo_nombre = ""

        for i in range(total_paginas):
            texto_pagina = doc_original[i].get_text()
            
            # Buscamos el número de póliza
            match = re.search(r"Póliza\s*No:?\s*(\d+)", texto_pagina, re.IGNORECASE)
            
            if match:
                # Si encontramos una póliza nueva, primero guardamos lo que teníamos antes
                if paginas_por_documento:
                    doc_temp = fitz.open()
                    for p in paginas_por_documento:
                        doc_temp.insert_pdf(doc_original, from_page=p, to_page=p)
                    zip_file.writestr(f"{ultimo_nombre}.pdf", doc_temp.tobytes())
                    doc_temp.close()
                
                # Empezamos un documento nuevo
                ultimo_nombre = f"Poliza_{match.group(1)}"
                paginas_por_documento = [i]
            else:
                # Si NO hay número de póliza (como en la pág 20), la añadimos a la anterior
                paginas_por_documento.append(i)
            
            progress_bar.progress((i + 1) / total_paginas)

        # Guardar el último documento pendiente
        if paginas_por_documento:
            doc_temp = fitz.open()
            for p in paginas_por_documento:
                doc_temp.insert_pdf(doc_original, from_page=p, to_page=p)
            zip_file.writestr(f"{ultimo_nombre}.pdf", doc_temp.tobytes())
            doc_temp.close()

    st.success("¡Proceso terminado! Las páginas de firmas fueron unidas correctamente.")
    st.download_button(
        label="⬇️ Descargar ZIP con documentos unidos",
        data=zip_buffer.getvalue(),
        file_name="polizas_reconstruidas.zip",
        mime="application/zip"
    )
    doc_original.close()
