#################################################################################
#                                                                               #
#   SISTEMA DE GESTIÓN LOGÍSTICA ITA - PLATAFORMA INTEGRAL (WEB + GESTIÓN)      #
#   VERSIÓN: 8.0 INFINITY (FULL BLINDADA)                                       #
#   AUTOR: YEFREY                                                               #
#                                                                               #
#   MÓDULOS INCLUIDOS (SIN RECORTES):                                           #
#   1.  CORE: Algoritmos de limpieza y ordenamiento natural (Tuplas).           #
#   2.  ADMINISTRACIÓN:                                                         #
#       - Carga Dinámica de Maestros.                                           #
#       - Control de Asistencia (Aparece SOLO al cargar datos).                 #
#       - Balanceo Automático Inteligente.                                      #
#       - AJUSTE MANUAL (Visor de Movimientos).                                 #
#   3.  GENERACIÓN DOCUMENTAL:                                                  #
#       - PDF Hoja de Ruta (Diseño Corporativo).                                #
#       - ZIP Maestro Administrativo (Estructura de 4 Carpetas + Banco).        #
#   4.  PORTAL WEB:                                                             #
#       - Interfaz para Técnicos (Solo descarga necesaria).                     #
#                                                                               #
#################################################################################

import streamlit as st
import fitz  # PyMuPDF para manipulación de PDFs
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

# ===============================================================================
#  SECCIÓN 1: CONFIGURACIÓN VISUAL Y ESTILOS (UI/UX PREMIUM)
# ===============================================================================

st.set_page_config(
    page_title="Logística ITA | Infinity v8.0",
    layout="wide",
    page_icon="🚛",
    initial_sidebar_state="expanded"
)

