#########################################################################################
#                                                                                       #
#   PLATAFORMA INTEGRAL DE LOGÍSTICA ITA - VERSIÓN 13.3 "CONTROL MANUAL TOTAL"          #
#   AUTOR: YEFREY                                                                       #
#   FECHA: FEBRERO 2026                                                                 #
#                                                                                       #
#   AJUSTE DE LÓGICA V13.3 (CONTROL ESTRICTO):                                          #
#   - Se elimina la "saturación automática" (el sistema ya no reparte solo).            #
#   - Todo lo que no tiene técnico activo va a la "Bolsa Pendiente".                    #
#   - Todo lo que excede el cupo de un técnico va a la "Bolsa Pendiente".               #
#   - En la Pestaña 3, el administrador decide manualmente qué cantidad y a quién       #
#     asignar, viendo claramente qué operarios están libres y cuáles son sus topes.     #
#########################################################################################

import streamlit as st
import fitz  # PyMuPDF: Motor de procesamiento de PDFs
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import os
import shutil
import time
import base64

# =======================================================================================
# SECCIÓN 1: CONFIGURACIÓN VISUAL, ESTILOS Y SESIÓN
# =======================================================================================

st.set_page_config(
    page_title="Logística ITA | v13.3 Control Manual",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Sistema Logístico ITA - Versión 13.3 Bolsa Manual Total"
    }
)

