import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata

# --- NORMALIZACIÓN TOTAL (Tildes, Espacios, Mayúsculas) ---
def limpiar_texto(texto):
    if not texto: return ""
    # Elimina caracteres invisibles, tildes y espacios extra
    texto = str(texto).upper().strip()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', texto) # Colapsa espacios múltiples

# --- LÓGICA DE NOMENCLATURA (BARRANQUILLA) ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 'BIS': 0.05}

def calcular_peso_direccion(dir_text):
    texto = limpiar_texto(dir_text)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    if match:
        peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0)
    else:
        peso = 0.0
    if "SUR" in texto: peso -= 5000 
    return peso

st.set_page_config(page_title="Logística Pro V90.0", layout="wide")
st.title("🚛 Sistema Logístico UT ITA RADIAN")
st.markdown("Cruce dinámico de **Cuenta (Excel)** vs **Póliza (PDF)** con ordenamiento por nomenclatura.")

pdf_file = st.file_uploader("1. Subir PDF (Pólizas y Recortes)", type="pdf")
excel_file = st.file_uploader("2. Subir Base de Datos (Excel o CSV)", type=["xlsx", "csv"])

if pdf_file and excel_file:
    if st.button("🚀 Iniciar Procesamiento"):
        # --- CARGA INTELIGENTE DEL ARCHIVO ---
        try:
            if excel_file.name.endswith('.csv'):
                # Intenta leer CSV detectando si es coma o punto y coma
                df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df = pd.read_excel(excel_file)
            
            # Limpiamos y normalizamos los nombres de las columnas
            df.columns = [limpiar_texto(c) for c in df.columns]
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()

        # --- BUSCADOR FLEXIBLE DE COLUMNAS (Independiente de espacios/mayúsculas) ---
        col_cuenta = next((c for c in df.columns if 'CUENTA' in c), None)
        col_tecnico = next((c for c in df.columns if 'TECNICO' in c or 'OPERARIO' in c or 'GESTOR' in c), None)
        col_barrio = next((c for c in df.columns if 'BARRIO' in c), None)
        col_dir = next((c for c in df.columns if 'DIRECCION' in c or 'DIR' in c), None)

        if not col_cuenta:
            st.error(f"❌ No se encontró la columna de Cuenta. Columnas detectadas: {list(df.columns)}")
            st.stop()

        # --- PROCESAMIENTO PDF Y UNIFICACIÓN ---
        doc_original = fitz.open(stream=pdf_file.read(), filetype="pdf")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_final:
            datos_gestores = {}
            i = 0
            while i < len(doc_original):
                texto_pag = doc_original[i].get_text()
                match_pol = re.search(r"Poliza\s*No:?\s*(\d+)", limpiar_texto(texto_pag), re.IGNORECASE)
                
                if match_pol:
                    poliza_id = str(match_pol.group(1))
                    paginas_doc = [i]
                    
                    # Une páginas de firmas/recortes (pág 19 y 20)
                    while i + 1 < len(doc_original):
                        texto_sig = limpiar_texto(doc_original[i+1].get_text())
                        if "POLIZA NO" not in texto_sig:
                            paginas_doc.append(i+1)
                            i += 1
                        else: break
                    
                    # Cruce Account (Excel) vs Policy (PDF)
                    info = df[df[col_cuenta].astype(str).str.contains(poliza_id)]
                    
                    if not info.empty:
                        gestor = limpiar_texto(info.iloc[0].get(col_tecnico, 'SIN_GESTOR')).replace(" ", "_")
                        barrio = limpiar_texto(info.iloc[0].get(col_barrio, 'SIN_BARRIO')).replace(" ", "_")
                        
                        pdf_uni = fitz.open()
                        for p in paginas_doc: pdf_uni.insert_pdf(doc_original, from_page=p, to_page=p)
                        
                        # Organización: GESTOR -> BARRIO -> Poliza.pdf
                        ruta_pdf = f"{gestor}/{barrio}/Poliza_{poliza_id}.pdf"
                        zip_final.writestr(ruta_pdf, pdf_uni.tobytes())
                        pdf_uni.close()

                        if gestor not in datos_gestores: datos_gestores[gestor] = []
                        datos_gestores[gestor].append(info.iloc[0])
                i += 1

            # --- GENERACIÓN DE TABLAS ORGANIZADAS POR NOMENCLATURA ---
            for gestor, filas in datos_gestores.items():
                df_gestor = pd.DataFrame(filas)
                # Ordenamiento: Barrio (A-Z) y Nomenclatura (Mayor a Menor)
                df_gestor['PESO_DIR'] = df_gestor[col_dir].apply(calcular_peso_direccion)
                df_gestor = df_gestor.sort_values(by=[col_barrio, 'PESO_DIR'], ascending=[True, False])

                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_gestor.drop(columns=['PESO_DIR']).to_excel(writer, index=False, sheet_name='Reparto')
                
                zip_final.writestr(f"{gestor}/TABLA_REPARTO_{gestor}.xlsx", output_xlsx.getvalue())

        st.success("✅ ¡Procesado con éxito! Las columnas fueron detectadas automáticamente.")
        st.download_button("⬇️ Descargar ZIP de Logística", zip_buffer.getvalue(), "Ruta_Maestra_ItaRadian.zip")
