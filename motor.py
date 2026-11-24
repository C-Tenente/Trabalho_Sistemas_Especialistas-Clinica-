"""
motor.py
--------
Motor de inferência por ENCADEAMENTO PARA FRENTE (forward chaining).

Ideia central:
    1. Temos um conjunto de FATOS (o que sabemos sobre o paciente).
    2. Temos um conjunto de REGRAS do tipo SE <condições> ENTÃO <conclusão>.
    3. O motor percorre as regras. Quando as condições de uma regra são
       satisfeitas pelos fatos atuais, a regra é "disparada" e a sua conclusão
       vira um NOVO FATO.
    4. Como um fato novo pode satisfazer outras regras, o motor repete o
       processo até que nenhuma regra nova consiga ser disparada.

Durante o processo, o motor guarda de onde veio cada conclusão (qual regra e
quais fatos a sustentaram). Isso é o que permite o módulo de EXPLICAÇÃO.

Observação sobre negação ("ausentes"): as regras só testam a ausência de
fatos informados diretamente pelo paciente (fatos "brutos"). Assim a ordem de
disparo das regras não altera o resultado.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Regra:
    """Uma regra SE-ENTÃO da base de conhecimento."""

    id: str                 # identificador da regra de negócio (ex.: "RN12")
    descricao: str          # descrição curta, usada nas explicações
    conclusao: str          # fato produzido quando a regra dispara
    premissas: tuple = ()   # TODOS estes fatos precisam estar presentes
    ausentes: tuple = ()    # NENHUM destes fatos pode estar presente
    pelo_menos: tuple = ()  # formato (n, (fato1, fato2, ...)): ao menos n presentes

    def aplicavel(self, fatos):
        """Retorna True se as condições da regra são satisfeitas pelos fatos."""
        if not self.premissas and not self.pelo_menos:
            return False  # uma regra precisa de pelo menos uma condição positiva
        if not all(p in fatos for p in self.premissas):
            return False
        if any(a in fatos for a in self.ausentes):
            return False
        if self.pelo_menos:
            n, lista = self.pelo_menos
            if sum(1 for f in lista if f in fatos) < n:
                return False
        return True

    def fatos_usados(self, fatos):
        """Lista os fatos presentes que sustentaram o disparo da regra."""
        usados = list(self.premissas)
        if self.pelo_menos:
            _, lista = self.pelo_menos
            usados += [f for f in lista if f in fatos and f not in usados]
        return usados


@dataclass
class Resultado:
    """Tudo o que o motor descobriu em uma execução."""

    fatos_iniciais: frozenset  # fatos informados pelo paciente
    fatos: set                 # fatos iniciais + fatos derivados
    origem: dict               # fato derivado -> lista de (regra, fatos_usados)
    ativadas: list             # regras disparadas, na ordem em que dispararam


class MotorInferencia:
    """Executa o encadeamento para frente sobre uma lista de regras."""

    def __init__(self, regras):
        self.regras = list(regras)
        ids = [r.id for r in self.regras]
        if len(ids) != len(set(ids)):
            raise ValueError("Existem regras com ID repetido na base de conhecimento.")

    def inferir(self, fatos_iniciais):
        fatos = set(fatos_iniciais)
        origem = {}
        ativadas = []
        ids_ativados = set()

        houve_mudanca = True
        while houve_mudanca:
            houve_mudanca = False
            for regra in self.regras:
                if regra.id in ids_ativados:
                    continue  # cada regra dispara no máximo uma vez
                if regra.aplicavel(fatos):
                    ids_ativados.add(regra.id)
                    ativadas.append(regra)
                    origem.setdefault(regra.conclusao, []).append(
                        (regra, regra.fatos_usados(fatos))
                    )
                    fatos.add(regra.conclusao)
                    houve_mudanca = True

        return Resultado(frozenset(fatos_iniciais), fatos, origem, ativadas)


def resolver_conflito(resultado, prioridades):
    """
    RN34 - Quando várias regras produzem recomendações diferentes, escolhe a
    de MAIOR prioridade como principal. As demais ficam como complementares.

    Retorna (recomendacao_principal, lista_de_outras). Se não houver nenhuma
    recomendação, retorna (None, []).
    """
    recomendacoes = [f for f in resultado.fatos if f.startswith("rec_")]
    if not recomendacoes:
        return None, []
    recomendacoes.sort(key=lambda f: (-prioridades.get(f, 0), f))
    return recomendacoes[0], recomendacoes[1:]
