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
ID_CHURNS = '1sPXv_zDJK0HJ02V8cQo560UBfOSpEUo1SAtsd-sk2Hk'

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
        }

        /* Forçar contraste nos botões que recebem bug de dark mode no cloud */
        [data-testid="stButton"] button,
        [data-testid="stPopover"] button,
        [data-testid="baseButton-secondary"] {
            background-color: #1E293B !important;
            border-color: #1E293B !important;
        }
        
        /* Força a cor do texto de absolutamente TUDO dentro do botao */
        [data-testid="stButton"] button,
        [data-testid="stButton"] button *,
        [data-testid="stPopover"] button,
        [data-testid="stPopover"] button *,
        [data-testid="baseButton-secondary"],
        [data-testid="baseButton-secondary"] * {
            color: #FFFFFF !important;
        }

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

def get_sheet_data(service, spreadsheet_id, range_name, silent=False, header_row=0):
    """Puxa os dados de uma aba específica da planilha e converte para Pandas DataFrame."""
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            return pd.DataFrame()

        # Permitir pular linhas no cabeçalho se especificado (útil para planilhas com títulos na linha 1)
        if header_row > 0 and len(values) > header_row:
            header = values[header_row]
            data = values[header_row+1:]
        else:
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
            row.append(i + header_row + 2) # ROW INDEX no Google Sheets (1-indexed + offset do cabeçalho)
            adjusted_data.append(row)

        header.append('_SheetRowIdx')
        df = pd.DataFrame(adjusted_data, columns=header)
        return df
    except Exception as e:
        if not silent:
            st.error(f"Erro ao ler a planilha ID {spreadsheet_id}: {e}")
        return pd.DataFrame()

def update_sheet_cell(service, spreadsheet_id, row_idx, col_idx, value, aba_nome=None):
    """Atualiza uma célula específica na planilha."""
    try:
        # Converter col_idx (0-based) para letra da coluna
        dividend = col_idx + 1
        col_letter = ''
        while dividend > 0:
            modulo = (dividend - 1) % 26
            col_letter = chr(65 + modulo) + col_letter
            dividend = int((dividend - modulo) / 26)
        
        range_name = f"'{aba_nome}'!{col_letter}{row_idx}" if aba_nome else f"{col_letter}{row_idx}"
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
    
    # Aba nova para Central de Avisos no Dossiê (Pula a primeira linha pois o cabeçalho real está na linha 2)
    df_avisos_novo = get_sheet_data(service, ID_AVISOS_NOVO, 'A:Z', header_row=1)
    
    # ——— Processar Churns (Múltiplas Abas de Meses) ———
    abas_churn = ['CHURN_JANEIRO', 'CHURN_FEVEREIRO', 'CHURN_MARCO', 'CHURN_ABRIL', 'CHURN_MAIO', 'CHURN_JUNHO', 'CHURN_JULHO', 'CHURN_AGOSTO', 'CHURN_SETEMBRO', 'CHURN_OUTUBRO', 'CHURN_NOVEMBRO', 'CHURN_DEZEMBRO']
    dfs_churn = []
    for aba_c in abas_churn:
        try:
            df_c = get_sheet_data(service, ID_CHURNS, f"'{aba_c}'!A:Z", silent=True, header_row=1)
            if not df_c.empty:
                df_c['AbaOrigem'] = aba_c
                dfs_churn.append(df_c)
        except: continue
        
    df_churns = pd.concat(dfs_churn, ignore_index=True) if dfs_churn else pd.DataFrame()
    
    return df_ajustes, df_folha, df_ocorrencias, df_ocorrencias_fora, df_ranking_editores, df_prioridades, df_avisos_novo, df_churns


