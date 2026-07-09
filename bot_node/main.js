const path = require('path');
const fs = require('fs');
const readline = require('readline');
const qrcode = require('qrcode');
const qrcodeTerminal = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return fallback;
}

function emit(payload) {
  process.stdout.write(JSON.stringify(payload) + '\n');
}

function chatIdFor(phone) {
  const raw = String(phone || '').replace(/\D/g, '');
  return raw ? `${raw}@c.us` : null;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function timeoutPromise(promise, timeoutMs, message) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(message)), timeoutMs);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
}

function firstExistingPath(candidates) {
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function packagedChromiumPath() {
  return firstExistingPath([
    path.join(__dirname, 'chromium', 'chrome-win64', 'chrome.exe'),
    path.join(__dirname, 'chromium', 'chrome-win', 'chrome.exe'),
    path.join(__dirname, 'chromium', 'chrome.exe')
  ]);
}

function isTransientSendError(err) {
  const message = String(err || '');
  return message.includes('No LID for user') ||
    message.includes('Runtime.callFunctionOn timed out') ||
    message.includes('ProtocolError') ||
    message.includes('Execution context was destroyed') ||
    message.includes('Target closed');
}

const authRoot = argValue('--auth-dir', path.join(__dirname, '..', 'data', 'wwebjs_auth'));
let isReady = false;
let readySince = 0;
const browserPath = packagedChromiumPath();

emit({ event: 'log', message: `Pasta de sessão LocalAuth: ${authRoot}` });
if (!browserPath) {
  emit({
    event: 'error',
    status: 'Erro',
    message: 'Chromium empacotado não encontrado. Reinstale o aplicativo ou verifique a pasta bot_node/chromium.'
  });
  process.exit(1);
}
emit({ event: 'log', message: `Chromium empacotado: ${browserPath}` });

const client = new Client({
  authStrategy: new LocalAuth({ clientId: 'appdeponto-bot', dataPath: authRoot }),
  takeoverOnConflict: true,
  takeoverTimeoutMs: 0,
  authTimeoutMs: 120000,
  qrMaxRetries: 5,
  puppeteer: {
    headless: true,
    executablePath: browserPath,
    protocolTimeout: 180000,
    timeout: 0,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-extensions'
    ]
  }
});

client.on('loading_screen', (percent, message) => {
  emit({ event: 'log', message: `Carregando WhatsApp: ${percent}% ${String(message || '')}`.trim() });
});

client.on('change_state', (state) => {
  emit({ event: 'log', message: `Estado do WhatsApp: ${String(state || '')}` });
});

client.on('qr', async (qr) => {
  isReady = false;
  try {
    const dataUrl = await qrcode.toDataURL(qr, { margin: 1, width: 300 });
    qrcodeTerminal.generate(qr, { small: true }, (ascii) => {
      emit({ event: 'qr', dataUrl, ascii, message: 'QR Code recebido. Escaneie pelo WhatsApp.' });
    });
  } catch (err) {
    emit({ event: 'qr', raw: qr, error: String(err), message: 'QR Code recebido, mas não foi possível gerar imagem.' });
  }
});

client.on('authenticated', () => {
  emit({ event: 'authenticated', status: 'Autenticado', message: 'WhatsApp autenticado. Sessão salva localmente. Aguardando carregamento final.' });
});

client.on('ready', async () => {
  isReady = false;
  emit({ event: 'status', status: 'Aquecendo', message: 'WhatsApp carregado. Aguardando estabilizar antes dos envios.' });
  await waitUntilUsable();
  await sleep(8000);
  isReady = true;
  readySince = Date.now();
  emit({ event: 'ready', status: 'Conectado', message: 'WhatsApp conectado e pronto para envio.' });
});

client.on('disconnected', (reason) => {
  isReady = false;
  emit({ event: 'status', status: 'Desconectado', message: `WhatsApp desconectado: ${String(reason || '')}` });
});

client.on('auth_failure', (message) => {
  isReady = false;
  emit({ event: 'error', status: 'Erro', message: `Falha de autenticação: ${message}` });
});

