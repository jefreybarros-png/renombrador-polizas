#################################################################################
#                                                                               #
#   PLATAFORMA INTEGRAL DE LOGÍSTICA ITA (WEB + GESTIÓN)                        #
#   VERSION: 6.0 DIAMOND EDITION                                                #
#   AUTOR: YEFREY                                                               #
#                                                                               #
#   NOVEDADES V6.0:                                                             #
#   1. INTEGRACIÓN DE LOGOTIPO CORPORATIVO.                                     #
#   2. INTERFAZ GRÁFICA "PREMIUM" (CSS AVANZADO).                               #
#   3. SISTEMA DE GESTIÓN DE ASISTENCIA (ACTIVAR/INACTIVAR TÉCNICOS).           #
#   4. BALANCEO INTELIGENTE QUE RESPETA LA ASISTENCIA.                          #
#   5. MANTENIMIENTO DE TODAS LAS FUNCIONES ANTERIORES (ZIP, WEB, MANUAL).      #
#                                                                               #
#################################################################################

import streamlit as st
import fitz  # PyMuPDF para procesamiento de PDFs
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
# SECCIÓN 1: CONFIGURACIÓN GLOBAL Y DISEÑO VISUAL
# ===============================================================================

st.set_page_config(
    page_title="Logística ITA | Panel Maestro",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded"
)

# --- CSS AVANZADO PARA DISEÑO "BONITO" ---
st.markdown("""
    <style>
    /* 1. Importación de Fuentes y Fondo */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .stApp { 
        background-color: #0F172A; /* Azul oscuro profundo */
        color: #F8FAFC; 
        font-family: 'Inter', sans-serif;
    }
    
    /* 2. Encabezado con Gradiente */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 0px 0px 30px rgba(56, 189, 248, 0.3);
    }

    /* 3. Personalización de Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        background-color: #1E293B;
        padding: 10px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        background-color: transparent; 
        color: #94A3B8; 
        border: none;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #3B82F6; 
        color: white; 
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
    }
    
    /* 4. Contenedores y Tarjetas */
    div[data-testid="stDataFrame"] { 
        background-color: #1E293B; 
        border-radius: 16px; 
        padding: 15px;
        border: 1px solid #334155;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    div[data-testid="stExpander"] {
        background-color: #1E293B;
        border-radius: 12px;
        border: 1px solid #334155;
    }

    /* 5. Botones de Acción (Estilo Neón/Moderno) */
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white; 
        border-radius: 12px; 
        height: 55px; 
        width: 100%; 
        font-size: 16px; 
        font-weight: 700; 
        border: none;
        letter-spacing: 0.5px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
    }
    div.stButton > button:first-child:hover { 
        transform: translateY(-2px);
        box-shadow: 0 10px 15px rgba(37, 99, 235, 0.5);
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
    }
    div.stButton > button:first-child:active {
        transform: translateY(1px);
    }
    
    /* 6. Botones de Descarga (Verde Esmeralda) */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white; 
        border-radius: 12px; 
        height: 60px; 
        width: 100%; 
        font-size: 18px; 
        font-weight: 700; 
        border: 1px solid #34D399;
        box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
    }
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(135deg, #34D399 0%, #10B981 100%);
        box-shadow: 0 10px 15px rgba(16, 185, 129, 0.4);
    }

    /* 7. Alertas y Métricas */
    div[data-testid="stMetricValue"] { color: #38BDF8 !important; }
    .stAlert { background-color: #1E293B; border: 1px solid #475569; color: #E2E8F0; border-radius: 10px; }
    
    /* 8. Logo en Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
        padding: 10px;
        background: rgba(255,255,255,0.05);
        border-radius: 15px;
    }
    .logo-img {
        max-width: 100%;
        height: auto;
        filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.5));
    }
    </style>
""", unsafe_allow_html=True)

