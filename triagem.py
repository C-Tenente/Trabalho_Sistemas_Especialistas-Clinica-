"""
Triagem da clinica

Este arquivo complementa a base_conhecimento.py que ja existe no projeto.
Ele aproveita o motor de inferencia e o modulo de explicacao do grupo.

Para executar:
    python triagem.py

Para rodar os testes automaticos:
    python triagem.py --testes

Deixe este arquivo na mesma pasta de:
    motor.py
    base_conhecimento.py
    explicacao.py

As regras sao exemplos didaticos de encaminhamento. O programa nao faz
diagnostico e nao substitui a avaliacao de um profissional de saude.
"""

import sys
import unittest
from dataclasses import replace

from motor import Regra, MotorInferencia, resolver_conflito
from base_conhecimento import (
    REGRAS,
    PERGUNTAS,
    SINAIS_ALERTA,
    DESCONHECIDOS,
    PRIORIDADES,
    RECOMENDACOES,
    rotulo,
)
from explicacao import explicar_como


# Se a pessoa nao souber responder ou pular uma pergunta de alerta,
# o sistema registra isso como informacao diferente de "nao".
NAO_RESPONDIDOS = tuple(
    f"nao_respondido_{sinal}" for sinal in SINAIS_ALERTA
)


def preparar_regras():
    """
    Ajusta a RN14 para que ela nao considere segura uma situacao em que
    algum sinal de alerta ficou sem resposta. Acrescenta a RN19B para
    tratar perguntas de alerta que foram puladas.
    """
    regras = []

    for regra in REGRAS:
        if regra.id == "RN14":
            regra = replace(
                regra,
                ausentes=regra.ausentes + NAO_RESPONDIDOS
            )
        regras.append(regra)

    regras.append(
        Regra(
            id="RN19B",
            descricao=(
                "Um sinal de alerta ficou sem resposta; solicitar "
                "avaliacao da equipe da clinica"
            ),
            pelo_menos=(1, NAO_RESPONDIDOS),
            conclusao="rec_avaliacao_humana",
        )
    )

    return regras


REGRAS_TRIAGEM = preparar_regras()


def montar_fatos(respostas):
    """
    Converte as respostas em fatos para o motor de inferencia.

    SIM: adiciona o fato positivo.
    NAO: nao adiciona o fato positivo.
    NAO_SEI: registra desconhecido, se for sinal de alerta.
    NAO_RESPONDIDO: registra pergunta pulada, se for sinal de alerta.

    As duas ultimas situacoes nunca sao tratadas como uma resposta NAO.
    """
    fatos = set()

    for fato, resposta in respostas.items():
        if resposta == "sim":
            fatos.add(fato)

        elif resposta == "nao_sei" and fato in SINAIS_ALERTA:
            fatos.add(f"desconhecido_{fato}")

        elif resposta == "nao_respondido" and fato in SINAIS_ALERTA:
            fatos.add(f"nao_respondido_{fato}")

    return fatos


def analisar_respostas(respostas):
    """Executa o encadeamento para frente e retorna o resultado."""
    fatos = montar_fatos(respostas)
    motor = MotorInferencia(REGRAS_TRIAGEM)
    resultado = motor.inferir(fatos)
    principal, complementares = resolver_conflito(resultado, PRIORIDADES)

    return resultado, principal, complementares


def pedir_resposta(pergunta):
    """Mostra uma pergunta e aceita quatro situacoes diferentes."""
    while True:
        print(f"\n{pergunta['texto']}")
        print("1 - Sim")
        print("2 - Nao")
        print("3 - Nao sei")
        print("4 - Prefiro nao responder / pular")
        print("P - Por que essa pergunta?")

        resposta = input("Resposta: ").strip().lower()

        if resposta == "p":
            print(pergunta.get("porque", "A pergunta ajuda na triagem."))
            continue

        opcoes = {
            "1": "sim",
            "2": "nao",
            "3": "nao_sei",
            "4": "nao_respondido",
        }

        if resposta in opcoes:
            return opcoes[resposta]

        print("Opcao invalida. Escolha 1, 2, 3 ou 4.")


def mostrar_resumo_respostas(respostas):
    nomes = {
        "sim": "Sim",
        "nao": "Nao",
        "nao_sei": "Nao sei",
        "nao_respondido": "Nao respondida",
    }

    print("\n========== RESUMO DAS RESPOSTAS ==========")
    for pergunta in PERGUNTAS:
        fato = pergunta["fato"]
        status = respostas.get(fato, "nao_respondido")
        print(f"- {pergunta['texto']} {nomes[status]}")


