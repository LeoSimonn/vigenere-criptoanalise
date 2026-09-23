# Cifra de Vigenère — Criptografia e Criptoanálise

**Autores:** Gustavo Melleu e Leonardo Monteiro

Trabalho de Segurança de Sistemas. Implementação em **Python 3** (sem
dependências externas) de:

1. **`cifrar.py`** — cifra (ou decifra, com senha conhecida) um arquivo de
   texto com a Cifra de Vigenère;
2. **`criptoanalise.py`** — quebra a cifra **sem conhecer a senha**, assumindo
   que o texto original está em português;
3. **`higienizacao.py`** — módulo comum de normalização do texto.

## Como executar

Requer Python 3.8+ (testado com 3.13).

### Parte 1 — Cifrar

```bash
python cifrar.py DomCasmurro.txt segredo
```

Gera `texto_criptografado.txt`. Opções:

| Opção          | Descrição                                            |
|----------------|------------------------------------------------------|
| `-o ARQUIVO`   | nome do arquivo de saída                             |
| `--decifrar`   | decifra em vez de cifrar (gera `texto_decifrado.txt`)|

A senha passa pela mesma higienização do texto: `"Segurança!"` vira `seguranca`.

### Parte 2 — Criptoanálise

```bash
python criptoanalise.py texto_criptografado.txt
```

Mostra a tabela de IC por tamanho de senha, o tamanho estimado, a chave
estimada e uma prévia do texto decifrado; grava o texto completo em
`texto_decifrado.txt`. Opções:

| Opção               | Padrão    | Descrição                                                  |
|---------------------|-----------|------------------------------------------------------------|
| `-o ARQUIVO`        | `texto_decifrado.txt` | arquivo de saída                               |
| `--max-tamanho N`   | 20        | maior tamanho de senha testado                             |
| `--tamanho N`       | —         | força o tamanho da senha (pula a estimativa por IC)        |
| `--amostra N`       | 2.000.000 | letras usadas na análise estatística (o arquivo inteiro é decifrado) |
| `--previa N`        | 400       | letras da prévia exibida na tela                           |

## Como funciona

### Higienização (`higienizacao.py`)

O texto é decomposto com Unicode NFKD (`ç` → `c` + cedilha), os acentos
combinantes são descartados, tudo vira minúsculo e só sobrevivem letras
`a`–`z`. Pontuação, números, espaços e símbolos são removidos. Arquivos são
lidos em blocos de 1 M caracteres, então arquivos grandes não estouram a
memória.

### Cifra de Vigenère (`cifrar.py`)

Cada letra é mapeada para um número (`a`=0 … `z`=25) e a senha é repetida
ciclicamente sobre o texto:

```
C_i = (P_i + K_i) mod 26        (cifrar)
P_i = (C_i - K_i) mod 26        (decifrar)
```

Como o arquivo é processado em blocos, a função recebe a posição global do
bloco para que a senha continue "de onde parou".

### Criptoanálise (`criptoanalise.py`)

**Etapa 1 — tamanho da senha (Índice de Coincidência).** Para cada tamanho
candidato `L` (1 … `--max-tamanho`), o texto cifrado é dividido em `L`
subtextos (posições `j, j+L, j+2L, …`). Todas as letras de um subtexto foram
deslocadas pela mesma letra da chave, ou seja, sofreram uma cifra de César —
que apenas renomeia as letras sem alterar a distribuição. Logo o IC do
subtexto permanece o do português (≈ 0,072–0,078). Se `L` estiver errado, os
subtextos misturam vários deslocamentos e o IC cai em direção a 1/26 ≈ 0,038.

```
IC = Σ f_i (f_i − 1) / ( N (N − 1) )
```

Múltiplos do tamanho real (2L, 3L, …) também têm IC alto, então o programa
escolhe o **menor** tamanho cujo IC está a até 3 % (da distância entre o IC
máximo e o IC aleatório) do maior IC encontrado. Se ainda assim um múltiplo
for escolhido, a chave recuperada será periódica (`segredosegredo`) e é
reduzida ao seu período mínimo (`segredo`).

**Etapa 2 — letras da senha (análise de frequência).** Para cada subtexto,
testam-se os 26 deslocamentos possíveis; para cada um, compara-se a
distribuição de letras "desfeita" com a distribuição do português usando o
teste qui-quadrado:

```
χ² = Σ (observado_x − esperado_x)² / esperado_x ,   esperado_x = N · p_x
```

O deslocamento com menor χ² é a letra da chave naquela posição.

**Decifragem.** Com a chave estimada, o arquivo inteiro é decifrado em blocos
com `P_i = (C_i − K_i) mod 26`.

## Resultado com o teste recomendado

`DomCasmurro.txt` + senha `segredo` (308.921 letras):

```
  tamanho    IC médio
        1    0.0468
        ...
        7    0.0767  <== mais provável
        ...
       14    0.0767

Tamanho da senha: 7
Chave estimada:   segredo
```

Em testes adicionais o ataque recuperou corretamente chaves de 1 a 20 letras
(incluindo casos como `aaaaab` e `abcabd`) com amostras de apenas 3.000
letras, e processou um arquivo de 209 MB (154 milhões de letras) em cerca
de 50 s por etapa.

## Limitações

* A senha precisa ter tamanho ≤ `--max-tamanho` (aumente a opção se
  necessário; o programa avisa quando nenhum tamanho apresenta IC compatível
  com português).
* Textos muito curtos (algumas centenas de letras) ou que não estejam em
  português degradam a análise estatística.
