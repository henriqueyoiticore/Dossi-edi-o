import streamlit as st
import pandas as pd
import plotly.express as px
import os
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Escopos necessários para ler e escrever no Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# IDs das planilhas (Extraídos dos links originais)
ID_AJUSTES = '1y8bw87uE8xkYFJMhKWbu-9Az1d6D8U3lJ5r_lfrjziI'
ID_FOLHA = '1PD2pwNYNUt1laQn_L2ikbVJmRk8Y0KKBHtS-kaV-Lqs'
ID_OCORRENCIAS_1 = '14o86RRH7x5cUylXk6ryEMr14bH12Y94UFDGaz6JOxkM'
ID_OCORRENCIAS_FORA = '16noLo9yfByjZLh4ZPbROz8p-RWdFZpxtiU2Uhz6ffhw'
ID_ORDEM_PRIORIDADE = '1IAPh05sT-HlQPUdhJ9WYdgDK2Frjb_YLbzHrznVZz5o'
ID_AVISOS_NOVO = '1jlZ240LkuecaRmfCLJKHumCbJA1un8-vKjmq2zrPcNs'

# =====================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA - FrameControl DNA
# =====================================================================
st.set_page_config(
    page_title="FrameControl | Dossiê do Cliente",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de CSS para Identidade Visual "Precision Cut"
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');

        :root {
            --surface-page: #F8FAFC;
            --surface-card: #FFFFFF;
            --accent-primary: #8B5CF6;
            --text-primary: #1E293B;
            --text-secondary: #FFFFFF;
            --border-subtle: rgba(0,0,0,0.06);
            --status-error: #EF4444;
            --status-warning: #F59E0B;
            --status-success: #10B981;
        }

        /* Forçar Fundo Branco e Texto Escuro em Tudo sem Quebrar Ícones */
        .stApp {
            background-color: #F8FAFC !important;
        }

        .stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3 {
            color: #1E293B !important;
            font-family: 'Inter', sans-serif;
        }

        /* Sidebar - Fundo Branco e Texto Escuro */
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
            background-color: #FFFFFF !important;
            border-right: 1px solid var(--border-subtle);
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebarNav"] span {
            color: #1E293B !important;
            opacity: 1 !important;
        }

        /* Restaurar Font dos Ícones */
        [data-testid="stIcon"] {
            font-family: "Material Symbols Outlined", "Material Icons", sans-serif !important;
        }

        /* Metrics Styling */
        [data-testid="stMetricValue"] {
            color: var(--accent-primary) !important;
            font-weight: 700 !important;
        }
        
        [data-testid="stMetricLabel"] {
            color: #475569 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
        }

        /* Cards e Containers */
        .stMetric {
            background: #FFFFFF !important;
            border: 1px solid var(--border-subtle) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
            border-radius: 12px !important;
            padding: 20px !important;
        }

        /* Corrigir inputs (Selectbox) para texto claro (fundo escuro) */
        [data-baseweb="select"] div {
            color: #FFFFFF !important;

        #MainMenu, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 1. AUTENTICAÇÃO E EXTRAÇÃO DE DADOS VIA API
# =====================================================================
def get_google_sheets_service():
    """Autentica o acesso ao Sheets (Suporta Modo Local e Cloud)."""
    
    # 1. Tentar Autenticação via Service Account (Recomendado para Streamlit Cloud)
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=SCOPES
            )
            return build('sheets', 'v4', credentials=creds)
    except:
        pass # Ignora erro de segredos não encontrados localmente

    # 2. Modo Local / Fallback (OAuth User Flow)
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Se não temos token e estamos no Cloud, o run_local_server vai falhar
            # Verificamos se client_secret existe para tentar o fluxo local
            if os.path.exists('client_secret.json'):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    st.error("Erro de Autenticação: O servidor não pode abrir um navegador para login.")
                    st.info("👉 Para rodar no nuvem (Streamlit Cloud), você deve usar uma **Service Account**.")
                    st.stop()
            else:
                st.error("Credenciais Google não encontradas (client_secret.json ou st.secrets).")
                st.stop()

    return build('sheets', 'v4', credentials=creds)

