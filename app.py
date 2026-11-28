"""
app.py
------
Interface web (Flask) refinada para o protótipo de Sistema Especialista da Clínica.
Reutiliza motor.py, base_conhecimento.py, explicacao.py, triagem.py,
regras_clinica.py e historico_medico.py.

Execução:
    python app.py
"""

from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session

from base_conhecimento import PERGUNTAS, RECOMENDACOES as REC_TRIAGEM, rotulo
from triagem import analisar_respostas
from explicacao import explicar_como, explicar_por_que
from regras_clinica import (
    obter_todas_regras,
    avaliar_fatos_clinicos,
    RECOMENDACOES_CLINICA,
    ROTULOS_CLINICA,
    rotulo_clinica,
)
import historico_medico as hm

app = Flask(__name__)
app.secret_key = "chave-didatica-clinica-sistemas-especialistas"

# ==============================================================================
# CONFIGURAÇÕES DE LOGIN PROVISÓRIO (DEMONSTRAÇÃO)

EMAIL_PROVISORIO = "atendimento@clinica-exemplo.com.br"
SENHA_PROVISORIA = "clinica123"
PERFIL_PROVISORIO = "profissional"
# ==============================================================================

# ==============================================================================
# CONFIGURAÇÕES VISUAIS (EDITE AQUI CORES, NOMES E TEXTOS DA PÁGINA)

NOME_CLINICA = "Clínica Exemplo [Placeholder]"
SUBTITULO_CLINICA = "Prototipo de Sistema Especialista • Triagem, Regras e Histórico"
TEXTO_AVISO_DIDATICO = (
    "Aviso didático: este sistema é um protótipo acadêmico de apoio a encaminhamento "
    "e regras de negócio. Não realiza diagnósticos médicos nem substitui avaliação "
    "profissional. Em emergências, procure atendimento emergencial imediatamente."
)

COR_PRIMARIA = "#163a5f"        # Cor principal (header, botões, títulos)
COR_PRIMARIA_HOVER = "#1e4e7e"  # Cor ao passar o mouse em botões
COR_FUNDO = "#f4f6f9"           # Cor de fundo da página
COR_CARD = "#ffffff"            # Cor de fundo dos blocos/cards
COR_BORDA = "#dce3ec"           # Cor das bordas
COR_TEXTO = "#1f2d3d"           # Cor principal do texto
COR_DESTAQUE_BG = "#eef6ff"     # Fundo do card de conclusão principal
COR_AVISO_BG = "#fff8e6"        # Fundo do aviso didático
COR_AVISO_BORDA = "#d97706"     # Borda do aviso didático
# ==============================================================================

def _usuario_logado():
    return session.get("usuario_sistema")


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        if email == EMAIL_PROVISORIO.lower() and senha == SENHA_PROVISORIA:
            session["usuario_sistema"] = {
                "email": EMAIL_PROVISORIO,
                "nome": "Equipe Clínica (Provisório)",
                "perfil": PERFIL_PROVISORIO,
            }
            return redirect(url_for("home"))

        hm.preparar_banco()
        with hm.conectar() as con:
            reg = con.execute(
                "SELECT nome_usuario, salt, senha_hash, perfil FROM usuarios WHERE nome_usuario = ?",
                (email,)
            ).fetchone()
        if reg and hm.conferir_senha(senha, reg[1], reg[2]):
            session["usuario_sistema"] = {
                "email": f"{reg[0]}@clinica.local",
                "nome": reg[0],
                "perfil": reg[3],
            }
            return redirect(url_for("home"))

        erro = "E-mail ou senha inválidos. Confira as credenciais provisórias abaixo."

    alerta_erro_html = f"<div class='alerta-erro'>{erro}</div>" if erro else ""

    corpo_login = f"""
    <div class="caixa" style="max-width: 480px; margin: 24px auto;">
      <h2 style="margin-top:0;">Acesso ao Sistema</h2>
      <p>Entre com seu e-mail e senha para acessar os módulos da clínica.</p>
      {alerta_erro_html}
      <form method="post">
        <div class="campo">
          <label for="campo-email">E-mail</label>
          <input id="campo-email" type="text" name="email" placeholder="{EMAIL_PROVISORIO}" required>
        </div>
        <div class="campo">
          <label for="campo-senha">Senha</label>
          <input id="campo-senha" type="password" name="senha" placeholder="Digite sua senha" required>
        </div>
        <div style="margin-top: 14px;">
          <button type="submit" style="width: 100%; max-width: 460px;">Entrar</button>
        </div>
      </form>
      <div class="destaque" style="margin-top: 16px; font-size: 0.88rem;">
        <strong>Aviso — Credenciais provisórias de demonstração:</strong><br>
        E-mail: <code>{EMAIL_PROVISORIO}</code><br>
        Senha: <code>{SENHA_PROVISORIA}</code><br>
        <small>Substitua essas credenciais antes de qualquer uso real fora do ambiente de testes.</small>
      </div>
    </div>
    """

    return renderizar_pagina(corpo_login, ocultar_menu=True)
    return render_template_string(
        HTML_BASE,
        nome_clinica=NOME_CLINICA,
        subtitulo_clinica=SUBTITULO_CLINICA,
        texto_aviso_didatico=TEXTO_AVISO_DIDATICO,
        conteudo=corpo_login,
        ocultar_menu=True,
        mostrar_voltar_home=False,
    )


