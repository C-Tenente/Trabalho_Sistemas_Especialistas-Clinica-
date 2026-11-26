"""
regras_clinica.py
-----------------
Expande a base de conhecimento da clínica para 25 regras integradas ao
MotorInferencia, cobrindo triagem, cadastro, agendamento, profissionais,
histórico médico e exceções/explicações.
"""

from motor import Regra, MotorInferencia, resolver_conflito
from base_conhecimento import (
    REGRAS as REGRAS_TRIAGEM_BASE,
    PRIORIDADES as PRIORIDADES_TRIAGEM,
    RECOMENDACOES as RECOMENDACOES_TRIAGEM,
    ROTULOS as ROTULOS_TRIAGEM,
    rotulo as rotulo_base,
)
from triagem import preparar_regras as preparar_regras_triagem

REGRAS_MODULOS_COMPLEMENTARES = [
    # Cadastro de pacientes (RN01, RN03, RN04)
    Regra(
        id="RN01",
        descricao="Cadastro incompleto por ausência de dados obrigatórios (nome, CPF, nascimento ou telefone)",
        premissas=("dados_obrigatorios_ausentes",),
        conclusao="cadastro_incompleto",
    ),
    Regra(
        id="RN03",
        descricao="Paciente menor de 18 anos sem responsável legal cadastrado torna o cadastro incompleto",
        premissas=("paciente_menor_18", "sem_responsavel_legal"),
        conclusao="cadastro_incompleto",
    ),
    Regra(
        id="RN04",
        descricao="Bloquear agendamento quando o paciente possui cadastro incompleto",
        premissas=("cadastro_incompleto", "tentativa_agendamento"),
        conclusao="rec_bloquear_agendamento",
    ),

    # Agendamento de consultas (RN30, RN06, RN07, RN08)
    Regra(
        id="RN30",
        descricao="Impedir agendamento em data anterior à data atual",
        premissas=("data_consulta_passada",),
        conclusao="rec_bloquear_agendamento",
    ),
    Regra(
        id="RN06",
        descricao="Bloquear agendamento se o profissional não tiver disponibilidade no horário",
        premissas=("profissional_indisponivel_horario",),
        ausentes=("data_consulta_passada",),
        conclusao="rec_bloquear_agendamento",
    ),
    Regra(
        id="RN07",
        descricao="Impedir duas consultas do mesmo profissional no mesmo horário",
        premissas=("conflito_horario_profissional",),
        ausentes=("data_consulta_passada",),
        conclusao="rec_bloquear_agendamento",
    ),
    Regra(
        id="RN08",
        descricao="Impedir duas consultas simultâneas para o mesmo paciente",
        premissas=("conflito_horario_paciente",),
        ausentes=("data_consulta_passada",),
        conclusao="rec_bloquear_agendamento",
    ),

    # Gestão de profissionais (RN20, RN21, RN24)
    Regra(
        id="RN20",
        descricao="Profissional deve possuir ao menos uma especialidade cadastrada",
        premissas=("profissional_sem_especialidade",),
        conclusao="rec_cadastro_profissional_invalido",
    ),
    Regra(
        id="RN21",
        descricao="Encaminhamento viável quando há especialidade compatível e profissional disponível",
        premissas=("especialidade_compativel", "profissional_disponivel"),
        conclusao="encaminhamento_viavel",
    ),
    Regra(
        id="RN24",
        descricao="Informar indisponibilidade e sugerir alternativa quando não há profissional disponível na especialidade",
        premissas=("sem_profissional_disponivel_especialidade",),
        conclusao="rec_sugerir_alternativa",
    ),

    # Histórico médico (RN28, RN26)
    Regra(
        id="RN28",
        descricao="Restringir acesso a informações médicas a usuários autorizados",
        premissas=("tentativa_acesso_historico", "usuario_nao_autorizado"),
        conclusao="rec_acesso_negado",
    ),
    Regra(
        id="RN26",
        descricao="Considerar alergias previamente informadas durante a análise do atendimento",
        premissas=("usuario_autorizado", "alergia_cadastrada", "analise_atendimento"),
        conclusao="rec_alerta_alergia",
    ),

    # Exceções e explicações (RN31, RN33)
    Regra(
        id="RN31",
        descricao="Rejeitar entradas inválidas com mensagem explicativa",
        premissas=("entrada_invalida",),
        conclusao="rec_entrada_invalida",
    ),
    Regra(
        id="RN33",
        descricao="Toda recomendação deve contar com explicação baseada nas regras ativadas",
        premissas=("recomendacao_gerada",),
        conclusao="explicacao_disponivel",
    ),
]


