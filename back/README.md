# ESF Assistente API

API FastAPI baseada no fluxograma `templates/ESF_Assistente.drawio.html`.

## Rodar localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Endpoints principais:

- `GET /health`
- `GET /api/chat/start`
- `POST /api/chat`
- `GET /webhooks/whatsapp` - verificação do webhook pela Meta
- `POST /webhooks/whatsapp` - recebimento de mensagens do WhatsApp
- `GET /politica-de-privacidade` - política pública exigida pela Meta
- `GET /exclusao-de-dados` - instruções públicas para solicitações de exclusão
- `GET /termos-de-uso` - termos públicos do assistente

## WhatsApp Cloud API

O webhook usa o mesmo fluxo de conversa da simulação React. Configure as variáveis de
`.env.example` no ambiente de produção, sem salvar tokens ou segredos no repositório.

- `META_VERIFY_TOKEN`: segredo definido por você e repetido no painel da Meta.
- `META_APP_SECRET`: chave secreta do app usada para validar a assinatura do webhook.
- `META_WHATSAPP_TOKEN`: token de acesso do usuário do sistema.
- `META_PHONE_NUMBER_ID`: identificador do número remetente no WhatsApp.
- `PUBLIC_BASE_URL`: URL HTTPS pública deste backend, sem barra no final.
- `META_GRAPH_API_VERSION`: versão da Graph API; o padrão atual do projeto é `v25.0`.

O serviço responde menus interativos, mantém o estado da conversa no SQLite e impede o
processamento duplicado do mesmo ID de mensagem.
## Banco de agendamentos

Localmente, os agendamentos ficam em `back/data/agendamentos.sqlite3`.

Em produção, configure um disco persistente no Render e defina uma destas variáveis de ambiente:

- `APPOINTMENTS_DB_PATH=/var/data/agendamentos.sqlite3`
- ou `APPOINTMENTS_DATA_DIR=/var/data`

Assim os agendamentos excluídos não voltam quando o serviço reiniciar.