@app.route("/logout")
def logout():
    session.pop("usuario_sistema", None)
    return redirect(url_for("login"))

CENARIOS_RAPIDOS = {
    "emergencia_peito": {
        "titulo": "Emergência: Dor no peito (RN12)",
        "fatos": ["dor_no_peito"],
    },
    "multiplos_alertas": {
        "titulo": "Múltiplos sinais de alerta: Desmaio + Confusão (RN18 / RN18B)",
        "fatos": ["desmaio", "confusao_mental"],
    },
    "agendamento_passado": {
        "titulo": "Agendamento em data passada (RN30)",
        "fatos": ["tentativa_agendamento", "data_consulta_passada"],
    },
    "cadastro_incompleto_ag": {
        "titulo": "Cadastro incompleto bloqueando agendamento (RN01 / RN04)",
        "fatos": ["dados_obrigatorios_ausentes", "tentativa_agendamento"],
    },
    "acesso_negado_hist": {
        "titulo": "Acesso negado ao histórico médico (RN28)",
        "fatos": ["tentativa_acesso_historico", "usuario_nao_autorizado"],
    },
    "entrada_invalida": {
        "titulo": "Rejeição de entrada inválida (RN31)",
        "fatos": ["entrada_invalida"],
    },
}

HTML_BASE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ nome_clinica }} — Sistema Especialista</title>
  <style>
    :root {
      --cor-primaria: {{ cor_primaria }};
      --cor-primaria-hover: {{ cor_primaria_hover }};
      --cor-fundo: {{ cor_fundo }};
      --cor-card: {{ cor_card }};
      --cor-borda: {{ cor_borda }};
      --cor-texto: {{ cor_texto }};
      --cor-destaque-bg: {{ cor_destaque_bg }};
      --cor-aviso-bg: {{ cor_aviso_bg }};
      --cor-aviso-borda: {{ cor_aviso_borda }};
    }

    * {
      box-sizing: border-box;
    }

    body {
      font-family: "Segoe UI", Arial, sans-serif;
      margin: 0;
      color: var(--cor-texto);
      background: var(--cor-fundo);
      line-height: 1.5;
    }

    /* --- HEADER DA CLÍNICA --- */
    header.topo-clinica {
      background: var(--cor-primaria);
      color: #ffffff;
      padding: 14px 22px;
      display: grid;
      grid-template-columns: 44px 1fr 44px;
      align-items: center;
      gap: 12px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    }

    header.topo-clinica .espaco-esquerda {
      position: relative;
      z-index: 110;
      display: flex;
      align-items: center;
      justify-content: flex-start;
    }

    header.topo-clinica .marca {
      text-align: center;
    }

    header.topo-clinica .marca h1 {
      margin: 0;
      font-size: 1.3rem;
      font-weight: 700;
    }

    header.topo-clinica .marca p {
      margin: 2px 0 0;
      font-size: 0.85rem;
      opacity: 0.9;
    }

    header.topo-clinica .btn-tres-pontinhos {
      position: relative;
      z-index: 111;
      background: rgba(255, 255, 255, 0.22);
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 6px;
      width: 40px;
      height: 40px;
      padding: 0;
      font-size: 1.35rem;
      font-weight: 700;
      line-height: 1;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    header.topo-clinica .btn-tres-pontinhos:hover {
      background: rgba(255, 255, 255, 0.35);
    }

    /* --- BACKDROP E BARRA LATERAL RETRÁTIL --- */
    .backdrop-menu {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.35);
      z-index: 80;
    }

    .backdrop-menu.aberto {
      display: block;
    }

    aside.barra-lateral {
      position: fixed;
      top: 0;
      left: -300px;
      width: 285px;
      height: 100vh;
      background: #ffffff;
      border-right: 1px solid var(--cor-borda);
      box-shadow: 4px 0 16px rgba(0, 0, 0, 0.16);
      padding: 20px 16px;
      z-index: 120;
      transition: left 0.22s ease;
      display: flex;
      flex-direction: column;
      gap: 8px;
      opacity: 1;
    }

    aside.barra-lateral.aberta {
      left: 0;
    }

    .barra-lateral-topo {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 10px;
      margin-bottom: 6px;
      border-bottom: 1px solid var(--cor-borda);
    }

    .barra-lateral-topo strong {
      color: var(--cor-primaria);
      font-size: 1rem;
    }

    .btn-fechar {
      background: transparent;
      color: var(--cor-texto);
      border: 1px solid var(--cor-borda);
      border-radius: 5px;
      padding: 4px 9px;
      cursor: pointer;
      font-size: 0.85rem;
    }

    aside.barra-lateral a {
      text-decoration: none;
      color: var(--cor-texto);
      padding: 10px 12px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.94rem;
      border: 1px solid transparent;
    }

    aside.barra-lateral a:hover {
      background: var(--cor-destaque-bg);
      border-color: var(--cor-borda);
      color: var(--cor-primaria);
    }

    /* --- CONTEÚDO PRINCIPAL, CARDS E MENSAGENS --- */
    main.container {
      max-width: 980px;
      margin: 22px auto 40px;
      padding: 0 18px;
    }

    .aviso {
      background: var(--cor-aviso-bg);
      border-left: 4px solid var(--cor-aviso-borda);
      padding: 12px 16px;
      border-radius: 5px;
      margin-bottom: 18px;
      font-size: 0.92rem;
    }

    .caixa {
      background: var(--cor-card);
      border: 1px solid var(--cor-borda);
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 14px;
    }

    a.card-link {
      display: block;
      text-decoration: none;
      color: var(--cor-texto);
      background: var(--cor-card);
      border: 1px solid var(--cor-borda);
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 14px;
      transition: transform 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease;
    }

    a.card-link:hover {
      border-color: var(--cor-primaria);
      box-shadow: 0 4px 12px rgba(22, 58, 95, 0.08);
      transform: translateY(-1px);
    }

    a.card-link h3 {
      margin: 0 0 6px;
      color: var(--cor-primaria);
    }

    a.card-link p {
      margin: 0;
      color: var(--cor-texto);
    }

    .destaque {
      background: var(--cor-destaque-bg);
      border-left: 4px solid var(--cor-primaria);
      padding: 12px 15px;
      border-radius: 5px;
      margin: 10px 0;
    }

    .alerta-erro {
      background: #fef2f2;
      border-left: 4px solid #dc2626;
      padding: 11px 15px;
      border-radius: 5px;
      margin: 10px 0;
      color: #7f1d1d;
    }

    .sucesso {
      background: #ecfdf5;
      border-left: 4px solid #059669;
      padding: 11px 15px;
      border-radius: 5px;
      margin: 10px 0;
      color: #064e3b;
    }

    .opcoes label {
      margin-right: 16px;
      cursor: pointer;
      display: inline-block;
      margin-top: 4px;
    }

    .porque {
      color: #52606d;
      font-size: 0.88rem;
      margin: 4px 0 8px;
    }

    pre {
      background: #18222f;
      color: #f0f4f8;
      padding: 12px 14px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 0.88rem;
    }

    /* --- BOTÕES, FORMULÁRIOS E TABELAS --- */
    button, .btn-link {
      background: var(--cor-primaria);
      color: #ffffff;
      border: none;
      padding: 9px 16px;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.92rem;
      font-weight: 600;
      text-decoration: none;
      display: inline-block;
    }

    button:hover, .btn-link:hover {
      background: var(--cor-primaria-hover);
    }

    button.secundario {
      background: #475569;
    }

    button.secundario:hover {
      background: #334155;
    }

    input[type="text"], input[type="password"], select, textarea {
      width: 100%;
      max-width: 460px;
      padding: 8px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 5px;
      margin: 4px 0 12px;
      font-family: inherit;
    }

    .campo {
      margin-bottom: 10px;
    }

    .campo label {
      display: block;
      font-weight: 600;
      font-size: 0.9rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--cor-card);
      font-size: 0.9rem;
    }

    th, td {
      border: 1px solid var(--cor-borda);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }

    th {
      background: #f1f5f9;
      color: var(--cor-primaria);
    }

    .badge {
      display: inline-block;
      background: #e2e8f0;
      color: #1e293b;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.8rem;
      margin: 2px;
      font-weight: 600;
    }