# =====================================================================
# 2. TRATAMENTO DE DADOS (COM ÍNDICE DE PROLIXIDADE)
# =====================================================================
def preparar_dados(df_ajustes, df_folha, df_ocorrencias, df_ocorrencias_fora, df_prioridades, df_avisos, df_churns):
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

        # Processar Churns
        if not df_churns.empty:
            col_data_ch = next((c for c in df_churns.columns if ('data de churn' in c.lower() or 'data' in c.lower()) and 'tentativa' not in c.lower() and 'recupera' not in c.lower()), None)
            if col_data_ch:
                df_churns['DataSort'] = df_churns[col_data_ch].apply(robust_date_parse)
                df_churns['Mes_Ano'] = df_churns['DataSort'].dt.strftime('%m/%Y').fillna('Desconhecido')
            else:
                df_churns['DataSort'] = pd.NaT
                df_churns['Mes_Ano'] = 'Desconhecido'
                
            # Lógica de Fallback: Se a data estiver vazia, infere o mês pelo nome da aba
            def infere_mes_aba(row):
                if row['Mes_Ano'] == 'Desconhecido':
                    aba = str(row.get('AbaOrigem', '')).upper()
                    if 'JANEIRO' in aba: return '01/2026'
                    if 'FEVEREIRO' in aba: return '02/2026'
                    if 'MARCO' in aba or 'MARÇO' in aba: return '03/2026'
                    if 'ABRIL' in aba: return '04/2026'
                    if 'MAIO' in aba: return '05/2026'
                    if 'JUNHO' in aba: return '06/2026'
                    if 'JULHO' in aba: return '07/2026'
                    if 'AGOSTO' in aba: return '08/2026'
                    if 'SETEMBRO' in aba: return '09/2026'
                    if 'OUTUBRO' in aba: return '10/2026'
                    if 'NOVEMBRO' in aba: return '11/2025'
                    if 'DEZ' in aba: return '12/2025'
                return row['Mes_Ano']
                
            df_churns['Mes_Ano'] = df_churns.apply(infere_mes_aba, axis=1)

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
        
    return df_ajustes, df_folha, df_ocorrencias, df_ocorrencias_fora, df_prioridades, df_avisos, df_churns

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