def get_sheet_data(service, spreadsheet_id, range_name, silent=False):
    """Puxa os dados de uma aba específica da planilha e converte para Pandas DataFrame."""
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            return pd.DataFrame()
            
        # Transforma os dados retornados em um DataFrame do Pandas
        header = values[0]
        data = values[1:]
        
        # Garantir colunas únicas (ex: '', '', '' -> 'Unnamed_1', 'Unnamed_2')
        new_header = []
        counts = {}
        for h in header:
            val = str(h).strip()
            if val == "": val = "Unnamed"
            if val in counts:
                counts[val] += 1
                new_header.append(f"{val}_{counts[val]}")
            else:
                counts[val] = 0
                new_header.append(val)
        header = new_header

        # Ajusta as linhas para terem o mesmo tamanho do cabeçalho
        num_cols = len(header)
        adjusted_data = []
        for i, row in enumerate(data):
            if len(row) < num_cols:
                row.extend([''] * (num_cols - len(row)))
            elif len(row) > num_cols:
                row = row[:num_cols]
            row.append(i + 2) # ROW INDEX no Google Sheets (1-indexed + header)
            adjusted_data.append(row)

        header.append('_SheetRowIdx')
        df = pd.DataFrame(adjusted_data, columns=header)
        return df
    except Exception as e:
        if not silent:
            st.error(f"Erro ao ler a planilha ID {spreadsheet_id}: {e}")
        return pd.DataFrame()

def update_sheet_cell(service, spreadsheet_id, row_idx, col_idx, value):
    """Atualiza uma célula específica na planilha."""
    try:
        # Converter col_idx (0-based) para letra da coluna
        dividend = col_idx + 1
        col_letter = ''
        while dividend > 0:
            modulo = (dividend - 1) % 26
            col_letter = chr(65 + modulo) + col_letter
            dividend = int((dividend - modulo) / 26)
        
        range_name = f"{col_letter}{row_idx}"
        body = {'values': [[value]]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption="USER_ENTERED", body=body).execute()
        return True, ""
    except Exception as e:
        erro_str = str(e)
        print(f"Erro ao atualizar planilha: {erro_str}")
        return False, erro_str

@st.cache_data(ttl=120)
def carregar_dados():
    service = get_google_sheets_service()

    # NOTA: Aqui nós definimos o Range genérico para pegar todas as colunas da primeira aba
    # Se uma planilha tiver um nome de aba específico (ex: 'Ocorrências!A:Z'), podemos ajustar aqui.
    # Por padrão, se não passar o nome da aba, a API vai tentar pegar da primeira aba visível.
    # Para planilhas simples, o range 'A:Z' costuma funcionar bem.
    
    # IMPORTANTE: A API do Sheets precisa do nome da aba + Range se houver múltiplas abas.
    # Como não sei os nomes das abas, vou tentar pegar o Range padrão de Dados. Se falhar, você me avisa os nomes das abas depois.
    # ——— Processar Folha de Pagamento (Múltiplas Abas de Meses) ———
    # Lista de abas que representam meses (baseado na estrutura da planilha)
    abas_meses = ['Outubro', 'Novembro', 'Dezembro', 'Janeiro', 'Fevereiro', 'Março']
    map_mes_pt = {
        'Outubro': '10/2025', 'Novembro': '11/2025', 'Dezembro': '12/2025',
        'Janeiro': '01/2026', 'Fevereiro': '02/2026', 'Março': '03/2026'
    }
    
    dfs_folha = []
    for aba in abas_meses:
        try:
            # Silent=True para não travar se o mês ainda não foi criado na folha
            df_m = get_sheet_data(service, ID_FOLHA, f"'{aba}'!A:Z", silent=True)
            if not df_m.empty:
                df_m['Mes_Ano'] = map_mes_pt.get(aba, 'Desconhecido')
                # Garantir que a coluna 'Vídeos' existe e é tratada como número
                col_v = next((c for c in df_m.columns if 'vídeo' in c.lower() or 'video' in c.lower()), None)
                if col_v:
                    df_m['_Producao'] = pd.to_numeric(df_m[col_v], errors='coerce').fillna(0)
                dfs_folha.append(df_m)
        except: continue
        
    df_folha = pd.concat(dfs_folha, ignore_index=True) if dfs_folha else pd.DataFrame()

    df_ajustes = get_sheet_data(service, ID_AJUSTES, 'A:ZZ')
    df_ocorrencias = get_sheet_data(service, ID_OCORRENCIAS_1, 'A:Z')
    df_ocorrencias_fora = get_sheet_data(service, ID_OCORRENCIAS_FORA, 'A:Z')
    # Aba com ranking consolidado (sem data - usada quando filtro = Todos)
    df_ranking_editores = get_sheet_data(service, ID_ORDEM_PRIORIDADE, 'Ranking editores!A:B')
    # Aba com todas as demandas e datas (usada para filtrar por mês)
    df_prioridades = get_sheet_data(service, ID_ORDEM_PRIORIDADE, 'Prioridades!A:H')
    
    # Aba nova para Central de Avisos no Dossiê
    df_avisos_novo = get_sheet_data(service, ID_AVISOS_NOVO, 'A:Z')
    
    return df_ajustes, df_folha, df_ocorrencias, df_ocorrencias_fora, df_ranking_editores, df_prioridades, df_avisos_novo


