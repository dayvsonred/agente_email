# Agente de Email para Vagas (OCR + IA)

Este projeto cria um agente em Python que:

- recebe um print de vaga;
- extrai o texto da imagem com OCR;
- identifica e-mail da vaga;
- seleciona trechos relevantes do seu curriculo (`pt` ou `en` automaticamente);
- gera assunto e corpo da mensagem no idioma do anuncio;
- envia o e-mail via SMTP (opcional, com `auto_send=true`).

## 1) Requisitos

- Python 3.11+
- Tesseract OCR instalado no sistema

No Windows, instale o Tesseract e, se necessario, ajuste o PATH.

## 2) Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite `.env` com:

- `OPENAI_API_KEY` (opcional, mas recomendado para mensagem melhor);
- dados SMTP do seu provedor;
- caminhos dos curriculos em `CV_FILE_PT` e `CV_FILE_EN`.
- `CV_FILE` como fallback para outros idiomas.
- pastas de fila em `TODOIST_DIR`, `DONE_DIR` e `ERRORSEND_DIR`.
- arquivo de log de processados em `PROCESSED_REGISTRY_FILE`.
- se necessario no Windows, caminho do binario em `TESSERACT_CMD`.

Selecao automatica de CV:

- vaga em portugues (`pt*`) usa `CV_FILE_PT`;
- vaga em ingles (`en*`) usa `CV_FILE_EN`;
- outros idiomas usam `CV_FILE`.

Fluxo de pastas:

- coloque novos prints em `data/todoist`;
- processe com endpoint `/process-todoist`;
- arquivos processados sao movidos para `data/done`;
- quando nao ha e-mail detectado e nao existe fallback, o print vai para `data/errosend`;
- o arquivo `data/processed_files.txt` guarda os hashes dos ja processados para evitar repetir.

## 3) Rodar a API

```bash
uvicorn app.main:app --reload --port 8000
```

No CMD do Windows, voce tambem pode usar:

```bat
run_api.bat
```

Swagger:

- `http://localhost:8000/docs`

## 4) Endpoints

### `POST /analyze`

Recebe imagem e retorna:

- e-mails detectados;
- idioma detectado;
- assunto/corpo sugeridos;
- pontos do CV usados.

Campos (multipart/form-data):

- `image`: arquivo da imagem
- `candidate_name`: opcional

### `POST /send`

Envia um e-mail com payload JSON:

```json
{
  "to_email": "rh@empresa.com",
  "subject": "Application for the role",
  "body": "Hello...",
  "dry_run": false
}
```

### `POST /process-and-send`

Faz tudo em um passo. Campos (multipart/form-data):

- `image`: arquivo da imagem
- `auto_send`: `true` para enviar automaticamente
- `candidate_name`: opcional

Se `auto_send=false`, apenas retorna a sugestao para revisao.

### `POST /process-todoist`

Processa todos os prints em `TODOIST_DIR`:

- processa apenas arquivos novos (por hash do arquivo);
- move processados para `DONE_DIR`;
- ignora duplicados ja processados e move para `DONE_DIR`;
- registra no `PROCESSED_REGISTRY_FILE`.

Campos (multipart/form-data):

- `auto_send`: `true` para enviar e-mail automaticamente
- `candidate_name`: opcional
- `fix_email`: e-mail fallback quando o print nao tiver e-mail
- `only_email`: sempre usa este e-mail e ignora o e-mail detectado no print

## 5) Modo terminal (sem chamar endpoint manualmente)

Worker por linha de comando:

```bash
python -m app.worker
```

Loop continuo com animacao no console (`/ | \ -`):

```bash
python -m app.worker --watch --interval 15
```

Atalho no CMD:

```bat
run_worker.bat
```

Com envio automatico:

```bash
python -m app.worker --watch --interval 15 --auto-send
```

Fallback de e-mail (se o print nao tiver e-mail):

```bash
python -m app.worker --watch --fix_email seuemail@dominio.com
```

Forcar envio para um e-mail fixo (ignora e-mail da imagem):

```bash
python -m app.worker --watch --only_email seuemail@dominio.com
```

## 6) Seguranca recomendada

- Use `AUTOMATION_TOKEN` no `.env` e envie no header `X-Automation-Key`.
- Use App Password (Gmail/Outlook), nao senha principal.
- Prefira revisar antes de enviar (`auto_send=false`).