# ===============================================================================
# SECCIÓN 2: GESTIÓN DEL SISTEMA DE ARCHIVOS
# ===============================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_carpeta_publica(accion="iniciar"):
    """
    Controlador del sistema de archivos para la publicación web.
    Garantiza que la carpeta exista y esté limpia antes de nuevas publicaciones.
    """
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try:
                os.makedirs(CARPETA_PUBLICA)
            except Exception as e:
                st.error(f"Error inicializando sistema de archivos: {e}")
                
    elif accion == "limpiar":
        if os.path.exists(CARPETA_PUBLICA):
            try:
                shutil.rmtree(CARPETA_PUBLICA)
                time.sleep(0.2) 
                os.makedirs(CARPETA_PUBLICA)
            except Exception as e:
                st.warning(f"Reintentando limpieza de archivos... ({e})")
                # Fallback
                if not os.path.exists(CARPETA_PUBLICA):
                    os.makedirs(CARPETA_PUBLICA)
        else:
            os.makedirs(CARPETA_PUBLICA)

# Iniciar sistema
gestionar_carpeta_publica("iniciar")

# ===============================================================================
# SECCIÓN 3: FUNCIONES DE NORMALIZACIÓN Y ORDENAMIENTO (CORE)
# ===============================================================================

def limpiar_estricto(txt):
    """Normalización agresiva de texto para cruces de bases de datos."""
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def normalizar_numero(txt):
    """Limpieza de números (polizas, cuentas) corrigiendo errores de Excel."""
    if not txt: return ""
    txt_str = str(txt)
    if txt_str.endswith('.0'): 
        txt_str = txt_str[:-2]
    nums = re.sub(r'\D', '', txt_str)
    return str(int(nums)) if nums else ""

def natural_sort_key(txt):
    """Algoritmo de ordenamiento humano (Calle 2 antes que Calle 10)."""
    if not txt: return tuple()
    txt = str(txt).upper()
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', txt))

# ===============================================================================
# SECCIÓN 4: LÓGICA DE NEGOCIO (CARGA Y BALANCEO)
# ===============================================================================

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    """Busca el técnico asignado a un barrio con múltiples estrategias de coincidencia."""
    if not barrio_input: return "SIN_ASIGNAR"
    
    b_raw = limpiar_estricto(str(barrio_input))
    if not b_raw: return "SIN_ASIGNAR"
    
    # 1. Coincidencia Exacta
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 2. Coincidencia Flexible (Sin prefijos)
    patrones = r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|VILLA|CIUDADELA|RESIDENCIAL)\b'
    b_flex = re.sub(patrones, '', b_raw).strip()
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 3. Coincidencia Parcial Segura
    for k, v in mapa_barrios.items():
        if len(k) > 4 and k in b_raw: 
            return v
            
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    """Carga el maestro Barrio -> Técnico."""
    mapa = {}
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, sep=None, engine='python')
        else: 
            df = pd.read_excel(file)
            
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Validación mínima
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
    """Extrae páginas de pólizas de un PDF grande."""
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
            
            # Detectar anexos en página siguiente
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
# SECCIÓN 5: GENERADOR PDF (DISEÑO CORPORATIVO)
# ===============================================================================

class PDFListado(FPDF):
    def header(self):
        # Cabecera Azul Corporativo
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        
        # Título
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA DE OPERACIONES', 0, 1, 'C')
        self.ln(10)

def crear_pdf_lista_final(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Datos Generales
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    fecha = datetime.now().strftime('%d/%m/%Y')
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {fecha} | TOTAL VISITAS: {len(df)}", 0, 1)
    
    # Encabezados
    headers = ['#', 'CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [10, 25, 25, 65, 85, 60]
    
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 9)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Datos
    pdf.set_font('Arial', '', 8)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        # Resaltar Apoyos
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
            str(idx), get_s('CUENTA'), get_s('MEDIDOR')[:15], 
            barrio_txt[:38], get_s('DIRECCION')[:60], get_s('CLIENTE')[:30]
        ]
        
        for val, w in zip(row_data, widths):
            try: val_e = val.encode('latin-1', 'replace').decode('latin-1')
            except: val_e = val
            pdf.cell(w, 7, val_e, 1, 0, 'L')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ===============================================================================
# SECCIÓN 6: ESTADO DE SESIÓN (PERSISTENCIA)
# ===============================================================================

if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
if 'zip_polizas_only' not in st.session_state: st.session_state['zip_polizas_only'] = None
if 'tecnicos_inactivos' not in st.session_state: st.session_state['tecnicos_inactivos'] = []

# ===============================================================================
# SECCIÓN 7: INTERFAZ - BARRA LATERAL (LOGO + CONTROL DE ASISTENCIA)
# ===============================================================================

