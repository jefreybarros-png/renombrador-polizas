#########################################################################################
#                                                                                       #
#   PLATAFORMA INTEGRAL DE LOGÍSTICA ITA - VERSIÓN 13.2 "EXCEDENTES MANUALES"           #
#   AUTOR: YEFREY                                                                       #
#   FECHA: FEBRERO 2026                                                                 #
#                                                                                       #
#   AJUSTE DE LÓGICA V13.0:                                                             #
#   - Cambio de algoritmo de reparto: De "Equitativo" a "Saturación" (Llenar Vaso).     #
#   AJUSTE V13.1:                                                                       #
#   - Se añade botón de REINICIO TOTAL para limpiar variables de sesión.                #
#   AJUSTE V13.2:                                                                       #
#   - Corrección de CSS para soportar Modo Claro (Google White Theme).                  #
#   - Los excedentes de cupo van a una Bolsa Manual en lugar de reasignarse solos.      #
#   - Se añade control de "Cantidad" en la Pestaña 3 para mover registros por bloque.   #
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

# Configuración inicial de la página
st.set_page_config(
    page_title="Logística ITA | v13.2 Saturation",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Sistema Logístico ITA - Versión 13.2 Llenado de Vaso"
    }
)

# Inicialización de Variables de Sesión (Estado Global)
if 'admin_logged_in' not in st.session_state: st.session_state['admin_logged_in'] = False
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = {}
if 'mapa_telefonos' not in st.session_state: st.session_state['mapa_telefonos'] = {}
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'col_map_final' not in st.session_state: st.session_state['col_map_final'] = None
if 'mapa_polizas_cargado' not in st.session_state: st.session_state['mapa_polizas_cargado'] = {}
if 'zip_admin_ready' not in st.session_state: st.session_state['zip_admin_ready'] = None
if 'tecnicos_activos_manual' not in st.session_state: st.session_state['tecnicos_activos_manual'] = []
if 'ultimo_archivo_procesado' not in st.session_state: st.session_state['ultimo_archivo_procesado'] = None

# Inyección de CSS (Estilos Avanzados - Adaptados para Modo Claro/Oscuro nativo)
st.markdown("""
    <style>
    /* FUENTES GLOBALES */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
    
    .stApp { 
        font-family: 'Roboto', sans-serif;
    }
    
    /* CONTENEDOR DE LOGO */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 25px;
        background: linear-gradient(180deg, rgba(100, 116, 139, 0.1) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 16px;
        border: 1px solid rgba(100, 116, 139, 0.2);
        margin-bottom: 25px;
    }
    
    .logo-img {
        width: 100px;
        height: auto;
        filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.4));
        transition: transform 0.3s ease;
    }
    .logo-img:hover { transform: scale(1.05); }
    
    .logo-text {
        font-family: 'Roboto', sans-serif;
        font-weight: 900;
        font-size: 26px;
        background: -webkit-linear-gradient(45deg, #0284C7, #4F46E5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 10px;
        letter-spacing: 1.5px;
    }
    
    /* BOTONES PRIMARIOS (AZUL) */
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
        color: white !important; 
        border-radius: 10px; 
        height: 52px; 
        width: 100%; 
        font-size: 16px; 
        font-weight: 700; 
        border: 1px solid #1D4ED8;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        text-transform: uppercase;
    }
    div.stButton > button:first-child:hover { 
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        transform: translateY(-1px);
    }
    
    /* BOTONES DE DESCARGA (VERDE) */
    div.stDownloadButton > button:first-child { 
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        color: white !important; 
        border-radius: 10px; 
        height: 58px; 
        width: 100%; 
        font-size: 17px; 
        font-weight: 700; 
        border: 1px solid #059669;
    }
    div.stDownloadButton > button:first-child:hover { 
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
    }

    /* MENSAJES DE ALERTA */
    .locked-msg {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #F87171;
        text-align: center;
        font-weight: bold;
    }
    
    .unlocked-msg {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #34D399;
        text-align: center;
        margin-top: 10px;
        font-weight: bold;
    }
    
    .tech-header {
        font-size: 32px; 
        font-weight: 800; 
        background: -webkit-linear-gradient(0deg, #0284C7, #4F46E5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 20px;
        border-bottom: 2px solid #38BDF8;
        padding-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# =======================================================================================
# SECCIÓN 2: GESTIÓN DE SISTEMA DE ARCHIVOS (PERSISTENCIA WEB)
# =======================================================================================

CARPETA_PUBLICA = "public_files"

def gestionar_sistema_archivos(accion="iniciar"):
    if accion == "iniciar":
        if not os.path.exists(CARPETA_PUBLICA):
            try:
                os.makedirs(CARPETA_PUBLICA)
            except OSError as e:
