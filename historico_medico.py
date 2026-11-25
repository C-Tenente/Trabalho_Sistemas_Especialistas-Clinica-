"""
Historico medico - modulo da clinica

Regras de negocio relacionadas:
RN25 - registrar os atendimentos realizados;
RN26 - mostrar alergias informadas para que sejam consideradas no atendimento;
RN27 - permitir a consulta dos atendimentos anteriores;
RN28 - restringir o acesso a usuarios autorizados;
RN29 - guardar o registro das alteracoes feitas no historico.

Para executar: python historico_medico.py

O arquivo historico_medico.db sera criado automaticamente na mesma pasta.
Primeiro acesso: admin / admin123. Crie outro administrador e troque a senha
de demonstracao antes de usar o sistema fora da apresentacao.
Use somente dados ficticios na demonstracao.
"""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime

BANCO = "historico_medico.db"
PERFIS_VALIDOS = ("profissional", "administrador")


# ------------------------- BANCO DE DADOS -------------------------

def conectar():
    conexao = sqlite3.connect(BANCO)
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def gerar_hash(senha, salt=None):
    """Gera um hash com salt individual para cada senha."""
    if salt is None:
        salt = os.urandom(16)
    resultado = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, 200_000
    )
    return salt.hex(), resultado.hex()


def conferir_senha(senha, salt_hex, hash_salvo):
    salt = bytes.fromhex(salt_hex)
    _, hash_digitado = gerar_hash(senha, salt)
    return hmac.compare_digest(hash_digitado, hash_salvo)