with st.sidebar:
    # 1. LOGO CORPORATIVO (Puedes cambiar la URL o usar una local)
    logo_url = "https://cdn-icons-png.flaticon.com/512/2942/2942813.png" # Placeholder bonito
    st.markdown(
        f"""
        <div class="logo-container">
            <img src="{logo_url}" class="logo-img">
        </div>
        """, unsafe_allow_html=True
    )
    
    st.markdown("<h2 style='text-align: center; color: #38BDF8;'>PANEL MAESTRO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 2. SELECTOR DE ROL
    modo_acceso = st.selectbox(
        "👤 PERFIL DE ACCESO", 
        ["👷 TÉCNICO", "⚙️ ADMINISTRADOR"],
        index=0
    )
    
    st.markdown("---")
    
    # 3. GESTIÓN DE ASISTENCIA (SOLO PARA ADMIN Y SI HAY DATOS)
    if modo_acceso == "⚙️ ADMINISTRADOR" and st.session_state['mapa_actual']:
        st.markdown("### 🚫 Gestión de Ausencias")
        st.info("Desmarca a los técnicos que NO trabajarán hoy. Su carga será repartida.")
        
        # Obtener lista completa de técnicos del maestro cargado
        todos_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
        
        # Widget Multiselect para seleccionar a los que SÍ están activos
        # Por defecto, todos están seleccionados
        tecnicos_activos_seleccion = st.multiselect(
            "Técnicos Activos (Desmarca para inactivar):",
            options=todos_tecnicos,
            default=todos_tecnicos
        )
        
        # Guardar en sesión quiénes están inactivos (la diferencia)
        st.session_state['tecnicos_activos_filtrados'] = tecnicos_activos_seleccion
        
        inactivos = len(todos_tecnicos) - len(tecnicos_activos_seleccion)
        if inactivos > 0:
            st.warning(f"⚠️ Hay {inactivos} técnicos inactivos.")
        else:
            st.success("✅ Cuadrilla completa.")
            
    st.markdown("---")
    st.caption("© 2026 Sistema Logístico V6.0 Diamond")

# ===============================================================================
# SECCIÓN 8: VISTA DEL TÉCNICO (PORTAL DE DESCARGA)
# ===============================================================================

if modo_acceso == "👷 TÉCNICO":
    st.markdown('<div class="main-header">🚛 Portal de Operaciones</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:18px;'>Selecciona tu nombre para acceder a la documentación del día.</p>", unsafe_allow_html=True)
    
    st.write("") # Espacio
    
    # Verificar carpeta pública
    if os.path.exists(CARPETA_PUBLICA):
        tecnicos_list = sorted([d for d in os.listdir(CARPETA_PUBLICA) if os.path.isdir(os.path.join(CARPETA_PUBLICA, d))])
    else:
        tecnicos_list = []
        
    if not tecnicos_list:
        st.info("🕒 Las rutas del día aún no están publicadas.")
        if st.button("🔄 Actualizar Portal", type="secondary"): st.rerun()
    else:
        col_center = st.columns([1, 2, 1])
        with col_center[1]:
            seleccion = st.selectbox("👇 BUSCA TU NOMBRE:", ["-- Seleccionar --"] + tecnicos_list)
        
        if seleccion != "-- Seleccionar --":
            path_tec = os.path.join(CARPETA_PUBLICA, seleccion)
            f_ruta = os.path.join(path_tec, "1_HOJA_DE_RUTA.pdf")
            f_leg = os.path.join(path_tec, "3_PAQUETE_LEGALIZACION.pdf")
            
            st.markdown(f"### 📄 Documentos para: <span style='color:#38BDF8'>{seleccion}</span>", unsafe_allow_html=True)
            st.write("")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown('<div class="status-card"><h4>📍 Hoja de Ruta</h4><p>Listado de clientes</p></div>', unsafe_allow_html=True)
                if os.path.exists(f_ruta):
                    with open(f_ruta, "rb") as f:
                        st.download_button("⬇️ DESCARGAR RUTA", f, f"Ruta_{seleccion}.pdf", "application/pdf", key="d1")
                else: st.error("No disponible")
                
            with c2:
                st.markdown('<div class="status-card"><h4>📎 Legalización</h4><p>Paquete de Pólizas</p></div>', unsafe_allow_html=True)
                if os.path.exists(f_leg):
                    with open(f_leg, "rb") as f:
                        st.download_button("⬇️ DESCARGAR LEGALIZACIÓN", f, f"Leg_{seleccion}.pdf", "application/pdf", key="d2")
                else: st.info("Sin pólizas hoy")

# ===============================================================================
# SECCIÓN 9: VISTA DEL ADMINISTRADOR (PANEL DE GESTIÓN)
# ===============================================================================

elif modo_acceso == "⚙️ ADMINISTRADOR":
    st.markdown('<div class="main-header">⚙️ Centro de Comando</div>', unsafe_allow_html=True)
    
    password = st.text_input("🔒 Clave de Acceso:", type="password")
    
    if password == "ita2026":
        
        t1, t2, t3, t4 = st.tabs([
            "1. 🗃️ Cargar Maestro", 
            "2. ⚖️ Procesar Rutas", 
            "3. 🛠️ Ajuste Fino", 
            "4. 🌍 Publicación"
        ])
        
        # --- TAB 1: MAESTRO ---
        with t1:
            st.markdown("### Base de Datos de Operarios")
            f_maestro = st.file_uploader("Subir Maestro (Excel/CSV)", type=["xlsx", "csv"])
            
            if f_maestro:
                with st.spinner("Indexando barrios y técnicos..."):
                    st.session_state['mapa_actual'] = cargar_maestro_dinamico(f_maestro)
                st.success(f"✅ Maestro cargado: {len(st.session_state['mapa_actual'])} barrios.")
                
            if st.session_state['mapa_actual']:
                # Calcular activos basado en el filtro de la sidebar
                if 'tecnicos_activos_filtrados' in st.session_state:
                    activos_count = len(st.session_state['tecnicos_activos_filtrados'])
                else:
                    activos_count = len(set(st.session_state['mapa_actual'].values()))
                    
                st.metric("Técnicos Habilitados para Hoy", activos_count)
                st.info("💡 Ve a la barra lateral para inactivar técnicos si es necesario.")

        # --- TAB 2: PROCESAMIENTO ---
        with t2:
            st.markdown("### Carga de Insumos Diarios")
            c_pdf, c_xls = st.columns(2)
            
            with c_pdf:
                up_pdf = st.file_uploader("1. PDF Pólizas (Opcional)", type="pdf")
                if up_pdf and st.button("Escaneado Manual PDF"):
                    with st.spinner("Procesando..."):
                        st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                        st.success(f"✅ {len(st.session_state['mapa_polizas_cargado'])} Pólizas.")

            with c_xls:
                up_xls = st.file_uploader("2. Excel Ruta (Obligatorio)", type=["xlsx", "csv"])
            
            # Verificar técnicos activos
            # Si se usó el filtro de la sidebar, usamos ese. Si no, usamos todos.
            tecnicos_para_balanceo = st.session_state.get('tecnicos_activos_filtrados', [])
            if not tecnicos_para_balanceo and st.session_state['mapa_actual']:
                 tecnicos_para_balanceo = sorted(list(set(st.session_state['mapa_actual'].values())))

            if up_xls and tecnicos_para_balanceo:
                try:
                    if up_xls.name.endswith('.csv'): df = pd.read_csv(up_xls, sep=None, engine='python', encoding='utf-8-sig')
                    else: df = pd.read_excel(up_xls)
                    cols = list(df.columns)
                    
                    st.markdown("---")
                    st.markdown("#### ⚙️ Configuración de Balanceo")
                    
                    # Tabla Cupos (Solo con técnicos activos)
                    df_cup = pd.DataFrame({"Técnico": tecnicos_para_balanceo, "Cupo": [35]*len(tecnicos_para_balanceo)})
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
                    
                    if st.button("🚀 EJECUTAR BALANCEO INTELIGENTE", type="primary"):
                        # Auto-scan check
                        if up_pdf and not st.session_state['mapa_polizas_cargado']:
                            st.session_state['mapa_polizas_cargado'] = procesar_pdf_polizas_avanzado(up_pdf)
                        
                        df_proc = df.copy()
                        
                        # 1. Asignar (Considerando mapa completo primero)
                        df_proc['TECNICO_IDEAL'] = df_proc[sb].apply(lambda x: buscar_tecnico_exacto(x, st.session_state['mapa_actual']))
                        
                        # 2. Reasignar Inactivos (Si el técnico ideal NO está en la lista de activos, marcar para mover)
                        # Inicialmente asignamos el ideal
                        df_proc['TECNICO_FINAL'] = df_proc['TECNICO_IDEAL']
                        df_proc['ORIGEN_REAL'] = None
                        
                        # Detectar filas asignadas a gente inactiva
                        # (Si 'TECNICO_IDEAL' no está en 'tecnicos_para_balanceo')
                        mask_inactivos = ~df_proc['TECNICO_FINAL'].isin(tecnicos_para_balanceo)
                        # A estas filas les pondremos un flag temporal o las trataremos como excedente total
                        # Estrategia: Asignarles temporalmente "SIN_ASIGNAR" para que el balanceo las coja
                        df_proc.loc[mask_inactivos, 'TECNICO_FINAL'] = "REASIGNAR_POR_INACTIVIDAD"
                        df_proc.loc[mask_inactivos, 'ORIGEN_REAL'] = df_proc.loc[mask_inactivos, 'TECNICO_IDEAL']

                        # 3. Ordenar
                        df_proc['S'] = df_proc[sd].astype(str).apply(natural_sort_key)
                        df_proc = df_proc.sort_values(by=[sb, 'S'])
                        
                        # 4. Balanceo (Solo entre ACTIVOS)
                        # Primero: Repartir los "REASIGNAR_POR_INACTIVIDAD"
                        filas_huerfanas = df_proc[df_proc['TECNICO_FINAL'] == "REASIGNAR_POR_INACTIVIDAD"]
                        for idx_h, row_h in filas_huerfanas.iterrows():
                            # Buscar técnico activo con menos carga
                            counts = df_proc[df_proc['TECNICO_FINAL'].isin(tecnicos_para_balanceo)]['TECNICO_FINAL'].value_counts()
                            # Crear base con 0 para los que no tienen nada aun
                            for t in tecnicos_para_balanceo:
                                if t not in counts: counts[t] = 0
                            
                            candidato = counts.idxmin() # El que menos tiene
                            df_proc.at[idx_h, 'TECNICO_FINAL'] = candidato
                            # ORIGEN_REAL ya estaba seteado arriba
                        
                        # Segundo: Balancear cargas excedentes de los activos
                        conteo = df_proc['TECNICO_FINAL'].value_counts()
                        for tech in [t for t in tecnicos_para_balanceo if conteo.get(t,0) > LIMITES.get(t,35)]:
                            tope = LIMITES.get(tech, 35)
                            rows = df_proc[df_proc['TECNICO_FINAL'] == tech]
                            exc = len(rows) - tope
                            if exc > 0:
                                mov = rows.index[-exc:]
                                now = df_proc['TECNICO_FINAL'].value_counts()
                                for t in tecnicos_para_balanceo: 
                                    if t not in now: now[t]=0
                                
                                best = sorted([t for t in tecnicos_para_balanceo if t!=tech], key=lambda x: now.get(x,0))[0]
                                df_proc.loc[mov, 'TECNICO_FINAL'] = best
                                df_proc.loc[mov, 'ORIGEN_REAL'] = tech
                        
                        st.session_state['df_simulado'] = df_proc.drop(columns=['S'])
                        st.session_state['col_map_final'] = cmap
                        st.success("✅ Ruta Balanceada (Inactivos Reasignados).")

                except Exception as e: st.error(f"Error: {e}")

        # --- TAB 3: AJUSTE MANUAL ---
        with t3:
            st.markdown("### 🛠️ Correcciones Manuales")
            if st.session_state['df_simulado'] is not None:
                df = st.session_state['df_simulado']
                cbar = st.session_state['col_map_final']['BARRIO']
                activos = sorted(df['TECNICO_FINAL'].unique()) # Solo mostramos los que quedaron con ruta

                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                with c1: org = st.selectbox("De (Origen):", ["-"]+list(activos))
                with c2: 
                    if org!="-":
                        brs = df[df['TECNICO_FINAL']==org][cbar].value_counts()
                        bar = st.selectbox("Barrio:", [f"{k} ({v})" for k,v in brs.items()])
                    else: bar=None
                with c3: dst = st.selectbox("Para (Destino):", ["-"]+tecnicos_para_balanceo)
                with c4:
                    st.write("")
                    if st.button("Mover"):
                        if bar and dst!="-":
                            rb = bar.rsplit(" (",1)[0]
                            msk = (df['TECNICO_FINAL']==org) & (df[cbar]==rb)
                            df.loc[msk, 'TECNICO_FINAL'] = dst
                            df.loc[msk, 'ORIGEN_REAL'] = org
                            st.session_state['df_simulado'] = df; st.rerun()
                
                # Visualización
                cls = st.columns(2)
                for i, t in enumerate(activos):
                    with cls[i%2]:
                        s = df[df['TECNICO_FINAL']==t]
                        r = s.groupby([cbar, 'ORIGEN_REAL'], dropna=False).size().reset_index(name='N')
                        r['B'] = r.apply(lambda x: f"⚠️ {x[cbar]} (APOYO)" if pd.notna(x['ORIGEN_REAL']) else x[cbar], axis=1)
                        with st.expander(f"👷 {t} ({len(s)})"): st.dataframe(r[['B','N']], hide_index=True, use_container_width=True)

        # --- TAB 4: PUBLICAR ---
        with t4:
            st.markdown("### 🌍 Distribución Final")
            if st.session_state['df_simulado'] is not None:
                dff = st.session_state['df_simulado']
                cmf = st.session_state['col_map_final']
                pls = st.session_state['mapa_polizas_cargado']
                tfin = [t for t in dff['TECNICO_FINAL'].unique() if "SIN_" not in t]
                
                if st.button("📢 PUBLICAR EN PORTAL WEB", type="primary"):
                    limpiar_carpeta_publica(); pg = st.progress(0)
                    for i, t in enumerate(tfin):
                        # Filtrar y Ordenar
                        dt = dff[dff['TECNICO_FINAL']==t].copy()
                        dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                        dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                        
                        # Crear carpeta
                        safe = str(t).replace(" ","_")
                        pto = os.path.join(CARPETA_PUBLICA, safe); os.makedirs(pto, exist_ok=True)
                        
                        # 1. Ruta
                        with open(os.path.join(pto, "1_HOJA_DE_RUTA.pdf"), "wb") as f:
                            f.write(crear_pdf_lista_final(dt, t, cmf))
                        
                        # 2. Legalización
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
                    st.success("✅ Rutas Publicadas Exitosamente.")
                    st.balloons()
                
                st.divider()
                st.markdown("#### 📦 Descargas Administrativas")
                
                if st.button("GENERAR ZIP MAESTRO"):
                    bf = io.BytesIO()
                    with zipfile.ZipFile(bf,"w") as z:
                        # Banco Polizas
                        if pls:
                            for k,v in pls.items(): z.writestr(f"00_BANCO_DE_POLIZAS_TOTAL/{k}.pdf", v)
                        
                        # Excel Total
                        out = io.BytesIO(); 
                        with pd.ExcelWriter(out, engine='xlsxwriter') as w: dff.to_excel(w, index=False)
                        z.writestr("00_CONSOLIDADO.xlsx", out.getvalue())
                        
                        # Tecnicos
                        for t in tfin:
                            safe = str(t).replace(" ","_")
                            dt = dff[dff['TECNICO_FINAL']==t].copy()
                            dt['S'] = dt[cmf['DIRECCION']].astype(str).apply(natural_sort_key)
                            dt = dt.sort_values(by=[cmf['BARRIO'], 'S']).drop(columns=['S'])
                            
                            z.writestr(f"{safe}/1_HOJA_DE_RUTA.pdf", crear_pdf_lista_final(dt, t, cmf))
                            
                            outt = io.BytesIO()
                            with pd.ExcelWriter(outt, engine='xlsxwriter') as w: dt.to_excel(w, index=False)
                            z.writestr(f"{safe}/2_TABLA_DIGITAL.xlsx", outt.getvalue())
                            
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
                    st.success("ZIP Listo.")
                
                if st.session_state['zip_admin_ready']:
                    st.download_button("⬇️ DESCARGAR ZIP COMPLETO", st.session_state['zip_admin_ready'], "Logistica_Total.zip", "application/zip")

            else: st.info("Pendiente procesar ruta.")
