# AppDePonto

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## IDEALIZACAO DO PROJETO

O AppDePonto foi desenvolvido para ajudar pequenos negocios a controlar ponto, tarefas operacionais, jornadas, ocorrencias e relatorios de forma simples, local e acessivel.

A proposta do projeto e oferecer uma ferramenta desktop que organize a rotina da empresa sem exigir sistemas caros, infraestrutura complexa ou assinaturas mensais. O app centraliza a marcacao de ponto, a conferencia de tarefas/POPs, o acompanhamento de faltas, atrasos e ocorrencias, alem de permitir uma integracao com WhatsApp para lembretes e avisos operacionais.

> **Versao demo:** a versao exposta neste GitHub e uma demonstracao publica do projeto. A versao final e privada, possui recursos comerciais e ajustes especificos de clientes, e nao pode ser exibida de forma completa na rede.

## SOBRE O APP

O AppDePonto e uma aplicacao desktop/local em Python para empresas que precisam controlar a rotina de colaboradores.

Ele foi pensado para pequenos negocios que desejam registrar ponto, organizar tarefas recorrentes, acompanhar ocorrencias e gerar relatorios sem depender de um sistema online complexo.

O app pode apoiar rotinas de:

- padarias;
- lanchonetes;
- restaurantes;
- mercados;
- lojas;
- pequenas equipes operacionais;
- empresas que trabalham com tarefas diarias e controle de ponto.

## FUNCIONALIDADES

- Area do colaborador.
- Area administrativa com login.
- Cadastro de colaboradores.
- Cadastro de setores.
- Cadastro de jornadas e escalas.
- Registro de ponto: entrada, pausa, retorno e saida.
- Calculo dinamico de retorno da pausa.
- Cadastro de tarefas e POPs por setor.
- Tarefas por horario, tolerancia e dias da semana.
- Checagem de tarefas do dia.
- Indicadores visuais de tarefas e ponto.
- Registro de ocorrencias.
- Tratativa e abono de faltas/ocorrencias.
- Metas individuais e gerais.
- Dashboard administrativo.
- Consulta de frequencia.
- Relatorio de pagamento em PDF.
- Relatorio de ocorrencias em PDF.
- Manutencao de dados antigos, PDFs e logs.
- Bot WhatsApp para lembretes e mensagens operacionais.
- Banco de dados local em Excel.
- Backups automaticos.
- Estrutura preparada para gerar executavel Windows com PyInstaller.

## EXEMPLO DE USO E OCORRENCIAS

A tabela abaixo exemplifica como o app pode ser usado na rotina de uma empresa. O foco principal esta nas ocorrencias, que ajudam o administrador a identificar faltas, atrasos, retornos fora do horario e tarefas/POPs nao cumpridos.

| Colaborador | Setor | Ponto do dia | Tarefas / POPs | Ocorrencias geradas | Tratativa administrativa | Impacto no acompanhamento |
| --- | --- | --- | --- | --- | --- | --- |
| Ana Paula | Cozinha | Entrada, pausa, retorno e saida registrados corretamente | Todas as tarefas do setor foram feitas dentro do horario | Nenhuma ocorrencia | Nenhuma acao necessaria | Frequencia regular, tarefas cumpridas e bonus mantido quando configurado |
| Bruno Silva | Atendimento | Ponto registrado normalmente, sem falta | Algumas tarefas foram feitas, mas uma tarefa obrigatoria ficou pendente apos a tolerancia | Tarefa nao cumprida ou tarefa atrasada | Administrador pode registrar observacao, orientar o colaborador e acompanhar reincidencia | Colaborador nao teve falta, mas aparece no painel de ocorrencias por descumprimento operacional |
| Carlos Mendes | Limpeza | Nao registrou entrada em dia esperado de trabalho | Nenhuma tarefa foi marcada, pois o colaborador nao compareceu | Falta nao abonada e tarefas nao cumpridas, quando aplicavel | Administrador pode manter como falta nao abonada ou abonar com motivo/documento | Falta entra no relatorio de frequencia, pode afetar bonus de assiduidade e relatorio de pagamento |
| Daniela Rocha | Padaria | Entrada registrada, pausa registrada, retorno feito apos a tolerancia | Tarefas concluidas normalmente | Retorno atrasado | Administrador pode registrar justificativa ou manter ocorrencia | Nao gera falta, mas registra comportamento de atraso no retorno da pausa |
| Eduardo Lima | Estoque | Nao registrou entrada, mas apresentou justificativa aceita | Tarefas do dia foram justificadas pela ausencia | Falta abonada | Administrador registra motivo do abono e observacao | Falta aparece como abonada, nao deve ser tratada como falta nao justificada |

Esse fluxo permite separar problemas diferentes. Um colaborador pode nao ter faltas, mas ainda assim gerar ocorrencias por tarefas nao cumpridas. Da mesma forma, um colaborador pode ter uma falta abonada que aparece no historico, mas nao deve ser tratada como falta nao justificada.

## LAYOUT E MODO DE USAR

Ao abrir o app, o colaborador acessa uma tela simples para selecionar seu nome, bater ponto e acompanhar as tarefas do dia.

