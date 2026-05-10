# ESF Assistente Chatbot

Um chatbot inteligente para assistência ESF (Estratégia Saúde da Família), desenvolvido com backend em FastAPI e frontend em React.

## 📋 Estrutura do Projeto

```
chatbot_esf/
├── back/          # Backend FastAPI
├── front/         # Frontend React + TypeScript
└── templates/     # Documentação e diagramas
```

## 🚀 Como Iniciar

### Backend

1. Instale as dependências:
```bash
cd back
pip install -r requirements.txt
```

2. Execute a API:
```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`

### Frontend

1. Instale as dependências:
```bash
cd front/chatbot_esf
npm install
```

2. Execute em modo desenvolvimento:
```bash
npm run dev
```

3. Ou faça build para produção:
```bash
npm run build
```

## 📚 Principais Endpoints

- `GET /health` - Verificar saúde da API
- `GET /api/chat/start` - Iniciar conversa
- `POST /api/chat` - Enviar mensagem

## 🛠️ Tecnologias

**Backend:**
- FastAPI
- Uvicorn

**Frontend:**
- React 19
- TypeScript
- Vite
- Leaflet (mapas)

## 📖 Documentação

Veja os READMEs específicos em cada pasta:
- [Backend](./back/README.md)
- [Frontend](./front/chatbot_esf/README.md)