/* Garantia visual do botão dos três pontinhos no header */
    header.topo-clinica {
      background: var(--cor-primaria, #163a5f) !important;
      color: #ffffff !important;
    }

    header.topo-clinica .btn-tres-pontinhos {
      background: #ffffff !important;
      color: #163a5f !important;
      border: 2px solid #ffffff !important;
      opacity: 1 !important;
      visibility: visible !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      width: 40px !important;
      height: 40px !important;
      font-size: 22px !important;
      font-weight: 700 !important;
      line-height: 1 !important;
      padding: 0 !important;
      cursor: pointer !important;
      z-index: 150 !important;
    }
  </style>
</head>
<body>
  <header class="topo-clinica">
    <div class="espaco-esquerda">
      {% if not ocultar_menu %}
      <button type="button" class="btn-tres-pontinhos" onclick="alternarMenu()" aria-label="Abrir menu de navegação" title="Opções">
        &#8942;
      </button>
      {% endif %}
    </div>

    <div class="marca">
      <h1>{{ nome_clinica }}</h1>
      <p>{{ subtitulo_clinica }}</p>
    </div>

    <div class="espaco-direita" aria-hidden="true"></div>
  </header>

  {% if not ocultar_menu %}
  <div id="backdropMenu" class="backdrop-menu" onclick="fecharMenu()"></div>
  <aside id="barraLateral" class="barra-lateral" aria-label="Menu lateral">
    <div class="barra-lateral-topo">
      <strong>Navegação</strong>
      <button type="button" class="btn-fechar" onclick="fecharMenu()">Fechar</button>
    </div>
    <a href="{{ url_for('home') }}" onclick="fecharMenu()">Início (Home)</a>
    <a href="{{ url_for('triagem') }}" onclick="fecharMenu()">1. Triagem Inicial</a>
    <a href="{{ url_for('simulador_regras') }}" onclick="fecharMenu()">2. Simulador de Regras</a>
    <a href="{{ url_for('historico') }}" onclick="fecharMenu()">3. Histórico Médico</a>
    <a href="{{ url_for('base_conhecimento') }}" onclick="fecharMenu()">4. Base de Conhecimento</a>
    <a href="{{ url_for('logout') }}" onclick="fecharMenu()">Sair</a>
  </aside>
  {% endif %}

  <main class="container">
    <div class="aviso">{{ texto_aviso_didatico }}</div>
    {{ conteudo | safe }}
  </main>

  <script>
    function alternarMenu() {
      document.getElementById("barraLateral").classList.toggle("aberta");
      document.getElementById("backdropMenu").classList.toggle("aberto");
    }
    function fecharMenu() {
      document.getElementById("barraLateral").classList.remove("aberta");
      document.getElementById("backdropMenu").classList.remove("aberto");
    }
  </script>
</body>
</html>
"""
def renderizar_pagina(conteudo, ocultar_menu=False):
    return render_template_string(
        HTML_BASE,
        nome_clinica=NOME_CLINICA,
        subtitulo_clinica=SUBTITULO_CLINICA,
        texto_aviso_didatico=TEXTO_AVISO_DIDATICO,
        cor_primaria=COR_PRIMARIA,
        cor_primaria_hover=COR_PRIMARIA_HOVER,
        cor_fundo=COR_FUNDO,
        cor_card=COR_CARD,
        cor_borda=COR_BORDA,
        cor_texto=COR_TEXTO,
        cor_destaque_bg=COR_DESTAQUE_BG,
        cor_aviso_bg=COR_AVISO_BG,
        cor_aviso_borda=COR_AVISO_BORDA,
        ocultar_menu=ocultar_menu,
        conteudo=conteudo,
    )

@app.route("/home")
def home():
    if not _usuario_logado():
        return redirect(url_for("login"))

    user = _usuario_logado()
    conteudo = f"""
    <div class="caixa">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
          <h2 style="margin:0;">Página Inicial — Escolha um Caminho</h2>
          <p style="margin:4px 0 0; color:#52606d;">Sessão ativa: <strong>{user['nome']}</strong> (<code>{user['email']}</code>)</p>
        </div>
        <a class="btn-link" href="{url_for('logout')}">Sair</a>
      </div>
    </div>

    <a class="card-link" href="{url_for('triagem')}">
      <h3>1. Triagem Inicial do Paciente</h3>
      <p>Coleta sintomas e sinais de alerta, diferencia <em>Sim</em>, <em>Não</em>, <em>Não sei</em> e <em>Não responder</em>, e exibe a explicação do raciocínio.</p>
    </a>

    <a class="card-link" href="{url_for('simulador_regras')}">
      <h3>2. Simulador de Regras e Fluxos da Clínica</h3>
      <p>Testa fatos e regras de negócio (triagem, cadastro, agendamento/exames, profissionais, histórico e exceções) no motor de inferência.</p>
    </a>

    <a class="card-link" href="{url_for('historico')}">
      <h3>3. Histórico Médico e Auditoria</h3>
      <p>Gerencia atendimentos, alergias, condições prévias, consulta de histórico e registro de operações na auditoria.</p>
    </a>

    <a class="card-link" href="{url_for('base_conhecimento')}">
      <h3>4. Base de Conhecimento</h3>
      <p>Consulta todas as regras ativas, premissas e conclusões processadas pelo motor de inferência.</p>
    </a>
    """
    return renderizar_pagina(conteudo, ocultar_menu=True)



def _render_bloco_explicacao(resultado, principal, complementares, mapa_recs, fn_rotulo):
    if not principal:
        return """
        <div class="alerta-erro">
          <strong>Sem conclusão definida (RN32 / Exceção):</strong> não foi possível chegar a uma recomendação
          com as informações fornecidas. Encaminhe para avaliação humana ou revise os fatos informados.
        </div>
        """

    rec_principal = mapa_recs.get(principal, principal)
    comp_html = ""
    if complementares:
        itens = "".join(
            f"<li><strong>{c}</strong>: {mapa_recs.get(c, c)}</li>" for c in complementares
        )
        comp_html = f"<div class='caixa'><h4>Recomendações complementares (menor prioridade):</h4><ul>{itens}</ul></div>"

    ativadas_badges = "".join(
        f"<span class='badge'>{r.id}</span>" for r in resultado.ativadas
    ) or "<span class='badge'>Nenhuma</span>"

    caminho_como = "\n".join(explicar_como(resultado, principal, fn_rotulo)) or "Sem cadeia de inferência registrada."
    caminho_porque = "\n".join(explicar_por_que(resultado, principal, fn_rotulo)) or "Sem regra direta registrada."

    return f"""
    <div class="destaque">
      <h3>Conclusão Principal ({principal})</h3>
      <p style="font-size:1.05rem; margin:6px 0;"><strong>{rec_principal}</strong></p>
      <p style="margin:6px 0 0;"><strong>Regras disparadas:</strong> {ativadas_badges}</p>
    </div>
    {comp_html}
    <div class="caixa">
      <h4>Como o sistema chegou à conclusão (encadeamento / RN33):</h4>
      <pre>{caminho_como}</pre>
      <h4>Por que essa conclusão se aplica (regras e fatos diretos):</h4>
      <pre>{caminho_porque}</pre>
    </div>
    """

@app.route("/")
def raiz():
    if not _usuario_logado():
        return redirect(url_for("login"))
    return redirect(url_for("home"))


@app.route("/triagem", methods=["GET", "POST"])
def triagem():
    if not _usuario_logado():
        return redirect(url_for("login"))
    bloco_resultado = ""
    resumo_html = ""

    if request.method == "POST":
        respostas = {}
        nomes_status = {
            "sim": "Sim",
            "nao": "Não",
            "nao_sei": "Não sei",
            "nao_respondido": "Não respondida",
        }
        linhas_resumo = []
        for p in PERGUNTAS:
            fato = p["fato"]
            resp = request.form.get(fato, "nao_respondido")
            if resp not in nomes_status:
                resp = "nao_respondido"
            respostas[fato] = resp
            linhas_resumo.append(f"<li>{p['texto']} — <strong>{nomes_status[resp]}</strong></li>")

        resultado, principal, complementares = analisar_respostas(respostas)
        resumo_html = f"<div class='caixa'><h4>Resumo das respostas coletadas</h4><ul>{''.join(linhas_resumo)}</ul></div>"
        bloco_resultado = _render_bloco_explicacao(
            resultado, principal, complementares, REC_TRIAGEM, rotulo
        )

    cards = []
    for p in PERGUNTAS:
        fato = p["fato"]
        cards.append(f"""
        <div class="caixa">
          <p style="margin:0 0 4px;"><strong>{p["texto"]}</strong></p>
          <p class="porque"><em>Por que perguntamos:</em> {p.get("porque", "")}</p>
          <div class="opcoes">
            <label><input type="radio" name="{fato}" value="sim"> Sim</label>
            <label><input type="radio" name="{fato}" value="nao"> Não</label>
            <label><input type="radio" name="{fato}" value="nao_sei"> Não sei</label>
            <label><input type="radio" name="{fato}" value="nao_respondido" checked> Não responder</label>
          </div>
        </div>
        """)

    conteudo = f"""
    <h2>Triagem Inicial do Paciente</h2>
    <p>Responda às perguntas abaixo. <strong>"Não sei"</strong> e <strong>"Não responder"</strong> são tratados de forma distinta de <strong>"Não"</strong> para evitar conclusões indevidas.</p>
    <form method="post">
      {''.join(cards)}
      <button type="submit">Executar Motor de Inferência</button>
    </form>
    <div style="margin-top:18px;">
      {bloco_resultado}
      {resumo_html}
    </div>
    """
    return render_template_string(
        HTML_BASE,
        nome_clinica=NOME_CLINICA,
        subtitulo_clinica=SUBTITULO_CLINICA,
        texto_aviso_didatico=TEXTO_AVISO_DIDATICO,
        conteudo=conteudo,
    )


@app.route("/regras-modulos", methods=["GET", "POST"])
def simulador_regras():
    fatos_opcoes = [
        k for k in ROTULOS_CLINICA.keys()
        if not k.startswith("rec_") and k != "explicacao_disponivel"
    ]
    selecionados = []
    bloco_resultado = ""

    if request.method == "POST":
        cenario = request.form.get("cenario", "").strip()
        if cenario in CENARIOS_RAPIDOS:
            selecionados = list(CENARIOS_RAPIDOS[cenario]["fatos"])
        else:
            selecionados = request.form.getlist("fatos")

        resultado, principal, complementares = avaliar_fatos_clinicos(selecionados)
        bloco_resultado = _render_bloco_explicacao(
            resultado, principal, complementares, RECOMENDACOES_CLINICA, rotulo_clinica
        )

    botoes_cenarios = "".join(
        f'<button type="submit" name="cenario" value="{chave}" class="secundario" style="margin:4px;">{dados["titulo"]}</button>'
        for chave, dados in CENARIOS_RAPIDOS.items()
    )

    selecionados_set = set(selecionados)
    checkboxes = "".join(
        f'<label style="display:block; margin:4px 0;"><input type="checkbox" name="fatos" value="{f}" '
        f'{"checked" if f in selecionados_set else ""}> <code>{f}</code> — {rotulo_clinica(f)}</label>'
        for f in fatos_opcoes
    )

    conteudo = f"""
    <h2>Simulador de Regras dos Módulos e Exceções (25 Regras)</h2>
    <div class="caixa">
      <h4 style="margin-top:0;">Cenários rápidos para teste e demonstração</h4>
      <form method="post">{botoes_cenarios}</form>
    </div>
    <form method="post">
      <div class="caixa">
        <h4 style="margin-top:0;">Ou escolha manualmente os fatos iniciais</h4>
        {checkboxes}
      </div>
      <button type="submit">Avaliar Fatos Selecionados</button>
    </form>
    <div style="margin-top:18px;">{bloco_resultado}</div>
    """
    return render_template_string(
        HTML_BASE,
        nome_clinica=NOME_CLINICA,
        subtitulo_clinica=SUBTITULO_CLINICA,
        texto_aviso_didatico=TEXTO_AVISO_DIDATICO,
        conteudo=conteudo,
    )


@app.route("/historico", methods=["GET", "POST"])
def historico():
    hm.preparar_banco()
    mensagem = ""
    erro = ""
    consulta_dados = None
    auditoria_dados = None

    if request.method == "POST":
        acao = request.form.get("acao", "")

        if acao == "login":
            usuario = request.form.get("usuario", "").strip()
            senha = request.form.get("senha", "")
            with hm.conectar() as con:
                reg = con.execute(
                    "SELECT nome_usuario, salt, senha_hash, perfil FROM usuarios WHERE nome_usuario = ?",
                    (usuario,)
                ).fetchone()
            if reg and hm.conferir_senha(senha, reg[1], reg[2]):
                session["usuario_hm"] = {"nome": reg[0], "perfil": reg[3]}
                mensagem = f"Sessão iniciada como {reg[0]} ({reg[3]})."
            else:
                erro = "RN31 / Autenticação: usuário ou senha inválidos."

        elif acao == "logout":
            session.pop("usuario_hm", None)
            mensagem = "Sessão encerrada."

        elif not session.get("usuario_hm"):
            erro = "RN28: acesso negado. Faça login com usuário autorizado para manipular o histórico médico."

        else:
            user = session["usuario_hm"]
            if acao == "registrar_atendimento":
                pac_id = request.form.get("paciente_id", "").strip()
                pac_nome = request.form.get("paciente_nome", "").strip()
                data_at = request.form.get("data_atendimento", "").strip()
                prof = request.form.get("profissional", "").strip()
                desc = request.form.get("descricao", "").strip()

                try:
                    datetime.strptime(data_at, "%d/%m/%Y")
                except ValueError:
                    erro = "RN31: data inválida. Utilize o formato DD/MM/AAAA."
                else:
                    if not pac_id or not prof or not desc:
                        erro = "RN31: informe identificador do paciente, profissional e resumo do atendimento."
                    else:
                        with hm.conectar() as con:
                            existe = hm.paciente_existe(con, pac_id)
                            if not existe:
                                if not pac_nome:
                                    erro = "RN01 / RN31: paciente não encontrado; informe o nome completo para cadastrar."
                                else:
                                    con.execute(
                                        "INSERT INTO pacientes (id, nome) VALUES (?, ?)",
                                        (pac_id, pac_nome)
                                    )
                            if not erro:
                                alergias = con.execute(
                                    "SELECT descricao FROM alergias WHERE paciente_id = ?",
                                    (pac_id,)
                                ).fetchall()
                                con.execute(
                                    """INSERT INTO atendimentos (paciente_id, data, descricao, profissional)
                                       VALUES (?, ?, ?, ?)""",
                                    (pac_id, data_at, desc, prof)
                                )
                                hm.registrar_operacao(
                                    con, user["nome"], "REGISTRO DE ATENDIMENTO (WEB)",
                                    pac_id, f"Atendimento em {data_at} com {prof}."
                                )
                                alerta_str = (
                                    " | RN26 ALERTA DE ALERGIA: " + ", ".join(a[0] for a in alergias)
                                    if alergias else " | Nenhuma alergia cadastrada."
                                )
                                mensagem = f"Atendimento registrado para o paciente '{pac_id}'{alerta_str}"

            elif acao == "cadastrar_alergia":
                pac_id = request.form.get("paciente_id_alergia", "").strip()
                alergia_desc = request.form.get("alergia_desc", "").strip()
                if not pac_id or not alergia_desc:
                    erro = "RN31: informe o código do paciente e a descrição da alergia."
                else:
                    with hm.conectar() as con:
                        if not hm.paciente_existe(con, pac_id):
                            erro = "RN31: paciente não cadastrado no histórico. Registre o paciente primeiro."
                        else:
                            con.execute(
                                "INSERT INTO alergias (paciente_id, descricao) VALUES (?, ?)",
                                (pac_id, alergia_desc)
                            )
                            hm.registrar_operacao(
                                con, user["nome"], "CADASTRO DE ALERGIA (WEB)",
                                pac_id, alergia_desc
                            )
                            mensagem = f"Alergia '{alergia_desc}' registrada para '{pac_id}'."

            elif acao == "consultar":
                pac_id = request.form.get("paciente_id_consulta", "").strip()
                with hm.conectar() as con:
                    pac = hm.paciente_existe(con, pac_id)
                    if not pac:
                        erro = "Paciente não encontrado."
                    else:
                        atend = con.execute(
                            """SELECT id, data, descricao, profissional
                               FROM atendimentos WHERE paciente_id = ? ORDER BY id DESC""",
                            (pac_id,)
                        ).fetchall()
                        alerg = con.execute(
                            "SELECT id, descricao FROM alergias WHERE paciente_id = ?",
                            (pac_id,)
                        ).fetchall()
                        cond = con.execute(
                            "SELECT id, descricao FROM condicoes WHERE paciente_id = ?",
                            (pac_id,)
                        ).fetchall()
                        hm.registrar_operacao(
                            con, user["nome"], "CONSULTA DE HISTORICO (WEB)",
                            pac_id, "Histórico consultado via web."
                        )
                        consulta_dados = {
                            "id": pac_id,
                            "nome": pac[0],
                            "atendimentos": atend,
                            "alergias": alerg,
                            "condicoes": cond,
                        }

            elif acao == "auditoria":
                if user["perfil"] != "administrador":
                    erro = "RN28: somente usuários com perfil 'administrador' podem consultar a auditoria."
                else:
                    with hm.conectar() as con:
                        auditoria_dados = con.execute(
                            """SELECT data_hora, usuario, operacao, paciente_id, detalhes
                               FROM auditoria ORDER BY id DESC LIMIT 30"""
                        ).fetchall()

    user_atual = session.get("usuario_hm")
    if not user_atual:
        sessao_html = """
        <div class="caixa">
          <h3>Login do Módulo de Histórico Médico (RN28)</h3>
          <p>Conta inicial de demonstração: <code>admin</code> / <code>admin123</code></p>
          <form method="post">
            <input type="hidden" name="acao" value="login">
            <div class="campo"><label>Usuário</label><input type="text" name="usuario" required></div>
            <div class="campo"><label>Senha</label><input type="password" name="senha" required></div>
            <button type="submit">Entrar</button>
          </form>
        </div>
        """
    else:
        sessao_html = f"""
        <div class="caixa">
          <strong>Usuário autenticado:</strong> {user_atual['nome']} (perfil: <code>{user_atual['perfil']}</code>)
          <form method="post" style="display:inline; margin-left:12px;">
            <input type="hidden" name="acao" value="logout">
            <button type="submit" class="secundario">Sair</button>
          </form>
          <form method="post" style="display:inline; margin-left:8px;">
            <input type="hidden" name="acao" value="auditoria">
            <button type="submit">Ver Auditoria (RN29)</button>
          </form>
        </div>

        <div class="caixa">
          <h3>Registrar Atendimento e Verificar Alergias (RN25 / RN26)</h3>
          <form method="post">
            <input type="hidden" name="acao" value="registrar_atendimento">
            <div class="campo"><label>Código do Paciente</label><input type="text" name="paciente_id" placeholder="Ex.: PAC01" required></div>
            <div class="campo"><label>Nome Completo (se novo)</label><input type="text" name="paciente_nome" placeholder="Ex.: Maria Silva"></div>
            <div class="campo"><label>Data (DD/MM/AAAA)</label><input type="text" name="data_atendimento" placeholder="Ex.: 26/11/2026" required></div>
            <div class="campo"><label>Profissional</label><input type="text" name="profissional" placeholder="Ex.: Dr. João" required></div>
            <div class="campo"><label>Resumo do Atendimento</label><textarea name="descricao" rows="2" required></textarea></div>
            <button type="submit">Salvar Atendimento</button>
          </form>
        </div>

        <div class="caixa">
          <h3>Cadastrar Alergia do Paciente (RN26)</h3>
          <form method="post">
            <input type="hidden" name="acao" value="cadastrar_alergia">
            <div class="campo"><label>Código do Paciente</label><input type="text" name="paciente_id_alergia" placeholder="Ex.: PAC01" required></div>
            <div class="campo"><label>Descrição da Alergia</label><input type="text" name="alergia_desc" placeholder="Ex.: Dipirona" required></div>
            <button type="submit">Salvar Alergia</button>
          </form>
        </div>

        <div class="caixa">
          <h3>Consultar Histórico do Paciente (RN27)</h3>
          <form method="post">
            <input type="hidden" name="acao" value="consultar">
            <div class="campo"><label>Código do Paciente</label><input type="text" name="paciente_id_consulta" placeholder="Ex.: PAC01" required></div>
            <button type="submit">Consultar</button>
          </form>
        </div>
        """

    detalhe_consulta_html = ""
    if consulta_dados:
        at_itens = "".join(
            f"<li><strong>{a[1]}</strong> — {a[3]}: {a[2]}</li>" for a in consulta_dados["atendimentos"]
        ) or "<li>Nenhum atendimento registrado.</li>"
        al_itens = "".join(f"<li>{al[1]}</li>" for al in consulta_dados["alergias"]) or "<li>Nenhuma alergia cadastrada.</li>"
        co_itens = "".join(f"<li>{co[1]}</li>" for co in consulta_dados["condicoes"]) or "<li>Nenhuma condição cadastrada.</li>"
        detalhe_consulta_html = f"""
        <div class="caixa">
          <h3>Histórico de {consulta_dados['nome']} ({consulta_dados['id']})</h3>
          <h4>Atendimentos</h4><ul>{at_itens}</ul>
          <h4>Alergias</h4><ul>{al_itens}</ul>
          <h4>Condições prévias</h4><ul>{co_itens}</ul>
        </div>
        """

    detalhe_auditoria_html = ""
    if auditoria_dados is not None:
        linhas_aud = "".join(
            f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3] or '-'}</td><td>{r[4]}</td></tr>"
            for r in auditoria_dados
        ) or "<tr><td colspan='5'>Sem registros de auditoria.</td></tr>"
        detalhe_auditoria_html = f"""
        <div class="caixa">
          <h3>Auditoria de Operações (RN29)</h3>
          <table>
            <thead><tr><th>Data/Hora</th><th>Usuário</th><th>Operação</th><th>Paciente</th><th>Detalhes</th></tr></thead>
            <tbody>{linhas_aud}</tbody>
          </table>
        </div>
        """

    msg_html = f"<div class='sucesso'>{mensagem}</div>" if mensagem else ""
    err_html = f"<div class='alerta-erro'>{erro}</div>" if erro else ""

    conteudo = f"""
    <h2>Histórico Médico e Auditoria</h2>
    {msg_html}
    {err_html}
    {sessao_html}
    {detalhe_consulta_html}
    {detalhe_auditoria_html}
    """
    return render_template_string(
        HTML_BASE,
        nome_clinica=NOME_CLINICA,
        subtitulo_clinica=SUBTITULO_CLINICA,
        texto_aviso_didatico=TEXTO_AVISO_DIDATICO,
        conteudo=conteudo,
    )


@app.route("/base")
def base_conhecimento():
    regras = obter_todas_regras()
    linhas = "".join(
        f"<tr><td><strong>{r.id}</strong></td><td>{r.descricao}</td>"
        f"<td><code>{', '.join(r.premissas) or '-'}</code></td>"
        f"<td><code>{r.conclusao}</code></td></tr>"
        for r in regras
    )
    conteudo = f"""
    <h2>Base de Conhecimento ({len(regras)} Regras Ativas)</h2>
    <p>Todas as regras abaixo são avaliadas pelo <code>MotorInferencia</code> com encadeamento para frente.</p>
    <table>
      <thead>
        <tr><th>ID</th><th>Descrição</th><th>Premissas Diretas</th><th>Conclusão / Fato</th></tr>
      </thead>
      <tbody>{linhas}</tbody>
    </table>
    """
    return render_template_string(
        HTML_BASE,
        nome_clinica=NOME_CLINICA,
        subtitulo_clinica=SUBTITULO_CLINICA,
        texto_aviso_didatico=TEXTO_AVISO_DIDATICO,
        conteudo=conteudo,
    )


if __name__ == "__main__":
    app.run(debug=True)