![imagePonto1](https://github.com/Miguel-Olimpio/AppDePonto/assets/107503116/imagePonto1)

### 1. Cadastre colaboradores e setores

Na area administrativa, o usuario cadastra colaboradores, setores e vinculos de trabalho.

Essas informacoes sao usadas para filtrar tarefas, organizar responsabilidades e calcular os registros de ponto.

![imagePonto2](https://github.com/Miguel-Olimpio/AppDePonto/assets/107503116/imagePonto2)

### 2. Configure jornadas e escalas

O administrador pode cadastrar jornadas semanais fixas ou escalas de trabalho.

As jornadas definem:

- horario de entrada;
- horario de saida;
- tempo de pausa;
- tolerancia;
- dias trabalhados;
- regras de escala, quando aplicavel.

### 3. Registre ponto

O colaborador registra:

- entrada;
- pausa;
- retorno;
- saida.

O retorno da pausa e calculado automaticamente com base no momento em que a pausa foi batida e no tempo de pausa configurado na jornada.

![imagePonto3](https://github.com/Miguel-Olimpio/AppDePonto/assets/107503116/imagePonto3)

### 4. Cadastre tarefas e POPs

As tarefas podem ser cadastradas por setor, horario, tolerancia e dias da semana.

Na tela do colaborador, aparecem apenas as tarefas relacionadas ao setor do colaborador e ao dia atual.

### 5. Acompanhe ocorrencias e frequencia

O sistema identifica atrasos, faltas, retornos atrasados e tarefas nao cumpridas.

O administrador pode visualizar ocorrencias, registrar tratativas e abonar faltas quando necessario.

![imagePonto4](https://github.com/Miguel-Olimpio/AppDePonto/assets/107503116/imagePonto4)

### 6. Gere relatorios

O app gera relatorios em PDF para apoiar a gestao da empresa.

Exemplos:

- relatorio de pagamento;
- relatorio de ocorrencias;
- consulta de frequencia;
- detalhes de faltas, atrasos e tarefas nao cumpridas.

Os PDFs sao salvos em:

```text
pdfs/
```

![imagePonto5](https://github.com/Miguel-Olimpio/AppDePonto/assets/107503116/imagePonto5)

### 7. Use o Bot WhatsApp

O modulo de WhatsApp permite conectar uma conta via WhatsApp Web para envio de lembretes e mensagens operacionais.

O bot utiliza um processo Node separado na pasta `bot_node/`.

Para uso em desenvolvimento:

```bash
cd bot_node
npm install
```

Depois, no app:

- acesse a area administrativa;
- abra Bot WhatsApp;
- clique em Iniciar bot;
- escaneie o QR Code;
- acompanhe o status e os logs pela interface.

A sessao do WhatsApp fica salva localmente em `data/wwebjs_auth/`, mas essa pasta nao e versionada no GitHub.

## TECNOLOGIAS UTILIZADAS

## Back end

- Python
- openpyxl
- pandas
- ReportLab

## Front end

- Tkinter
- ttkbootstrap

## Bot WhatsApp

- Node.js
- whatsapp-web.js
- qrcode

## Testes e empacotamento

- pytest
- PyInstaller

## COMO EXECUTAR O PROJETO

Pre-requisitos:

- Python 3.10 ou superior.
- Node.js, caso deseje usar o Bot WhatsApp em desenvolvimento.

```bash
# clonar repositorio
git clone https://github.com/Miguel-Olimpio/AppDePonto.git

# entrar na pasta do projeto
cd AppDePonto

# criar ambiente virtual opcional
python -m venv .venv

# ativar ambiente virtual no Windows
.venv\Scripts\activate

# instalar dependencias Python
pip install -r requirements.txt

# executar o projeto
python main.py
```

Para instalar dependencias do bot:

```bash
cd bot_node
npm install
```

## BANCO DE DADOS LOCAL

O app utiliza planilhas Excel como banco de dados local.

Na primeira execucao, o sistema cria automaticamente:

```text
data/
pdfs/
backups/
icon/
```

Arquivos principais:

```text
data/colaboradores.xlsx
data/ponto.xlsx
data/tarefas_pops.xlsx
data/ocorrencias.xlsx
data/setores.xlsx
data/metas.xlsx
data/bot_config.xlsx
```

Esses arquivos nao sao versionados no GitHub, pois podem conter dados reais de clientes.

## TESTES

Para rodar os testes:

```bash
python -m pytest tests -q
```

## GERAR EXECUTAVEL

Para gerar o executavel Windows:

```bash
pyinstaller --clean --noconfirm ControlePontoTarefas.spec
```

O executavel sera criado em:

```text
dist/ControlePontoTarefas/ControlePontoTarefas.exe
```

Estrutura esperada para distribuicao:

```text
ControlePontoTarefas/
  ControlePontoTarefas.exe
  data/
  pdfs/
  backups/
  icon/
  _internal/
```

## OBSERVACOES SOBRE ARQUIVOS GRANDES

O repositorio nao inclui:

- planilhas de dados;
- PDFs gerados;
- backups;
- sessoes do WhatsApp;
- `node_modules`;
- Chromium empacotado;
- runtime local de Node;
- builds do PyInstaller.

Esses arquivos devem ser gerados, instalados ou empacotados conforme o ambiente de uso.

## ESTRUTURA DO PROJETO

```text
app/
  bot/
  config/
  models/
  repositories/
  services/
  ui/
  utils/
  pdf/
bot_node/
tests/
icon/
pyinstaller_hooks/
main.py
requirements.txt
ControlePontoTarefas.spec
```

## OBSERVACOES

- Esta e uma versao demo.
- A versao comercial completa e privada.
- Dados locais, sessoes, PDFs, backups, builds e dependencias pesadas nao sao enviados ao GitHub.
- O app foi desenvolvido para uso desktop/local.
- A persistencia demonstrativa utiliza Excel local.

## AUTOR

Miguel Olimpio de Paula Netto

## LICENCA

Este projeto esta sob licenca MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
