"""
Módulo de higienização (normalização) de texto.

Antes de cifrar ou analisar um texto, ele precisa ser reduzido ao alfabeto
de 26 letras (a-z). Este módulo implementa exatamente as regras pedidas
na especificação do trabalho:

    1. converter tudo para minúsculas;
    2. remover acentos e sinais diacríticos (á -> a, ç -> c, ã -> a, ...);
    3. remover pontuação, números, espaços e caracteres especiais;
    4. manter somente letras de 'a' a 'z'.

As funções aqui são usadas tanto pelo cifrador (texto e senha) quanto
pelo criptoanalisador (para tolerar arquivos cifrados com quebras de
linha ou outros caracteres estranhos).
"""

import unicodedata


# Tamanho (em caracteres) de cada pedaço lido do disco quando processamos
# arquivos grandes. Ler em blocos evita carregar arquivos enormes de uma
# só vez na memória.
TAMANHO_BLOCO = 1024 * 1024  # 1 milhão de caracteres por bloco


def higienizar(texto: str) -> str:
    """
    Normaliza uma string, devolvendo apenas letras minúsculas de a-z.

    Etapas:
      - NFKD decompõe cada caractere acentuado em "letra base + acento".
        Ex.: 'ç' vira 'c' + '̧' (cedilha combinante), 'ã' vira 'a' + '~'.
      - Os acentos combinantes pertencem à categoria Unicode "Mn"
        (Mark, nonspacing) e são descartados.
      - Tudo é convertido para minúsculas.
      - Só sobrevivem caracteres entre 'a' e 'z'.
    """
    decomposto = unicodedata.normalize("NFKD", texto)
    resultado = []
    for caractere in decomposto:
        # Descarta os acentos que ficaram "soltos" após a decomposição.
        if unicodedata.category(caractere) == "Mn":
            continue
        c = caractere.lower()
        if "a" <= c <= "z":
            resultado.append(c)
    return "".join(resultado)


def higienizar_arquivo_em_blocos(caminho: str):
    """
    Gera (yield) o conteúdo higienizado de um arquivo, bloco a bloco.

    É um gerador: em vez de devolver a string inteira, entrega pedaços
    já normalizados. Assim, arquivos com centenas de megabytes podem ser
    cifrados sem estourar a memória.

    O arquivo é aberto como UTF-8; bytes inválidos são ignorados em vez
    de derrubar o programa (útil para arquivos com codificação mista).
    """
    with open(caminho, "r", encoding="utf-8", errors="ignore") as arquivo:
        while True:
            bloco = arquivo.read(TAMANHO_BLOCO)
            if not bloco:
                break
            yield higienizar(bloco)


def ler_arquivo_higienizado(caminho: str) -> str:
    """
    Lê um arquivo inteiro e devolve o texto higienizado como uma única
    string. Conveniente quando o texto precisa ficar todo em memória
    (caso da criptoanálise, que faz várias passagens sobre ele).
    """
    return "".join(higienizar_arquivo_em_blocos(caminho))
