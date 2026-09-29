# Do zero: o que fazer com estes arquivos

Escrito para quem nunca programou. Leia na ordem e não pule.

---

## Primeiro, três palavras que eu usei sem explicar

**Repositório (ou "repo").** É só uma pasta comum no seu computador que ganhou
um superpoder: ela guarda o histórico de todas as versões de todos os arquivos
dentro dela. Nada se perde, nada é sobrescrito para sempre.

**Commit.** É salvar um ponto no tempo. Como tirar uma foto da pasta inteira e
escrever uma legenda: "mudei a taxa de 1% para 0,8%". Depois você pode voltar
para qualquer foto antiga. Um commit nunca é apagado.

**Push.** É mandar essas fotos para a nuvem (o GitHub), para que existam mesmo
se o seu computador morrer.

É isso. Nada mais complicado que isso.

---

## PARTE 1 — Onde colocar a pasta

**Coloque em `Documentos`.** Crie uma pasta chamada `meu-guardiao` lá dentro.

Onde **não** colocar, e por quê:

- **Área de trabalho:** funciona, mas vira bagunça rápido.
- **Google Drive, Dropbox ou iCloud:** *não coloque aqui.* Esses serviços
  sincronizam sozinhos e brigam com o controle de versão, corrompendo o
  histórico. Essa é a recomendação mais importante desta página. O backup na
  nuvem vai existir, mas pelo GitHub, que é feito para isso.

Caminho final:

- Mac: `/Users/seunome/Documents/meu-guardiao`
- Windows: `C:\Users\seunome\Documents\meu-guardiao`

Descompacte o zip lá dentro. Tem que ficar assim:

```
meu-guardiao/
├── motor_dor/
│   ├── __init__.py
│   ├── parametros.py
│   ├── modelos.py
│   ├── financeiro.py
│   └── motor.py
├── tests/
│   ├── __init__.py
│   └── test_motor.py
├── exemplo.py
├── calibracao.py
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

Se ao descompactar aparecer `meu-guardiao/meu-guardiao/...`, arraste a pasta de
dentro para fora. A estrutura importa: `motor.py` precisa estar dentro de
`motor_dor/`.

---

## PARTE 2 — Fazer rodar (15 minutos)

> ### Antes de tudo: não digite as crases
> Neste guia os comandos aparecem em caixinhas. As três crases (```) que
> delimitam a caixinha são **só formatação** — digite apenas o que está
> dentro. Se você digitar as crases, o terminal responde com um erro
> `CommandNotFoundException`.

> ### Windows: use `python`, não `python3`
> O Windows vem com um atalho falso chamado `python3` que só abre a Microsoft
> Store. Em todos os comandos deste guia, **no Windows troque `python3` por
> `python`** e `pip3` por `pip`. No Mac, use `python3` normalmente.

### Abrir o terminal

**Mac:** Cmd+Espaço, digite "Terminal", Enter.
**Windows:** menu Iniciar, digite "PowerShell", Enter.

É uma janela preta onde você digita comandos. Assusta no começo e depois vira
rotina.

### Instalar o Python

Digite e dê Enter:

```
python3 --version
```

Se aparecer `Python 3.10` ou maior, pule para o próximo passo.

Se der erro, instale:

**Windows**
1. Vá em **python.org/downloads** e clique no botão amarelo "Download Python".
2. Abra o arquivo baixado. Na primeira tela, **marque a caixa
   "Add python.exe to PATH"**, embaixo. Ela vem desmarcada. Se esquecer, nada
   funciona depois.
3. Clique em "Install Now" e espere.
4. **Feche o PowerShell inteiro e abra de novo.** O terminal só enxerga o
   Python novo em janelas abertas depois da instalação.
5. Confira com `python --version`.
6. Se ainda aparecer a mensagem da Microsoft Store: Configurações → Aplicativos
   → Configurações avançadas de aplicativos → **Aliases de execução de
   aplicativo** → desligue `python.exe` e `python3.exe`. Feche e reabra o
   PowerShell.

**Mac:** baixe em python.org → Downloads, abra o instalador, avance até o fim.