# =====================================================================
# 2. TRATAMENTO DE DADOS (COM ÍNDICE DE PROLIXIDADE)
# =====================================================================
def preparar_dados(df_ajustes, df_folha, df_ocorrencias, df_ocorrencias_fora, df_prioridades, df_avisos):
    try:
        # Helper para encontrar coluna de data por palavras-chave
        def find_date_col(df):
            keywords = ['data', 'carimbo', 'upload', 'solicita', 'inicio', 'solicitação']
            for col in df.columns:
                if any(k in col.lower() for k in keywords):
                    return col
            return df.columns[0] # Fallback
            
        # Parse robusto de data (especialmente para DD/MM e formatos variados)
        def robust_date_parse(val):
            if not val or str(val).strip().lower() in ['', 'nan', 'none']: 
                return pd.NaT
            s = str(val).strip()
            
            # 1. Tenta formatos com Ano
            for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y/%m/%d"]:
                try:
                    return pd.to_datetime(s, format=fmt)
                except: continue
                
            # 2. Se for DD/MM, tenta inferir o ano (2025 ou 2026)
            # Baseado na proximidade com a data atual ou dados da planilha
            if s.count('/') == 1:
                parts = s.split('/')
                if len(parts) == 2:
                    try:
                        d, m = int(parts[0]), int(parts[1])
                        # Se o mês for alto (ex: Nov), provavelmente é 2025. Se for baixo (Jan), 2026.
                        # Mas melhor tentar converter e ver se faz sentido.
                        # Por padrão, se estamos em 2026, tentamos 2026 primeiro.
                        test_year = 2026
                        if m >= 10: test_year = 2025 # Out/Nov/Dez costumam ser do ano passado nesse contexto
                        return pd.to_datetime(f"{s}/{test_year}", format="%d/%m/%Y")
                    except: pass
            
            # 3. Fallback pandas
            return pd.to_datetime(s, errors='coerce', dayfirst=True)

        # Processar Ajustes (Tickets)
        if not df_ajustes.empty:
            col_data_aj = find_date_col(df_ajustes)
            df_ajustes['DataSort'] = df_ajustes[col_data_aj].apply(robust_date_parse)
            df_ajustes = df_ajustes.sort_values('DataSort', ascending=False)

        # Processar Ocorrências
        if not df_ocorrencias.empty:
            col_data = find_date_col(df_ocorrencias)
            df_ocorrencias['Data'] = df_ocorrencias[col_data].apply(robust_date_parse)
            df_ocorrencias['Mes_Ano'] = df_ocorrencias['Data'].dt.strftime('%m/%Y').fillna('Desconhecido')
        
        # Processar Erros Fora
        if not df_ocorrencias_fora.empty:
            col_data_fora = find_date_col(df_ocorrencias_fora)
            df_ocorrencias_fora['Data'] = df_ocorrencias_fora[col_data_fora].apply(robust_date_parse)
            df_ocorrencias_fora['Mes_Ano'] = df_ocorrencias_fora['Data'].dt.strftime('%m/%Y').fillna('Desconhecido')
        
        # Processar Folha (Já vem com Mes_Ano do carregar_dados)
        if not df_folha.empty:
            # Se já tivermos _Producao, não precisamos de find_date_col pra Folha (ela é mensal)
            # Mas para o filtro global de datas, podemos tentar inferir uma data fictícia do mês
            def inferir_data_folha(mes_ano):
                try:
                    return pd.to_datetime(f"01/{mes_ano}", format="%d/%m/%Y")
                except: return pd.NaT
            df_folha['Data'] = df_folha['Mes_Ano'].apply(inferir_data_folha)

        # Processar Prioridades (Aba Central)
        if not df_prioridades.empty:
            # PRIORIDADE: Usar 'Prazo real' para alinhar com a visualização do usuário
            col_data_pr = next((c for c in df_prioridades.columns if 'prazo' in c.lower()), find_date_col(df_prioridades))
            df_prioridades['_Data'] = df_prioridades[col_data_pr].apply(robust_date_parse)
            df_prioridades['_Mes_Ano'] = df_prioridades['_Data'].dt.strftime('%m/%Y').fillna('Desconhecido')

        # Processar nova aba de Avisos
        if not df_avisos.empty:
            col_prazo = next((c for c in df_avisos.columns if 'prazo' in c.lower()), find_date_col(df_avisos))
            df_avisos['_Data_Prazo'] = df_avisos[col_prazo].apply(robust_date_parse)

        # Ordenar por data (Mais recentes primeiro)
        if not df_ocorrencias.empty and 'Data' in df_ocorrencias.columns:
            df_ocorrencias = df_ocorrencias.sort_values('Data', ascending=False)
        if not df_ocorrencias_fora.empty and 'Data' in df_ocorrencias_fora.columns:
            df_ocorrencias_fora = df_ocorrencias_fora.sort_values('Data', ascending=False)
        if not df_folha.empty and 'Data' in df_folha.columns:
            df_folha = df_folha.sort_values('Data', ascending=False)

        # 📌 MANTENDO OS DADOS BRUTOS E CRIANDO O ÍNDICE DE PROLIXIDADE
        if not df_ocorrencias.empty:
            col_descricao = next((col for col in df_ocorrencias.columns if any(k in col.lower() for k in ['detalhamento', 'descri', 'ocorrencia'])), df_ocorrencias.columns[3] if len(df_ocorrencias.columns) > 3 else df_ocorrencias.columns[-1])
            df_ocorrencias['Texto_Bruto'] = df_ocorrencias[col_descricao].fillna("Sem descrição")
            
            # 📌 NOVA CATEGORIZAÇÃO DE OCORRÊNCIAS (SEÇÃO EDIÇÃO)
            def categorizar(texto):
                t = str(texto).lower()
                if any(q in t for q in ['prazo', 'atraso', 'demora', 'quando', 'cade', 'cadê', 'cobrança', 'pronto', 'prontos', 'falta', 'hoje', 'ainda n', 'dia']): return "COBRANÇA DE PRAZO"
                if any(q in t for q in ['simples', 'rápido', 'fácil', 'pequeno', 'tarja', 'logo', 'texto']): return "TAREFA SIMPLES"
                if any(q in t for q in ['problema', 'erro', 'falha', 'técnico', 'áudio', 'render', 'corrompido', 'som', 'ruído']): return "PROBLEMA TÉCNICO"
                if any(q in t for q in ['múltiplos', 'vários', 'lote', 'pacote', 'mais de um', 'dois', 'três', 'bloco']): return "MÚLTIPLOS VÍDEOS"
                if any(q in t for q in ['ajuste', 'correção', 'corrigir', 'mudar', 'alterar', 'refazer', 'cor', 'corte']): return "AJUSTES/CORREÇÕES"
                if any(q in t for q in ['doc', 'documento', 'drive', 'link', 'pasta']): return "CORREÇÕES (VIA DOCS)"
                if any(q in t for q in ['crític', 'urgente', 'cliente', 'pra ontem', 'reclam']): return "CRÍTICO/URGENTE"
                if any(q in t for q in ['status', 'como está', 'andamento', 'feito']): return "STATUS DE CORREÇÕES"
                if any(q in t for q in ['formato', 'reels', 'shorts', 'tiktok', 'quadrado', 'horizontal', 'vertical', 'proporção', 'broll', 'b-roll', 'inserção']): return "MUDANÇA DE FORMATO"
                if any(q in t for q in ['pendente', 'esqueceu', 'não foi']): return "VÍDEOS PENDENTES"
                return "OUTROS"
                
            df_ocorrencias['Tipo_Ocorrência'] = df_ocorrencias['Texto_Bruto'].apply(categorizar)

        # 📌 NOVA CATEGORIZAÇÃO DE OCORRÊNCIAS (FORA DA EDIÇÃO)
        if not df_ocorrencias_fora.empty:
            def categorizar_fora(texto):
                t = str(texto).lower()
                if any(q in t for q in ['status', 'planilha', 'não mudaram', 'não colocaram', 'saber que tem', 'manual']): return "PROCESSO/STATUS (PLANILHA)"
                if any(q in t for q in ['corrompido', 'grava', 'áudio', 'ruim', 'inalterado', 'separado', 'incompleto', 'baixa qualidade']): return "PROB. TÉCNICO (GRAVAÇÃO)"
                if any(q in t for q in ['desorganizado', 'bagunça', 'quebra cabeça', 'procurar', 'pasta', 'drive', 'Dropbox']): return "DESORGANIZAÇÃO DE DRIVE"
                if any(q in t for q in ['upload', 'subiu', 'demora', 'atraso', 'link']): return "ATRASO DE UPLOAD/LINK"
                if any(q in t for q in ['ajuste', 'alteração', 'meses depois', 'tempo depois', 'antigo', 'refazer', 'picado']): return "AJUSTES TARDIOS/PICADOS"
                return "OUTROS"

            col_desc_fora = next((col for col in df_ocorrencias_fora.columns if any(k in col.lower() for k in ['incidente', 'descri', 'ocorrencia'])), df_ocorrencias_fora.columns[1] if len(df_ocorrencias_fora.columns) > 1 else df_ocorrencias_fora.columns[-1])
            df_ocorrencias_fora['Tipo_Ocorrência'] = df_ocorrencias_fora[col_desc_fora].fillna("Sem descrição").apply(categorizar_fora)

    except Exception as e:
        st.warning(f"Aviso no tratamento dos dados: {e}")
        
    return df_ajustes, df_folha, df_ocorrencias, df_ocorrencias_fora, df_prioridades, df_avisos

