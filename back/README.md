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
