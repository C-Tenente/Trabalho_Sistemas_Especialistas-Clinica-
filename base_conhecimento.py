"""
base_conhecimento.py
--------------------
Base de conhecimento do módulo de TRIAGEM da clínica.

AVISO: as regras abaixo são exemplos didáticos de encaminhamento, e não
protocolos clínicos validados. O sistema não diagnostica doenças.

Convenções de nomes dos fatos:
    - fatos informados pelo paciente: "dor_no_peito", "febre", ...
    - "desconhecido_X": o paciente respondeu "não sei" sobre o sinal de alerta X
    - fatos derivados intermediários: "multiplos_sinais_alerta", ...
    - recomendações finais: começam com "rec_"
"""

from motor import Regra

# ---------------------------------------------------------------------------
# Fatos básicos
# ---------------------------------------------------------------------------

# Sinais de alerta: quando presentes, indicam possível gravidade.
SINAIS_ALERTA = (
    "dor_no_peito",
    "dificuldade_respirar_intensa",
    "desmaio",
    "confusao_mental",
    "febre_alta",
)

# Para cada sinal de alerta, existe o fato "desconhecido_<sinal>", usado
# quando o paciente responde "não sei".
DESCONHECIDOS = tuple(f"desconhecido_{s}" for s in SINAIS_ALERTA)

# ---------------------------------------------------------------------------
# Regras (RN12 a RN19 do documento de regras de negócio)
# ---------------------------------------------------------------------------

REGRAS = [
    # RN19 - informações insuficientes sobre sinais de alerta
    Regra(
        id="RN19",
        descricao="Informação insuficiente sobre um sinal de alerta: solicitar avaliação humana",
        premissas=(),
        pelo_menos=(1, DESCONHECIDOS),
        conclusao="rec_avaliacao_humana",
    ),
    # RN12 - dor no peito
    Regra(
        id="RN12",
        descricao="Dor no peito exige orientação de avaliação emergencial",
        premissas=("dor_no_peito",),
        conclusao="rec_emergencia",
    ),
    # RN13 - dificuldade intensa para respirar
    Regra(
        id="RN13",
        descricao="Dificuldade intensa para respirar exige orientação de atendimento emergencial",
        premissas=("dificuldade_respirar_intensa",),
        conclusao="rec_emergencia",
    ),
    # RN14 - febre com sintomas leves, sem sinais de alerta
    Regra(
        id="RN14",
        descricao="Febre com sintomas leves e sem sinais de alerta: avaliação clínica convencional",
        premissas=("febre", "sintoma_leve"),
        ausentes=SINAIS_ALERTA + DESCONHECIDOS,
        conclusao="rec_avaliacao_clinica",
    ),
    # RN15 - sintomas persistentes
    Regra(
        id="RN15",
        descricao="Sintomas persistentes devem ser avaliados por um profissional",
        premissas=("sintoma_persistente",),
        conclusao="rec_avaliacao_profissional",
    ),
    # RN16 - sintomas cardíacos
    Regra(
        id="RN16",
        descricao="Sintomas relacionados à saúde cardíaca: avaliação médica apropriada",
        premissas=("sintoma_cardiaco",),
        conclusao="rec_cardiologica",
    ),
    # RN17 - sintomas respiratórios
    Regra(
        id="RN17",
        descricao="Sintomas respiratórios: clínico geral ou pneumologista, conforme avaliação profissional",
        premissas=("sintoma_respiratorio",),
        conclusao="rec_respiratoria",
    ),
    # RN18 - múltiplos sinais de alerta (encadeamento em dois passos)
    # Passo 1: dois ou mais sinais de alerta geram o fato intermediário.
    Regra(
        id="RN18",
        descricao="Dois ou mais sinais de alerta caracterizam múltiplos sinais de alerta",
        pelo_menos=(2, SINAIS_ALERTA),
        conclusao="multiplos_sinais_alerta",
    ),
    # Passo 2: o fato intermediário gera a recomendação de prioridade.
    Regra(
        id="RN18B",
        descricao="Múltiplos sinais de alerta recebem prioridade de avaliação",
        premissas=("multiplos_sinais_alerta",),
        conclusao="rec_prioridade_alta",
    ),
]

# ---------------------------------------------------------------------------
# Prioridade das recomendações (usada na resolução de conflitos, RN34)
# Quanto maior o número, mais prioritária é a recomendação.
# ---------------------------------------------------------------------------

PRIORIDADES = {
    "rec_emergencia": 100,
    "rec_prioridade_alta": 80,
    "rec_avaliacao_humana": 70,
    "rec_cardiologica": 60,
    "rec_respiratoria": 55,
    "rec_avaliacao_profissional": 50,
    "rec_avaliacao_clinica": 40,
}

# ---------------------------------------------------------------------------
# Textos exibidos ao usuário
# ---------------------------------------------------------------------------