# Inyección de CSS Avanzado
st.markdown("""
    <style>
    /* FUENTES Y FONDO */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap');
    
    .stApp { 
        background-color: #0B1120; /* Azul muy oscuro (Night) */
        color: #E2E8F0; 
        font-family: 'Roboto', sans-serif;
    }
    
    /* SIDEBAR PERSONALIZADA */
    section[data-testid="stSidebar"] {
        background-color: #111827; /* Gris oscuro */
        border-right: 1px solid #1F2937;
    }
    
    /* LOGO CONTAINER */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px 10px;
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #334155;
    }
    .logo-img {
        width: 100px;
        height: auto;
        filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.5));
        margin-bottom: 10px;
    }
    .logo-text {
        font-weight: 900;
        font-size: 24px;
        color: #38BDF8;
        letter-spacing: 2px;
        margin: 0;
    }
    
    /* PESTAÑAS (TABS) */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        background-color: #1F2937;
        padding: 8px;
        border-radius: 12px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
    }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        background-color: transparent; 
        color: #94A3B8; 
        border: none;
        font-weight: 600;
        font-size: 15px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* DATAFRAMES */
    div[data-testid="stDataFrame"] { 
        background-color: #1F2937; 
        border-radius: 10px; 
        padding: 10px; 
        border: 1px solid #374151;
    }
    
    /* BOTONES DE ACCIÓN (AZULES) */
    div.stButton > button:first-child { 
        background: linear-gradient(90deg, #2563EB 0%, #3B82F6 100%);
        color: white; 
        border-radius: 8px; 
        height: 50px; 
        width: 100%; 
        font-size: 16px; 
        font-weight: 800; 
        border: none;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:first-child:hover { 
        background: linear-gradient(90deg, #1D4ED8 0%, #2563EB 100%);
        transform: scale(1.01);
        box-shadow: 0 0 15px rgba(37, 99, 235, 0.4);
    }
    
    /* BOTONES DE DESCARGA (VERDES) */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(90deg, #059669 0%, #10B981 100%);
        color: white; 
        border-radius: 8px; 
        height: 60px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: 700; 
        border: 1px solid #34D399;
    }
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(90deg, #047857 0%, #059669 100%);
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }

    /* CARD DE ESTADO */
    .status-card {
        background-color: #1E293B;
        border-left: 5px solid #38BDF8;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .status-title { font-weight: bold; color: #38BDF8; font-size: 1.1em; }
    .status-desc { color: #94A3B8; font-size: 0.9em; margin: 0; }
    
    /* HEADER TÉCNICO */
    .tech-title {
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        background: -webkit-linear-gradient(0deg, #34D399, #38BDF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ===============================================================================
#  SECCIÓN 2: GESTIÓN DE DIRECTORIOS Y ARCHIVOS
# ===============================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_sistema_archivos(accion="iniciar"):
    """
    Controlador maestro del sistema de archivos.
    Evita conflictos de permisos y asegura que la carpeta pública exista.
    """
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try:
                os.makedirs(CARPETA_PUBLICA)
            except OSError as e:
                st.error(f"Error crítico del sistema de archivos: {e}")
                
    elif accion == "limpiar":
        # Borrado recursivo seguro
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                time.sleep(0.1) # Pausa técnica para liberar handles
                os.makedirs(CARPETA_PUBLICA)
            except Exception as e:
                # Fallback: intentar borrar contenido interno si la carpeta está bloqueada
                try:
                    for filename in os.listdir(CARPETA_PUBLICA):
                        file_path = os.path.join(CARPETA_PUBLICA, filename)
                        if os.path.isfile(file_path): os.unlink(file_path)
                        elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except: pass
        else:
            os.makedirs(CARPETA_PUBLICA)

# Inicialización obligatoria
gestionar_sistema_archivos("iniciar")

# ===============================================================================
#  SECCIÓN 3: FUNCIONES CORE (LIMPIEZA, ORDENAMIENTO, BÚSQUEDA)
# ===============================================================================

def limpiar_estricto(txt):
    """Normalización de cadenas para cruces de datos exactos."""
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """Limpia números de póliza/celular quitando basura y decimales de Excel."""
    if not txt: return ""
    txt_str = str(txt)
    if txt_str.endswith('.0'): txt_str = txt_str[:-2]
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """
    Algoritmo de Ordenamiento Natural.
    Clave para que 'Calle 2' aparezca antes que 'Calle 10'.
    """
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """
    Motor de búsqueda de técnico por barrio.
    Estrategia en cascada: Exacta -> Flexible -> Parcial.
    """
    if not barrio_input: return "SIN_ASIGNAR"
    
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: return "SIN_ASIGNAR"
    
    # 1. Exacto
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 2. Flexible (sin prefijos comunes)
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL|CONJUNTO)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 3. Parcial (Contención segura)
    for k, v in mapa_barrios.items():
        if len(k) > 4 and k in b_raw: return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """
    Lee el archivo maestro y extrae la relación Barrio -> Técnico.
    Soporta CSV y Excel. Detecta columnas automáticamente.
    """
    mapa = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        if len(df.columns) < 2: return {}
            
        c_barrio = df.columns[0]
        c_tecnico = df.columns[1]

        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_barrio]))
            t = str(row[c_tecnico]).upper().strip()
            
            if t and t != "NAN" and b: 
                mapa[b] = t
                
    except Exception as e:
        st.error(f"Error en maestro: {str(e)}")
        return {}
        
    return mapa

def procesar_pdf_polizas_avanzado(file_obj):
    """Escanea PDF y separa páginas por número de póliza detectado."""
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
            
            # Anexos en página siguiente
            if i + 1 < total_paginas:
                texto_siguiente = doc[i+1].get_text()
                if not re.search(r'(?:Póliza|Poliza|Cuenta)', texto_siguiente, re.IGNORECASE):
                    sub_doc.insert_pdf(doc, from_page=i+1, to_page=i+1)
            
            pdf_bytes = sub_doc.tobytes()
            sub_doc.close()
            
            for m in matches:
                diccionario_extraido[normalizar_numero(m)] = pdf_bytes
                
    return diccionario_extraido

# ===============================================================================
#  SECCIÓN 4: GENERADOR DE PDF (CLASE CORPORATIVA)
# ===============================================================================

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
        if pd.notna(row.get('ORIGEN_REAL')):
            barrio_txt = f"[APOYO] {barrio_txt}"
            pdf.set_text_color(200, 0, 0) # Rojo
        else:
            pdf.set_text_color(0, 0, 0)

        def get_s(k):
            c = col_map.get(k)
            return str(row[c]) if c and c != "NO TIENE" else ""

        row_data = [
            str(idx), 
            get_s('CUENTA'), 
            get_s('MEDIDOR')[:15], 
            barrio_txt[:38], 
            get_s('DIRECCION')[:60], 
            get_s('CLIENTE')[:30]
        ]
        
        for val, w in zip(row_data, widths):
            try: val_e = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_e = val
            pdf.cell(w, 7, val_e, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ===============================================================================
#  SECCIÓN 5: ESTADO DE SESIÓN (PERSISTENCIA GLOBAL)
# ===============================================================================

if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
# Variable crítica para la asistencia (Lista de técnicos activos)
if 'tecnicos_activos_manual' not in st.session_state: st.session_state['tecnicos_activos_manual'] = []

# ===============================================================================
#  SECCIÓN 6: BARRA LATERAL INTELIGENTE (NAVEGACIÓN Y ASISTENCIA)
# ===============================================================================

with st.sidebar:
    # 1. LOGOTIPO Y MARCA
    st.markdown("""
        <div class="logo-container">
            <img src="https://cdn-icons-png.flaticon.com/512/2942/2942813.png" class="logo-img">
            <p class="logo-text">ITA RADIAN</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. SELECTOR DE ROL
    modo_acceso = st.selectbox(
        "PERFIL DE ACCESO", 
        ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0
    )
    
    st.divider()
    
    # 3. CONTROL DE ASISTENCIA (LÓGICA BLINDADA)
    # Solo se muestra si:
    # A) Eres Administrador
    # B) Ya cargaste la base de datos en la Pestaña 1 (mapa_actual no está vacío)
    if modo_acceso == "⚙️ ADMINISTRADOR":
        
        if st.session_state['mapa_actual']:
            st.markdown("### 📅 Control de Asistencia")
            st.info("Desmarca a quienes NO trabajan hoy. El sistema reasignará sus zonas.")
            
            # Obtener lista completa de técnicos
            todos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
            
            # Widget de Selección
            seleccion_activos = st.multiselect(
                "Técnicos Habilitados:",
                options=todos_tecnicos,
                default=todos_tecnicos,
                key="widget_asistencia_sidebar"
            )
            
            # Guardar en sesión
            st.session_state['tecnicos_activos_manual'] = seleccion_activos
            
            # Feedback visual
            ausentes = len(todos_tecnicos) - len(seleccion_activos)
            if ausentes > 0:
                st.warning(f"🔴 {ausentes} Técnicos Inactivos")
            else:
                st.success("🟢 Cuadrilla Completa")
        else:
            # Si no hay datos, mostramos mensaje placeholder
            st.caption("ℹ️ Carga el Maestro de Operarios para ver la lista de asistencia aquí.")

    elif modo_acceso == "👷 TÉCNICO":
        st.info("Bienvenido al Portal de Autogestión v8.0")

    st.markdown("---")
    st.caption("© 2026 Sistema Logístico ITA")

# ===============================================================================
#  SECCIÓN 7: VISTA DEL TÉCNICO (DESCARGA SEGURA)
# ===============================================================================

if modo_acceso == "👷 TÉCNICO":
    st.markdown('<div class="tech-title">ZONA DE DESCARGAS</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Selecciona tu nombre para acceder a la documentación oficial.</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Verificar archivos
    tecnicos_list = []
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_list = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    
    if not tecnicos_list:
        st.info("🕒 Las rutas aún no están publicadas. Espera la confirmación del Coordinador.")
        if st.button("🔄 Recargar"): st.rerun()
    else:
        # Selector Central
        col_c = st.columns([1, 2, 1])
        with col_c[1]:
            seleccion = st.selectbox("👇 BUSCA TU NOMBRE:", ["-- Seleccionar --"] + tecnicos_list)
        
        if seleccion != "-- Seleccionar --":
            path_base = os.path.join(CARPETA_PUBLICA, seleccion)
            f_ruta = os.path.join(path_base, "1_HOJA_DE_RUTA.pdf")
            f_leg = os.path.join(path_base, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown(f"<h3 style='text-align:center; color:#38BDF8;'>Documentos para: {seleccion}</h3>", unsafe_allow_html=True)
            st.write("")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("""
                <div class="status-card">
                    <span class="status-title">📍 Hoja de Ruta</span>
                    <p class="status-desc">Listado de visitas y direcciones.</p>
                </div>
                """, unsafe_allow_html=True)
                if os.path.exists(f_ruta):
                    with open(f_ruta, "rb") as f:
                        st.download_button("⬇️ DESCARGAR RUTA", f, f"Ruta_{seleccion}.pdf", "application/pdf", key="d1")
                else: st.error("No disponible")
            
            with c2:
                st.markdown("""
                <div class="status-card">
                    <span class="status-title">📂 Legalización</span>
                    <p class="status-desc">Paquete de pólizas y anexos.</p>
                </div>
                """, unsafe_allow_html=True)
                if os.path.exists(f_leg):
                    with open(f_leg, "rb") as f:
                        st.download_button("⬇️ DESCARGAR PAQUETE", f, f"Leg_{seleccion}.pdf", "application/pdf", key="d2")
                else: st.info("Sin pólizas hoy.")

# ===============================================================================
#  SECCIÓN 8: VISTA DEL ADMINISTRADOR (PANEL MAESTRO)
# ===============================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    st.title("⚙️ Panel de Control Logístico")
    
    pwd = st.text_input("🔑 Contraseña:", type="password")
    
    if pwd == "ita2026":
        
        # DEFINICIÓN DE TABS
        tab1, tab2, tab3, tab4 = st.tabs([
            "1. 🗃️ Base Operarios", 
            "2. ⚖️ Carga & Balanceo", 
            "3. 🛠️ Ajuste Manual", 
            "4. 🌍 Publicación"
        ])
        
        # --- TAB 1: BASE DE OPERARIOS ---
        with tab1:
            st.markdown("### Configuración de Zonas")
            f_maestro = st.file_uploader("Subir Maestro (Excel/CSV)", type=["xlsx", "csv"])
            
            if f_maestro:
                with st.spinner("Indexando..."):
                    st.session_state['mapa_actual'] = cargar_maestro_dinamico(f_maestro)
                st.success(f"✅ Maestro cargado: {len(st.session_state['mapa_actual'])} barrios.")
                # Recargar para actualizar la sidebar inmediatamente
                # st.rerun() 

        # --- TAB 2: CARGA Y BALANCEO ---
        with tab2:
            st.markdown("### Procesamiento de Rutas")
            c_pdf, c_xls = st.columns(2)
            
            with c_pdf:
                st.markdown("**1. Pólizas (PDF)**")
                up_pdf = st.file_uploader("Archivo de Pólizas", type="pdf")
                if up_pdf and st.button("Escanear PDF"):
                    with st.spinner("Procesando..."):
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                        st.success(f"✅ {len(st.session_state['mapa_polizas_cargado'])} Pólizas extraídas.")

            with c_xls:
                st.markdown("**2. Ruta Diaria (Excel)**")
                up_xls = st.file_uploader("Archivo de Ruta", type=["xlsx", "csv"])
            
            # Determinar técnicos activos desde la sidebar o todos
            if 'tecnicos_activos_manual' in st.session_state and st.session_state['tecnicos_activos_manual']:
                tecnicos_hoy = st.session_state['tecnicos_activos_manual']
            elif st.session_state['mapa_actual']:
                tecnicos_hoy = sorted(list(set(st.session_state['mapa_actual'].values())))
            else:
                tecnicos_hoy = []

            if up_xls and tecnicos_hoy:
                if up_xls.name.endswith('.csv'): df = pd.read_csv(up_xls, sep=None, engine='python', encoding='utf-8-sig')
                else: df = pd.read_excel(up_xls)
                cols = list(df.columns)
                
                st.divider()
                st.markdown("#### Parámetros de Balanceo")
                
                # Cupos
                df_cup = pd.DataFrame({"Técnico": tecnicos_hoy, "Cupo": [35]*len(tecnicos_hoy)})
                ed_cup = st.data_editor(df_cup, column_config={"Cupo": st.column_config.NumberColumn(min_value=1)}, hide_index=True, use_container_width=True)
                LIMITES = dict(zip(ed_cup["Técnico"], ed_cup["Cupo"]))
                
                # Mapeo
                def ix(k): 
                    for i,c in enumerate(cols): 
                        for x in k: 
                            if x in str(c).upper(): return i
                    return 0
                
                c1, c2, c3 = st.columns(3)
                sb = c1.selectbox("Barrio", cols, index=ix(['BARRIO']))
                sd = c2.selectbox("Dirección", cols, index=ix(['DIR','DIRECCION']))
                sc = c3.selectbox("Cuenta", cols, index=ix(['CUENTA']))
                sm = st.selectbox("Medidor", ["NO TIENE"]+cols, index=ix(['MEDIDOR'])+1)
                sl = st.selectbox("Cliente", ["NO TIENE"]+cols, index=ix(['CLIENTE'])+1)
                cmap = {'BARRIO': sb, 'DIRECCION': sd, 'CUENTA': sc, 'MEDIDOR': sm if sm!="NO TIENE" else None, 'CLIENTE': sl if sl!="NO TIENE" else None}
                
                if st.button("🚀 EJECUTAR BALANCEO", type="primary"):
                    # Auto-scan PDF
                    if up_pdf and not st.session_state['mapa_polizas_cargado']:
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                    
                    df_proc = df.copy()
                    
                    # 1. Asignar Ideal
                    df_proc['TECNICO_IDEAL'] = df_proc[sb].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                    
                    # 2. Manejo de Inactivos
                    # Si el tecnico ideal NO esta en la lista de 'tecnicos_hoy', se marca como VACANTE
                    df_proc['TECNICO_FINAL'] = df_proc['TECNICO_IDEAL'].apply(lambda x: x if x in tecnicos_hoy else "VACANTE")
                    df_proc['ORIGEN_REAL'] = None
                    
                    # Marcar origen para los vacantes
                    mask_vac = df_proc['TECNICO_FINAL'] == "VACANTE"
                    df_proc.loc[mask_vac, 'ORIGEN_REAL'] = df_proc.loc[mask_vac, 'TECNICO_IDEAL']
                    
                    # 3. Ordenar
                    df_proc['S'] = df_proc[sd].astype(str).apply(natural_sort_key)
                    df_proc = df_proc.sort_values(by=[sb, 'S'])
                    
                    # 4. Repartir Vacantes (A quien menos tiene)
                    vacantes = df_proc[df_proc['TECNICO_FINAL'] == "VACANTE"]
                    for idx_v, _ in vacantes.iterrows():
                        # Contar carga actual de los presentes
                        conteo_live = df_proc[df_proc['TECNICO_FINAL'].isin(tecnicos_hoy)]['TECNICO_FINAL'].value_counts()
                        # Asegurar ceros
                        for t in tecnicos_hoy:
                            if t not in conteo_live: conteo_live[t] = 0
                        
                        mejor = conteo_live.idxmin()
                        df_proc.at[idx_v, 'TECNICO_FINAL'] = mejor
                    
                    # 5. Balancear Excedentes
                    conteo = df_proc['TECNICO_FINAL'].value_counts()
                    for tech in [t for t in tecnicos_hoy if conteo.get(t,0) > LIMITES.get(t,35)]:
                        tope = LIMITES.get(tech, 35)
                        rows = df_proc[df_proc['TECNICO_FINAL'] == tech]
                        exc = len(rows) - tope
                        
                        if exc > 0:
                            mov = rows.index[-exc:]
                            now = df_proc['TECNICO_FINAL'].value_counts()
                            for t in tecnicos_hoy: 
                                if t not in now: now[t]=0
                            
                            best = sorted([t for t in tecnicos_hoy if t!=tech], key=lambda x: now.get(x,0))[0]
                            df_proc.loc[mov, 'TECNICO_FINAL'] = best
                            df_proc.loc[mov, 'ORIGEN_REAL'] = tech
                    
                    st.session_state['df_simulado'] = df_proc.drop(columns=['S'])
                    st.session_state['col_map_final'] = cmap
                    st.success("✅ Balanceo completado (Asistencia aplicada).")

        # --- TAB 3: AJUSTE MANUAL ---
        with tab3:
            st.markdown("### 🛠️ Corrección Manual")
            if st.session_state['df_simulado'] is not None:
                df = st.session_state['df_simulado']
                cbar = st.session_state['col_map_final']['BARRIO']
                activos_con_carga = sorted(df['TECNICO_FINAL'].unique())
                
                # Lista destino: Técnicos que vinieron hoy
                destinos_posibles = st.session_state.get('tecnicos_activos_manual', [])

                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
                with c1: org = st.selectbox("De:", ["-"]+list(activos_con_carga))
                with c2: 
                    if org!="-":
                        brs = df[df['TECNICO_FINAL']==org][cbar].value_counts()
                        bar = st.selectbox("Barrio:", [f"{k} ({v})" for k,v in brs.items()])
                    else: bar=None
                with c3: dst = st.selectbox("Para:", ["-"]+destinos_posibles)
                with c4:
                    st.write("")
                    if st.button("Mover"):
                        if bar and dst!="-":
                            rb = bar.rsplit(" (",1)[0]
                            msk = (df['TECNICO_FINAL']==org) & (df[cbar]==rb)
                            df.loc[msk, 'TECNICO_FINAL'] = dst
                            df.loc[msk, 'ORIGEN_REAL'] = org
                            st.session_state['df_simulado'] = df; st.rerun()
                
                cls = st.columns(2)
                for i, t in enumerate(activos_con_carga):
                    with cls[i%2]:
                        s = df[df['TECNICO_FINAL']==t]
                        r = s.groupby([cbar, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='N')
                        r['B'] = r.apply(lambda x: f"⚠️ {x[cbar]} (APOYO)" if pd.notna(x['ORIGEN_REAL']) else x[cbar], axis=1)
                        with st.expander(f"👷 {t} ({len(s)})"): st.dataframe(r[['B','N']], hide_index=True, use_container_width=True)
            else: st.info("Sin datos de ruta.")

        # --- TAB 4: PUBLICAR ---
        with tab4:
            st.markdown("### 🌍 Distribución Final")
            if st.session_state['df_simulado'] is not None:
                dff = st.session_state['df_simulado']
                cmf = st.session_state['col_map_final']
                pls = st.session_state['mapa_polizas_cargado']
                tfin = [t for t in dff['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                if st.button("📢 PUBLICAR EN PORTAL WEB", type="primary"):
                    gestionar_sistema_archivos("limpiar")
                    pg = st.progress(0)
                    
                    for i, t in enumerate(tfin):
                        # Carpeta Técnico
                        safe = str(t).replace(" ","_")
                        pto = os.path.join(CARPETA_PUBLICA, safe); os.makedirs(pto, exist_ok=True)
                        
                        # Datos Filtrados
                        dt = dff[dff['TECNICO_FINAL']==t].copy()
                        dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                        dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                        
                        # 1. Hoja Ruta
                        with open(os.path.join(pto, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                            f.write(crear_pdf_lista_final(dt, t, cmf))
                        
                        # 2. Paquete Legalización
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
                st.markdown("#### 📦 Respaldo Administrativo (ZIP)")
                
                if st.button("GENERAR ZIP COMPLETO"):
                    bf = io.BytesIO()
                    with zipfile.ZipFile(bf,"w") as z:
                        # 00. Banco de Polizas (Total)
                        if pls:
                            for k,v in pls.items(): z.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                        
                        # 00. Excel Consolidado
                        out = io.BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as w: dff.to_excel(w, index=False)
                        z.writestr("00_CONSOLIDADO_GENERAL.xlsx", out.getvalue())
                        
                        # Estructura por Técnico
                        for t in tfin:
                            safe = str(t).replace(" ","_")
                            dt = dff[dff['TECNICO_FINAL']==t].copy()
                            dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                            dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                            
                            # 1_HOJA
                            z.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista_final(dt, t, cmf))
                            
                            # 2_TABLA
                            ot = io.BytesIO()
                            with pd.ExcelWriter(ot, engine='xlsxwriter') as w: dt.to_excel(w, index=False)
                            z.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", ot.getvalue())
                            
                            # 3_LEGALIZACION y 4_POLIZAS
                            if pls:
                                mg = fitz.open(); n=0
                                for _,r in dt.iterrows():
                                    c = normalizar_numero(str(r[cmf['CUENTA']]))
                                    if c in pls:
                                        # Carpeta 4
                                        z.writestr(f"{safe}/4_POLIZAS_INDIVIDUALES/{c}.pdf", pls[c])
                                        # Carpeta 3 (Merge)
                                        with fitz.open(stream=pls[c], filetype="pdf") as x: mg.insert_pdf(x)
                                        n+=1
                                if n>0: z.writestr(f"{safe}/3_PAQUETE_LEGALIZACION.pdf", mg.tobytes())
                                mg.close()
                                
                    st.session_state['zip_admin_ready'] = bf.getvalue()
                    st.success("ZIP Creado.")
                
                if st.session_state['zip_admin_ready']:
                    st.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_admin_ready'], "Logistica_Total.zip", "application/zip")

            else: st.info("Falta procesar.")
    
    elif pwd: st.error("Acceso Denegado")