client.initialize().catch((err) => {
  const message = String(err);
  const friendly = message.includes('browser is already running')
    ? 'Existe uma sessão do WhatsApp ainda aberta usando esta pasta. Feche outras janelas/processos do bot ou use Limpar sessão para gerar um novo QR Code.'
    : message;
  emit({ event: 'error', status: 'Erro', message: friendly });
});

async function waitUntilUsable() {
  for (let attempt = 1; attempt <= 12; attempt += 1) {
    try {
      const state = await timeoutPromise(client.getState(), 10000, 'Tempo limite ao verificar estado do WhatsApp.');
      emit({ event: 'log', message: `Estado verificado: ${String(state || '')}` });
      if (!state || ['CONNECTED', 'OPENING', 'PAIRING'].includes(String(state))) return true;
    } catch (err) {
      emit({ event: 'log', message: `Aguardando estado do WhatsApp (${attempt}/12): ${String(err)}` });
    }
    await sleep(2500);
  }
  return false;
}

async function resolveChatId(phone) {
  const direct = chatIdFor(phone);
  let lastError = null;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      const numberId = await timeoutPromise(
        client.getNumberId(String(phone || '').replace(/\D/g, '')),
        45000,
        'Tempo limite ao resolver número no WhatsApp Web.'
      );
      if (numberId && numberId._serialized) return numberId._serialized;
      return null;
    } catch (err) {
      lastError = err;
      emit({ event: 'log', message: `Falha ao resolver número ${phone} (${attempt}/2): ${String(err)}` });
      await sleep(3000);
    }
  }
  emit({ event: 'log', message: `Usando envio direto para ${phone} após falha na resolução: ${String(lastError || '')}` });
  return direct;
}

async function sendText(phone, message) {
  if (Date.now() - readySince < 5000) {
    await sleep(5000);
  }
  const direct = chatIdFor(phone);
  const resolved = await resolveChatId(phone);
  const candidates = [];
  if (resolved) candidates.push(resolved);
  if (direct && direct !== resolved) candidates.push(direct);
  if (!candidates.length) {
    throw new Error('Número inválido ou sem WhatsApp.');
  }
  let lastError = null;
  for (const candidate of candidates) {
    for (let attempt = 1; attempt <= 2; attempt += 1) {
      try {
        await timeoutPromise(
          client.sendMessage(candidate, message),
          90000,
          'Tempo limite ao enviar mensagem pelo WhatsApp Web. Tente novamente em alguns segundos.'
        );
        return true;
      } catch (err) {
        lastError = err;
        emit({ event: 'log', message: `Falha ao enviar para ${candidate} (${attempt}/2): ${String(err)}` });
        if (!isTransientSendError(err)) break;
        await sleep(4000 * attempt);
      }
    }
  }
  throw lastError || new Error('Falha desconhecida ao enviar mensagem.');
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on('line', async (line) => {
  let command;
  try {
    command = JSON.parse(line);
  } catch (err) {
    emit({ event: 'error', message: `Comando inválido: ${line}` });
    return;
  }

  if (command.action === 'stop') {
    emit({ event: 'log', message: 'Encerrando bot.' });
    try { await client.destroy(); } catch (err) {}
    process.exit(0);
  }

  if (command.action === 'send') {
    const id = String(command.id || '');
    const phone = String(command.phone || '').replace(/\D/g, '');
    const message = String(command.message || '');
    if (!chatIdFor(phone) || !message) {
      emit({ event: 'send_result', id, ok: false, message: 'Telefone ou mensagem vazios.' });
      return;
    }
    if (!isReady) {
      emit({ event: 'send_result', id, ok: false, phone, message: 'WhatsApp ainda não está conectado. Aguarde o status Conectado.' });
      return;
    }
    try {
      await sendText(phone, message);
      emit({ event: 'send_result', id, ok: true, phone, message: 'Mensagem enviada com sucesso.' });
    } catch (err) {
      emit({ event: 'send_result', id, ok: false, phone, message: String(err) });
    }
  }
});
