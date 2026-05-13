import streamlit as st
import pandas as pd
import numpy as np
import pdfplumber
import re
import io
import os
import json
import hashlib
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Focus ERP - Viabilidade",
    layout="wide",
    page_icon="📈"
)

st.markdown("""
<style>
/* Base */
.stApp { background-color: #f1f3f5; }
html, body, [class*="st-"] { font-size: 16px !important; }

/* Cabeçalhos */
.header-box {
    background-color: #1a1a2e;
    color: #ffffff;
    padding: 22px 30px;
    border-radius: 10px;
    font-size: 28px;
    font-weight: 900;
    text-align: center;
    margin-bottom: 20px;
    border-bottom: 5px solid #1a73e8;
    letter-spacing: 1px;
}
.sub-header {
    background-color: #444;
    color: #fff;
    padding: 10px 18px;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
    margin: 16px 0 10px 0;
}

/* Caixas brancas */
.main-box {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 22px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.09);
    margin-bottom: 20px;
}

/* Valor final */
.valor-final-destaque {
    background-color: #ffff00;
    color: #000000 !important;
    padding: 30px;
    border-radius: 16px;
    text-align: center;
    font-size: 42px !important;
    font-weight: 900;
    border: 6px solid #000;
    margin: 20px 0;
    box-shadow: 0 10px 28px rgba(0,0,0,0.3);
}

/* Status */
.status-final {
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    font-weight: bold;
    font-size: 24px;
    color: white;
    margin-top: 16px;
}
.bg-azul    { background-color: #1a73e8; }
.bg-verde   { background-color: #28a745; }
.bg-amarelo { background-color: #ffc107; color: black !important; }
.bg-vermelho{ background-color: #dc3545; }

/* Painel resumo engenharia */
.painel-resumo {
    background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
    border-radius: 14px;
    padding: 26px;
    margin-top: 24px;
    border: 2px solid #3a3a5e;
    box-shadow: 0 8px 28px rgba(0,0,0,0.3);
}
.painel-resumo-titulo {
    color: #fff;
    font-size: 20px;
    font-weight: 900;
    letter-spacing: 2px;
    text-align: center;
    margin-bottom: 20px;
    text-transform: uppercase;
    border-bottom: 3px solid #1a73e8;
    padding-bottom: 10px;
}
.card-resumo {
    background-color: rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.12);
    margin-bottom: 8px;
}
.card-resumo-label {
    color: #aaaacc;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.card-resumo-valor           { color: #ffffff; font-size: 20px; font-weight: 900; }
.card-resumo-valor.destaque  { color: #ffe600; font-size: 26px; }
.card-resumo-valor.verde     { color: #4cff91; }
.card-resumo-valor.vermelho  { color: #ff6b6b; }
.card-resumo-valor.amarelo   { color: #ffc107; }

.badge-status { display:inline-block; padding:8px 24px; border-radius:50px; font-size:18px; font-weight:900; letter-spacing:1px; margin-top:4px; }
.badge-aprovado-ideal { background-color:#1a73e8; color:white; }
.badge-aprovado       { background-color:#28a745; color:white; }
.badge-ressalva       { background-color:#ffc107; color:#000; }
.badge-reprovado      { background-color:#dc3545; color:white; }

.linha-eng {
    background-color: rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 8px 14px;
    margin-bottom: 5px;
    display: flex;
    justify-content: space-between;
}
.linha-eng-nome { color: #aaaacc; font-size: 13px; }
.linha-eng-val  { color: #ffffff; font-size: 13px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CONSTANTES E CONFIGURAÇÕES
# ==========================================
FILE_PRODUTOS   = "BASE_APP_VIABILIDADE - PRODUTOS.csv"
FILE_SECUNDARIA = "database_produtos_consolidado.csv"
FILE_ORCAMENTOS = "banco_orcamentos.csv"
FILE_USERS      = "usuarios.json"

CODIGOS_INUTILIZADOS = {
    'PP0368','PP0048','PP037B','PP043B','PP0736','PP072B','PP083B',
    'PP001B','PP002B','PP038B','PP058B','NB003','NC001','NC002',
    'NB001','NB002','N013B','N014B','2599','F058B','V001',
    'K003L','K004L','K006L','K065','K084','CABOHPR','1429','1976','2732'
}

MP_PRECOS_PADRAO = {
    "Cobre (kg)":               83.00,
    "Alumínio (kg)":            18.50,
    "PVC Marfim (kg)":           9.50,
    "PVC Hepr/Xlpe (kg)":       17.50,
    "Capa PP (kg)":              9.30,
    "PVC Atox (kg)":            18.60,
    "PVC Emborrachado (kg)":    11.99,
    "Skin/Cores (kg)":          20.00,
    "Embalagem 1 - Filme (un)": 16.70,
    "Embalagem 2 - Etiquetas (un)": 0.10,
}


# ==========================================
# 3. FUNÇÕES UTILITÁRIAS
# ==========================================

def gerar_hash(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def carregar_usuarios() -> dict:
    if not os.path.exists(FILE_USERS):
        dados = {"admin": {"senha": gerar_hash("maxfio123"), "setor": "ADMIN"}}
        with open(FILE_USERS, "w", encoding="utf-8") as f:
            json.dump(dados, f)
        return dados
    with open(FILE_USERS, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_usuario(nome: str, senha: str, setor: str) -> None:
    users = carregar_usuarios()
    users[nome] = {"senha": gerar_hash(senha), "setor": setor}
    with open(FILE_USERS, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)


def autenticar(usuario: str, senha: str) -> bool:
    users = carregar_usuarios()
    if usuario in users:
        return users[usuario]["senha"] == gerar_hash(senha)
    # Login legado (sem hash) — retrocompatibilidade
    return (usuario == "admin" and senha == "maxfio123") or \
           (usuario == "venda" and senha == "1234")


# ==========================================
# 4. CARREGAMENTO DO CSV DE PRODUTOS
# ==========================================

@st.cache_data(show_spinner="Carregando base de produtos…")
def carregar_dados(tipo_base: str = "principal") -> pd.DataFrame:
    """
    Lê o CSV de produtos, normaliza colunas e retorna DataFrame pronto.
    Compatível com separador ';' e decimal tanto '.' quanto ','.
    """
    arquivo = FILE_PRODUTOS if tipo_base == "principal" else FILE_SECUNDARIA

    if not os.path.exists(arquivo):
        st.warning(f"⚠️ Arquivo '{arquivo}' não encontrado na pasta do projeto.")
        return pd.DataFrame()

    df = pd.DataFrame()
    for enc in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            df = pd.read_csv(arquivo, sep=";", encoding=enc, on_bad_lines="skip")
            break
        except (UnicodeDecodeError, ValueError):
            continue
    else:
        st.error(f"Não foi possível decodificar '{arquivo}'. Salve-o como UTF-8 no Excel.")
        return pd.DataFrame()

    df.columns = [c.strip() for c in df.columns]

    # --- Renomeação flexível de colunas ---
    rename_map: dict = {}
    for col in df.columns:
        cn = col.upper().replace("Ç", "C").replace("Ã", "A").replace("Á", "A").replace("É", "E")
        if ("GRUPO" in cn or "FAMILIA" in cn) and "GRUPO/FAMILIA (Abrev.)" not in rename_map.values():
            rename_map[col] = "GRUPO/FAMILIA (Abrev.)"
        elif ("PRECO" in cn or "PREÇO" in cn or "PREC" in cn) and "UNIT" in cn:
            rename_map[col] = "Preço_Unit"
        elif ("CODIGO" in cn or "CÓDIGO" in cn or cn == "CODIGO") and "Código" not in rename_map.values():
            rename_map[col] = "Código"
        elif "NOME" in cn and "PRODUTO" in cn and "Nome do produto" not in rename_map.values():
            rename_map[col] = "Nome do produto"
        elif "PESO" in cn and "TOTAL" in cn and "Peso_Total_kg" not in rename_map.values():
            rename_map[col] = "Peso_Total_kg"

    # Mapeamento direto para o CSV enviado pelo usuário
    direto = {
        "CÓDIGO":         "Código",
        "CODIGO":         "Código",
        "Preço Unitário": "Preço_Unit",
        "Preco Unitario": "Preço_Unit",
        "Preco_Unitario": "Preço_Unit",
        "Preço_Unitario": "Preço_Unit",
        "Preço Unitario": "Preço_Unit",
    }
    for orig, dest in direto.items():
        if orig in df.columns and dest not in df.columns:
            rename_map[orig] = dest

    df = df.rename(columns=rename_map)

    # Garante colunas obrigatórias
    obrigatorias = {
        "GRUPO/FAMILIA (Abrev.)": "Sem Grupo",
        "Preço_Unit":             0.0,
        "Código":                 "",
        "Nome do produto":        "",
        "Peso_Total_kg":          0.0,
    }
    for col, default in obrigatorias.items():
        if col not in df.columns:
            df[col] = default

    # Remove códigos inutilizados
    df = df[~df["Código"].astype(str).str.strip().isin(CODIGOS_INUTILIZADOS)]

    # Converte colunas numéricas (aceita vírgula como decimal)
    cols_num = [
        "Preço_Unit", "Cobre_kg", "Aluminio_kg", "PVC_kg",
        "Peso_Total_kg", "PVC_HEPR", "Capa_PP_kg", "PVC_Atox_kg",
        "PVC_Emb_kg", "Skin_kg", "Embalagem_kg", "Etiqueta_un",
    ]
    for col in cols_num:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .pipe(pd.to_numeric, errors="coerce")
                .fillna(0.0)
            )

    df = df.reset_index(drop=True)
    return df


# ==========================================
# 5. FUNÇÕES DE NEGÓCIO
# ==========================================

def calcular_custo_tecnico(row: pd.Series) -> float:
    """Calcula custo de matéria-prima de um produto usando preços do session_state."""
    mp = st.session_state.get("mp_precos", MP_PRECOS_PADRAO)

    def get_val(col: str) -> float:
        """Retorna valor numérico de uma coluna, ou 0.0 se não existir."""
        val = row.get(col, 0.0)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return 0.0
        return float(val)

    total = (
        get_val("Cobre_kg")     * mp["Cobre (kg)"]                   +
        get_val("Aluminio_kg")  * mp["Alumínio (kg)"]                +
        get_val("PVC_kg")       * mp["PVC Marfim (kg)"]              +
        get_val("PVC_HEPR")     * mp["PVC Hepr/Xlpe (kg)"]           +
        get_val("Capa_PP_kg")   * mp["Capa PP (kg)"]                 +
        get_val("PVC_Atox_kg")  * mp["PVC Atox (kg)"]                +
        get_val("PVC_Emb_kg")   * mp["PVC Emborrachado (kg)"]        +
        get_val("Skin_kg")      * mp["Skin/Cores (kg)"]              +
        get_val("Embalagem_kg") * mp["Embalagem 1 - Filme (un)"]     +
        get_val("Etiqueta_un")  * mp["Embalagem 2 - Etiquetas (un)"]
    )
    return round(total, 4)


def extrair_dados_pdf(file) -> dict:
    """Tenta extrair código, cliente, CNPJ e itens de um PDF de orçamento."""
    dados = {"cliente": "", "cnpj": "", "itens": []}
    try:
        file.seek(0)
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            texto = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
                    for m in re.findall(r"(\d{4,6})\s+(.*?)\s+(\d+)\s+([\d,.]+)", t):
                        dados["itens"].append({
                            "Código":    m[0],
                            "Descrição": m[1].strip(),
                            "Qtd":       float(m[2]),
                            "Preço_Un":  float(m[3].replace(".", "").replace(",", ".")),
                        })
            m_cli = re.search(r"(?:Cliente|Razão Social):\s*(.*)", texto, re.IGNORECASE)
            if m_cli:
                dados["cliente"] = m_cli.group(1).strip()
            m_cnpj = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto)
            if m_cnpj:
                dados["cnpj"] = m_cnpj.group(0)
    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")
    return dados


def salvar_orcamento(dados: dict) -> None:
    df_novo = pd.DataFrame([dados])
    if not os.path.exists(FILE_ORCAMENTOS):
        df_novo.to_csv(FILE_ORCAMENTOS, index=False, sep=";", encoding="utf-8")
    else:
        df_novo.to_csv(FILE_ORCAMENTOS, mode="a", header=False, index=False, sep=";", encoding="utf-8")


def carregar_historico() -> pd.DataFrame:
    if os.path.exists(FILE_ORCAMENTOS):
        try:
            return pd.read_csv(FILE_ORCAMENTOS, sep=";", encoding="utf-8", on_bad_lines="skip")
        except Exception as e:
            st.error(f"Erro ao ler histórico: {e}")
    return pd.DataFrame()


# ==========================================
# 6. INICIALIZAÇÃO DE SESSION STATE
# ==========================================
defaults = {
    "logado":     False,
    "user_atual": "",
    "carrinho":   [],
    "mp_precos":  MP_PRECOS_PADRAO.copy(),
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ==========================================
# 7. TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.markdown('<div class="header-box">🔒 Focus ERP — Acesso ao Sistema</div>', unsafe_allow_html=True)
    col_login = st.columns([1, 2, 1])[1]
    with col_login:
        u = st.text_input("Usuário", key="login_u")
        p = st.text_input("Senha", type="password", key="login_p")
        if st.button("Entrar", use_container_width=True):
            if autenticar(u, p):
                st.session_state.logado    = True
                st.session_state.user_atual = u
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    st.stop()


# ==========================================
# 8. SIDEBAR E CARREGAMENTO DA BASE
# ==========================================
with st.sidebar:
    st.markdown(f"**Usuário:** `{st.session_state.user_atual}`")
    base_ativa = st.toggle("📦 Marcas Secundárias", value=False)
    if st.button("🚪 Sair"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

df_base = carregar_dados("secundaria" if base_ativa else "principal")

COL_GRUPO = "GRUPO/FAMILIA (Abrev.)"
if not df_base.empty and COL_GRUPO in df_base.columns:
    grupos_lista = ["Todas"] + sorted(
        str(g) for g in df_base[COL_GRUPO].dropna().unique()
    )
else:
    grupos_lista = ["Todas"]


# ==========================================
# 9. ABAS PRINCIPAIS
# ==========================================
tab_orc, tab_preco, tab_eng, tab_hist, tab_adm, tab_cfg = st.tabs([
    "🛒 Orçamentos",
    "🏷️ Tabela de Preços",
    "📑 Engenharia",
    "📜 Histórico",
    "⚙️ Admin",
    "🔧 Configurações",
])


# ══════════════════════════════════════════
# ABA 1 — ORÇAMENTOS
# ══════════════════════════════════════════
with tab_orc:
    st.markdown('<div class="header-box">🚀 SISTEMA DE ORÇAMENTOS</div>', unsafe_allow_html=True)

    # Cabeçalho do orçamento
    with st.container():
        st.markdown('<div class="main-box">', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        c1.markdown(f"📅 **Data de Emissão:** {datetime.now().strftime('%d/%m/%Y')}")
        cod_bimer = c2.text_input("🔢 Código BIMER", placeholder="Digite o código gerado no BIMER")
        st.divider()
        c3, c4 = st.columns([2, 1])
        cli  = c3.text_input("👤 Cliente", value=st.session_state.get("cli_temp", ""))
        cnpj = c4.text_input("📄 CNPJ",   value=st.session_state.get("cnpj_temp", ""))
        st.markdown("</div>", unsafe_allow_html=True)

    # Importação via PDF
    with st.expander("📄 Importar dados via PDF"):
        arq_pdf = st.file_uploader("Arraste o PDF do orçamento", type=["pdf"])
        if arq_pdf and st.button("Analisar PDF"):
            res = extrair_dados_pdf(arq_pdf)
            st.session_state["cli_temp"]  = res["cliente"]
            st.session_state["cnpj_temp"] = res["cnpj"]
            for item in res["itens"]:
                base_row = df_base[df_base["Código"].astype(str) == str(item["Código"])]
                peso_un  = float(base_row["Peso_Total_kg"].values[0]) if not base_row.empty else 0.0
                custo_un = calcular_custo_tecnico(base_row.iloc[0]) if not base_row.empty else 0.0
                st.session_state.carrinho.append({
                    "Código":    item["Código"],
                    "Descrição": item["Descrição"],
                    "Peso_Un":   peso_un,
                    "Qtd":       item["Qtd"],
                    "Preço_Un":  item["Preço_Un"],
                    "Custo_Un":  custo_un,
                })
            st.success("Dados importados com sucesso!")
            st.rerun()

    # Pesquisa e adição manual
    with st.expander("🔍 Pesquisar e Adicionar Produto", expanded=True):
        f1, f2, f3 = st.columns([1, 1, 2])
        v_fam = f1.selectbox("Família", grupos_lista, key="orc_familia")
        v_cod = f2.text_input("Código",    key="orc_cod")
        v_des = f3.text_input("Descrição", key="orc_desc")

        df_filtro = df_base.copy()
        if v_fam != "Todas" and COL_GRUPO in df_filtro.columns:
            df_filtro = df_filtro[df_filtro[COL_GRUPO] == v_fam]
        if v_cod:
            df_filtro = df_filtro[df_filtro["Código"].astype(str).str.contains(v_cod, case=False, na=False)]
        if v_des:
            df_filtro = df_filtro[df_filtro["Nome do produto"].str.contains(v_des, case=False, na=False)]

        if not df_filtro.empty:
            opcoes = df_filtro["Código"].astype(str) + " — " + df_filtro["Nome do produto"]
            sel = st.selectbox("Resultado", opcoes, key="orc_sel")
            cod_sel = sel.split(" — ")[0].strip()
            rows = df_base[df_base["Código"].astype(str) == cod_sel]
            if not rows.empty:
                row_sel = rows.iloc[0]
                q1, q2, q3 = st.columns(3)
                qtd_add = q1.number_input("Quantidade", min_value=0.1, value=100.0, step=10.0, key="orc_qtd")
                prc_add = q2.number_input("Preço Unit.", value=float(row_sel["Preço_Unit"]), format="%.4f", key="orc_prc")
                if q3.button("📥 Adicionar ao Orçamento"):
                    custo = calcular_custo_tecnico(row_sel)
                    st.session_state.carrinho.append({
                        "Código":    str(row_sel["Código"]),
                        "Descrição": str(row_sel["Nome do produto"]),
                        "Peso_Un":   float(row_sel["Peso_Total_kg"]),
                        "Qtd":       qtd_add,
                        "Preço_Un":  prc_add,
                        "Custo_Un":  custo,
                    })
                    st.rerun()
        else:
            st.info("Nenhum produto encontrado com os filtros aplicados.")

    # Botão limpar carrinho
    if st.session_state.carrinho:
        if st.button("🗑️ Limpar Carrinho"):
            st.session_state.carrinho = []
            st.rerun()

    # ── Editor do carrinho ──────────────────────────────────────────
    v_f        = 0.0
    margem_liq = 0.0
    status_tx  = "SEM ITENS"
    df_ed      = pd.DataFrame()

    if st.session_state.carrinho:
        st.markdown('<div class="sub-header">🛒 ITENS NO ORÇAMENTO</div>', unsafe_allow_html=True)

        df_cart = pd.DataFrame(st.session_state.carrinho)
        df_cart["Total"]           = df_cart["Qtd"] * df_cart["Preço_Un"]
        df_cart["Peso Total (kg)"] = df_cart["Qtd"] * (df_cart["Peso_Un"] / 100.0)

        df_ed = st.data_editor(
            df_cart,
            column_order=["Código", "Descrição", "Qtd", "Preço_Un", "Peso Total (kg)", "Total"],
            column_config={
                "Código":          st.column_config.TextColumn(disabled=True),
                "Descrição":       st.column_config.TextColumn(disabled=True),
                "Peso Total (kg)": st.column_config.NumberColumn(disabled=True, format="%.3f"),
                "Total":           st.column_config.NumberColumn(disabled=True, format="R$ %.2f"),
                "Qtd":             st.column_config.NumberColumn(min_value=0.1,  format="%.2f"),
                "Preço_Un":        st.column_config.NumberColumn(min_value=0.0,  format="%.4f"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_carrinho",
        )

        # Sincroniza edições de volta ao session_state
        if not df_ed.equals(df_cart):
            st.session_state.carrinho = df_ed.to_dict("records")
            st.rerun()

        subt       = df_ed["Total"].sum()
        peso_geral = df_ed["Peso Total (kg)"].sum()
        c_tot_ind  = df_ed.apply(
            lambda r: r["Qtd"] * float(r.get("Custo_Un", 0) or 0), axis=1
        ).sum()

        # ── Condições financeiras ──
        st.markdown('<div class="sub-header">💳 CONDIÇÕES FINANCEIRAS</div>', unsafe_allow_html=True)
        st.markdown('<div class="main-box">', unsafe_allow_html=True)
        cf1, cf2, cf3 = st.columns(3)
        n_parc  = cf1.number_input("Parcelas",              1,   12,  1)
        dias_p  = cf2.number_input("Prazo Total (Dias)",    0,  360, 30)
        juros_m = cf3.number_input("Taxa Juros Mensal (%)", 0.0, 15.0, 0.0, step=0.1)
        v_f = subt * (1 + (juros_m / 100.0) * (dias_p / 30.0))
        st.markdown(
            f'<div class="valor-final-destaque">VALOR FINAL (RB): R$ {v_f:,.2f}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Análise de viabilidade ──
        st.markdown('<div class="sub-header">📈 ANÁLISE DE VIABILIDADE</div>', unsafe_allow_html=True)
        st.markdown('<div class="main-box">', unsafe_allow_html=True)
        av1, av2, av3, av4 = st.columns(4)
        com_ext     = av1.number_input("Comissão Ext. (%)", 0.0, 10.0, 3.0,  step=0.1)
        com_int     = av1.number_input("Comissão Int. (%)", 0.0, 10.0, 0.65, step=0.05)
        taxa_op     = av2.number_input("Taxa Op. (%)",      0.0, 10.0, 3.5,  step=0.1)
        frete_cif   = av2.number_input("Frete CIF (%)",     0.0, 10.0, 3.0,  step=0.1)
        desc_vista  = av3.number_input("Desc. Vista (%)",   0.0, 15.0, 0.0,  step=0.1)
        taxa_cartao = av3.number_input("Taxa Cartão (%)",   0.0, 10.0, 0.0,  step=0.1)
        imp         = av4.number_input("Impostos (%)",      0.0, 30.0, 12.0, step=0.5)
        vmcb        = av4.number_input("VMCB (R$)",         0.0, value=0.0,  step=100.0)

        total_ded_perc = com_ext + com_int + taxa_op + frete_cif + desc_vista + taxa_cartao + imp
        despesa_liq    = v_f * (total_ded_perc / 100.0)
        receita_liq    = v_f - despesa_liq
        lucro_liq      = receita_liq - c_tot_ind - vmcb
        margem_liq     = (lucro_liq / v_f * 100.0) if v_f > 0 else 0.0

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Custo Técnico",   f"R$ {c_tot_ind:,.2f}")
        m2.metric("Venda Bruta",     f"R$ {v_f:,.2f}")
        m3.metric("Receita Líquida", f"R$ {receita_liq:,.2f}")
        m4.metric("Lucro Líquido",   f"R$ {lucro_liq:,.2f}")

        if margem_liq > 13:
            cl_status, status_tx = "bg-azul",    "✅ APROVADO IDEAL"
        elif 10 <= margem_liq <= 13:
            cl_status, status_tx = "bg-verde",   "✅ APROVADO"
        elif 8  <= margem_liq < 10:
            cl_status, status_tx = "bg-amarelo", "⚠️ RESSALVA"
        else:
            cl_status, status_tx = "bg-vermelho","❌ REPROVADO"

        st.markdown(
            f'<div class="status-final {cl_status}">{status_tx} — MARGEM: {margem_liq:.2f}%</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Painel Engenharia ──
        mp_precos = st.session_state.mp_precos
        df_eng    = df_ed.copy()

        def safe(col: str) -> pd.Series:
            if col in df_eng.columns:
                return pd.to_numeric(df_eng[col], errors="coerce").fillna(0.0)
            return pd.Series([0.0] * len(df_eng), index=df_eng.index)

        cobre_tot    = (safe("Cobre_kg")     * df_eng["Qtd"] / 100.0).sum()
        aluminio_tot = (safe("Aluminio_kg")  * df_eng["Qtd"] / 100.0).sum()
        pvc_tot      = (safe("PVC_kg")       * df_eng["Qtd"] / 100.0).sum()
        hepr_tot     = (safe("PVC_HEPR")     * df_eng["Qtd"] / 100.0).sum()
        pp_tot       = (safe("Capa_PP_kg")   * df_eng["Qtd"] / 100.0).sum()
        atox_tot     = (safe("PVC_Atox_kg")  * df_eng["Qtd"] / 100.0).sum()
        emb_tot      = (safe("PVC_Emb_kg")   * df_eng["Qtd"] / 100.0).sum()
        skin_tot     = (safe("Skin_kg")      * df_eng["Qtd"] / 100.0).sum()
        filme_tot    = (safe("Embalagem_kg") * df_eng["Qtd"] / 100.0).sum()
        etiq_tot     = (safe("Etiqueta_un")  * df_eng["Qtd"]         ).sum()

        custo_mp_total = (
            cobre_tot    * mp_precos["Cobre (kg)"]                   +
            aluminio_tot * mp_precos["Alumínio (kg)"]                +
            pvc_tot      * mp_precos["PVC Marfim (kg)"]              +
            hepr_tot     * mp_precos["PVC Hepr/Xlpe (kg)"]           +
            pp_tot       * mp_precos["Capa PP (kg)"]                 +
            atox_tot     * mp_precos["PVC Atox (kg)"]                +
            emb_tot      * mp_precos["PVC Emborrachado (kg)"]        +
            skin_tot     * mp_precos["Skin/Cores (kg)"]              +
            filme_tot    * mp_precos["Embalagem 1 - Filme (un)"]     +
            etiq_tot     * mp_precos["Embalagem 2 - Etiquetas (un)"]
        )

        st.markdown('<div class="painel-resumo">', unsafe_allow_html=True)
        st.markdown('<div class="painel-resumo-titulo">📐 PAINEL DE ENGENHARIA — RESUMO DO ORÇAMENTO</div>', unsafe_allow_html=True)

        pe1, pe2, pe3, pe4 = st.columns(4)

        def card(col_obj, label, valor, cls=""):
            col_obj.markdown(
                f'<div class="card-resumo">'
                f'<div class="card-resumo-label">{label}</div>'
                f'<div class="card-resumo-valor {cls}">{valor}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        card(pe1, "Peso Total",     f"{peso_geral:,.1f} kg")
        card(pe2, "Custo MP Total", f"R$ {custo_mp_total:,.2f}")
        card(pe3, "Venda Bruta",    f"R$ {v_f:,.2f}", "destaque")
        card(pe4, "Margem Líquida", f"{margem_liq:.2f}%",
             "verde" if margem_liq >= 10 else ("amarelo" if margem_liq >= 8 else "vermelho"))

        st.markdown("<br>", unsafe_allow_html=True)
        el1, el2 = st.columns(2)
        with el1:
            for label, kg, preco_unit in [
                ("Cobre",         cobre_tot,    mp_precos["Cobre (kg)"]),
                ("Alumínio",      aluminio_tot, mp_precos["Alumínio (kg)"]),
                ("PVC Marfim",    pvc_tot,      mp_precos["PVC Marfim (kg)"]),
                ("PVC HEPR/XLPE", hepr_tot,     mp_precos["PVC Hepr/Xlpe (kg)"]),
                ("Capa PP",       pp_tot,       mp_precos["Capa PP (kg)"]),
            ]:
                st.markdown(
                    f'<div class="linha-eng">'
                    f'<span class="linha-eng-nome">{label}</span>'
                    f'<span class="linha-eng-val">{kg:,.3f} kg → R$ {kg*preco_unit:,.2f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with el2:
            for label, kg, preco_unit in [
                ("PVC Atox",         atox_tot,  mp_precos["PVC Atox (kg)"]),
                ("PVC Emborrachado", emb_tot,   mp_precos["PVC Emborrachado (kg)"]),
                ("Skin/Cores",       skin_tot,  mp_precos["Skin/Cores (kg)"]),
                ("Embalagem Filme",  filme_tot, mp_precos["Embalagem 1 - Filme (un)"]),
                ("Etiquetas",        etiq_tot,  mp_precos["Embalagem 2 - Etiquetas (un)"]),
            ]:
                st.markdown(
                    f'<div class="linha-eng">'
                    f'<span class="linha-eng-nome">{label}</span>'
                    f'<span class="linha-eng-val">{kg:,.3f} un → R$ {kg*preco_unit:,.2f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        badge_map = {
            "✅ APROVADO IDEAL": "badge-aprovado-ideal",
            "✅ APROVADO":       "badge-aprovado",
            "⚠️ RESSALVA":      "badge-ressalva",
            "❌ REPROVADO":      "badge-reprovado",
        }
        badge_cls = badge_map.get(status_tx, "badge-reprovado")
        st.markdown(
            f'<div style="text-align:center;margin-top:18px;">'
            f'<span class="badge-status {badge_cls}">{status_tx}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Salvar orçamento ──
        st.divider()
        if st.button("💾 Salvar Orçamento no Histórico", use_container_width=True):
            registro = {
                "Data":         datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Codigo_Bimer": cod_bimer,
                "Cliente":      cli,
                "CNPJ":         cnpj,
                "Valor_Bruto":  round(v_f, 2),
                "Custo_MP":     round(custo_mp_total, 2),
                "Margem_Perc":  round(margem_liq, 2),
                "Status":       status_tx,
                "Usuario":      st.session_state.user_atual,
                "Itens":        len(df_ed),
                "Peso_Total":   round(peso_geral, 2),
            }
            salvar_orcamento(registro)
            st.success("✅ Orçamento salvo com sucesso!")


# ══════════════════════════════════════════
# ABA 2 — TABELA DE PREÇOS
# ══════════════════════════════════════════
with tab_preco:
    st.markdown('<div class="header-box">🏷️ TABELA DE PREÇOS</div>', unsafe_allow_html=True)

    if df_base.empty:
        st.warning("Base de produtos não carregada.")
    else:
        tp1, tp2, tp3 = st.columns([1, 1, 2])
        tp_fam = tp1.selectbox("Família", grupos_lista, key="tp_fam")
        tp_cod = tp2.text_input("Código", key="tp_cod")
        tp_des = tp3.text_input("Descrição", key="tp_des")

        df_tp = df_base.copy()
        if tp_fam != "Todas" and COL_GRUPO in df_tp.columns:
            df_tp = df_tp[df_tp[COL_GRUPO] == tp_fam]
        if tp_cod:
            df_tp = df_tp[df_tp["Código"].astype(str).str.contains(tp_cod, case=False, na=False)]
        if tp_des:
            df_tp = df_tp[df_tp["Nome do produto"].str.contains(tp_des, case=False, na=False)]

        colunas_show = [c for c in ["Código", "Nome do produto", COL_GRUPO, "Preço_Unit", "Peso_Total_kg"] if c in df_tp.columns]
        st.dataframe(
            df_tp[colunas_show].rename(columns={"Preço_Unit": "Preço Unit. (R$)", "Peso_Total_kg": "Peso/100m (kg)"}),
            use_container_width=True,
            height=520,
        )
        st.caption(f"**{len(df_tp)} produtos** exibidos de {len(df_base)} na base ativa.")


# ══════════════════════════════════════════
# ABA 3 — ENGENHARIA (CONSULTA UNITÁRIA)
# ══════════════════════════════════════════
with tab_eng:
    st.markdown('<div class="header-box">📑 FICHA TÉCNICA — ENGENHARIA</div>', unsafe_allow_html=True)

    if df_base.empty:
        st.warning("Base de produtos não carregada.")
    else:
        ec1, ec2 = st.columns([1, 2])
        eng_cod = ec1.text_input("Código do produto", key="eng_cod")
        eng_des = ec2.text_input("Descrição",         key="eng_des")

        df_eng_f = df_base.copy()
        if eng_cod:
            df_eng_f = df_eng_f[df_eng_f["Código"].astype(str).str.contains(eng_cod, case=False, na=False)]
        if eng_des:
            df_eng_f = df_eng_f[df_eng_f["Nome do produto"].str.contains(eng_des, case=False, na=False)]

        if not df_eng_f.empty:
            sel_eng = st.selectbox(
                "Selecione o produto",
                df_eng_f["Código"].astype(str) + " — " + df_eng_f["Nome do produto"],
                key="eng_sel",
            )
            cod_eng = sel_eng.split(" — ")[0].strip()
            row_eng = df_base[df_base["Código"].astype(str) == cod_eng].iloc[0]

            custo_eng  = calcular_custo_tecnico(row_eng)
            preco_eng  = float(row_eng.get("Preço_Unit", 0) or 0)
            margem_eng = ((preco_eng - custo_eng) / preco_eng * 100) if preco_eng > 0 else 0

            st.divider()
            ec3, ec4, ec5 = st.columns(3)
            ec3.metric("Custo MP (por 100m)", f"R$ {custo_eng:.4f}")
            ec4.metric("Preço Tabela",        f"R$ {preco_eng:.4f}")
            ec5.metric("Margem MP",           f"{margem_eng:.1f}%")

            mp_precos = st.session_state.mp_precos
            composicao = {
                "Cobre":            (float(row_eng.get("Cobre_kg",    0) or 0), mp_precos["Cobre (kg)"]),
                "Alumínio":         (float(row_eng.get("Aluminio_kg", 0) or 0), mp_precos["Alumínio (kg)"]),
                "PVC Marfim":       (float(row_eng.get("PVC_kg",      0) or 0), mp_precos["PVC Marfim (kg)"]),
                "PVC HEPR/XLPE":    (float(row_eng.get("PVC_HEPR",    0) or 0), mp_precos["PVC Hepr/Xlpe (kg)"]),
                "Capa PP":          (float(row_eng.get("Capa_PP_kg",  0) or 0), mp_precos["Capa PP (kg)"]),
                "PVC Atox":         (float(row_eng.get("PVC_Atox_kg", 0) or 0), mp_precos["PVC Atox (kg)"]),
                "PVC Emborrachado": (float(row_eng.get("PVC_Emb_kg",  0) or 0), mp_precos["PVC Emborrachado (kg)"]),
                "Skin/Cores":       (float(row_eng.get("Skin_kg",     0) or 0), mp_precos["Skin/Cores (kg)"]),
                "Embalagem Filme":  (float(row_eng.get("Embalagem_kg",0) or 0), mp_precos["Embalagem 1 - Filme (un)"]),
                "Etiquetas":        (float(row_eng.get("Etiqueta_un", 0) or 0), mp_precos["Embalagem 2 - Etiquetas (un)"]),
            }

            df_comp = pd.DataFrame(
                [(mat, qty, preco, qty * preco) for mat, (qty, preco) in composicao.items()],
                columns=["Material", "Qtd/100m", "Preço Unit.", "Custo Total"],
            )
            df_comp = df_comp[df_comp["Qtd/100m"] > 0]
            st.dataframe(
                df_comp.style.format({"Qtd/100m": "{:.4f}", "Preço Unit.": "R$ {:.4f}", "Custo Total": "R$ {:.4f}"}),
                use_container_width=True,
                hide_index=True,
            )

            obs = str(row_eng.get("Observação", "") or row_eng.get("Observacao", "") or "")
            if obs and obs.strip() and obs.strip().lower() != "nan":
                st.warning(f"⚠️ Observação: {obs}")
        else:
            st.info("Digite um código ou descrição para pesquisar.")


# ══════════════════════════════════════════
# ABA 4 — HISTÓRICO
# ══════════════════════════════════════════
with tab_hist:
    st.markdown('<div class="header-box">📜 HISTÓRICO DE ORÇAMENTOS</div>', unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum orçamento salvo ainda.")
    else:
        h1, h2 = st.columns([2, 1])
        busca_hist = h1.text_input("🔍 Pesquisar (cliente, código, status…)", key="hist_busca")
        h2.markdown(f"**{len(df_hist)} orçamentos** registrados")

        if busca_hist:
            mask = df_hist.apply(
                lambda r: r.astype(str).str.contains(busca_hist, case=False).any(), axis=1
            )
            df_hist = df_hist[mask]

        st.dataframe(df_hist, use_container_width=True, height=480)

        csv_bytes = df_hist.to_csv(index=False, sep=";", encoding="utf-8").encode("utf-8")
        st.download_button(
            "⬇️ Exportar CSV",
            data=csv_bytes,
            file_name=f"historico_orcamentos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )


# ══════════════════════════════════════════
# ABA 5 — ADMIN
# ══════════════════════════════════════════
with tab_adm:
    st.markdown('<div class="header-box">⚙️ ADMINISTRAÇÃO</div>', unsafe_allow_html=True)

    if st.session_state.user_atual not in ("admin",):
        st.error("Acesso restrito ao administrador.")
    else:
        adm1, adm2 = st.columns([1, 2])

        with adm1:
            st.subheader("Cadastrar Usuário")
            u_nome  = st.text_input("Login",  key="adm_login")
            u_pass  = st.text_input("Senha",  type="password", key="adm_pass")
            u_setor = st.selectbox("Setor", ["ADMIN", "COMERCIAL", "PCP", "ESTOQUE"], key="adm_setor")
            if st.button("Cadastrar", key="adm_cad"):
                if u_nome and u_pass:
                    salvar_usuario(u_nome, u_pass, u_setor)
                    st.success(f"Usuário '{u_nome}' salvo!")
                else:
                    st.warning("Preencha login e senha.")

        with adm2:
            st.subheader("Usuários cadastrados")
            users    = carregar_usuarios()
            df_users = pd.DataFrame([
                {"Login": k, "Setor": v.get("setor", "—")} for k, v in users.items()
            ])
            st.dataframe(df_users, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("⚠️ Zona de Risco")
        if st.button("🗑️ Apagar TODO o Histórico de Orçamentos", type="secondary"):
            if os.path.exists(FILE_ORCAMENTOS):
                os.remove(FILE_ORCAMENTOS)
                st.success("Histórico apagado.")
            else:
                st.info("Nenhum histórico encontrado.")


# ══════════════════════════════════════════
# ABA 6 — CONFIGURAÇÕES (Preços de MP)
# ══════════════════════════════════════════
with tab_cfg:
    st.markdown('<div class="header-box">🔧 CONFIGURAÇÕES — PREÇOS DE MATÉRIA-PRIMA</div>', unsafe_allow_html=True)
    st.info("Altere os preços abaixo. Os custos técnicos serão recalculados automaticamente.")

    mp_atual     = st.session_state.mp_precos
    novos_precos = {}

    colunas_mp = st.columns(2)
    for i, (mat, preco) in enumerate(mp_atual.items()):
        col = colunas_mp[i % 2]
        novos_precos[mat] = col.number_input(
            f"{mat}",
            value=float(preco),
            min_value=0.0,
            step=0.01,
            format="%.4f",
            key=f"cfg_mp_{i}",
        )

    if st.button("💾 Salvar Preços de MP", use_container_width=True):
        st.session_state.mp_precos = novos_precos
        carregar_dados.clear()
        st.success("✅ Preços atualizados! Os cálculos do orçamento já usam os novos valores.")
        st.rerun()

    st.divider()
    if st.button("↩️ Restaurar Padrões de Fábrica"):
        st.session_state.mp_precos = MP_PRECOS_PADRAO.copy()
        st.success("Preços restaurados para os valores padrão.")
        st.rerun()