def preparar_banco():
    with conectar() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_usuario TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL
                    CHECK (perfil IN ('profissional', 'administrador'))
            );

            CREATE TABLE IF NOT EXISTS pacientes (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS atendimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id TEXT NOT NULL,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                profissional TEXT NOT NULL,
                FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
            );

            CREATE TABLE IF NOT EXISTS alergias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
            );

            CREATE TABLE IF NOT EXISTS condicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
            );

            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                operacao TEXT NOT NULL,
                paciente_id TEXT,
                detalhes TEXT NOT NULL,
                data_hora TEXT NOT NULL
            );
        """)

        # Conta inicial para facilitar a primeira execucao em sala.
        existe = con.execute(
            "SELECT id FROM usuarios WHERE nome_usuario = 'admin'"
        ).fetchone()

        if not existe:
            salt, senha_hash = gerar_hash("admin123")
            con.execute(
                """INSERT INTO usuarios
                   (nome_usuario, salt, senha_hash, perfil)
                   VALUES (?, ?, ?, ?)""",
                ("admin", salt, senha_hash, "administrador")
            )


def registrar_operacao(con, usuario, operacao, paciente_id, detalhes):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    con.execute(
        """INSERT INTO auditoria
           (usuario, operacao, paciente_id, detalhes, data_hora)
           VALUES (?, ?, ?, ?, ?)""",
        (usuario, operacao, paciente_id, detalhes, agora)
    )


# ------------------------- ACESSO AO SISTEMA -------------------------

def fazer_login():
    print("\n========== ACESSO AO SISTEMA ==========")
    nome = input("Usuario: ").strip()
    senha = input("Senha: ")

    with conectar() as con:
        registro = con.execute(
            """SELECT nome_usuario, salt, senha_hash, perfil
               FROM usuarios WHERE nome_usuario = ?""",
            (nome,)
        ).fetchone()

    if registro and conferir_senha(senha, registro[1], registro[2]):
        print(f"\nBem-vindo(a), {registro[0]}!")
        return {"nome": registro[0], "perfil": registro[3]}

    print("Usuario ou senha incorretos.")
    return None


def cadastrar_usuario(usuario_logado):
    if usuario_logado["perfil"] != "administrador":
        print("Somente o administrador pode cadastrar usuarios.")
        return

    nome = input("Nome de usuario: ").strip()
    senha = input("Senha (minimo de 6 caracteres): ")
    perfil = input("Perfil (profissional/administrador): ").strip().lower()

    if not nome or len(senha) < 6 or perfil not in PERFIS_VALIDOS:
        print("Dados invalidos. Confira o nome, a senha e o perfil.")
        return

    salt, senha_hash = gerar_hash(senha)

    try:
        with conectar() as con:
            con.execute(
                """INSERT INTO usuarios
                   (nome_usuario, salt, senha_hash, perfil)
                   VALUES (?, ?, ?, ?)""",
                (nome, salt, senha_hash, perfil)
            )
            registrar_operacao(
                con, usuario_logado["nome"], "CADASTRO DE USUARIO",
                None, f"Usuario '{nome}' cadastrado com perfil '{perfil}'."
            )
        print("Usuario cadastrado.")
    except sqlite3.IntegrityError:
        print("Ja existe um usuario com esse nome.")


# ------------------------- PACIENTES -------------------------

def localizar_ou_cadastrar_paciente():
    paciente_id = input("Codigo/identificador do paciente: ").strip()
    if not paciente_id:
        print("O identificador e obrigatorio.")
        return None

    with conectar() as con:
        paciente = con.execute(
            "SELECT id, nome FROM pacientes WHERE id = ?", (paciente_id,)
        ).fetchone()

    if paciente:
        print(f"Paciente encontrado: {paciente[1]}")
        return paciente_id

    print("Paciente ainda nao consta neste modulo.")
    nome = input("Nome completo: ").strip()
    if not nome:
        print("O nome e obrigatorio.")
        return None

    try:
        with conectar() as con:
            con.execute(
                "INSERT INTO pacientes (id, nome) VALUES (?, ?)",
                (paciente_id, nome)
            )
        print("Paciente cadastrado.")
        return paciente_id
    except sqlite3.IntegrityError:
        print("Nao foi possivel cadastrar o paciente.")
        return None


def paciente_existe(con, paciente_id):
    return con.execute(
        "SELECT nome FROM pacientes WHERE id = ?", (paciente_id,)
    ).fetchone()


# ------------------------- REGISTROS DO HISTORICO -------------------------

def registrar_atendimento(usuario):
    paciente_id = localizar_ou_cadastrar_paciente()
    if not paciente_id:
        return

    data = input("Data do atendimento (DD/MM/AAAA): ").strip()
    try:
        datetime.strptime(data, "%d/%m/%Y")
    except ValueError:
        print("Data invalida. Use o formato DD/MM/AAAA.")
        return

    profissional = input("Nome do profissional: ").strip()
    descricao = input("Resumo do atendimento: ").strip()

    if not profissional or not descricao:
        print("Preencha o profissional e a descricao.")
        return

    with conectar() as con:
        alergias = con.execute(
            "SELECT descricao FROM alergias WHERE paciente_id = ?",
            (paciente_id,)
        ).fetchall()

        con.execute(
            """INSERT INTO atendimentos
               (paciente_id, data, descricao, profissional)
               VALUES (?, ?, ?, ?)""",
            (paciente_id, data, descricao, profissional)
        )
        registrar_operacao(
            con, usuario["nome"], "REGISTRO DE ATENDIMENTO",
            paciente_id, f"Atendimento de {data} registrado."
        )

    print("Atendimento registrado com sucesso.")
    if alergias:
        print("\nATENCAO: existem alergias informadas no cadastro:")
        for alergia in alergias:
            print(f"- {alergia[0]}")
        print("Confira essas informacoes durante o atendimento.")
    else:
        print("Nao ha alergias cadastradas neste modulo.")


def registrar_alergia_ou_condicao(usuario, tipo):
    paciente_id = localizar_ou_cadastrar_paciente()
    if not paciente_id:
        return

    descricao = input("Descricao: ").strip()
    if not descricao:
        print("A descricao nao pode ficar vazia.")
        return

    # O nome da tabela vem de uma lista fixa, nunca da entrada do usuario.
    tabelas = {"alergia": "alergias", "condicao": "condicoes"}
    tabela = tabelas[tipo]

    with conectar() as con:
        con.execute(
            f"INSERT INTO {tabela} (paciente_id, descricao) VALUES (?, ?)",
            (paciente_id, descricao)
        )
        registrar_operacao(
            con, usuario["nome"], f"CADASTRO DE {tipo.upper()}",
            paciente_id, descricao
        )

    print("Informacao registrada.")


# ------------------------- CONSULTA E ALTERACAO -------------------------

def consultar_historico(usuario):
    paciente_id = input("Codigo/identificador do paciente: ").strip()

    with conectar() as con:
        paciente = paciente_existe(con, paciente_id)
        if not paciente:
            print("Paciente nao encontrado.")
            return

        atendimentos = con.execute(
            """SELECT id, data, descricao, profissional
               FROM atendimentos
               WHERE paciente_id = ?
               ORDER BY id DESC""",
            (paciente_id,)
        ).fetchall()

        alergias = con.execute(
            "SELECT id, descricao FROM alergias WHERE paciente_id = ?",
            (paciente_id,)
        ).fetchall()

        condicoes = con.execute(
            "SELECT id, descricao FROM condicoes WHERE paciente_id = ?",
            (paciente_id,)
        ).fetchall()

        registrar_operacao(
            con, usuario["nome"], "CONSULTA DO HISTORICO",
            paciente_id, "Historico consultado."
        )

    print(f"\n========== HISTORICO: {paciente[0].upper()} ==========")

    print("\nATENDIMENTOS")
    if atendimentos:
        for item in atendimentos:
            print(
                f"Codigo: {item[0]} | Data: {item[1]}\n"
                f"Profissional: {item[3]}\nDescricao: {item[2]}\n"
            )
    else:
        print("Nenhum atendimento registrado.")

    print("ALERGIAS INFORMADAS")
    if alergias:
        for item in alergias:
            print(f"Codigo: {item[0]} | {item[1]}")
    else:
        print("Nenhuma alergia foi informada neste modulo.")

    print("\nCONDICOES PREVIAMENTE RELATADAS")
    if condicoes:
        for item in condicoes:
            print(f"Codigo: {item[0]} | {item[1]}")
    else:
        print("Nenhuma condicao foi registrada.")


def alterar_registro(usuario):
    """Altera uma descricao e guarda o valor anterior e o novo na auditoria."""
    paciente_id = input("Codigo/identificador do paciente: ").strip()

    print("\nQual informacao deseja alterar?")
    print("1 - Atendimento")
    print("2 - Alergia")
    print("3 - Condicao")
    escolha = input("Opcao: ").strip()

    configuracoes = {
        "1": ("atendimentos", "descricao", "id"),
        "2": ("alergias", "descricao", "id"),
        "3": ("condicoes", "descricao", "id")
    }
    if escolha not in configuracoes:
        print("Opcao invalida.")
        return

    tabela, campo, chave = configuracoes[escolha]
    try:
        registro_id = int(input("Codigo do registro: ").strip())
    except ValueError:
        print("Digite um codigo numerico.")
        return

    with conectar() as con:
        registro = con.execute(
            f"SELECT {campo} FROM {tabela} WHERE {chave} = ? AND paciente_id = ?",
            (registro_id, paciente_id)
        ).fetchone()

        if not registro:
            print("Registro nao encontrado para esse paciente.")
            return

        descricao_antiga = registro[0]
        print(f"Descricao atual: {descricao_antiga}")
        descricao_nova = input("Nova descricao: ").strip()

        if not descricao_nova:
            print("A nova descricao nao pode ficar vazia.")
            return

        con.execute(
            f"UPDATE {tabela} SET {campo} = ? WHERE {chave} = ?",
            (descricao_nova, registro_id)
        )
        registrar_operacao(
            con, usuario["nome"], "ALTERACAO DE HISTORICO",
            paciente_id,
            f"Tabela: {tabela}; registro: {registro_id}; "
            f"anterior: '{descricao_antiga}'; novo: '{descricao_nova}'."
        )

    print("Alteracao realizada e registrada na auditoria.")


def consultar_auditoria(usuario):
    if usuario["perfil"] != "administrador":
        print("Somente o administrador pode consultar a auditoria.")
        return

    with conectar() as con:
        registros = con.execute(
            """SELECT data_hora, usuario, operacao, paciente_id, detalhes
               FROM auditoria ORDER BY id DESC"""
        ).fetchall()

    print("\n========== REGISTRO DE OPERACOES ==========")
    if not registros:
        print("Ainda nao ha operacoes registradas.")
        return

    for data, autor, operacao, paciente_id, detalhes in registros:
        print(
            f"\n{data} | Usuario: {autor} | {operacao}\n"
            f"Paciente: {paciente_id or '-'} | {detalhes}"
        )


# ------------------------- MENU PRINCIPAL -------------------------

def mostrar_menu():
    print("""