def render_central_avisos(df_avisos, df_ocorrencias_fora):
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

    # Remover anos inválidos (ex: 1900 originários de formatação nas planilhas)
    df_avisos = df_avisos[df_avisos['_Data_Prazo'].dt.year >= 2000]

    # PREPARAÇÃO PARA CONFRONTO DE BLOQUEIOS (Ocorrências Fora da Edição)
    col_mm_avisos = next((c for c in df_avisos.columns if 'mentorado' in c.lower() or 'cliente' in c.lower()), None)
    if not col_mm_avisos: col_mm_avisos = next((c for c in df_avisos.columns if 'mentor' in c.lower()), None) # Fallback

    col_mm_fora = next((c for c in df_ocorrencias_fora.columns if 'mentorado' in c.lower() or 'cliente' in c.lower()), None)
    if not col_mm_fora: col_mm_fora = next((c for c in df_ocorrencias_fora.columns if 'mentor' in c.lower()), None) # Fallback
    col_bloq_fora = next((c for c in df_ocorrencias_fora.columns if 'bloqueio' in c.lower()), None)
    col_motivo_fora = next((c for c in df_ocorrencias_fora.columns if 'motivo' in c.lower()), None)
    col_res_fora = next((c for c in df_ocorrencias_fora.columns if 'resolução' in c.lower() or 'resolucao' in c.lower()), None)
    col_desc_fora = next((c for c in df_ocorrencias_fora.columns if 'descrição' in c.lower() or 'incidente' in c.lower() or 'ocorrência' in c.lower() or 'ocorrencia' in c.lower()), None)

    bloqueados_info = {}
    resolvidos_info = {}
    if not df_ocorrencias_fora.empty and col_mm_fora and col_bloq_fora:
        # Filtra quem está com BLOQUEIO explicitamente
        mask_b = df_ocorrencias_fora[col_bloq_fora].astype(str).str.strip().str.upper() == 'BLOQUEIO'
        df_bloq = df_ocorrencias_fora[mask_b]
        for _, row_b in df_bloq.iterrows():
            nome = str(row_b.get(col_mm_fora, '')).strip().lower()
            if nome:
                motivo = row_b.get(col_motivo_fora, "Sem motivo listado") if col_motivo_fora else "N/A"
                desc = row_b.get(col_desc_fora, "Sem ocorrência listada") if col_desc_fora else "N/A"
                idx_real = row_b.get('_SheetRowIdx')
                bloqueados_info[nome] = {'motivo': motivo, 'desc': desc, 'idx': idx_real}
                
        # Filtra quem está com RESOLVIDO explicitamente
        mask_r = df_ocorrencias_fora[col_bloq_fora].astype(str).str.strip().str.upper() == 'RESOLVIDO'
        df_res = df_ocorrencias_fora[mask_r]
        for _, row_r in df_res.iterrows():
            nome = str(row_r.get(col_mm_fora, '')).strip().lower()
            if nome:
                motivo = row_r.get(col_motivo_fora, "Sem motivo listado") if col_motivo_fora else "N/A"
                desc = row_r.get(col_desc_fora, "Sem ocorrência listada") if col_desc_fora else "N/A"
                resolucao = row_r.get(col_res_fora, "Sem resolução informada") if col_res_fora else "N/A"
                idx_real = row_r.get('_SheetRowIdx')
                resolvidos_info[nome] = {'motivo': motivo, 'desc': desc, 'resolucao': resolucao, 'idx': idx_real}

    hoje = pd.Timestamp.now().normalize()
    
    # "todos que estiverem passado o prazo de entrega e não estiver como finalizado, configura atraso"
    mask_atrasados = (df_avisos['_Data_Prazo'] < hoje) & (~df_avisos[col_status].astype(str).str.lower().str.contains('finalizado', na=False))
    
    fim_semana = hoje + pd.Timedelta(days=(6 - hoje.weekday()))
    mask_semana = (df_avisos['_Data_Prazo'] >= hoje) & (df_avisos['_Data_Prazo'] <= fim_semana) & (~df_avisos[col_status].astype(str).str.lower().str.contains('finalizado', na=False))
    
    # Criar uma flag no dataframe de avisos para descobrir quem está bloqueado usando lógica fuzzy string match
    if col_mm_avisos:
        def check_status(nome_aviso, target_info):
            nome_a = str(nome_aviso).strip().lower()
            if not nome_a or nome_a == 'nan': return False
            for nome_b in target_info.keys():
                # Busca simples de contenção
                if nome_a in nome_b or nome_b in nome_a:
                    return True
                # Considerar typos em lh/ll caso comum do Guillermo/Guilhermo
                if nome_a.replace('ll', 'lh') in nome_b or nome_a.replace('lh', 'll') in nome_b:
                    return True
            return False
            
        df_avisos['_Nome_Lower'] = df_avisos[col_mm_avisos].astype(str).str.strip().str.lower()
        df_avisos['_Is_Blocked'] = df_avisos[col_mm_avisos].apply(lambda n: check_status(n, bloqueados_info))
        df_avisos['_Is_Resolved'] = df_avisos[col_mm_avisos].apply(lambda n: check_status(n, resolvidos_info))
    else:
        df_avisos['_Is_Blocked'] = False
        df_avisos['_Is_Resolved'] = False

    # Separar os bloqueados daqueles que realmente cabem à edição
    v_bloqueados = df_avisos[(mask_atrasados | mask_semana) & df_avisos['_Is_Blocked']].copy()
    v_resolvidos = df_avisos[(mask_atrasados | mask_semana) & df_avisos['_Is_Resolved'] & ~df_avisos['_Is_Blocked']].copy()
    v_atrasados = df_avisos[mask_atrasados & ~df_avisos['_Is_Blocked'] & ~df_avisos['_Is_Resolved']].copy()
    v_semana = df_avisos[mask_semana & ~df_avisos['_Is_Blocked'] & ~df_avisos['_Is_Resolved']].copy()
    
    # Exibir todas as colunas da planilha original (exceto as colunas de controle interno adicionadas no código)
    colunas_internas = ['_Data_Prazo', '_Mes_Ano', '_SheetRowIdx', 'DataSort', 'Data', 'Mes_Ano', 'Texto_Bruto', 'Tipo_Ocorrência', '_Nome_Lower', '_Is_Blocked', '_Is_Resolved']
    c_v = [c for c in df_avisos.columns if c not in colunas_internas]
    
    # ================= UI DE BLOQUEADOS ===================
    if not v_bloqueados.empty:
        st.markdown('<div style="color:#B45309; font-weight:700; margin-bottom: 10px; font-size: 1.2rem;">🛑 Bloqueados por Fatores Externos</div>', unsafe_allow_html=True)
        
        # Como o usuário precisa interagir com os bloqueados, vamos exibir em um formato de lista expansível ou cards
        for i, (_, block_row) in enumerate(v_bloqueados.iterrows()):
            nome = str(block_row.get(col_mm_avisos, '')).strip()
            nome_key_base = nome.lower()
            
            # Recuperar os metadados tolerando as mesmas diferenças
            motivo = 'Não informado'
            desc = 'Não informada'
            idx_planilha = None
            for k, meta in bloqueados_info.items():
                if nome_key_base in k or k in nome_key_base or nome_key_base.replace('ll', 'lh') in k or nome_key_base.replace('lh', 'll') in k:
                    motivo = meta.get('motivo', 'Não informado')
                    desc = meta.get('desc', 'Não informada')
                    idx_planilha = meta.get('idx')
                    break

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 1.5, 1.5, 1])
                c1.write(f"**Cliente:** {nome}")
                c2.write(f"**Ocorrência:** {desc}")
                c3.write(f"**Motivo:** {motivo}")
                
                with c4:
                    if idx_planilha and col_bloq_fora and col_res_fora:
                        with st.popover("✅ Block resolvido", use_container_width=True):
                            st.write("Confirmar resolução e destravar produção?")
                            # Usamos um iterador garantido 'i' na key para evitar quebra de aplicativo em caso de índices duplicados da planilha
                            res_texto = st.text_input(f"Como foi resolvido para {nome}?", key=f"res_{idx_planilha}_{i}")
                            if st.button("Confirmar Resolução", key=f"btn_{idx_planilha}_{i}", type="primary"):
                                with st.spinner("Atualizando planilha..."):
                                    # Obter index numérico das colunas na df_ocorrencias_fora (0-indexed para a função update)
                                    # Ignoramos _SheetRowIdx ao buscar a posição usando columns.get_loc
                                    try:
                                        idx_col_bloq = df_ocorrencias_fora.columns.tolist().index(col_bloq_fora)
                                        idx_col_res = df_ocorrencias_fora.columns.tolist().index(col_res_fora)
                                        service = get_google_sheets_service()
                                        
                                        # ID da Planilha de Ocorrências (de onde vem o bloqueio)
                                        ID_OCORRENCIAS_FORA = '16noLo9yfByjZLh4ZPbROz8p-RWdFZpxtiU2Uhz6ffhw'
                                        
                                        ok1, err1 = update_sheet_cell(service, ID_OCORRENCIAS_FORA, idx_planilha, idx_col_res, res_texto)
                                        ok2, err2 = update_sheet_cell(service, ID_OCORRENCIAS_FORA, idx_planilha, idx_col_bloq, "RESOLVIDO")
                                        
                                        if ok1 and ok2:
                                            st.success("Bloqueio finalizado!")
                                            st.cache_data.clear() # Limpa o cash de leitura
                                            st.rerun() # Recarrega a página instantaneamente
                                        else:
                                            st.error(f"Erro ao salvar: {err1} / {err2}")
                                    except Exception as e:
                                        st.error(f"Erro na matriz de colunas: {e}")
                    else:
                        st.write("⚠️ Colunas API faltando")
        st.divider()

    # ================= UI RESTANTE ===================
    st.markdown('<div style="color:#9F1239; font-weight:700;">🚨 Atrasados (Edição)</div>', unsafe_allow_html=True)
    if not v_atrasados.empty: 
        st.dataframe(v_atrasados[c_v], use_container_width=True, hide_index=True)
    else: 
        st.success("Tudo em dia para a edição!")
        
    st.markdown('<div style="color:#5B21B6; font-weight:700; margin-top:20px;">📅 Entregas desta Semana</div>', unsafe_allow_html=True)
    if not v_semana.empty: 
        st.dataframe(v_semana[c_v], use_container_width=True, hide_index=True)
    else: 
        st.info("Fila vazia para esta semana.")

    # ================= UI DE RESOLVIDOS ===================
    if not v_resolvidos.empty:
        st.markdown('<div style="color:#10B981; font-weight:700; margin-bottom: 10px; font-size: 1.2rem; margin-top:30px;">✅ Blocks Resolvidos (Tracking)</div>', unsafe_allow_html=True)
        for i, (_, res_row) in enumerate(v_resolvidos.iterrows()):
            nome = str(res_row.get(col_mm_avisos, '')).strip()
            nome_key_base = nome.lower()
            
            motivo = 'Não informado'
            desc = 'Não informada'
            resolucao = 'Não informada'
            for k, meta in resolvidos_info.items():
                if nome_key_base in k or k in nome_key_base or nome_key_base.replace('ll', 'lh') in k or nome_key_base.replace('lh', 'll') in k:
                    motivo = meta.get('motivo', 'Não informado')
                    desc = meta.get('desc', 'Não informada')
                    resolucao = meta.get('resolucao', 'Não informada')
                    break
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 1.5, 1.5, 1])
                c1.write(f"**Cliente:** {nome}")
                c2.write(f"**Ocorrência:** {desc}")
                c3.write(f"**Motivo Anterior:** {motivo}")
                c4.write(f"**Resolução:** {resolucao}")

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
                # Filtrar colunas indesejadas a pedido do usuário: 'prazo real' e 'Entregue'
                cols_pr = [c for c in res_pr.columns if not c.startswith('_') and c.lower() not in ['prazo real', 'entregue']]
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

