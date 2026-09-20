"""
Parte 2 — Criptoanálise da Cifra de Vigenère (quebra sem conhecer a senha).

Uso:
    python criptoanalise.py <texto_criptografado.txt> [-o texto_decifrado.txt]
                            [--max-tamanho 20] [--tamanho N] [--amostra N]

Premissa: o texto original está em português.

O ataque acontece em duas etapas:

  Etapa 1 — Descobrir o tamanho da senha (Índice de Coincidência)
      Para cada tamanho candidato L (1..max), o texto cifrado é dividido
      em L subtextos: o subtexto j contém as letras das posições
      j, j+L, j+2L, ...  Todas as letras de um mesmo subtexto foram
      cifradas com a MESMA letra da chave, ou seja, sofreram o mesmo
      deslocamento (uma cifra de César). Um deslocamento de César apenas
      "renomeia" as letras, mas não altera a distribuição de frequências;
      portanto o IC do subtexto continua igual ao do português (~0,072).
      Se L estiver errado, cada subtexto mistura vários deslocamentos e o
      IC cai em direção ao valor de texto aleatório (1/26 ≈ 0,038).

          IC = Σ f_i (f_i - 1) / ( N (N - 1) )

  Etapa 2 — Descobrir cada letra da senha (análise de frequência)
      Com o tamanho L conhecido, para cada subtexto testamos os 26
      deslocamentos possíveis e escolhemos o que deixa as frequências das
      letras mais parecidas com as do português (teste qui-quadrado).
      O deslocamento de cada subtexto é justamente a letra da chave
      naquela posição.

  Por fim o texto é decifrado:  P_i = (C_i - K_i) mod 26.
"""

import argparse
import sys
from collections import Counter

from cifrar import processar_arquivo
from higienizacao import higienizar_arquivo_em_blocos

ORD_A = ord("a")
TAMANHO_ALFABETO = 26

# Frequência relativa (%) das letras no português. Fonte: tabelas clássicas
# de frequência de letras em textos em português (valores aproximados).
FREQUENCIA_PORTUGUES = {
    "a": 14.63, "b": 1.04, "c": 3.88, "d": 4.99, "e": 12.57, "f": 1.02,
    "g": 1.30, "h": 1.28, "i": 6.18, "j": 0.40, "k": 0.02, "l": 2.78,
    "m": 4.74, "n": 5.05, "o": 10.73, "p": 2.52, "q": 1.20, "r": 6.53,
    "s": 7.81, "t": 4.34, "u": 4.63, "v": 1.67, "w": 0.01, "x": 0.21,
    "y": 0.01, "z": 0.47,
}

# Mesma tabela como lista de probabilidades indexada por 0..25 ('a'..'z').
_soma = sum(FREQUENCIA_PORTUGUES.values())
PROB_PORTUGUES = [FREQUENCIA_PORTUGUES[chr(ORD_A + i)] / _soma for i in range(TAMANHO_ALFABETO)]

# IC esperado para português = Σ p_i², e IC de texto uniformemente aleatório = 1/26.
IC_PORTUGUES = sum(p * p for p in PROB_PORTUGUES)     # ≈ 0,072
IC_ALEATORIO = 1.0 / TAMANHO_ALFABETO                  # ≈ 0,038


# ---------------------------------------------------------------------------
# Etapa 1 — Índice de Coincidência e tamanho da chave
# ---------------------------------------------------------------------------

def indice_coincidencia(contagens: Counter, n: int) -> float:
    """
    Calcula IC = Σ f_i (f_i - 1) / (N (N - 1)) a partir das contagens de
    letras `contagens` de um texto com `n` letras.
    """
    if n < 2:
        return 0.0
    return sum(f * (f - 1) for f in contagens.values()) / (n * (n - 1))


def subtextos(texto: str, tamanho: int):
    """
    Divide o texto em `tamanho` subtextos, um por posição da chave.
    texto[j::tamanho] pega as letras das posições j, j+L, j+2L, ...
    """
    return [texto[j::tamanho] for j in range(tamanho)]


def ic_medio(texto: str, tamanho: int) -> float:
    """
    IC médio dos subtextos obtidos ao supor que a chave tem `tamanho` letras.
    """
    ics = [indice_coincidencia(Counter(sub), len(sub)) for sub in subtextos(texto, tamanho)]
    return sum(ics) / len(ics)