# =====================================================================
# INTERFACE DO DASHBOARD
# =====================================================================

def render_header(titulo, subtitulo):
    st.markdown(f"""
<div style="background-color: white; padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-subtle); margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); display: flex; align-items: center; gap: 1.5rem;">
    <div style="background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%); width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 15px -3px rgba(124, 58, 237, 0.3);">
        <svg viewBox="0 0 24 24" width="32" height="32" stroke="white" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
    </div>
    <div>
        <h1 style="margin: 0; font-size: 1.75rem; color: #1E293B; letter-spacing: -0.025em; font-weight: 800;">{titulo}</h1>
        <p style="margin: 0; color: #64748B; font-size: 0.875rem; font-weight: 500;">{subtitulo}</p>
    </div>
</div>
""", unsafe_allow_html=True)

def render_central_avisos(df_avisos):
    render_header("Central de Avisos", "Gestão de Prazos e Entregas")
    
    if df_avisos.empty:
        st.info("Nenhuma demanda encontrada na base de avisos.")
        return
        
    # Identificar coluna de status (status Edição)
    col_status = next((c for c in df_avisos.columns if 'status' in c.lower() and 'edi' in c.lower()), None)
    if not col_status:
        # Fallback
        col_status = next((c for c in df_avisos.columns if 'status' in c.lower()), None)
        
    if not col_status or '_Data_Prazo' not in df_avisos.columns:
        st.warning("Colunas de 'Status Edição' ou 'Prazo' não identificadas.")
        st.dataframe(df_avisos, use_container_width=True, hide_index=True)
        return

    hoje = pd.Timestamp.now().normalize()
    
    # "todos que estiverem passado o prazo de entrega e não estiver como finalizado, configura atraso"
    mask_atrasados = (df_avisos['_Data_Prazo'] < hoje) & (~df_avisos[col_status].astype(str).str.lower().str.contains('finalizado', na=False))
    v_atrasados = df_avisos[mask_atrasados]
    
    fim_semana = hoje + pd.Timedelta(days=(6 - hoje.weekday()))
    mask_semana = (df_avisos['_Data_Prazo'] >= hoje) & (df_avisos['_Data_Prazo'] <= fim_semana) & (~df_avisos[col_status].astype(str).str.lower().str.contains('finalizado', na=False))
    v_semana = df_avisos[mask_semana]
    
    c_v = [c for c in df_avisos.columns if not c.startswith('_') and c not in ['_SheetRowIdx']]
    
    st.markdown('<div style="color:#9F1239; font-weight:700;">🚨 Atrasados</div>', unsafe_allow_html=True)
    if not v_atrasados.empty: 
        st.dataframe(v_atrasados[c_v], use_container_width=True, hide_index=True)
    else: 
        st.success("Tudo em dia!")
        
    st.markdown('<div style="color:#5B21B6; font-weight:700; margin-top:20px;">📅 Entregas desta Semana</div>', unsafe_allow_html=True)
    if not v_semana.empty: 
        st.dataframe(v_semana[c_v], use_container_width=True, hide_index=True)
    else: 
        st.info("Fila vazia para esta semana.")