# Inicialización de Variables de Sesión
if 'admin_logged_in' not in st.session_state: st.session_state['admin_logged_in'] = False
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'mapa_telefonos' not in st.session_state: st.session_state['mapa_telefonos'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
if 'tecnicos_activos_manual' not in st.session_state: st.session_state['tecnicos_activos_manual'] = []
if 'ultimo_archivo_procesado' not in st.session_state: st.session_state['ultimo_archivo_procesado'] = None
if 'limites_cupo' not in st.session_state: st.session_state['limites_cupo'] = {}

# Inyección de CSS (Soporte Modo Claro/Oscuro)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
    .stApp { font-family: 'Roboto', sans-serif; }
    
    .logo-container {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 25px; background: linear-gradient(180deg, rgba(100, 116, 139, 0.1) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 16px; border: 1px solid rgba(100, 116, 139, 0.2); margin-bottom: 25px;
    }
    .logo-img { width: 100px; height: auto; filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.4)); transition: transform 0.3s ease; }
    .logo-img:hover { transform: scale(1.05); }
    .logo-text { font-family: 'Roboto', sans-serif; font-weight: 900; font-size: 26px; background: -webkit-linear-gradient(45deg, #0284C7, #4F46E5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-top: 10px; letter-spacing: 1.5px; }
    
    div.stButton > button:first-child { background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%); color: white !important; border-radius: 10px; height: 52px; width: 100%; font-size: 16px; font-weight: 700; border: 1px solid #1D4ED8; box-shadow: 0 4px 6px rgba(0,0,0,0.2); text-transform: uppercase; }
    div.stButton > button:first-child:hover { background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); transform: translateY(-1px); }
    div.stDownloadButton > button:first-child { background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white !important; border-radius: 10px; height: 58px; width: 100%; font-size: 17px; font-weight: 700; border: 1px solid #059669; }
    div.stDownloadButton > button:first-child:hover { background: linear-gradient(135deg, #10B981 0%, #059669 100%); }

    .locked-msg { background-color: #FEE2E2; color: #991B1B; padding: 15px; border-radius: 8px; border: 1px solid #F87171; text-align: center; font-weight: bold; }
    .unlocked-msg { background-color: #D1FAE5; color: #065F46; padding: 10px; border-radius: 8px; border: 1px solid #34D399; text-align: center; margin-top: 10px; font-weight: bold; }
    .tech-header { font-size: 32px; font-weight: 800; background: -webkit-linear-gradient(0deg, #0284C7, #4F46E5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #38BDF8; padding-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# =======================================================================================
# SECCIÓN 2: GESTIÓN DE SISTEMA DE ARCHIVOS (PERSISTENCIA WEB)
# =======================================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_sistema_archivos(accion="iniciar"):
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try: os.makedirs(CARPETA_PUBLICA)
            except OSError as e: st.error(f"Error: {e}")
    elif accion == "limpiar":
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                time.sleep(0.2)
                os.makedirs(CARPETA_PUBLICA)
            except Exception:
                try:
                    for filename in os.listdir(CARPETA_PUBLICA):
                        file_path = os.path.join(CARPETA_PUBLICA, filename)
                        if os.path.isfile(file_path): os.unlink(file_path)
                        elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except: pass
        else: os.makedirs(CARPETA_PUBLICA)

gestionar_sistema_archivos("iniciar")

# =======================================================================================
# SECCIÓN 3: FUNCIONES DE NORMALIZACIÓN Y LÓGICA CORE
# =======================================================================================

def limpiar_estricto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    if not txt: return ""
    txt_str = str(txt)
    if txt_str.endswith('.0'): txt_str = txt_str[:-2]
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    if not barrio_input: return "SIN_ASIGNAR"
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: return "SIN_ASIGNAR"
    
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL|CONJUNTO)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    for k, v in mapa_barrios.items():
        if len(k) > 4 and k in b_raw: return v
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    mapa, telefonos = {}, {}
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
            
        df.columns = [str(c).upper().strip() for c in df.columns]
        col_barrio = next((c for c in df.columns if 'BARRIO' in c or 'SECTOR' in c), None)
        col_tecnico = next((c for c in df.columns if 'TECNICO' in c or 'OPERARIO' in c or 'NOMBRE' in c), None)
        col_celular = next((c for c in df.columns if 'CEL' in c or 'TEL' in c or 'MOVIL' in c), None)

        if not col_barrio or not col_tecnico:
            st.error("❌ El archivo debe tener columnas 'BARRIO' y 'TECNICO'.")
            return {}, {}

        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[col_barrio]))
            t = str(row[col_tecnico]).upper().strip()
            if t and t != "NAN" and b: 
                mapa[b] = t
                if col_celular and pd.notna(row[col_celular]):
                    tel = normalizar_numero(row[col_celular])
                    if tel: telefonos[t] = tel
    except Exception as e:
        st.error(f"Error leyendo maestro: {str(e)}")
        return {}, {}
    return mapa, telefonos

def procesar_pdf_polizas_avanzado(file_obj):
    file_obj.seek(0)
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    diccionario_extraido = {}
    total_paginas = len(doc)
    
    for i in range(total_paginas):
        texto_pagina = doc[i].get_text()
        matches = re.findall(r'(?:Póliza|Poliza|Cuenta)\D{0,20}(\d{4,15})', texto_pagina, re.IGNORECASE)
        if matches:
            sub_doc = fitz.open()
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
            if i + 1 < total_paginas:
                texto_siguiente = doc[i+1].get_text()
                if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                    sub_doc.insert_pdf(doc, from_page=i+1, to_page=i+1)
            pdf_bytes = sub_doc.tobytes()
            sub_doc.close()
            for m in matches: diccionario_extraido[normalizar_numero(m)] = pdf_bytes
    return diccionario_extraido

# =======================================================================================
# SECCIÓN 4: GENERACIÓN DE DOCUMENTOS PDF (FPDF)
# =======================================================================================

class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista_final(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha = datetime.now().strftime('%d/%m/%Y')
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha} | TOTAL VISITAS: {len(df)}", 0, 1)
    
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        barrio_txt = str(row[col_map['BARRIO']])
        # Si origen_real tiene datos y no es el propio técnico ideal, es apoyo
        if pd.notna(row.get('ORIGEN_REAL')) and str(row.get('ORIGEN_REAL')) != tecnico:
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)

        def get_s(k):
            c = col_map.get(k)
            return str(row[c]) if c and c != "NO TIENE" else ""

        row_data = [str(idx), get_s('CUENTA'), get_s('MEDIDOR')[:15], barrio_txt[:38], get_s('DIRECCION')[:60], get_s('CLIENTE')[:30]]
        for val, w in zip(row_data, widths):
            try: val_e = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_e = val
            pdf.cell(w, 7, val_e, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# =======================================================================================
# SECCIÓN 5: BARRA LATERAL INTELIGENTE Y SEGURA
# =======================================================================================

with st.sidebar:
    st.markdown("""
        <div class="logo-container">
            <img src="https://cdn-icons-png.flaticon.com/512/2942/2942813.png" class="logo-img">
            <p class="logo-text">ITA RADIAN</p>
        </div>
    """, unsafe_allow_html=True)
    
    modo_acceso = st.selectbox("PERFIL DE ACCESO", ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"], index=0)
    st.markdown("---")
    
    if modo_acceso == "⚙️ ADMINISTRADOR":
        if st.session_state.get('admin_logged_in', False):
            if st.session_state['mapa_actual']:
                st.markdown("### 📋 Gestión de Asistencia")
                st.info("Desmarca a los técnicos ausentes.")
                todos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
                seleccion_activos = st.multiselect("Técnicos Habilitados:", options=todos_tecnicos, default=todos_tecnicos, key="widget_asistencia_dinamico")
                st.session_state['tecnicos_activos_manual'] = seleccion_activos
                inactivos = len(todos_tecnicos) - len(seleccion_activos)
                if inactivos > 0: st.error(f"🔴 {inactivos} Técnicos INACTIVOS")
                else: st.success("🟢 Cuadrilla Completa")
            else:
                st.caption("ℹ️ Carga el Maestro en Pestaña 1 para habilitar este panel.")
        else:
            st.markdown("""<div class="locked-msg">🔒 MENÚ BLOQUEADO<br>Inicia sesión.</div>""", unsafe_allow_html=True)

    elif modo_acceso == "👷 TÉCNICO":
        st.info("Bienvenido al Portal de Autogestión v13.3")

    st.markdown("---")
    st.caption("Sistema Logístico Seguro v13.3")

# =======================================================================================
# SECCIÓN 6: VISTA DEL TÉCNICO (PORTAL DE DESCARGAS)
# =======================================================================================

if modo_acceso == "👷 TÉCNICO":
    st.markdown('<div class="tech-header">ZONA DE DESCARGAS</div>', unsafe_allow_html=True)
    
    tecnicos_list = []
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_list = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    
    if not tecnicos_list:
        col_c = st.columns([1, 2, 1])
        with col_c[1]:
            st.warning("⏳ Las rutas del día aún no están disponibles.")
            if st.button("🔄 Consultar Nuevamente", type="secondary"): st.rerun()
    else:
        col_espacio1, col_centro, col_espacio2 = st.columns([1, 2, 1])
        with col_centro: seleccion = st.selectbox("👇 SELECCIONA TU NOMBRE:", ["-- Seleccionar --"] + tecnicos_list)
        
        if seleccion != "-- Seleccionar --":
            path_tec = os.path.join(CARPETA_PUBLICA, seleccion)
            f_ruta = os.path.join(path_tec, "1_HOJA_DE_RUTA.pdf")
            f_leg = os.path.join(path_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown(f"<h3 style='text-align:center; color:#0284C7; margin-top:20px;'>Hola, <span>{seleccion}</span></h3>", unsafe_allow_html=True)
            st.write("")
            c_izq, c_der = st.columns(2)
            
            with c_izq:
                st.markdown("""<div style='background:#1E293B; padding:20px; border-radius:10px; border-left:5px solid #38BDF8;'><h4 style='color:#38BDF8; margin:0;'>📄 1. Hoja de Ruta</h4><p style='color:#F8FAFC; margin:5px 0 0 0;'>Listado de visitas y clientes.</p></div>""", unsafe_allow_html=True)
                if os.path.exists(f_ruta):
                    with open(f_ruta, "rb") as f: st.download_button("⬇️ DESCARGAR RUTA", f, f"Ruta_{seleccion}.pdf", "application/pdf", key="d_ruta", use_container_width=True)
                else: st.error("No disponible")
                
            with c_der:
                st.markdown("""<div style='background:#1E293B; padding:20px; border-radius:10px; border-left:5px solid #34D399;'><h4 style='color:#34D399; margin:0;'>📂 2. Legalización</h4><p style='color:#F8FAFC; margin:5px 0 0 0;'>Paquete de Pólizas.</p></div>""", unsafe_allow_html=True)
                if os.path.exists(f_leg):
                    with open(f_leg, "rb") as f: st.download_button("⬇️ DESCARGAR PAQUETE", f, f"Leg_{seleccion}.pdf", "application/pdf", key="d_leg", use_container_width=True)
                else: st.info("Hoy no tienes pólizas.")

# =======================================================================================
# SECCIÓN 7: VISTA DEL ADMINISTRADOR (PANEL DE GESTIÓN)
# =======================================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    if not st.session_state.get('admin_logged_in', False):
        col_login_spacer1, col_login, col_login_spacer2 = st.columns([1, 1, 1])
        with col_login:
            st.markdown("<h2 style='text-align: center;'>🔐 Acceso Administrativo</h2>", unsafe_allow_html=True)
            password = st.text_input("Contraseña:", type="password", placeholder="Ingresa tu clave aquí...")
            if st.button("INGRESAR AL SISTEMA", type="primary"):
                if password == "ita2026":
                    st.session_state['admin_logged_in'] = True
                    st.success("✅ Acceso Concedido")
                    st.rerun()
                else: st.error("❌ Contraseña Incorrecta")
    else:
        col_tit, col_logout = st.columns([4, 1])
        with col_tit: st.markdown("## ⚙️ Panel Maestro de Logística")
        with col_logout:
            if st.button("Cerrar Sesión"):
                st.session_state['admin_logged_in'] = False
                st.rerun()
        
        tab1, tab2, tab3, tab4 = st.tabs(["1. 🗃️ Base Operarios", "2. ⚖️ Carga & Asignación Base", "3. 🛠️ Ajuste Manual Total", "4. 🌍 Publicación Final"])
        
        # --- TAB 1: CARGA DE MAESTRO ---
        with tab1:
            st.markdown("### Acciones de Mantenimiento")
            col_reset, col_explain = st.columns([1, 2])
            with col_reset:
                if st.button("🗑️ REINICIAR SISTEMA (NUEVA OPERACIÓN)", type="primary"):
                    st.session_state['mapa_actual'] = {}
                    st.session_state['mapa_telefonos'] = {}
                    st.session_state['df_simulado'] = None
                    st.session_state['col_map_final'] = None
                    st.session_state['mapa_polizas_cargado'] = {}
                    st.session_state['zip_admin_ready'] = None
                    st.session_state['tecnicos_activos_manual'] = []
                    st.session_state['ultimo_archivo_procesado'] = None
                    st.session_state['limites_cupo'] = {}
                    st.success("✅ Sistema reseteado correctamente. Memoria limpia.")
                    time.sleep(1)
                    st.rerun()
            with col_explain:
                st.caption("⚠️ Úsalo antes de cargar un nuevo archivo maestro para evitar cruce de datos.")

            st.divider()
            st.markdown("### Configuración de Zonas y Técnicos")
            f_maestro = st.file_uploader("Subir Maestro (Excel/CSV)", type=["xlsx", "csv"])
            
            if f_maestro:
                if st.session_state.get('ultimo_archivo_procesado') != f_maestro.name:
                    with st.spinner("Indexando base de datos y limpiando memoria anterior..."):
                        nuevo_mapa, nuevos_telefonos = cargar_maestro_dinamico(f_maestro)
                        if nuevo_mapa:
                            st.session_state['mapa_actual'] = nuevo_mapa
                            st.session_state['mapa_telefonos'] = nuevos_telefonos
                            st.session_state['df_simulado'] = None 
                            st.session_state['tecnicos_activos_manual'] = []
                            st.session_state['ultimo_archivo_procesado'] = f_maestro.name
                            st.success(f"✅ Maestro cargado con éxito: {len(nuevo_mapa)} barrios detectados.")
                            time.sleep(1)
                            st.rerun() 
                        else: st.error("❌ Error en el archivo: No se encontraron columnas válidas.")
                else: st.info(f"Archivo activo: {f_maestro.name}")
            
            if st.session_state['mapa_actual']:
                st.write(f"**Total Barrios:** {len(st.session_state['mapa_actual'])}")
                st.write(f"**Total Técnicos:** {len(set(st.session_state['mapa_actual'].values()))}")

        # --- TAB 2: PROCESO DIARIO ---
        with tab2:
            st.markdown("### Carga de Insumos del Día")
            
            c_pdf, c_xls = st.columns(2)
            with c_pdf:
                st.markdown("**1. Pólizas (PDF)**")
                up_pdf = st.file_uploader("Archivo PDF Pólizas", type="pdf")
                if up_pdf and st.button("Escanear PDF"):
                    with st.spinner("Procesando..."):
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                        st.success(f"✅ {len(st.session_state['mapa_polizas_cargado'])} Pólizas extraídas.")

            with c_xls:
                st.markdown("**2. Ruta (Excel)**")
                up_xls = st.file_uploader("Archivo Excel Ruta", type=["xlsx", "csv"])
            
            if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                tecnicos_hoy = st.session_state['tecnicos_activos_manual']
            elif st.session_state['mapa_actual']:
                tecnicos_hoy = sorted(list(set(st.session_state['mapa_actual'].values())))
            else: tecnicos_hoy = []

            if up_xls and tecnicos_hoy:
                if up_xls.name.endswith('.csv'): df = pd.read_csv(up_xls, sep=None, engine='python', encoding='utf-8-sig')
                else: df = pd.read_excel(up_xls)
                
                # CORRECCIÓN COLUMNAS DUPLICADAS
                cols = []
                for c in df.columns:
                    c_str = str(c).strip()
                    if c_str not in cols: cols.append(c_str)
                
                st.divider()
                st.markdown("#### Parámetros de Balanceo (Cupos)")
                st.info("Define el límite por técnico. Lo que exceda se irá a la Bolsa Manual.")
                df_cup = pd.DataFrame({"Técnico": tecnicos_hoy, "Cupo": [35]*len(tecnicos_hoy)})
                ed_cup = st.data_editor(df_cup, column_config={"Cupo": st.column_config.NumberColumn(min_value=1)}, hide_index=True, use_container_width=True)
                LIMITES = dict(zip(ed_cup["Técnico"], ed_cup["Cupo"]))
                
                def buscar_col(palabras_clave, opcional=False):
                    for i, col_name in enumerate(cols):
                        for palabra in palabras_clave:
                            if palabra in col_name.upper():
                                return i + 1 if opcional else i
                    return 0
                
                c1, c2, c3 = st.columns(3)
                sb = c1.selectbox("Barrio", cols, index=buscar_col(['BARRIO']) if cols else 0)
                sd = c2.selectbox("Dirección", cols, index=buscar_col(['DIR','DIRECCION']) if cols else 0)
                sc = c3.selectbox("Cuenta", cols, index=buscar_col(['CUENTA']) if cols else 0)
                
                opciones_opcionales = ["NO TIENE"] + cols
                sm = st.selectbox("Medidor", opciones_opcionales, index=buscar_col(['MEDIDOR'], True))
                sl = st.selectbox("Cliente", opciones_opcionales, index=buscar_col(['CLIENTE'], True))
                
                cmap = {'BARRIO': sb, 'DIRECCION': sd, 'CUENTA': sc, 'MEDIDOR': sm if sm!="NO TIENE" else None, 'CLIENTE': sl if sl!="NO TIENE" else None}
                
                if st.button("🚀 EJECUTAR ASIGNACIÓN BASE Y CREAR BOLSA MANUAL", type="primary"):
                    if up_pdf and not st.session_state['mapa_polizas_cargado']:
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                    
                    # Guardamos límites en sesión para usarlos en Pestaña 3
                    st.session_state['limites_cupo'] = LIMITES
                    
                    df_proc = df.copy()
                    
                    # 1. Asignar Idealmente
                    df_proc['TECNICO_IDEAL'] = df_proc[sb].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                    df_proc['TECNICO_FINAL'] = df_proc['TECNICO_IDEAL']
                    df_proc['ORIGEN_REAL'] = None # Solo se usará para rastrear de dónde vino el apoyo
                    
                    # 2. Ordenar Alfabéticamente las Calles
                    df_proc['S'] = df_proc[sd].astype(str).apply(natural_sort_key)
                    df_proc = df_proc.sort_values(by=[sb, 'S'])

                    # =========================================================
                    # LÓGICA V13.3: TODO A LA BOLSA (Sin Técnico y Excedentes)
                    # =========================================================
                    
                    # A. Los que NO tienen técnico activo hoy -> A LA BOLSA
                    msk_sin_tecnico = ~df_proc['TECNICO_FINAL'].isin(tecnicos_hoy)
                    df_proc.loc[msk_sin_tecnico, 'ORIGEN_REAL'] = "SIN TÉCNICO ACTIVO"
                    df_proc.loc[msk_sin_tecnico, 'TECNICO_FINAL'] = "⚠️ BOLSA PENDIENTE"
                    
                    # B. Los técnicos activos que EXCEDEN su cupo -> Excedente A LA BOLSA
                    for tech in tecnicos_hoy:
                        tope = LIMITES.get(tech, 35)
                        idx_tech = df_proc[df_proc['TECNICO_FINAL'] == tech].index
                        
                        if len(idx_tech) > tope:
                            excedente = len(idx_tech) - tope
                            # Tomamos los últimos registros para enviarlos a la bolsa
                            indices_mover = idx_tech[-excedente:]
                            df_proc.loc[indices_mover, 'ORIGEN_REAL'] = f"EXCEDE CUPO ({tech})"
                            df_proc.loc[indices_mover, 'TECNICO_FINAL'] = "⚠️ BOLSA PENDIENTE"

                    st.session_state['df_simulado'] = df_proc.drop(columns=['S'])
                    st.session_state['col_map_final'] = cmap
                    st.success("✅ Asignación lista. Los huérfanos y excedentes están en la Pestaña 3 (Ajuste Manual).")

            elif not tecnicos_hoy and st.session_state['mapa_actual']:
                st.error("⚠️ No hay técnicos activos. Revisa la barra lateral.")

        # --- TAB 3: AJUSTE MANUAL (CANTIDAD Y BOLSA) ---
        with tab3:
            st.markdown("### 🛠️ Ajuste Manual y Reparto de Bolsa")
            if st.session_state['df_simulado'] is not None:
                df = st.session_state['df_simulado']
                cbar = st.session_state['col_map_final']['BARRIO']
                limites = st.session_state.get('limites_cupo', {})
                
                if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                    todos_activos_hoy = sorted(st.session_state['tecnicos_activos_manual'])
                else:
                    todos_activos_hoy = sorted(list(set(st.session_state['mapa_actual'].values())))

                # 1. MOSTRAR LA GRAN BOLSA PENDIENTE
                bolsa_df = df[df['TECNICO_FINAL'] == "⚠️ BOLSA PENDIENTE"]
                if not bolsa_df.empty:
                    st.warning(f"🚨 Tienes {len(bolsa_df)} visitas en la BOLSA pendientes por asignar (Sin técnico o Excedentes).")
                    resumen_bolsa = bolsa_df.groupby([cbar, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='Cantidad Pendiente')
                    st.dataframe(resumen_bolsa, use_container_width=True, hide_index=True)
                else:
                    st.success("🎉 ¡Bolsa vacía! Todas las visitas están asignadas.")
                
                st.divider()
                st.markdown("#### 🔄 Mover Visitas")
                
                activos_con_carga = sorted(df['TECNICO_FINAL'].unique())
                opciones_destino = ["-", "⚠️ BOLSA PENDIENTE"] + todos_activos_hoy
                
                c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1.5, 1, 1])
                with c1: org = st.selectbox("De:", ["-"] + list(activos_con_carga))
                with c2: 
                    if org != "-":
                        brs = df[df['TECNICO_FINAL']==org][cbar].value_counts()
                        bar = st.selectbox("Barrio:", [f"{k} ({v})" for k,v in brs.items()])
                    else: bar=None
                with c3: dst = st.selectbox("Para:", opciones_destino)
                with c4:
                    if bar:
                        max_cant = int(bar.split("(")[1].replace(")",""))
                        cant = st.number_input("Cantidad", min_value=1, max_value=max_cant, value=max_cant)
                    else:
                        cant = 1
                with c5:
                    st.write("")
                    if st.button("Mover Manualmente", use_container_width=True):
                        if bar and dst != "-" and org != dst:
                            rb = bar.rsplit(" (",1)[0]
                            # Seleccionar la cantidad exacta a mover
                            idx_to_move = df[(df['TECNICO_FINAL']==org) & (df[cbar]==rb)].head(cant).index
                            
                            for idx in idx_to_move:
                                # Si viene de la bolsa o se asigna manualmente entre técnicos, guardamos origen
                                # para que aparezca la etiqueta [APOYO] en el PDF, excepto si vuelve a la Bolsa
                                if dst != "⚠️ BOLSA PENDIENTE" and org == "⚠️ BOLSA PENDIENTE":
                                    # Cuando sale de la bolsa a un técnico
                                    df.loc[idx, 'ORIGEN_REAL'] = df.loc[idx, 'TECNICO_IDEAL']
                                elif dst != "⚠️ BOLSA PENDIENTE" and org != "⚠️ BOLSA PENDIENTE":
                                    # Cuando se mueve entre técnicos directamente
                                    df.loc[idx, 'ORIGEN_REAL'] = org
                                    
                                df.loc[idx, 'TECNICO_FINAL'] = dst
                                
                            st.session_state['df_simulado'] = df
                            st.rerun()
                
                st.divider()
                st.markdown("#### 👷 Estado de Cuadrilla (Visitas / Cupo Máximo)")
                # GRID DE VISUALIZACIÓN CON INDICADOR DE CUPO
                cls = st.columns(2)
                for i, t in enumerate(todos_activos_hoy):
                    with cls[i%2]:
                        s = df[df['TECNICO_FINAL']==t]
                        cantidad = len(s)
                        tope = limites.get(t, 35)
                        
                        if cantidad == 0:
                            titulo_card = f"🟢 {t} (LIBRE - 0 / {tope})"
                        elif cantidad > tope:
                            titulo_card = f"🔴 {t} ({cantidad} / {tope} - SOBRESATURADO)"
                        else:
                            titulo_card = f"👷 {t} ({cantidad} / {tope})"
                            
                        with st.expander(titulo_card, expanded=(cantidad > 0)):
                            if cantidad > 0:
                                r = s.groupby([cbar, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='N')
                                # Solo mostrar advertencia visual si es realmente apoyo
                                def format_barrio(row):
                                    es_apoyo = pd.notna(row['ORIGEN_REAL']) and str(row['ORIGEN_REAL']) != t and row['ORIGEN_REAL'] != "SIN TÉCNICO ACTIVO"
                                    if es_apoyo: return f"⚠️ {row[cbar]} (Apoyo)"
                                    return row[cbar]
                                    
                                r['B'] = r.apply(format_barrio, axis=1)
                                st.dataframe(r[['B','N']], hide_index=True, use_container_width=True)
                            else:
                                st.caption("Disponible para recibir carga completa de la Bolsa.")
            else: st.info("Sin datos de ruta procesados.")

        # --- TAB 4: PUBLICAR ---
        with tab4:
            st.markdown("### 🌍 Distribución")
            if st.session_state['df_simulado'] is not None:
                dff = st.session_state['df_simulado']
                
                # Validar que no queden excedentes antes de publicar
                excedentes_pendientes = len(dff[dff['TECNICO_FINAL'] == "⚠️ BOLSA PENDIENTE"])
                if excedentes_pendientes > 0:
                    st.error(f"⚠️ Atención: Aún tienes {excedentes_pendientes} visitas en la 'Bolsa Pendiente'. Ve a la Pestaña 3 para asignarlas manualmente a los operarios libres antes de publicar.")
                else:
                    cmf = st.session_state['col_map_final']
                    pls = st.session_state['mapa_polizas_cargado']
                    tfin = [t for t in dff['TECNICO_FINAL'].unique() if "SIN_" not in t and "⚠️" not in t]
                    
                    if st.button("📢 PUBLICAR EN PORTAL WEB", type="primary"):
                        gestionar_sistema_archivos("limpiar")
                        pg = st.progress(0)
                        for i, t in enumerate(tfin):
                            dt = dff[dff['TECNICO_FINAL']==t].copy()
                            dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                            dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                            
                            safe = str(t).replace(" ","_")
                            pto = os.path.join(CARPETA_PUBLICA, safe); os.makedirs(pto, exist_ok=True)
                            
                            with open(os.path.join(pto, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                                f.write(crear_pdf_lista_final(dt, t, cmf))
                            
                            if pls:
                                mg = fitz.open(); n=0
                                for _,r in dt.iterrows():
                                    c = normalizar_numero(str(r[cmf['CUENTA']]))
                                    if c in pls:
                                        with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                        n+=1
                                if n>0:
                                    with open(os.path.join(pto, "3_PAQUETE_LEGALIZACION.pdf"), "wb") as f: f.write(mg.tobytes())
                                mg.close()
                            pg.progress((i+1)/len(tfin))
                        st.success("✅ Publicado en Web.")
                        st.balloons()
                    
                    st.divider()
                    st.markdown("#### 📦 Descargas Administrativas")
                    
                    if st.button("GENERAR ZIP MAESTRO COMPLETO"):
                        bf = io.BytesIO()
                        with zipfile.ZipFile(bf,"w") as z:
                            if pls:
                                for k,v in pls.items(): z.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                            
                            out = io.BytesIO(); 
                            with pd.ExcelWriter(out, engine='xlsxwriter') as w: dff.to_excel(w, index=False)
                            z.writestr("00_CONSOLIDADO.xlsx", out.getvalue())
                            
                            for t in tfin:
                                safe = str(t).replace(" ","_")
                                dt = dff[dff['TECNICO_FINAL']==t].copy()
                                dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                                dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                                
                                z.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista_final(dt, t, cmf))
                                
                                ot = io.BytesIO()
                                with pd.ExcelWriter(ot, engine='xlsxwriter') as w: dt.to_excel(w, index=False)
                                z.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", ot.getvalue())
                                
                                if pls:
                                    mg = fitz.open(); n=0
                                    for _,r in dt.iterrows():
                                        c = normalizar_numero(str(r[cmf['CUENTA']]))
                                        if c in pls:
                                            z.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{c}.pdf", pls[c])
                                            with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                            n+=1
                                    if n>0: z.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", mg.tobytes())
                                    mg.close()
                                    
                        st.session_state['zip_admin_ready'] = bf.getvalue()
                        st.success("ZIP Creado.")
                    
                    if st.session_state['zip_admin_ready']:
                        st.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_admin_ready'], "Logistica_Total.zip", "application/zip")

            else: st.info("Pendiente procesar ruta.")