def obter_todas_regras():
    """Retorna as 25 regras (11 da triagem + 14 dos demais módulos/exceções)."""
    regras_triagem = preparar_regras_triagem()
    # Garante que RN14 continue respeitando a base original caso REGRAS_TRIAGEM_BASE seja usado direto
    ids_triagem = {r.id for r in regras_triagem}
    extras = [r for r in REGRAS_MODULOS_COMPLEMENTARES if r.id not in ids_triagem]
    return regras_triagem + extras


PRIORIDADES_CLINICA = {
    **PRIORIDADES_TRIAGEM,
    "rec_acesso_negado": 95,
    "rec_entrada_invalida": 90,
    "rec_bloquear_agendamento": 85,
    "rec_cadastro_profissional_invalido": 85,
    "rec_alerta_alergia": 75,
    "rec_sugerir_alternativa": 52,
}

RECOMENDACOES_CLINICA = {
    **RECOMENDACOES_TRIAGEM,
    "rec_acesso_negado": (
        "ACESSO NEGADO: informações médicas são restritas a usuários autorizados."
    ),
    "rec_entrada_invalida": (
        "ENTRADA INVÁLIDA: os dados informados não atendem ao formato ou regra esperada."
    ),
    "rec_bloquear_agendamento": (
        "AGENDAMENTO BLOQUEADO: verifique pendências de cadastro, data válida, "
        "disponibilidade do profissional ou conflito de horário."
    ),
    "rec_cadastro_profissional_invalido": (
        "CADASTRO DE PROFISSIONAL INVÁLIDO: é obrigatório informar ao menos uma especialidade."
    ),
    "rec_alerta_alergia": (
        "ALERTA DE ALERGIA: o paciente possui alergia registrada; considere-a na conduta/prescrição."
    ),
    "rec_sugerir_alternativa": (
        "SEM DISPONIBILIDADE NA ESPECIALIDADE: informe a indisponibilidade e apresente alternativa adequada."
    ),
}

ROTULOS_CLINICA = {
    **ROTULOS_TRIAGEM,
    "dados_obrigatorios_ausentes": "dados obrigatórios do paciente estão ausentes",
    "paciente_menor_18": "paciente é menor de 18 anos",
    "sem_responsavel_legal": "não há responsável legal cadastrado",
    "cadastro_incompleto": "cadastro do paciente está incompleto",
    "tentativa_agendamento": "há tentativa de agendamento de consulta",
    "data_consulta_passada": "data da consulta está no passado",
    "profissional_indisponivel_horario": "profissional sem disponibilidade no horário solicitado",
    "conflito_horario_profissional": "profissional já possui consulta no mesmo horário",
    "conflito_horario_paciente": "paciente já possui consulta no mesmo horário",
    "especialidade_compativel": "especialidade é compatível com a necessidade",
    "profissional_disponivel": "profissional está disponível",
    "encaminhamento_viavel": "encaminhamento ao profissional é viável",
    "sem_profissional_disponivel_especialidade": "não há profissional disponível na especialidade solicitada",
    "profissional_sem_especialidade": "profissional não possui especialidade cadastrada",
    "tentativa_acesso_historico": "há tentativa de acesso ao histórico médico",
    "usuario_nao_autorizado": "usuário não possui autorização para acessar o histórico",
    "usuario_autorizado": "usuário está autorizado",
    "alergia_cadastrada": "paciente possui alergia cadastrada",
    "analise_atendimento": "análise de atendimento em andamento",
    "entrada_invalida": "entrada inválida fornecida pelo usuário",
    "recomendacao_gerada": "recomendação gerada pelo sistema especialista",
    "explicacao_disponivel": "justificativa baseada nas regras ativadas disponível",
    "rec_bloquear_agendamento": "bloqueio de agendamento",
    "rec_cadastro_profissional_invalido": "alerta de cadastro de profissional inválido",
    "rec_sugerir_alternativa": "sugestão de alternativa por indisponibilidade",
    "rec_acesso_negado": "bloqueio por acesso não autorizado",
    "rec_alerta_alergia": "alerta de alergia registrada",
    "rec_entrada_invalida": "rejeição de entrada inválida",
}


def rotulo_clinica(fato):
    return ROTULOS_CLINICA.get(fato, rotulo_base(fato))


def avaliar_fatos_clinicos(fatos_iniciais):
    """Roda as 25 regras no MotorInferencia e resolve conflitos com PRIORIDADES_CLINICA."""
    regras = obter_todas_regras()
    motor = MotorInferencia(regras)
    resultado = motor.inferir(fatos_iniciais)
    principal, complementares = resolver_conflito(resultado, PRIORIDADES_CLINICA)
    return resultado, principal, complementares