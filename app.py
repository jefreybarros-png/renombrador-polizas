import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata

# --- NORMALIZACIÓN DE TEXTO ---
def normalizar(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# --- LÓGICA DE PESO PARA DIRECCIONES (Barranquilla Style) ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 'BIS': 0.05}

def calcular_peso_direccion(dir_text):
    texto = normalizar(dir_text)
    # Extrae número y letra (ej: 95B o 45BIS)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    if match:
        peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0)
    else:
        peso = 0.0
    # El SUR se penaliza para que en orden descendente quede al final de la ruta
    if "SUR" in texto: peso -= 5000 
    return peso

st.set_page_config(page_title="Logística Pro V89.0", layout="wide")
st.title("🚛 Organizador de Rutas: Carpeta por Gestor > Barrio > Dirección")

pdf_file = st.file_uploader("1. Subir PDF (Actas de Triple A)", type="pdf")
excel_file = st.file_uploader("2. Subir Excel (Ruta Operativa)", type=["xlsx", "csv"])

if pdf_file and excel_file:
    if st.button("🚀 Procesar y Organizar Todo"):
        # Carga de Base de Datos
        df = pd.read_excel(excel_file) if ".xlsx" in excel_file.name else pd.read_csv(excel_file)
        df.columns = [normalizar(c) for c in df.columns]
        
        doc_original = fitz.open(stream=pdf_file.read(), filetype="pdf")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_final:
            datos_gestores = {}

            # --- ESCANEO Y UNIFICACIÓN DE DOCUMENTOS (Pág 19 y 20) ---
            i = 0
            while i < len(doc_original):
                texto_pag = doc_original[i].get_text()
                match_pol = re.search(r"Póliza\s*No:?\s*(\d+)", texto_pag, re.IGNORECASE)
                
                if match_pol:
                    poliza_pdf = str(match_pol.group(1))
                    paginas_doc = [i]
                    
                    # Unificación de recortes/firmas (hojas sin póliza propia)
                    while i + 1 < len(doc_original):
                        if not re.search(r"Póliza\s*No:?", doc_original[i+1].get_text(), re.IGNORECASE):
                            paginas_doc.append(i+1)
                            i += 1
                        else: break
                    
                    # Cruce de datos: PDF (Póliza) == Excel (Cuenta)
                    info = df[df['CUENTA'].astype(str).str.contains(poliza_pdf)]
                    
                    if not info.empty:
                        nombre_gestor = normalizar(info.iloc[0].get('TECNICO', 'SIN_GESTOR')).replace(" ", "_")
                        nombre_barrio = normalizar(info.iloc[0].get('BARRIO', 'SIN_BARRIO')).replace(" ", "_")
                        
                        pdf_uni = fitz.open()
                        for p in paginas_doc: pdf_uni.insert_pdf(doc_original, from_page=p, to_page=p)
                        
                        # Organización interna del ZIP: GESTOR -> BARRIO -> POLIZA.pdf
                        ruta_pdf = f"{nombre_gestor}/{nombre_barrio}/Poliza_{poliza_pdf}.pdf"
                        zip_final.writestr(ruta_pdf, pdf_uni.tobytes())
                        pdf_uni.close()

                        if nombre_gestor not in datos_gestores: datos_gestores[nombre_gestor] = []
                        datos_gestores[nombre_gestor].append(info.iloc[0])
                i += 1

            # --- ORDENAMIENTO DE TABLAS DE REPARTO ---
            for gestor, filas in datos_gestores.items():
                df_gestor = pd.DataFrame(filas)
                # Cálculo de peso para orden descendente por nomenclatura
                df_gestor['PESO_DIR'] = df_gestor['DIRECCION'].apply(calcular_peso_direccion)
                # Orden: Barrio alfabético, Dirección de Mayor a Menor
                df_gestor = df_gestor.sort_values(by=['BARRIO', 'PESO_DIR'], ascending=[True, False])

                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_gestor.drop(columns=['PESO_DIR']).to_excel(writer, index=False, sheet_name='Mi_Ruta')
                
                # Tabla de reparto dentro de la carpeta raíz del gestor
                zip_final.writestr(f"{gestor}/TABLA_REPARTO_{gestor}.xlsx", output_xlsx.getvalue())

        st.success("✅ ¡Ruta Maestra organizada! Carpetas listas por gestor y barrio.")
        st.download_button("⬇️ Descargar ZIP de Logística", zip_buffer.getvalue(), "Ruta_Maestra_ItaRadian.zip")
