"""
explicacao.py
-------------
Módulo de EXPLICAÇÃO do sistema especialista (RN33).

Responde a duas perguntas clássicas:
    - POR QUÊ?  -> quais regras e fatos sustentam esta conclusão.
    - COMO?     -> o caminho completo do raciocínio, dos fatos informados
                   até a conclusão (incluindo conclusões intermediárias).
"""


def explicar_por_que(resultado, fato, rotulo):
    """Lista as regras que concluíram `fato` e os fatos que as sustentaram."""
    linhas = []
    for regra, usados in resultado.origem.get(fato, []):
        motivos = "; ".join(rotulo(u) for u in usados)
        linhas.append(f"Regra {regra.id}: {regra.descricao}. Fatos considerados: {motivos}.")
    return linhas


def explicar_como(resultado, fato, rotulo, nivel=0, vistos=None):
    """
    Monta o caminho do raciocínio até `fato`, de forma recursiva.
    Fatos derivados são explicados pelas regras que os produziram; fatos
    informados pelo paciente aparecem como "fato informado".
    """
    vistos = set() if vistos is None else vistos
    recuo = "   " * nivel
    linhas = []
    for regra, usados in resultado.origem.get(fato, []):
        linhas.append(f"{recuo}[{regra.id}] {rotulo(fato)}  <-  {regra.descricao}")
        for u in usados:
            if u in resultado.origem and u not in vistos:
                vistos.add(u)
                linhas += explicar_como(resultado, u, rotulo, nivel + 1, vistos)
            else:
                linhas.append(f"{recuo}   - fato informado: {rotulo(u)}")
    return linhas
