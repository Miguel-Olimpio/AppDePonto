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

## LAYOUT E MODO DE USAR

Ao abrir o app, o colaborador acessa uma tela simples para selecionar seu nome, bater ponto e acompanhar as tarefas do dia.

![imagePonto1](https://github.com/user-attachments/assets/a23174ab-be6d-4ee8-9e20-f251fbc4fdf0)

### 1. Cadastre colaboradores e setores

Na area administrativa, o usuario cadastra colaboradores, setores e vinculos de trabalho.

Essas informacoes sao usadas para filtrar tarefas, organizar responsabilidades e calcular os registros de ponto.

![imagePonto2](https://github.com/user-attachments/assets/71a9544f-eb3b-4253-a944-cd7f80d8b557)

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

![imagePonto3](https://github.com/user-attachments/assets/339e8703-fe8d-489f-b950-8c049c5ab6cc)

### 4. Cadastre tarefas e POPs

As tarefas podem ser cadastradas por setor, horario, tolerancia e dias da semana.

Na tela do colaborador, aparecem apenas as tarefas relacionadas ao setor do colaborador e ao dia atual.

### 5. Acompanhe ocorrencias e frequencia

O sistema identifica atrasos, faltas, retornos atrasados e tarefas nao cumpridas.

O administrador pode visualizar ocorrencias, registrar tratativas e abonar faltas quando necessario.

![imagePonto4](https://github.com/user-attachments/assets/e9f17bcd-1eef-4a08-b819-eed11c192aaa)

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

![imagePonto5](https://github.com/user-attachments/assets/bc7ced84-1c9f-4321-8dc2-b1975fe342d6)

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

A imagem abaixo demonstra a conexao do WhatsApp Bot, o acompanhamento do status e um exemplo de mensagem enviada para colaboradores.

![imagePonto6](https://github.com/user-attachments/assets/1c480db8-54cd-49d2-bcfc-748220c957c3)

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
