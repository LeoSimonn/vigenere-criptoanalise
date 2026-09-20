"""
Parte 1 — Cifra de Vigenère (criptografia e decifragem com senha conhecida).

Uso:
    python cifrar.py <arquivo.txt> <senha> [-o saida.txt]
    python cifrar.py <arquivo.txt> <senha> --decifrar [-o saida.txt]

Exemplo:
    python cifrar.py DomCasmurro.txt segredo
    -> gera texto_criptografado.txt

Funcionamento:
    1. O texto de entrada é higienizado (só letras a-z, minúsculas).
    2. A senha também é higienizada.
    3. A senha é repetida ciclicamente ao longo do texto.
    4. Cada letra é deslocada:   C_i = (P_i + K_i) mod 26
       (ou, para decifrar,       P_i = (C_i - K_i) mod 26)
    5. O resultado é gravado no arquivo de saída.

O arquivo é processado em blocos, então textos muito grandes funcionam
sem carregar tudo na memória.
"""

import argparse
import sys

from higienizacao import higienizar, higienizar_arquivo_em_blocos

# Códigos numéricos: 'a' = 0, 'b' = 1, ..., 'z' = 25.
ORD_A = ord("a")
TAMANHO_ALFABETO = 26


def vigenere(texto: str, chave: str, decifrar: bool = False, posicao_inicial: int = 0) -> str:
    """
    Aplica a Cifra de Vigenère a um trecho de texto já higienizado.

    Parâmetros:
        texto           - string contendo apenas letras a-z.
        chave           - senha já higienizada (letras a-z, não vazia).
        decifrar        - False para cifrar, True para decifrar.
        posicao_inicial - índice global da primeira letra deste trecho.
                          Serve para que, ao processar o arquivo em blocos,
                          a chave continue "de onde parou" no bloco anterior.

    Retorna o trecho transformado.
    """
    # Pré-calcula os deslocamentos de cada letra da chave: 's' -> 18, etc.
    deslocamentos = [ord(k) - ORD_A for k in chave]
    tamanho_chave = len(deslocamentos)

    # Para decifrar, basta usar o deslocamento negativo (mod 26).
    sinal = -1 if decifrar else 1

    saida = []
    for i, letra in enumerate(texto):
        p = ord(letra) - ORD_A                      # letra do texto (0..25)
        k = deslocamentos[(posicao_inicial + i) % tamanho_chave]  # letra da chave
        c = (p + sinal * k) % TAMANHO_ALFABETO      # operação modular
        saida.append(chr(c + ORD_A))
    return "".join(saida)


def processar_arquivo(entrada: str, saida: str, chave: str, decifrar: bool) -> int:
    """
    Lê `entrada` em blocos, higieniza, cifra/decifra com `chave` e grava
    em `saida`. Retorna a quantidade de letras processadas.
    """
    total = 0
    with open(saida, "w", encoding="utf-8") as arquivo_saida:
        for bloco in higienizar_arquivo_em_blocos(entrada):
            # `total` é a posição global da primeira letra do bloco,
            # garantindo a continuidade da chave entre blocos.
            arquivo_saida.write(vigenere(bloco, chave, decifrar, posicao_inicial=total))
            total += len(bloco)
    return total


def main():
    parser = argparse.ArgumentParser(
        description="Cifra (ou decifra) um arquivo de texto com a Cifra de Vigenère."
    )
    parser.add_argument("arquivo", help="arquivo .txt com o texto original")
    parser.add_argument("senha", help="senha (chave) a ser usada")
    parser.add_argument(
        "-o", "--saida",
        help="arquivo de saída (padrão: texto_criptografado.txt ou texto_decifrado.txt)",
    )
    parser.add_argument(
        "--decifrar", action="store_true",
        help="decifra em vez de cifrar (a senha deve ser conhecida)",
    )
    args = parser.parse_args()

    # A senha passa pela mesma higienização do texto: "Segredo!" -> "segredo".
    chave = higienizar(args.senha)
    if not chave:
        sys.exit("Erro: a senha precisa conter ao menos uma letra de a-z.")

    if args.saida is None:
        args.saida = "texto_decifrado.txt" if args.decifrar else "texto_criptografado.txt"

    try:
        total = processar_arquivo(args.arquivo, args.saida, chave, args.decifrar)
    except FileNotFoundError:
        sys.exit(f"Erro: arquivo '{args.arquivo}' não encontrado.")

    operacao = "decifradas" if args.decifrar else "cifradas"
    print(f"Senha utilizada (higienizada): {chave}")
    print(f"Letras {operacao}: {total}")
    print(f"Arquivo gerado: {args.saida}")


if __name__ == "__main__":
    main()