def estimar_tamanho_chave(texto: str, max_tamanho: int):
    """
    Testa tamanhos de 1 até `max_tamanho` e devolve (tamanho_escolhido, tabela),
    onde tabela é a lista [(tamanho, ic_medio), ...] para exibição.

    Critério de escolha:
      O tamanho correto L produz IC ≈ IC do português. Porém múltiplos de L
      (2L, 3L, ...) também produzem IC alto, pois cada subtexto continua
      sendo uma cifra de César pura. Para não escolher um múltiplo, pegamos
      o MENOR tamanho cujo IC esteja "próximo do máximo" encontrado.
      Sub-múltiplos e tamanhos errados misturam deslocamentos diferentes e
      ficam bem abaixo desse limiar.
    """
    tabela = [(L, ic_medio(texto, L)) for L in range(1, max_tamanho + 1)]

    ic_maximo = max(ic for _, ic in tabela)
    # Tolerância: 3% da distância entre o IC máximo e o IC de texto aleatório.
    # (Valor calibrado empiricamente; se por ruído um múltiplo de L for
    # escolhido, a função `reduzir_periodo` corrige a chave depois.)
    limiar = ic_maximo - 0.03 * (ic_maximo - IC_ALEATORIO)

    for L, ic in tabela:              # tabela está em ordem crescente de L
        if ic >= limiar:
            return L, tabela
    return tabela[-1][0], tabela      # nunca deve acontecer, mas por segurança


# ---------------------------------------------------------------------------
# Etapa 2 — Análise de frequência e recuperação da chave
# ---------------------------------------------------------------------------

def qui_quadrado(contagens: Counter, n: int, deslocamento: int) -> float:
    """
    Mede o quanto as frequências do subtexto, "desfeitas" com o
    `deslocamento` dado, se afastam das frequências do português.

    Se a letra da chave for `deslocamento`, a letra cifrada (x + d) mod 26
    corresponde à letra original x. Comparamos, então, a contagem observada
    de (x + d) com a contagem esperada de x em português:  n * p_x.

        χ² = Σ (observado_x - esperado_x)² / esperado_x

    Quanto menor o χ², melhor o ajuste.
    """
    total = 0.0
    for x in range(TAMANHO_ALFABETO):
        letra_cifrada = chr(ORD_A + (x + deslocamento) % TAMANHO_ALFABETO)
        observado = contagens.get(letra_cifrada, 0)
        esperado = n * PROB_PORTUGUES[x]
        total += (observado - esperado) ** 2 / esperado
    return total


def melhor_deslocamento(subtexto: str) -> int:
    """
    Testa os 26 deslocamentos possíveis para um subtexto e devolve o que
    minimiza o qui-quadrado — ou seja, a letra da chave (0 = 'a', ...).
    """
    contagens = Counter(subtexto)
    n = len(subtexto)
    return min(range(TAMANHO_ALFABETO), key=lambda d: qui_quadrado(contagens, n, d))


def recuperar_chave(texto: str, tamanho: int) -> str:
    """
    Descobre o deslocamento de cada posição da chave e monta a senha.
    """
    return "".join(chr(ORD_A + melhor_deslocamento(sub)) for sub in subtextos(texto, tamanho))