RECOMENDACOES = {
    "rec_emergencia": (
        "ATENDIMENTO DE EMERGÊNCIA: procure um pronto-socorro ou ligue para o SAMU (192) "
        "agora. Não espere por agendamento de consulta."
    ),
    "rec_prioridade_alta": (
        "PRIORIDADE ALTA: você apresenta mais de um sinal de alerta. Procure avaliação "
        "profissional o mais rápido possível."
    ),
    "rec_avaliacao_humana": (
        "AVALIAÇÃO HUMANA: faltam informações importantes sobre sinais de alerta. "
        "Fale com a equipe de atendimento da clínica para uma avaliação."
    ),
    "rec_cardiologica": (
        "AVALIAÇÃO CARDIOLÓGICA: seus sintomas sugerem avaliação médica da saúde do coração."
    ),
    "rec_respiratoria": (
        "AVALIAÇÃO RESPIRATÓRIA: encaminhamento para clínico geral ou pneumologista, "
        "conforme avaliação profissional."
    ),
    "rec_avaliacao_profissional": (
        "AVALIAÇÃO PROFISSIONAL: sintomas persistentes devem ser avaliados por um profissional de saúde."
    ),
    "rec_avaliacao_clinica": (
        "AVALIAÇÃO CLÍNICA CONVENCIONAL: agende uma consulta com clínico geral. "
        "Se surgir algum sinal de alerta, procure atendimento imediatamente."
    ),
}

# Nomes legíveis dos fatos, usados nas explicações.
ROTULOS = {
    "dor_no_peito": "paciente relata dor no peito",
    "dificuldade_respirar_intensa": "paciente relata dificuldade intensa para respirar",
    "desmaio": "paciente relata desmaio",
    "confusao_mental": "paciente relata confusão mental",
    "febre_alta": "paciente relata febre muito alta",
    "febre": "paciente relata febre",
    "sintoma_leve": "sintomas são leves",
    "sintoma_persistente": "sintomas persistem há mais de 7 dias",
    "sintoma_cardiaco": "paciente relata sintomas cardíacos",
    "sintoma_respiratorio": "paciente relata sintomas respiratórios",
    "multiplos_sinais_alerta": "há múltiplos sinais de alerta",
    "desconhecido_dor_no_peito": "paciente não soube informar se tem dor no peito",
    "desconhecido_dificuldade_respirar_intensa": "paciente não soube informar sobre dificuldade para respirar",
    "desconhecido_desmaio": "paciente não soube informar sobre desmaio",
    "desconhecido_confusao_mental": "paciente não soube informar sobre confusão mental",
    "desconhecido_febre_alta": "paciente não soube informar sobre febre muito alta",
    "rec_emergencia": "orientação de atendimento de emergência",
    "rec_prioridade_alta": "orientação de prioridade alta de avaliação",
    "rec_avaliacao_humana": "orientação de avaliação humana",
    "rec_cardiologica": "orientação de avaliação cardiológica",
    "rec_respiratoria": "orientação de avaliação respiratória",
    "rec_avaliacao_profissional": "orientação de avaliação profissional",
    "rec_avaliacao_clinica": "orientação de avaliação clínica convencional",
}


def rotulo(fato):
    """Devolve o nome legível de um fato (ou o próprio nome, se não houver)."""
    return ROTULOS.get(fato, fato)


# ---------------------------------------------------------------------------
# Perguntas feitas ao paciente (cada resposta "sim" vira um fato)
# O campo "porque" é usado quando o usuário pergunta "por que você pergunta isso?"
# ---------------------------------------------------------------------------

PERGUNTAS = [
    {
        "fato": "dor_no_peito",
        "texto": "Você está sentindo dor no peito?",
        "porque": "Dor no peito é um sinal de alerta. A regra RN12 verifica isso primeiro, "
                  "pois pode exigir atendimento de emergência.",
    },
    {
        "fato": "dificuldade_respirar_intensa",
        "texto": "Você está com muita dificuldade para respirar?",
        "porque": "Dificuldade intensa para respirar é um sinal de alerta (regra RN13) "
                  "e pode exigir atendimento de emergência.",
    },
    {
        "fato": "desmaio",
        "texto": "Você desmaiou ou sentiu que ia desmaiar?",
        "porque": "Desmaio é um sinal de alerta. Ele conta para a regra RN18, que identifica "
                  "múltiplos sinais de alerta.",
    },
    {
        "fato": "confusao_mental",
        "texto": "Você está confuso, desorientado ou com dificuldade para falar?",
        "porque": "Confusão mental é um sinal de alerta e conta para a regra RN18.",
    },
    {
        "fato": "febre",
        "texto": "Você está com febre (qualquer valor)?",
        "porque": "A febre é uma das condições da regra RN14 (febre com sintomas leves).",
    },
    {
        "fato": "febre_alta",
        "texto": "Sua febre é muito alta (39,5 °C ou mais)?",
        "porque": "Febre muito alta é um sinal de alerta e afasta a regra RN14. "
                  "Também conta para a regra RN18.",
    },
    {
        "fato": "sintoma_leve",
        "texto": "Seus sintomas são leves (você consegue fazer suas atividades normalmente)?",
        "porque": "A regra RN14 só se aplica a sintomas leves.",
    },
    {
        "fato": "sintoma_persistente",
        "texto": "Os sintomas duram mais de 7 dias?",
        "porque": "A regra RN15 encaminha sintomas persistentes para avaliação profissional.",
    },
    {
        "fato": "sintoma_cardiaco",
        "texto": "Você tem palpitações, batimentos irregulares ou inchaço nas pernas?",
        "porque": "A regra RN16 relaciona esses sintomas à saúde cardíaca.",
    },
    {
        "fato": "sintoma_respiratorio",
        "texto": "Você tem tosse, chiado ou falta de ar leve?",
        "porque": "A regra RN17 relaciona esses sintomas ao sistema respiratório.",
    },
]
