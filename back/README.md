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
## Banco de agendamentos

Localmente, os agendamentos ficam em `back/data/agendamentos.sqlite3`.

Em produção, configure um disco persistente no Render e defina uma destas variáveis de ambiente:

- `APPOINTMENTS_DB_PATH=/var/data/agendamentos.sqlite3`
- ou `APPOINTMENTS_DATA_DIR=/var/data`

Assim os agendamentos excluídos não voltam quando o serviço reiniciar.