### Entrar na pasta

```
cd ~/Documents/meu-guardiao
```

No Mac tem um atalho: digite `cd ` (com espaço), arraste a pasta
`meu-guardiao` do Finder para dentro da janela do terminal, e dê Enter.

No Windows use `cd $HOME\Documents\meu-guardiao`.

### Rodar

```
python3 exemplo.py
```

Deve aparecer uma tabela com três personas, capitais e Protection Score.
**Se apareceu, o motor está rodando na sua máquina.**

Depois rode o confronto com os seus casos reais:

```
python3 calibracao.py
```

E os testes, que avisam se algum número saiu do lugar:

```
pip3 install pytest
python3 -m pytest tests/ -q
```

Tem que terminar com `34 passed`.

### Se der errado

| Mensagem | O que fazer |
|---|---|
| `python3 não foi encontrado... Microsoft Store` | Windows: use `python` em vez de `python3`. Se persistir, desligue os aliases de execução (Parte 2) |
| `'\`\`\`' não é reconhecido como nome de cmdlet` | Você digitou as crases. Digite só o comando de dentro da caixinha |
| `command not found: python3` | Python não instalado, ou faltou marcar "Add python.exe to PATH" |
| `No such file or directory: exemplo.py` | Você não está na pasta certa. Rode `ls` (Mac) ou `dir` (Windows) e veja se `exemplo.py` aparece |
| `ModuleNotFoundError: motor_dor` | A estrutura de pastas está errada. Confira se existe a pasta `motor_dor` com os arquivos dentro |
| `command not found: pip3` | Use `python -m pip install pytest` (Windows) ou `python3 -m pip install pytest` (Mac) |

---

## PARTE 3 — Claude Code (o caminho recomendado)

Sem o Claude Code, o ciclo é: eu gero arquivo aqui no chat → você baixa → você
descompacta → você substitui os arquivos certos → você confere. Seis passos
manuais a cada alteração, e cada um é uma chance de erro.

Com o Claude Code, eu abro a pasta `meu-guardiao` direto na sua máquina, leio
os arquivos que já estão lá, altero no lugar, rodo os testes e faço o commit.
Você só conversa comigo e olha o resultado.

**O que você precisa:** a mesma assinatura do Claude que você já tem, e o
aplicativo instalado. Depois de instalado, você aponta para a pasta
`meu-guardiao` uma vez e pronto.

Para o tamanho deste projeto, é a diferença entre me mandar arquivos por
e-mail e me dar acesso à mesa de trabalho.

---

## PARTE 4 — GitHub (o backup que nunca falha)

Eu não guardo nada entre conversas. Cada sessão começa do zero. **Se o
histórico depender de mim, ele falha.** Ele precisa morar num lugar seu.

1. Crie uma conta em **github.com** (grátis).
2. Instale o **GitHub Desktop** em desktop.github.com. É interface gráfica,
   com botões — você não precisa decorar comando nenhum.
3. Abra: File → Add Local Repository → escolha a pasta `meu-guardiao`.
4. Vai aparecer um aviso dizendo que a pasta ainda não é um repositório.
   Clique em **"create a repository"**.
5. Marque **"Keep this code private"**. É importante: o código é seu.
6. Clique em **"Publish repository"**.

Pronto. A partir daí, sempre que algo mudar, o GitHub Desktop mostra
exatamente o que mudou, linha por linha. Você escreve uma frase curta
descrevendo a mudança, clica em **Commit** e depois em **Push**. O histórico
fica gravado para sempre e dá para voltar a qualquer ponto.

---

## PARTE 5 — A rotina, depois de montado

Toda vez que mexermos no motor:

```
python3 -m pytest tests/ -q
```

Se algum teste falhar, **não faça commit.** Ou um número mudou sem querer, ou
a versão do motor precisa ser atualizada no `CHANGELOG.md`.

Regra que não se quebra: **mudou número de saída, mudou versão.** Uma cotação
gravada sob a versão 1.1.0 precisa ser recalculável com a versão 1.1.0 daqui a
dez anos, inclusive dentro de um processo judicial.