========== HISTORICO MEDICO ==========
1 - Registrar atendimento
2 - Cadastrar alergia
3 - Cadastrar condicao previamente relatada
4 - Consultar historico de um paciente
5 - Alterar uma informacao do historico
6 - Cadastrar usuario
7 - Consultar registro de operacoes
0 - Sair
""")


def executar():
    preparar_banco()
    print("Sistema da Clinica - Modulo de Historico Medico")
    print("Primeiro acesso: usuario admin | senha admin123")

    usuario = fazer_login()
    if not usuario:
        return

    while True:
        mostrar_menu()
        opcao = input("Escolha uma opcao: ").strip()

        if opcao == "1":
            registrar_atendimento(usuario)
        elif opcao == "2":
            registrar_alergia_ou_condicao(usuario, "alergia")
        elif opcao == "3":
            registrar_alergia_ou_condicao(usuario, "condicao")
        elif opcao == "4":
            consultar_historico(usuario)
        elif opcao == "5":
            alterar_registro(usuario)
        elif opcao == "6":
            cadastrar_usuario(usuario)
        elif opcao == "7":
            consultar_auditoria(usuario)
        elif opcao == "0":
            print("Sistema encerrado.")
            break
        else:
            print("Opcao invalida. Escolha uma opcao do menu.")


if __name__ == "__main__":
    executar()
