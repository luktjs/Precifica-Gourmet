from datetime import datetime
import io
import json
import os
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURAÇÕES DE E-MAIL (GMAIL)
# ==========================================
EMAIL_REMETENTE = "gabriela_gabi_bibi1992@hotmail.com"
SENHA_APP_GMAIL = "6554728"

# Configuração da página otimizada para responsividade
st.set_page_config(
    page_title="Precifica Gourmet | Gestão Inteligente",
    page_icon="🍰",
    layout="wide",
    initial_sidebar_state="auto",
)

# ==========================================
# CSS CUSTOMIZADO RESPONSIVO (PC & MOBILE UX)
# ==========================================
st.markdown(
    """
    <style>
        /* Fundo geral e tipografia fluida */
        .stApp {
            background-color: #121214;
            color: #E1E1E6;
            font-family: 'Inter', sans-serif;
        }
        
        /* Títulos adaptáveis */
        .main-title {
            font-size: 2rem;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -0.5px;
            margin-bottom: 0px;
        }
        
        .subtitle {
            font-size: 0.95rem;
            color: #A8A8B3;
            margin-bottom: 20px;
        }

        /* Garantir que inputs e botões ocupem 100% do espaço em dispositivos móveis */
        .stButton button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
            padding: 10px 15px;
            transition: all 0.2s ease-in-out;
        }
        
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            background-color: #29292E !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: 1px solid #323238 !important;
        }

        /* Ajuste de tabelas para scroll suave em telemóveis */
        div[data-testid="stDataFrame"] {
            width: 100%;
            overflow-x: auto;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS (SQLITE)
# ==========================================


def init_db():
  conn = sqlite3.connect("banco_precifica.db")
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            senha TEXT,
            email TEXT,
            logo BLOB
        )
    """)

  cursor.execute("PRAGMA table_info(usuarios)")
  colunas = [col[1] for col in cursor.fetchall()]
  if "email" not in colunas:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredientes (
            username TEXT,
            ingrediente TEXT,
            unidade TEXT,
            preco_emb REAL,
            qtd_emb REAL,
            custo_unit REAL
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS instrumentos (
            username TEXT,
            item TEXT,
            valor REAL
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS receitas (
            username TEXT,
            receita TEXT,
            rendimento INTEGER,
            itens_utilizados TEXT,
            custo_ingredientes REAL
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS margens_receitas (
            username TEXT,
            receita TEXT,
            mao_de_obra REAL,
            embalagem REAL,
            outros_custos REAL,
            margem REAL
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS kits (
            username TEXT,
            produto_final TEXT,
            preco_custo REAL,
            preco_sugerido REAL,
            lucro REAL,
            itens_inclusos TEXT
        )
    """)

  cursor.execute("PRAGMA table_info(kits)")
  colunas_kits = [col[1] for col in cursor.fetchall()]
  if "itens_inclusos" not in colunas_kits:
    cursor.execute("ALTER TABLE kits ADD COLUMN itens_inclusos TEXT")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            username TEXT,
            data TEXT,
            produto TEXT,
            quantidade INTEGER,
            preco_unitario REAL,
            faturamento REAL,
            custo_unitario REAL,
            custo_total REAL,
            lucro_bruto REAL,
            forma_pagamento TEXT,
            observacoes TEXT
        )
    """)

  cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
  if not cursor.fetchone():
    cursor.execute(
        "INSERT INTO usuarios (username, senha, email, logo) VALUES (?, ?, ?,"
        " ?)",
        ("admin", "123456", "admin@precificagourmet.com", None),
    )

  conn.commit()
  conn.close()


init_db()

if "autenticado" not in st.session_state:
  st.session_state.autenticado = False
if "username" not in st.session_state:
  st.session_state.username = ""
if "exibir_painel_cliente" not in st.session_state:
  st.session_state.exibir_painel_cliente = False
if "codigo_verificacao_enviado" not in st.session_state:
  st.session_state.codigo_verificacao_enviado = None
if "dados_temp_cadastro" not in st.session_state:
  st.session_state.dados_temp_cadastro = {}

# ==========================================
# FUNÇÃO DE E-MAIL
# ==========================================


def enviar_email_verificacao(destinatario, codigo):
  try:
    msg = MIMEMultipart()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario
    msg["Subject"] = "Código de Verificação - Precifica Gourmet"

    corpo = f"""
        Olá!
        
        Você solicitou o cadastro no sistema Precifica Gourmet.
        O seu código de verificação de 6 dígitos é: {codigo}
        
        Insira este código na tela de cadastro para concluir a ativação da sua conta.
        """
    msg.attach(MIMEText(corpo, "plain"))

    servidor = smtplib.SMTP("smtp.gmail.com", 587)
    servidor.starttls()
    servidor.login(EMAIL_REMETENTE, SENHA_APP_GMAIL)
    servidor.sendmail(EMAIL_REMETENTE, destinatario, msg.as_string())
    servidor.quit()
    return True
  except Exception as e:
    print(f"Erro ao enviar e-mail: {e}")
    return False


# ==========================================
# CARREGAMENTO DE DADOS
# ==========================================


def carregar_dados_usuario(username):
  conn = sqlite3.connect("banco_precifica.db")

  cursor = conn.cursor()
  cursor.execute("SELECT logo FROM usuarios WHERE username = ?", (username,))
  res_logo = cursor.fetchone()
  logo_blob = res_logo[0] if res_logo and res_logo[0] else None

  df_ing = pd.read_sql_query(
      "SELECT ingrediente as Ingrediente, unidade as Unidade, preco_emb as"
      ' "Preço pago no produto (R$)", qtd_emb as "Qtd na Embalagem",'
      ' custo_unit as "Custo Unitário (R$)" FROM ingredientes WHERE'
      " username = ?",
      conn,
      params=(username,),
  )

  df_inst = pd.read_sql_query(
      "SELECT item as 'Item / Utensílio', valor as 'Valor Investido (R$)' FROM"
      " instrumentos WHERE username = ?",
      conn,
      params=(username,),
  )

  df_vendas = pd.read_sql_query(
      "SELECT data as Data, produto as Produto, quantidade as Quantidade,"
      ' preco_unitario as "Preço unitário", faturamento as Faturamento,'
      ' custo_unitario as "Custo unitário", custo_total as "Custo total",'
      ' lucro_bruto as "Lucro bruto", forma_pagamento as "Forma de'
      ' pagamento", observacoes as Observações FROM vendas WHERE username = ?',
      conn,
      params=(username,),
  )

  cursor.execute(
      "SELECT produto_final, preco_custo, preco_sugerido, lucro, itens_inclusos"
      " FROM kits WHERE username = ?",
      (username,),
  )
  kit_rows = cursor.fetchall()
  lista_kits = []
  for k in kit_rows:
    lista_kits.append({
        "Produto Final": k[0],
        "Preço de Custo": k[1],
        "Preço sugerido": k[2],
        "Lucro": k[3],
        "Itens Inclusos": json.loads(k[4]) if k[4] else [],
    })
  df_kits = pd.DataFrame(lista_kits)
  if df_kits.empty:
    df_kits = pd.DataFrame(
        columns=[
            "Produto Final",
            "Preço de Custo",
            "Preço sugerido",
            "Lucro",
            "Itens Inclusos",
        ]
    )

  cursor.execute(
      "SELECT receita, rendimento, itens_utilizados, custo_ingredientes FROM"
      " receitas WHERE username = ?",
      (username,),
  )
  rec_rows = cursor.fetchall()
  lista_receitas = []

  for r in rec_rows:
    lista_receitas.append({
        "Receita": r[0],
        "Rendimento": r[1],
        "Itens Utilizados": json.loads(r[2]),
        "Custo Ingredientes": r[3],
    })
  df_receitas = pd.DataFrame(lista_receitas)
  if df_receitas.empty:
    df_receitas = pd.DataFrame(
        columns=["Receita", "Rendimento", "Itens Utilizados", "Custo Ingredientes"]
    )

  cursor.execute(
      "SELECT receita, mao_de_obra, embalagem, outros_custos, margem FROM"
      " margens_receitas WHERE username = ?",
      (username,),
  )
  marg_rows = cursor.fetchall()
  dict_margens = {}
  for m in marg_rows:
    dict_margens[m[0]] = {
        "Mão de obra": m[1],
        "Embalagem": m[2],
        "Outros custos": m[3],
        "Margem": m[4],
    }

  conn.close()

  st.session_state.ingredientes = df_ing
  st.session_state.instrumentos = df_inst
  st.session_state.vendas = df_vendas
  st.session_state.kits = df_kits
  st.session_state.receitas = df_receitas
  st.session_state.margens_receitas = dict_margens
  st.session_state.logo_img = (
      io.BytesIO(logo_blob) if logo_blob else None
  )


# ==========================================
# CABEÇALHO ADAPTÁVEL (MOBILE & PC)
# ==========================================
col_titulo, col_painel = st.columns([5, 3])

with col_titulo:
  st.markdown(
      "<div style='padding-top: 5px;'><h1 class='main-title'>🍰 Precifica"
      " Gourmet</h1><p class='subtitle'>Gestão inteligente para"
      " confeitaria</p></div>",
      unsafe_allow_html=True,
  )

with col_painel:
  if st.session_state.autenticado:
    with st.container():
      cp1, cp2 = st.columns([2, 3])
      with cp1:
        if st.session_state.get("logo_img") is not None:
          st.image(st.session_state.logo_img, width=100)
        else:
          st.markdown(
              "<p style='font-size:0.75rem; color:#888;'>Sem logótipo</p>",
              unsafe_allow_html=True,
          )
      with cp2:
        st.markdown(
            f"<p style='font-size:0.85rem; color:#fff; margin:0;'>Olá,"
            f" <b>{st.session_state.username}</b></p>",
            unsafe_allow_html=True,
        )
        if st.button("⚙️ Perfil", key="btn_painel_cliente"):
          st.session_state.exibir_painel_cliente = not st.session_state.get(
              "exibir_painel_cliente", False
          )
          st.rerun()
  else:
    st.markdown(
        "<p style='font-size:0.8rem; color:#888; text-align:right;'>Faça login"
        " para aceder</p>",
        unsafe_allow_html=True,
    )

# ==========================================
# ABAS DO SISTEMA
# ==========================================
if not st.session_state.autenticado:
  tab_cadastro, tab_login = st.tabs(["📝 Novo Utilizador", "🔐 Aceder Conta"])
else:
  tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
      "📊 Dash",
      "🛠️ Utens.",
      "🛒 Ingred.",
      "📋 Receitas",
      "💰 Preços",
      "📦 Combos",
      "📈 Vendas",
  ])

# ==========================================
# CONTEÚDO DE CADASTRO E LOGIN
# ==========================================
if not st.session_state.autenticado:
  with tab_cadastro:
    st.subheader("📝 Criar Nova Conta")
    if st.session_state.codigo_verificacao_enviado is None:
      with st.form("form_novo_usuario"):
        novo_u = st.text_input("Nome de Utilizador")
        novo_email = st.text_input("E-mail para Validação")
        novo_s = st.text_input("Palavra-passe", type="password")
        novo_s_conf = st.text_input("Confirmar Palavra-passe", type="password")
        btn_enviar_codigo = st.form_submit_button("Enviar Código por E-mail")

        if btn_enviar_codigo:
          if not novo_u or not novo_email or not novo_s or not novo_s_conf:
            st.error("Preencha todos os campos obrigatórios.")
          elif novo_s != novo_s_conf:
            st.error("❌ As palavras-passe não coincidem.")
          else:
            conn = sqlite3.connect("banco_precifica.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM usuarios WHERE username = ? OR email = ?",
                (novo_u, novo_email),
            )
            if cursor.fetchone():
              st.error("Este utilizador ou e-mail já se encontra registado.")
              conn.close()
            else:
              conn.close()
              codigo = str(random.randint(100000, 999999))
              with st.spinner("A enviar código de verificação..."):
                sucesso_envio = enviar_email_verificacao(novo_email, codigo)
              if sucesso_envio:
                st.session_state.codigo_verificacao_enviado = codigo
                st.session_state.dados_temp_cadastro = {
                    "username": novo_u,
                    "email": novo_email,
                    "senha": novo_s,
                }
                st.success(
                    f"📨 Código enviado com sucesso para **{novo_email}**!"
                )
                st.rerun()
              else:
                st.error(
                    "❌ Falha ao enviar e-mail. Verifique a configuração do"
                    " Gmail."
                )
    else:
      st.info(
          f"Insira o código de 6 dígitos enviado para:"
          f" **{st.session_state.dados_temp_cadastro.get('email')}**"
      )
      with st.form("form_verificacao_codigo"):
        codigo_digitado = st.text_input("Código de Confirmação", max_chars=6)
        btn_validar = st.form_submit_button("Validar e Concluir Registo")
        if btn_validar:
          if codigo_digitado == st.session_state.codigo_verificacao_enviado:
            dados = st.session_state.dados_temp_cadastro
            conn = sqlite3.connect("banco_precifica.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, senha, email, logo) VALUES (?,"
                " ?, ?, ?)",
                (dados["username"], dados["senha"], dados["email"], None),
            )
            conn.commit()
            conn.close()
            st.success(
                "🎉 Conta ativada com sucesso! Vá até à aba de Login para"
                " entrar."
            )
            st.session_state.codigo_verificacao_enviado = None
            st.session_state.dados_temp_cadastro = {}
          else:
            st.error("❌ Código incorreto.")

  with tab_login:
    st.subheader("🔐 Entrar no Sistema")
    with st.form("form_login"):
      u_input = st.text_input("Utilizador ou E-mail")
      s_input = st.text_input("Palavra-passe", type="password")
      btn_l = st.form_submit_button("Aceder Painel")
      if btn_l:
        conn = sqlite3.connect("banco_precifica.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, senha FROM usuarios WHERE username = ? OR email ="
            " ?",
            (u_input, u_input),
        )
        res = cursor.fetchone()
        conn.close()
        if res and res[1] == s_input:
          st.session_state.autenticado = True
          st.session_state.username = res[0]
          carregar_dados_usuario(res[0])
          st.success("Sessão iniciada com sucesso!")
          st.rerun()
        else:
          st.error("Credenciais inválidas.")

# ==========================================
# PAINEL DO UTILIZADOR (CONFIGURAÇÃO DE LOGO)
# ==========================================
if st.session_state.get("autenticado", False) and st.session_state.get(
    "exibir_painel_cliente", False
):
  st.markdown("---")
  with st.container():
    st.subheader(f"⚙️ Configurações da Conta — {st.session_state.username}")
    logo_file_painel = st.file_uploader(
        "Carregar Logótipo da Marca (PNG/JPG)", type=["png", "jpg", "jpeg"]
    )
    if logo_file_painel is not None:
      logo_bytes = logo_file_painel.read()
      st.session_state.logo_img = io.BytesIO(logo_bytes)
      conn = sqlite3.connect("banco_precifica.db")
      cursor = conn.cursor()
      cursor.execute(
          "UPDATE usuarios SET logo = ? WHERE username = ?",
          (logo_bytes, st.session_state.username),
      )
      conn.commit()
      conn.close()
      st.success("Logótipo atualizado com sucesso!")
      st.rerun()
    if st.button("✖️ Fechar Definições"):
      st.session_state.exibir_painel_cliente = False
      st.rerun()
  st.markdown("---")

# ==========================================
# LÓGICA DAS ABAS DO SISTEMA
# ==========================================
if st.session_state.autenticado:
  current_user = st.session_state.username


  def salvar_tabela(nome_tabela):
    conn = sqlite3.connect("banco_precifica.db")
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM {nome_tabela} WHERE username = ?", (current_user,)
    )

    if nome_tabela == "ingredientes":
      for _, r in st.session_state.ingredientes.iterrows():
        p = float(r["Preço pago no produto (R$)"])
        q = float(r["Qtd na Embalagem"])
        unidade_val = str(r["Unidade"])
        custo_u = p / q if q > 0 else 0.0
        cursor.execute(
            "INSERT INTO ingredientes VALUES (?, ?, ?, ?, ?, ?)",
            (current_user, r["Ingrediente"], unidade_val, p, q, custo_u),
        )
    elif nome_tabela == "instrumentos":
      for _, r in st.session_state.instrumentos.iterrows():
        cursor.execute(
            "INSERT INTO instrumentos VALUES (?, ?, ?)",
            (current_user, r["Item / Utensílio"], r["Valor Investido (R$)"]),
        )
    elif nome_tabela == "kits":
      for _, r in st.session_state.kits.iterrows():
        itens_json = (
            json.dumps(r["Itens Inclusos"])
            if isinstance(r["Itens Inclusos"], list)
            else json.dumps([])
        )
        cursor.execute(
            "INSERT INTO kits VALUES (?, ?, ?, ?, ?, ?)",
            (
                current_user,
                r["Produto Final"],
                r["Preço de Custo"],
                r["Preço sugerido"],
                r["Lucro"],
                itens_json,
            ),
        )
    elif nome_tabela == "vendas":
      for _, r in st.session_state.vendas.iterrows():
        cursor.execute(
            "INSERT INTO vendas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                current_user,
                r["Data"],
                r["Produto"],
                int(r["Quantidade"]),
                r["Preço unitário"],
                r["Faturamento"],
                r["Custo unitário"],
                r["Custo total"],
                r["Lucro bruto"],
                r["Forma de pagamento"],
                r["Observações"],
            ),
        )
    conn.commit()
    conn.close()


  # 1. DASHBOARD
  with tab1:
    st.subheader(f"📊 Painel de Desempenho")
    total_investido_inst = (
        st.session_state.instrumentos["Valor Investido (R$)"].sum()
        if not st.session_state.instrumentos.empty
        else 0
    )
    total_ingredientes_cad = len(st.session_state.ingredientes)
    total_receitas_cad = len(st.session_state.receitas)
    faturamento_total = (
        st.session_state.vendas["Faturamento"].sum()
        if not st.session_state.vendas.empty
        else 0
    )
    lucro_total_vendas = (
        st.session_state.vendas["Lucro bruto"].sum()
        if not st.session_state.vendas.empty
        else 0
    )
    total_vendas_realizadas = (
        st.session_state.vendas["Quantidade"].sum()
        if not st.session_state.vendas.empty
        else 0
    )

    col1, col2 = st.columns(2)
    col1.metric("💰 Faturamento", f"R$ {faturamento_total:.2f}")
    col2.metric("📈 Lucro Bruto", f"R$ {lucro_total_vendas:.2f}")

    col3, col4 = st.columns(2)
    col3.metric("🛠️ Utensílios", f"R$ {total_investido_inst:.2f}")
    col4.metric("📦 Vendidos", int(total_vendas_realizadas))

    st.markdown("---")
    if st.button("🔒 Encerrar Sessão (Logout)"):
      st.session_state.autenticado = False
      st.session_state.username = ""
      st.session_state.logo_img = None
      st.rerun()

  # 2. INSTRUMENTOS
  with tab2:
    st.subheader("🛠️ Utensílios")
    with st.form("form_instrumento"):
      nome_inst = st.text_input("Nome do Equipamento")
      valor_inst = st.number_input(
          "Valor Investido (R$)", min_value=0.0, format="%.2f"
      )
      btn_inst = st.form_submit_button("Adicionar")
      if btn_inst and nome_inst:
        novo_i = {
            "Item / Utensílio": nome_inst,
            "Valor Investido (R$)": valor_inst,
        }
        st.session_state.instrumentos = pd.concat(
            [st.session_state.instrumentos, pd.DataFrame([novo_i])],
            ignore_index=True,
        )
        salvar_tabela("instrumentos")
        st.success("Guardado com sucesso!")

    if not st.session_state.instrumentos.empty:
      st.dataframe(
          st.session_state.instrumentos.style.format(
              {"Valor Investido (R$)": "R$ {:.2f}"}
          ),
          use_container_width=True,
      )

  # 3. INGREDIENTES
  with tab3:
    st.subheader("🛒 Ingredientes")
    with st.form("form_ingrediente"):
      nome_ing = st.text_input("Nome do Ingrediente")
      un_medida = st.selectbox("Unidade", ["g", "ml", "un"])
      preco_emb_str = st.text_input("Preço da embalagem (R$)", value="0.00")
      qtd_emb_str = st.text_input("Qtd na embalagem", value="100")
      btn_cad_ing = st.form_submit_button("Guardar Ingrediente")

      if btn_cad_ing and nome_ing:
        try:
          preco_emb = float(
              preco_emb_str.strip().replace(".", "").replace(",", ".")
          )
          qtd_emb = float(
              qtd_emb_str.strip().replace(".", "").replace(",", ".")
          )
        except ValueError:
          preco_emb, qtd_emb = 0.0, 0.0

        if preco_emb > 0 and qtd_emb > 0:
          custo_unit = preco_emb / qtd_emb
          novo_ing = {
              "Ingrediente": nome_ing,
              "Unidade": un_medida,
              "Preço pago no produto (R$)": preco_emb,
              "Qtd na Embalagem": qtd_emb,
              "Custo Unitário (R$)": custo_unit,
          }
          df_ing = st.session_state.ingredientes.dropna(subset=["Ingrediente"])
          st.session_state.ingredientes = pd.concat(
              [df_ing, pd.DataFrame([novo_ing])], ignore_index=True
          )
          salvar_tabela("ingredientes")
          st.success("Registo efetuado!")

    if not st.session_state.ingredientes.empty:
      df_editado = st.data_editor(
          st.session_state.ingredientes.dropna(subset=["Ingrediente"]),
          num_rows="dynamic",
          key="editor_ingredientes",
          use_container_width=True,
      )
      if not df_editado.equals(st.session_state.ingredientes):
        st.session_state.ingredientes = df_editado
        for idx, row in st.session_state.ingredientes.iterrows():
          p = float(row["Preço pago no produto (R$)"])
          q = float(row["Qtd na Embalagem"])
          if q > 0:
            st.session_state.ingredientes.loc[idx, "Custo Unitário (R$)"] = (
                p / q
            )
        salvar_tabela("ingredientes")
        st.rerun()

  # 4. FICHAS TÉCNICAS
  with tab4:
    st.subheader("📋 Fichas Técnicas")
    if st.session_state.ingredientes.empty:
      st.warning("⚠️ Cadastre ingredientes primeiro.")
    else:
      if "temp_df_itens" not in st.session_state:
        st.session_state.temp_df_itens = pd.DataFrame(
            columns=["Ingrediente", "Quantidade"]
        )

      lista_receitas_nomes = (
          st.session_state.receitas["Receita"].tolist()
          if not st.session_state.receitas.empty
          else []
      )
      opcao_receita = st.selectbox(
          "Selecionar Receita", ["➕ [Criar Nova]"] + lista_receitas_nomes
      )

      if opcao_receita == "➕ [Criar Nova]":
        nome_nova_rec = st.text_input("Nome da Receita")
        rendimento_novo = st.number_input(
            "Rendimento (unidades)", min_value=1, value=10, step=1
        )
        df_itens_editavel = st.data_editor(
            st.session_state.temp_df_itens,
            num_rows="dynamic",
            key="editor_nova_receita",
            use_container_width=True,
            column_config={
                "Ingrediente": st.column_config.SelectboxColumn(
                    "Ingrediente",
                    options=st.session_state.ingredientes[
                        "Ingrediente"
                    ].tolist(),
                ),
            },
        )
        if st.button("💾 Guardar Receita"):
          if nome_nova_rec.strip():
            itens_salvar = (
                df_itens_editavel.dropna(subset=["Ingrediente"]).to_dict(
                    orient="records"
                )
                if not df_itens_editavel.empty
                else []
            )
            conn = sqlite3.connect("banco_precifica.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO receitas VALUES (?, ?, ?, ?, ?)",
                (current_user, nome_nova_rec, int(rendimento_novo), json.dumps(itens_salvar), 0.0),
            )
            conn.commit()
            conn.close()
            carregar_dados_usuario(current_user)
            st.success("Receita guardada!")
            st.rerun()

  # 5. PRECIFICAÇÃO
  with tab5:
    st.subheader("💰 Precificação")
    if st.session_state.receitas.empty:
      st.warning("Sem receitas cadastradas.")
    else:
      dados_precificacao = []
      for _, row in st.session_state.receitas.iterrows():
        nome_r = row["Receita"]
        rend = row["Rendimento"]
        c_ing = float(row["Custo Ingredientes"])
        if nome_r not in st.session_state.margens_receitas:
          st.session_state.margens_receitas[nome_r] = {
              "Mão de obra": 0.0,
              "Embalagem": 0.95,
              "Outros custos": 0.25,
              "Margem": 50.0,
          }
        m = st.session_state.margens_receitas[nome_r]
        custo_tot = c_ing + m["Mão de obra"] + m["Embalagem"] + m["Outros custos"]
        custo_un = custo_tot / rend if rend > 0 else 0
        preco_sug = custo_un * (1 + (m["Margem"] / 100))
        dados_precificacao.append({
            "Receita": nome_r,
            "Custo total": custo_tot,
            "Preço sugerido": preco_sug,
        })
      st.dataframe(pd.DataFrame(dados_precificacao), use_container_width=True)

  # 6. COMBOS / CAIXAS
  with tab6:
    st.subheader("📦 Caixas e Combos")
    if st.session_state.receitas.empty:
      st.warning("Cadastre receitas primeiro.")
    else:
      opcoes_produtos = st.session_state.receitas["Receita"].tolist()
      if "combo_lista_itens" not in st.session_state:
        st.session_state.combo_lista_itens = []

      with st.form("form_novo_combo"):
        nome_combo = st.text_input("Nome da Caixa / Combo")
        if st.form_submit_button("➕ Adicionar Item"):
          st.session_state.combo_lista_itens.append(opcoes_produtos[0])
          st.rerun()

        itens_para_salvar = []
        for idx, item_atual in enumerate(
            st.session_state.combo_lista_itens[:]
        ):
          escolha = st.selectbox(
              f"Item {idx+1}",
              opcoes_produtos,
              key=f"combo_p_{idx}",
          )
          itens_para_salvar.append(
              {"Produto Unitário": escolha, "Quantidade": 1, "Custo Unitário": 0}
          )

        custo_emb_caixa = st.number_input(
            "Custo da Embalagem Física (R$)", min_value=0.0
        )
        margem_combo = st.number_input("Margem de Lucro (%)", value=50.0)

        if st.form_submit_button("💾 Guardar Combo"):
          if nome_combo.strip():
            p_sug = (custo_emb_caixa + 10) * (1 + (margem_combo / 100))
            conn = sqlite3.connect("banco_precifica.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO kits VALUES (?, ?, ?, ?, ?, ?)",
                (
                    current_user,
                    nome_combo,
                    10.0,
                    p_sug,
                    p_sug - 10.0,
                    json.dumps(itens_para_salvar),
                ),
            )
            conn.commit()
            conn.close()
            st.session_state.combo_lista_itens = []
            carregar_dados_usuario(current_user)
            st.success("Combo criado!")
            st.rerun()

  # 7. VENDAS (MOBILE OTIMIZADO)
  with tab7:
    st.subheader("📈 Registo de Vendas")
    if st.session_state.kits.empty:
      st.warning("Registe pelo menos um Combo na aba anterior.")
    else:
      combos_disponiveis = st.session_state.kits["Produto Final"].tolist()
      precos_combos_dict = {
          k["Produto Final"]: float(k["Preço sugerido"])
          for _, k in st.session_state.kits.iterrows()
      }
      custos_combos_dict = {
          k["Produto Final"]: float(k["Preço de Custo"])
          for _, k in st.session_state.kits.iterrows()
      }

      with st.form("form_venda"):
        data_hoje_str = datetime.today().strftime("%d/%m/%Y")
        data_venda_str = st.text_input(
            "Data (DD/MM/AAAA)", value=data_hoje_str
        )
        prod_venda = st.selectbox("Produto", combos_disponiveis)
        qtd_venda = st.number_input("Quantidade", min_value=1, value=1, step=1)
        preco_unit_venda = st.number_input(
            "Preço Praticado (R$)",
            min_value=0.0,
            value=precos_combos_dict.get(prod_venda, 0.0),
            format="%.2f",
        )
        forma_pag = st.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro"])
        obs_venda = st.text_input("Observações (Opcional)")

        if st.form_submit_button("Registar Venda"):
          custo_unit_ref = custos_combos_dict.get(prod_venda, 0.0)
          faturamento = preco_unit_venda * qtd_venda
          custo_total = custo_unit_ref * qtd_venda

          nova_venda = {
              "Data": data_venda_str,
              "Produto": prod_venda,
              "Quantidade": int(qtd_venda),
              "Preço unitário": float(preco_unit_venda),
              "Faturamento": float(faturamento),
              "Custo unitário": float(custo_unit_ref),
              "Custo total": float(custo_total),
              "Lucro bruto": float(faturamento - custo_total),
              "Forma de pagamento": forma_pag,
              "Observações": obs_venda,
          }
          st.session_state.vendas = pd.concat(
              [st.session_state.vendas, pd.DataFrame([nova_venda])],
              ignore_index=True,
          )
          salvar_tabela("vendas")
          st.success("Venda registada!")

    if not st.session_state.vendas.empty:
      st.dataframe(st.session_state.vendas, use_container_width=True)
      if "confirmar_limpeza_vendas" not in st.session_state:
        st.session_state.confirmar_limpeza_vendas = False

      if not st.session_state.confirmar_limpeza_vendas:
        if st.button("🗑️ Limpar Vendas"):
          st.session_state.confirmar_limpeza_vendas = True
          st.rerun()
      else:
        st.warning("Deseja mesmo apagar todo o histórico?")
        if st.button("✅ Sim, apagar"):
          st.session_state.vendas = pd.DataFrame(columns=[
              "Data",
              "Produto",
              "Quantidade",
              "Preço unitário",
              "Faturamento",
              "Custo unitário",
              "Custo total",
              "Lucro bruto",
              "Forma de pagamento",
              "Observações",
          ])
          conn = sqlite3.connect("banco_precifica.db")
          cursor = conn.cursor()
          cursor.execute(
              "DELETE FROM vendas WHERE username = ?", (current_user,)
          )
          conn.commit()
          conn.close()
          st.session_state.confirmar_limpeza_vendas = False
          st.success("Histórico limpo!")
          st.rerun()
        if st.button("❌ Cancelar"):
          st.session_state.confirmar_limpeza_vendas = False
          st.rerun()