def render_dossie(df_ocorrencias, df_ocorrencias_fora, df_ajustes, df_prioridades):
    render_header("Dossiê do Cliente", "Histórico Consolidado | Visão 360º")
    
    # Barra de busca centralizada
    col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
    with col_s2:
        # Usar session_state para permitir que botões de sugestão preencham a busca
        if 'search_dossie_val' not in st.session_state:
            st.session_state['search_dossie_val'] = ""
            
        nome_busca = st.text_input("👤 Nome do Cliente", value=st.session_state['search_dossie_val'], placeholder="Digite o nome para gerar o dossiê...", help="Busca em todas as bases de dados")
        btn_gerar = st.button("Gerar Dossiê Completo", use_container_width=True, type="primary")

    if nome_busca or btn_gerar:
        # Normalizar nomes para busca
        termo = str(nome_busca).strip().lower()
        
        if not termo:
            st.warning("Por favor, digite um nome para pesquisar.")
            return

        # 1. Identificar colunas de nome em cada base
        col_n_aj = next((c for c in df_ajustes.columns if 'nome' in c.lower()), None)
        col_n_oc = next((c for c in df_ocorrencias.columns if 'mentorado' in c.lower() or 'cliente' in c.lower()), None)
        col_n_of = next((c for c in df_ocorrencias_fora.columns if 'cliente' in c.lower()), None)
        col_n_pr = next((c for c in df_prioridades.columns if 'nome' in c.lower()), None)

        # 2. Filtrar Dados
        res_aj = df_ajustes[df_ajustes[col_n_aj].astype(str).str.lower().str.contains(termo, na=False)] if col_n_aj else pd.DataFrame()
        res_oc = df_ocorrencias[df_ocorrencias[col_n_oc].astype(str).str.lower().str.contains(termo, na=False)] if col_n_oc else pd.DataFrame()
        res_of = df_ocorrencias_fora[df_ocorrencias_fora[col_n_of].astype(str).str.lower().str.contains(termo, na=False)] if col_n_of else pd.DataFrame()
        res_pr = df_prioridades[df_prioridades[col_n_pr].astype(str).str.lower().str.contains(termo, na=False)] if col_n_pr else pd.DataFrame()

        if res_aj.empty and res_oc.empty and res_of.empty and res_pr.empty:
            st.error(f"Nenhum registro encontrado para '{nome_busca}'.")
            return

        # 3. Métricas de Resumo
        st.subheader("📊 Resumo de Atividades")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tickets de Ajuste", len(res_aj))
        m2.metric("Incidentes (Edição)", len(res_oc))
        m3.metric("Incidentes (Externos)", len(res_of))
        m4.metric("Vídeos em Pauta", len(res_pr))

        # 4. Blocos de Informação
        tab1, tab2, tab3, tab4 = st.tabs(["🕒 Histórico de Ocorrências", "🎫 Tickets de Ajuste", "🎬 Status de Produção", "🚨 Incidentes Externos"])

        with tab1:
            st.markdown("### Histórico Consolidado de Incidentes")
            # Unificar ocorrências internas e externas para linha do tempo
            timeline = []
            
            if not res_oc.empty:
                for _, r in res_oc.iterrows():
                    timeline.append({
                        'Data': r.get('Data', 'N/A'),
                        'Origem': '🛠️ Interno',
                        'Tipo': r.get('Tipo_Ocorrência', 'Outros'),
                        'Descrição': r.get('Texto_Bruto', 'N/A')
                    })
            
            if not res_of.empty:
                col_d_of = next((c for c in df_ocorrencias_fora.columns if 'descri' in c.lower()), 'Descrição')
                for _, r in res_of.iterrows():
                    timeline.append({
                        'Data': r.get('Data', 'N/A'),
                        'Origem': '🚨 Externo',
                        'Tipo': r.get('Tipo_Ocorrência', 'Outros'),
                        'Descrição': r.get(col_d_of, 'N/A')
                    })
            
            if timeline:
                df_timeline = pd.DataFrame(timeline).sort_values('Data', ascending=False)
                st.dataframe(df_timeline, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma ocorrência registrada para este cliente.")

        with tab2:
            st.markdown("### Solicitações de Ajustes (Tickets)")
            if not res_aj.empty:
                cols_aj = [c for c in res_aj.columns if not c.startswith('_') and c not in ['Endereço de e-mail']]
                st.dataframe(res_aj[cols_aj], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum ticket de ajuste encontrado.")

        with tab3:
            st.markdown("### Status Atual na Produção")
            if not res_pr.empty:
                cols_pr = [c for c in res_pr.columns if not c.startswith('_')]
                st.dataframe(res_pr[cols_pr], use_container_width=True, hide_index=True)
                
                # Highlight de Atrasos
                atrasados = res_pr[res_pr['Entregue'].str.lower() != 'entregou']
                if not atrasados.empty:
                    st.warning(f"⚠️ Existem {len(atrasados)} vídeos com entrega pendente para este cliente.")
            else:
                st.info("Cliente não encontrado na pauta de produção atual.")

        with tab4:
            st.markdown("### Incidentes Fora da Edição")
            if not res_of.empty:
                cols_of = [c for c in res_of.columns if not c.startswith('_') and c not in ['Mes_Ano', 'Data']]
                st.dataframe(res_of[cols_of], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum incidente externo registrado para este cliente.")

    else:
        # Tela inicial do dossiê
        st.info("Use a busca acima para encontrar o histórico de um cliente específico.")


# Main Application Logic
with st.spinner("FrameControl Engine Initializing..."):
    raw_ajustes, raw_folha, raw_ocorrencias, raw_ocorrencias_fora, df_ranking_editores, df_prioridades, raw_avisos = carregar_dados()
    
    if raw_ocorrencias is not None:
        df_ajustes_p, df_folha_p, df_ocorrencias_p, df_ocorrencias_fora_p, df_prioridades_p, df_avisos_p = preparar_dados(raw_ajustes, raw_folha, raw_ocorrencias, raw_ocorrencias_fora, df_prioridades, raw_avisos)
        
        st.session_state['df_prioridades_raw'] = df_prioridades_p
        
        # Sidebar Navigation
        st.sidebar.title("FrameControl Docs")
        page = st.sidebar.radio("Navegação", ["Dossiê do Cliente", "Central de Avisos"])
        st.sidebar.divider()
        
        if page == "Dossiê do Cliente":
            render_dossie(df_ocorrencias_p, df_ocorrencias_fora_p, df_ajustes_p, df_prioridades_p)
        elif page == "Central de Avisos":
            render_central_avisos(df_avisos_p)
    else:
        st.warning("Falha ao carregar dados. Verifique a autenticação.")