def reduzir_periodo(chave: str) -> str:
    """
    Se a chave for a repetição de um padrão menor (ex.: "segredosegredo"),
    devolve apenas o padrão ("segredo"). Isso acontece quando a Etapa 1
    escolhe um múltiplo do tamanho real — a decifragem continua correta,
    mas a senha exibida fica mais fiel à original.
    """
    n = len(chave)
    for periodo in range(1, n):
        if n % periodo == 0 and chave[:periodo] * (n // periodo) == chave:
            return chave[:periodo]
    return chave


# ---------------------------------------------------------------------------
# Entrada/saída e programa principal
# ---------------------------------------------------------------------------

def ler_amostra(caminho: str, limite: int) -> str:
    """
    Lê (higienizando) apenas as primeiras `limite` letras do arquivo.

    A estatística do ataque converge com poucas dezenas de milhares de
    letras; não há necessidade de carregar um arquivo gigante inteiro para
    analisá-lo. A decifragem final, essa sim, percorre o arquivo todo.
    """
    partes, total = [], 0
    for bloco in higienizar_arquivo_em_blocos(caminho):
        partes.append(bloco)
        total += len(bloco)
        if total >= limite:
            break
    return "".join(partes)[:limite]


def main():
    parser = argparse.ArgumentParser(
        description="Quebra a Cifra de Vigenère sem conhecer a senha (texto em português)."
    )
    parser.add_argument("arquivo", help="arquivo com o texto cifrado")
    parser.add_argument("-o", "--saida", default="texto_decifrado.txt",
                        help="arquivo de saída com o texto decifrado (padrão: texto_decifrado.txt)")
    parser.add_argument("--max-tamanho", type=int, default=20,
                        help="maior tamanho de senha a testar (padrão: 20)")
    parser.add_argument("--tamanho", type=int, default=None,
                        help="força um tamanho de senha em vez de estimá-lo pelo IC")
    parser.add_argument("--amostra", type=int, default=2_000_000,
                        help="quantidade máxima de letras usadas na análise estatística (padrão: 2.000.000)")
    parser.add_argument("--previa", type=int, default=400,
                        help="quantas letras do texto decifrado mostrar na tela (padrão: 400)")
    args = parser.parse_args()

    # --- Leitura da amostra para análise -----------------------------------
    try:
        amostra = ler_amostra(args.arquivo, args.amostra)
    except FileNotFoundError:
        sys.exit(f"Erro: arquivo '{args.arquivo}' não encontrado.")

    if len(amostra) < 2 * args.max_tamanho:
        sys.exit("Erro: texto cifrado curto demais para a análise estatística.")

    print(f"Letras analisadas: {len(amostra)}")
    print(f"IC de referência — português: {IC_PORTUGUES:.4f}   aleatório: {IC_ALEATORIO:.4f}")
    print()

    # --- Etapa 1: tamanho da senha ----------------------------------------
    tamanho_estimado, tabela = estimar_tamanho_chave(amostra, args.max_tamanho)

    print("Etapa 1 — Índice de Coincidência por tamanho de senha")
    print("  tamanho    IC médio")
    for L, ic in tabela:
        marcador = "  <== mais provável" if L == tamanho_estimado else ""
        print(f"  {L:7d}    {ic:.4f}{marcador}")
    print()

    tamanho = args.tamanho if args.tamanho else tamanho_estimado
    if args.tamanho:
        print(f"Tamanho de senha forçado pelo usuário: {tamanho}")
    else:
        print(f"Tamanho estimado da senha: {tamanho}")

    # Sanidade: o IC do tamanho escolhido deveria ficar próximo do IC do
    # português. Se ficou mais perto do IC aleatório, nenhum tamanho testado
    # "encaixou" — provavelmente a senha é maior que --max-tamanho.
    ic_escolhido = dict(tabela)[tamanho_estimado]
    if ic_escolhido < (IC_PORTUGUES + IC_ALEATORIO) / 2:
        print(f"AVISO: o IC obtido ({ic_escolhido:.4f}) está longe do esperado para "
              f"português ({IC_PORTUGUES:.4f}).")
        print(f"       A senha pode ser maior que {args.max_tamanho} letras "
              f"(tente --max-tamanho maior) ou o texto não está em português.")
    print()

    # --- Etapa 2: análise de frequência -----------------------------------
    chave_bruta = recuperar_chave(amostra, tamanho)

    print("Etapa 2 — Análise de frequência (deslocamento por posição)")
    for posicao, letra in enumerate(chave_bruta):
        print(f"  posição {posicao + 1}: deslocamento {ord(letra) - ORD_A:2d}  ->  '{letra}'")
    print()

    chave = reduzir_periodo(chave_bruta)
    if chave != chave_bruta:
        print(f"A chave '{chave_bruta}' é a repetição de '{chave}'; "
              f"o tamanho real da senha é {len(chave)}.")
    print(f"Tamanho da senha: {len(chave)}")
    print(f"Chave estimada:   {chave}")
    print()

    # --- Decifragem do arquivo completo -----------------------------------
    total = processar_arquivo(args.arquivo, args.saida, chave, decifrar=True)
    print(f"Texto decifrado ({total} letras) salvo em: {args.saida}")
    print()

    # Mostra o início do texto decifrado para conferência visual.
    with open(args.saida, "r", encoding="utf-8") as f:
        previa = f.read(args.previa)
    print("Prévia do texto decifrado:")
    print(previa)


if __name__ == "__main__":
    main()
