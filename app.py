import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN VISUAL (ESTILO ITA RADIAN) ---
COLOR_CORPORATIVO = "#003366"  # Azul oscuro del html.txt
COLOR_ENCABEZADO = "#E6E6E6"   # Gris claro para alternar

# --- FUNCIONES DE NORMALIZACIÓN ---
def limpiar_texto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

# --- LÓGICA DE ORDENAMIENTO (BARRANQUILLA) ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'E': 0.5, 'BIS': 0.05}

def calcular_peso_direccion(dir_text):
    texto = limpiar_texto(dir_text)
    match = re.search(r'(\d+)\s*(BIS|[A-I])?', texto)
    peso = float(match.group(1)) + VALOR_SUFIJOS.get(match.group(2), 0.0) if match else 0.0
    if "SUR" in texto: peso -= 5000  # Penalización para enviar SUR al final
    return peso

# --- GENERADOR DE PDF HORIZONTAL (ESTILO HTML) ---
class PDFRuta(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(0, 51, 102) # #003366 RGB
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'UT ITA RADIAN - REPORTE DE RUTA OPERATIVA', 0, 1, 'C', 1)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf_lista_tecnico(df_tecnico, nombre_tecnico):
    pdf = PDFRuta(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    # Info del Técnico
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"GESTOR: {nombre_tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(2)
    
    # Encabezados de Tabla
    cols = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    anchos = [30, 30, 50, 80, 70] # Ajustar según contenido
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    for col, w in zip(cols, anchos):
        # Intentar buscar la columna en el DF (flexible)
        col_name = next((c for c in df_tecnico.columns if col in c), col)
        pdf.cell(w, 8, col_name, 1, 0, 'C', 1)
    pdf.ln()
    
    # Filas
    pdf.set_font('Arial', '', 8)
    for _, row in df_tecnico.iterrows():
        for col, w in zip(cols, anchos):
            # Buscar nombre real de columna
            real_col = next((c for c in df_tecnico.columns if col in c), None)
            valor = str(row[real_col])[:45] if real_col else "" # Recortar texto largo
            pdf.cell(w, 7, valor, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- GENERADOR DE EXCEL CON ESTILO ---
def generar_excel_estilizado(df_data, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_data.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Formatos
        header_fmt = workbook.add_format({'bold': True, 'fg_color': '#003366', 'font_color': 'white', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1})
        
        for col_num, value in enumerate(df_data.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 20) # Ancho auto aproximado
            
    return output.getvalue()

# --- APP STREAMLIT ---
st.set_page_config(page_title="Logística Master V100", layout="wide")
st.title("🚛 Logística ITA RADIAN: Sistema de Reparto Total")

pdf_file = st.file_uploader("1. Subir PDF (Pólizas)", type="pdf")
excel_file = st.file_uploader("2. Subir Base (Excel/CSV)", type=["xlsx", "csv"])

if pdf_file and excel_file:
    if st.button("🚀 Generar Estructura Completa"):
        # 1. Carga de Datos
        try:
            if excel_file.name.endswith('.csv'):
                df_base = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df_base = pd.read_excel(excel_file)
            
            # Limpieza de columnas
            cols_orig = df_base.columns.tolist()
            mapa_cols = {limpiar_texto(c): c for c in cols_orig}
            
            # Buscador de columnas clave
            def find_col(keywords):
                for k in keywords:
                    for clean_c in mapa_cols:
                        if k in clean_c: return mapa_cols[clean_c]
                return None

            col_cta = find_col(['CUENTA', 'POLIZA', 'NRO'])
            col_tec = find_col(['TECNICO', 'GESTOR', 'OPERARIO'])
            col_barrio = find_col(['BARRIO', 'SECTOR'])
            col_dir = find_col(['DIRECCION', 'DIR'])
            
            if not col_cta:
                st.error("❌ No se encontró columna CUENTA.")
                st.stop()

        except Exception as e:
            st.error(f"Error archivo: {e}")
            st.stop()

        # 2. Procesar PDF y Mapear
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        # Diccionarios para almacenamiento
        mapa_poliza_pdf_bytes = {} # {num_poliza: bytes_pdf_unificado}
        
        i = 0
        while i < len(doc):
            text = doc[i].get_text()
            match = re.search(r"Póliza\s*No:?\s*(\d+)", text, re.IGNORECASE)
            if match:
                pol_num = match.group(1)
                pages = [i]
                # Unir páginas siguientes (recortes)
                while i + 1 < len(doc):
                    if "Póliza No" not in doc[i+1].get_text():
                        pages.append(i+1)
                        i += 1
                    else: break
                
                # Crear PDF bytes unificado
                sub_doc = fitz.open()
                for p in pages: sub_doc.insert_pdf(doc, from_page=p, to_page=p)
                mapa_poliza_pdf_bytes[pol_num] = sub_doc.tobytes()
                sub_doc.close()
            i += 1
        
        # 3. Cruzar Información y Crear Estructura
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            
            # --- A. BASE TOTAL ORGANIZADA ---
            df_base['PESO_DIR'] = df_base[col_dir].astype(str).apply(calcular_peso_direccion)
            df_base_sorted = df_base.sort_values(by=[col_tec, col_barrio, 'PESO_DIR'], ascending=[True, True, False])
            
            excel_total = generar_excel_estilizado(df_base_sorted.drop(columns=['PESO_DIR']), "Base_General")
            zf.writestr("BASE_GENERAL/Base_Total_Organizada.xlsx", excel_total)
            
            # Guardar TODOS los PDFs en una carpeta raíz
            for pol, pdf_bytes in mapa_poliza_pdf_bytes.items():
                zf.writestr(f"BASE_GENERAL/TODOS_PDFS_DIVIDIDOS/Poliza_{pol}.pdf", pdf_bytes)

            # --- B. CARPETAS POR TÉCNICO ---
            tecnicos = df_base_sorted[col_tec].unique()
            
            for tec in tecnicos:
                nombre_tec_clean = limpiar_texto(str(tec)).replace(" ", "_")
                df_tec = df_base_sorted[df_base_sorted[col_tec] == tec].copy()
                
                if df_tec.empty: continue
                
                # 1. Excel del Técnico (Bonito)
                excel_tec = generar_excel_estilizado(df_tec.drop(columns=['PESO_DIR']), "Ruta_Tecnico")
                zf.writestr(f"CARPETAS_TECNICOS/{nombre_tec_clean}/Tabla_Reparto.xlsx", excel_tec)
                
                # 2. PDF Horizontal (Lista para firmar)
                pdf_lista = generar_pdf_lista_tecnico(df_tec, str(tec))
                zf.writestr(f"CARPETAS_TECNICOS/{nombre_tec_clean}/Tabla_Reparto_Horizontal.pdf", pdf_lista)
                
                # 3. Paquete de Impresión (Merge de PDFs) y PDFs Individuales
                merged_doc = fitz.open()
                
                for idx, row in df_tec.iterrows():
                    pol_id = str(row[col_cta])
                    # Buscar si existe el PDF para esta cuenta
                    # Intentamos match exacto o contenido
                    pdf_bytes_found = None
                    for p_key, p_val in mapa_poliza_pdf_bytes.items():
                        if p_key in pol_id: # Flexibilidad en el match
                            pdf_bytes_found = p_val
                            break
                    
                    if pdf_bytes_found:
                        # Guardar Individual
                        zf.writestr(f"CARPETAS_TECNICOS/{nombre_tec_clean}/POLIZAS_INDIVIDUALES/Poliza_{pol_id}.pdf", pdf_bytes_found)
                        
                        # Agregar al paquete de impresión
                        with fitz.open(stream=pdf_bytes_found, filetype="pdf") as temp_doc:
                            merged_doc.insert_pdf(temp_doc)
                
                if len(merged_doc) > 0:
                    zf.writestr(f"CARPETAS_TECNICOS/{nombre_tec_clean}/PAQUETE_IMPRESION_LISTO.pdf", merged_doc.tobytes())
                merged_doc.close()

        st.success("✅ ¡Proceso completado con Éxito! Estructura generada.")
        st.download_button("⬇️ Descargar Paquete Logístico Completo", zip_buffer.getvalue(), "Logistica_ITA_RADIAN.zip")