def render_churns(df_churns, filtro_mes):
    render_header("Controle de Churns", "Análise de Cancelamentos Não Recuperados")
    
    if df_churns.empty:
        st.info("Nenhum dado de Churn disponível para exibição (Tabelas vazias).")
        return
        
    if not filtro_mes or filtro_mes == "Selecione":
        st.info("Selecione um mês no menu lateral para visualizar os dados.")
        return
        
    # Filtrar pelo Mês
    if 'Mes_Ano' in df_churns.columns:
        df_mes = df_churns[df_churns['Mes_Ano'] == filtro_mes].copy()
    else:
        df_mes = pd.DataFrame()
        
    try:
        # Identificar colunas vitais
        col_status = next((c for c in df_mes.columns if 'status churn' in c.lower()), None)
        col_resp_rev = next((c for c in df_mes.columns if 'respons' in c.lower() and 'revers' in c.lower()), None)
        col_obs = next((c for c in df_mes.columns if 'observa' in c.lower()), None)
        
        # Identificar colunas auxiliares (Dados do Cartão)
        col_cliente = next((c for c in df_mes.columns if 'cliente' in c.lower() and 'contato' not in c.lower() and 'e-mail' not in c.lower()), df_mes.columns[0] if not df_mes.empty else "N/A")
        col_cs = next((c for c in df_mes.columns if 'cs' in c.lower() and 'respons' in c.lower() and 'contato' not in c.lower()), "N/A")
        col_valor = next((c for c in df_mes.columns if 'valor' in c.lower()), "N/A")
        col_data = next((c for c in df_mes.columns if 'data' in c.lower() and c != 'Data de Tentativa de Reversão' and c != 'Data de Recuperaçaõ'), "N/A")
        col_cat = next((c for c in df_mes.columns if 'categoria' in c.lower()), "N/A")
        
        if not col_status:
            st.warning("Coluna 'Status Churn' não encontrada na planilha de Churns.")
            return
            
        # Segmentar os DataFrames por Lógica do Fluxo
        def classificar_fluxo(row):
            cliente_val = str(row.get(col_cliente, "")).strip().lower()
            if not cliente_val or cliente_val in ['nan', 'none', 'nao informado']:
                return 'OUTRO' # Ignorar lixo e linhas 100% vazias da planilha
                
            status = str(row[col_status]).strip().lower() if col_status else ""
            obs = str(row.get(col_obs, "")).strip() if col_obs else ""
            
            # Sanitização para lidar com acentos importados 'Não' / 'Nao' / 'No'
            import unicodedata
            status_clean = unicodedata.normalize('NFKD', status).encode('ASCII', 'ignore').decode('utf-8').strip()
            
            # Verificações seguras com In em vez de comparador estendido
            if status_clean == 'recuperado' or ('recuperado' in status_clean and 'n' in status_clean and obs and obs.lower() not in ['nan', 'none']):
                return 'HISTORICO'
            elif 'tentativa' in status_clean:
                return 'EM_TENTATIVA'
            elif 'recuperado' in status_clean and 'n' in status_clean:
                return 'ABERTO'
            return 'OUTRO' # Se não é nenhum, é linha inútil (Retirado o fallback sujo)
            
        df_mes['Fluxo'] = df_mes.apply(classificar_fluxo, axis=1)
        
        df_abertos = df_mes[df_mes['Fluxo'] == 'ABERTO']
        df_tentativa = df_mes[df_mes['Fluxo'] == 'EM_TENTATIVA']
        df_historico = df_mes[df_mes['Fluxo'] == 'HISTORICO']
        
    except Exception as e:
        st.error(f"Erro fatal ao processar os status de Churn: {str(e)}")
        return
        
    # Helper para re-render de Cards
    def render_card_churn(row, idx_for_key, bg_color="#FFFFFF"):
        cliente = str(row.get(col_cliente, 'Não informado')).strip() if col_cliente != 'N/A' else 'N/A'
        cs = str(row.get(col_cs, 'Não informado')).strip() if col_cs != 'N/A' else 'N/A'
        valor = str(row.get(col_valor, 'Não informado')).strip() if col_valor != 'N/A' else 'N/A'
        data_c = str(row.get(col_data, 'Não informada')).strip() if col_data != 'N/A' else 'N/A'
        cat = str(row.get(col_cat, 'Não informada')).strip() if col_cat != 'N/A' else 'N/A'
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 15px; margin-bottom: 5px;">
            <div style="display:flex; justify-content:space-between;">
                <div style="width: 20%;"><span style='color:#64748B; font-size:11px; font-weight:600; text-transform:uppercase;'>Cliente</span><br><span style='font-size:15px; font-weight:500; color:#1E293B;'>{cliente}</span></div>
                <div style="width: 20%;"><span style='color:#64748B; font-size:11px; font-weight:600; text-transform:uppercase;'>CS</span><br><span style='font-size:14px; color:#1E293B;'>{cs}</span></div>
                <div style="width: 20%;"><span style='color:#64748B; font-size:11px; font-weight:600; text-transform:uppercase;'>Valor</span><br><span style='font-size:15px; color:#10B981; font-weight:600;'>{valor}</span></div>
                <div style="width: 20%;"><span style='color:#64748B; font-size:11px; font-weight:600; text-transform:uppercase;'>Categoria</span><br><span style='font-size:14px; color:#1E293B;'>{cat}</span></div>
                <div style="width: 20%;"><span style='color:#64748B; font-size:11px; font-weight:600; text-transform:uppercase;'>Data</span><br><span style='font-size:14px; color:#1E293B;'>{data_c}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    service = get_google_sheets_service()
    ID_CHURNS = '1sPXv_zDJK0HJ02V8cQo560UBfOSpEUo1SAtsd-sk2Hk'
    idx_col_status = df_mes.columns.tolist().index(col_status) if col_status else -1
    idx_col_resp = df_mes.columns.tolist().index(col_resp_rev) if col_resp_rev else -1
    idx_col_obs = df_mes.columns.tolist().index(col_obs) if col_obs else -1

    # -------------------- SESSÃO: CHURNS ABERTOS --------------------
    if not df_abertos.empty:
        st.markdown(f"### 🔴 Churns Não Recuperados ({len(df_abertos)})")
        for i, row in df_abertos.iterrows():
            aba_origem = row.get('AbaOrigem')
            linha_planilha = row.get('_SheetRowIdx')
            
            with st.container():
                render_card_churn(row, f"ab_{i}")
                if idx_col_resp != -1 and idx_col_status != -1 and linha_planilha is not None:
                    with st.popover("Definir responsável"):
                        with st.form(key=f"frm_resp_{i}"):
                            opcoes_resp = ["Apenas CS", "CS + Head", "Daniel", "Arthur"]
                            resp_novo = st.selectbox("Qual o nome do responsável por rever esse Churn?", options=opcoes_resp, key=f"resp_{i}")
                            submit_resp = st.form_submit_button("Salvar e Iniciar Reversão", type="primary")
                            
                            if submit_resp:
                                with st.spinner("Registrando..."):
                                    try:
                                        # Pula a camada do Streamlit e olha os IDs do sheets nu e cru pra cravar as colunas!
                                        resp = service.spreadsheets().values().get(spreadsheetId=ID_CHURNS, range=f"'{aba_origem}'!A2:Z2").execute()
                                        headers_reais = resp.get('values', [[]])[0]
                                        real_c_resp = next((i for i, c in enumerate(headers_reais) if 'respons' in str(c).lower() and 'revers' in str(c).lower()), idx_col_resp)
                                        real_c_status = next((i for i, c in enumerate(headers_reais) if 'status churn' in str(c).lower()), idx_col_status)
                                    except:
                                        real_c_resp = idx_col_resp
                                        real_c_status = idx_col_status
                                        
                                    ok1, _ = update_sheet_cell(service, ID_CHURNS, int(linha_planilha), real_c_resp, resp_novo, aba_origem)
                                    ok2, _ = update_sheet_cell(service, ID_CHURNS, int(linha_planilha), real_c_status, "Em tentativa de reversão", aba_origem)
                                    if ok1 and ok2:
                                        st.success("Reversão Iniciada!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("Falha ao se conectar com a Planilha Google.")
        st.divider()

    # -------------------- SESSÃO: EM TENTATIVA --------------------
    if not df_tentativa.empty:
        st.markdown(f"### 🟡 Em Tentativa de Reversão ({len(df_tentativa)})")
        for i, row in df_tentativa.iterrows():
            aba_origem = row.get('AbaOrigem')
            linha_planilha = row.get('_SheetRowIdx')
            
            with st.container():
                # Amarelo clarinho pro background ("#FEF9C3")
                render_card_churn(row, f"ten_{i}", bg_color="#FEF9C3")
                
                if idx_col_obs != -1 and idx_col_status != -1 and linha_planilha is not None:
                    cx1, cx2 = st.columns(2)
                    with cx1:
                        with st.popover("🟢 RECUPERADO", use_container_width=True):
                            with st.form(key=f"frm_rec_{i}"):
                                obs_r = st.text_area("Observação / Motivo da Reversão", key=f"obs_r_{i}")
                                submit_r = st.form_submit_button("Confirmar Reversão")
                                if submit_r:
                                    with st.spinner("Atualizando base..."):
                                        try:
                                            resp = service.spreadsheets().values().get(spreadsheetId=ID_CHURNS, range=f"'{aba_origem}'!A2:Z2").execute()
                                            headers_reais = resp.get('values', [[]])[0]
                                            real_c_obs = next((i for i, c in enumerate(headers_reais) if 'observa' in str(c).lower()), idx_col_obs)
                                            real_c_status = next((i for i, c in enumerate(headers_reais) if 'status churn' in str(c).lower()), idx_col_status)
                                        except:
                                            real_c_obs = idx_col_obs
                                            real_c_status = idx_col_status
                                            
                                        update_sheet_cell(service, ID_CHURNS, int(linha_planilha), real_c_obs, obs_r, aba_origem)
                                        update_sheet_cell(service, ID_CHURNS, int(linha_planilha), real_c_status, "Recuperado", aba_origem)
                                        st.cache_data.clear()
                                        st.rerun()
                    with cx2:
                        with st.popover("❌ NÃO RECUPERADO", use_container_width=True):
                            with st.form(key=f"frm_nrec_{i}"):
                                obs_nr = st.text_area("Motivo do fracasso na Reversão", key=f"obs_nr_{i}")
                                submit_nr = st.form_submit_button("Confirmar Fim da Tentativa")
                                if submit_nr:
                                    with st.spinner("Registrando fim..."):
                                        try:
                                            resp = service.spreadsheets().values().get(spreadsheetId=ID_CHURNS, range=f"'{aba_origem}'!A2:Z2").execute()
                                            headers_reais = resp.get('values', [[]])[0]
                                            real_c_obs = next((i for i, c in enumerate(headers_reais) if 'observa' in str(c).lower()), idx_col_obs)
                                            real_c_status = next((i for i, c in enumerate(headers_reais) if 'status churn' in str(c).lower()), idx_col_status)
                                        except:
                                            real_c_obs = idx_col_obs
                                            real_c_status = idx_col_status
                                            
                                        update_sheet_cell(service, ID_CHURNS, int(linha_planilha), real_c_obs, obs_nr, aba_origem)
                                        update_sheet_cell(service, ID_CHURNS, int(linha_planilha), real_c_status, "Não recuperado", aba_origem)
                                        st.cache_data.clear()
                                        st.rerun()
        st.divider()

    # -------------------- SESSÃO: HISTÓRICO --------------------
    if not df_historico.empty:
        st.markdown(f"### 🏁 Histórico de Churns - Mês {filtro_mes} ({len(df_historico)})")
        for i, row in df_historico.iterrows():
            status_atual = str(row.get(col_status, '')).upper()
            obs_atual = str(row.get(col_obs, '')).strip() if col_obs else ""
            
            with st.container(border=True):
                # Fundo de cor leve dependendo do success/failure do histórico 
                cor_bg = "#DCFCE7" if "RECUPERADO" in status_atual and "NÃO" not in status_atual and "NAO" not in status_atual else "#F1F5F9"
                render_card_churn(row, f"hist_{i}", bg_color=cor_bg)
                st.markdown(f"<div style='padding: 5px 15px; font-size:14px;'><span style='font-weight:600;'>Status Final:</span> {status_atual} | <span style='font-weight:600;'>Obs:</span> {obs_atual}</div>", unsafe_allow_html=True)
                
    if df_abertos.empty and df_tentativa.empty and df_historico.empty:
        st.success(f"Nenhum Churn encontrado para o mês de {filtro_mes} 🎉")

# Main Application Logic
with st.spinner("FrameControl Engine Initializing..."):
    raw_ajustes, raw_folha, raw_ocorrencias, raw_ocorrencias_fora, df_ranking_editores, df_prioridades, raw_avisos, raw_churns = carregar_dados()
    
    if raw_ocorrencias is not None:
        df_ajustes_p, df_folha_p, df_ocorrencias_p, df_ocorrencias_fora_p, df_prioridades_p, df_avisos_p, df_churns_p = preparar_dados(raw_ajustes, raw_folha, raw_ocorrencias, raw_ocorrencias_fora, df_prioridades, raw_avisos, raw_churns)
        
        st.session_state['df_prioridades_raw'] = df_prioridades_p
        
        # Sidebar Navigation
        st.sidebar.title("FrameControl Docs")
        page = st.sidebar.radio("Navegação", ["Dossiê do Cliente", "Central de Avisos", "Controle de Churns"])
        
        filtro_mes_churn = None
        if page == "Controle de Churns":
            if not df_churns_p.empty and 'Mes_Ano' in df_churns_p.columns:
                meses_c = [m for m in df_churns_p['Mes_Ano'].dropna().unique() if str(m) != 'Desconhecido']
                meses_c = sorted(meses_c, reverse=True)
            else:
                meses_c = []
                
            st.sidebar.markdown("### Filtros de Churn")
            if meses_c:
                filtro_mes_churn = st.sidebar.selectbox("📅 Selecione o Mês do Churn", meses_c)
            else:
                st.sidebar.info("Aguardando carregar dados de meses")
                
        st.sidebar.divider()
        
        if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if page == "Dossiê do Cliente":
            render_dossie(df_ocorrencias_p, df_ocorrencias_fora_p, df_ajustes_p, df_prioridades_p)
        elif page == "Central de Avisos":
            render_central_avisos(df_avisos_p, df_ocorrencias_fora_p)
        elif page == "Controle de Churns":
            render_churns(df_churns_p, filtro_mes_churn)
    else:
        st.warning("Falha ao carregar dados. Verifique a autenticação.")