def mostrar_resultado(resultado, principal, complementares):
    print("\n========== RESULTADO DA TRIAGEM ==========")

    if principal is None:
        print(
            "Nao foi possivel chegar a uma recomendacao com as respostas "
            "informadas. Encaminhe o caso para avaliacao da equipe da clinica."
        )
        print("Nenhuma regra de recomendacao foi ativada.")
        return

    print(RECOMENDACOES.get(principal, principal))

    if complementares:
        print("\nOutras orientacoes identificadas:")
        for recomendacao in complementares:
            texto = RECOMENDACOES.get(recomendacao, recomendacao)
            print(f"- {texto}")

    print("\n========== COMO O SISTEMA CHEGOU A ISSO ==========")
    caminho = explicar_como(resultado, principal, rotulo)

    if caminho:
        for linha in caminho:
            print(linha)
    else:
        print("A recomendacao foi obtida a partir das regras ativadas.")

    print("\nRegras ativadas:")
    if resultado.ativadas:
        for regra in resultado.ativadas:
            print(f"- {regra.id}: {regra.descricao}")
    else:
        print("- Nenhuma regra foi ativada.")


def executar_triagem():
    print("=" * 54)
    print("SISTEMA DA CLINICA - TRIAGEM INICIAL")
    print("=" * 54)
    print(
        "Responda as perguntas com as opcoes apresentadas. "
        "Nao sei e pular sao respostas diferentes de Nao."
    )
    print(
        "\nATENCAO: esta ferramenta e apenas um prototipo didatico. "
        "Nao realiza diagnosticos."
    )
    print(
        "Se houver dor no peito, dificuldade intensa para respirar ou "
        "outro sinal grave, procure atendimento de emergencia imediatamente."
    )

    respostas = {}
    for pergunta in PERGUNTAS:
        respostas[pergunta["fato"]] = pedir_resposta(pergunta)

    mostrar_resumo_respostas(respostas)
    resultado, principal, complementares = analisar_respostas(respostas)
    mostrar_resultado(resultado, principal, complementares)


# ------------------------- TESTES AUTOMATICOS -------------------------

class TestesTriagem(unittest.TestCase):

    def testar_dor_no_peito_gera_emergencia(self):
        respostas = {"dor_no_peito": "sim"}
        _, principal, _ = analisar_respostas(respostas)
        self.assertEqual(principal, "rec_emergencia")

    def testar_nao_sei_nao_e_tratado_como_nao(self):
        respostas = {
            "febre": "sim",
            "sintoma_leve": "sim",
            "dor_no_peito": "nao_sei",
        }
        resultado, principal, _ = analisar_respostas(respostas)
        self.assertEqual(principal, "rec_avaliacao_humana")
        self.assertNotIn("rec_avaliacao_clinica", resultado.fatos)

    def testar_pergunta_pulada_pede_avaliacao_humana(self):
        respostas = {
            "febre": "sim",
            "sintoma_leve": "sim",
            "dor_no_peito": "nao_respondido",
        }
        resultado, principal, _ = analisar_respostas(respostas)
        self.assertEqual(principal, "rec_avaliacao_humana")
        self.assertNotIn("rec_avaliacao_clinica", resultado.fatos)

    def testar_febre_leve_sem_alertas(self):
        respostas = {
            "dor_no_peito": "nao",
            "dificuldade_respirar_intensa": "nao",
            "desmaio": "nao",
            "confusao_mental": "nao",
            "febre": "sim",
            "febre_alta": "nao",
            "sintoma_leve": "sim",
        }
        _, principal, _ = analisar_respostas(respostas)
        self.assertEqual(principal, "rec_avaliacao_clinica")

    def testar_dois_sinais_de_alerta_ativam_prioridade(self):
        respostas = {
            "dor_no_peito": "nao",
            "dificuldade_respirar_intensa": "nao",
            "desmaio": "sim",
            "confusao_mental": "sim",
            "febre_alta": "nao",
        }
        resultado, _, _ = analisar_respostas(respostas)
        self.assertIn("multiplos_sinais_alerta", resultado.fatos)
        self.assertIn("rec_prioridade_alta", resultado.fatos)


def rodar_testes():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestesTriagem)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    return resultado.wasSuccessful()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--testes":
        sucesso = rodar_testes()
        sys.exit(0 if sucesso else 1)
    executar_triagem()
