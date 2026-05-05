from dataclasses import dataclass
from typing import Dict, List, Optional
import unicodedata


START_NODE = "inicio"
INFO_NODE = "informacoes"
AFTER_INFO_NODE = "mais_alguma_coisa"
END_NODE = "encerrado"


@dataclass(frozen=True)
class FlowOption:
    id: str
    label: str


@dataclass(frozen=True)
class FlowResult:
    current_node: str
    messages: List[str]
    options: List[FlowOption]
    ended: bool = False


ROOT_OPTIONS = [
    FlowOption("informacoes", "Informacoes"),
    FlowOption("horario", "Horario de funcionamento"),
]

INFO_OPTIONS = [
    FlowOption("coleta", "Coleta laboratorial"),
    FlowOption("grupos", "Grupos da comunidade"),
    FlowOption("testes_rapidos", "Curativos e testes rapidos"),
    FlowOption("servicos", "Servicos"),
    FlowOption("equipe", "Equipe"),
    FlowOption("endereco", "Endereco"),
    FlowOption("medicamentos", "Medicamentos/Receitas"),
    FlowOption("voltar_inicio", "Voltar ao inicio"),
]

AFTER_INFO_OPTIONS = [
    FlowOption("informacoes", "Ver outras informacoes"),
    FlowOption("voltar_inicio", "Voltar ao inicio"),
    FlowOption("encerrar", "Encerrar atendimento"),
]

CONTENT_RESPONSES: Dict[str, str] = {
    "coleta": (
        "A coleta laboratorial (LABVIDA) com agendamento previo acontece as tercas e "
        "quintas-feiras, as 8h. Lembre-se do jejum quando indicado pelo medico e leve "
        "seu pedido de exame e Cartao SUS."
    ),
    "grupos": (
        "Temos 4 grupos abertos a comunidade:\n"
        "- Amigos da Saude: segundas, 8h\n"
        "- Vida Leve: tercas, 14h\n"
        "- Fisioterapia UFN: quartas, 8h\n"
        "- Gestantes: mensal, confirme a data na recepcao"
    ),
    "testes_rapidos": (
        "Testes rapidos acontecem todos os dias, das 8h as 11h e das 13h as 16h. "
        "Estao disponiveis HIV, sifilis, hepatites B e C e gravidez, conforme protocolo."
    ),
    "servicos": (
        "Servicos disponiveis:\n"
        "- Consultas medicas\n"
        "- Consultas de enfermagem\n"
        "- Puericultura e pre-natal\n"
        "- Coleta de citopatologico\n"
        "- Vacinacao\n"
        "- Coleta laboratorial\n"
        "- Odontologia\n"
        "- Curativos e procedimentos\n"
        "- Testes rapidos\n"
        "- Visitas domiciliares\n"
        "- Grupos de educacao em saude\n"
        "- Renovacao de receitas"
    ),
    "equipe": (
        "Nossa equipe tem 2 medicos(as), 2 enfermeiros(as), 2 tecnicos(as) de enfermagem, "
        "8 agentes comunitarios de saude e 1 dentista, com media de 40 horas semanais."
    ),
    "endereco": (
        "A ESF fica na R. Agostinho Scolari, 546 - Urlandia, Santa Maria - RS, "
        "97070-030, Brasil."
    ),
    "horario": (
        "Atendemos de segunda a sexta-feira, das 8h ao meio-dia e das 13h as 17h.\n"
        "Quartas-feiras a tarde a unidade esta fechada para reuniao de equipe.\n"
        "Nao ha atendimento aos fins de semana e feriados. Em emergencias, ligue 192 (SAMU).\n"
        "Importante: sempre traga um documento de identificacao (RG, CPF e Cartao SUS) "
        "para consultas, retirada de medicamentos e atualizacao de cadastro."
    ),
    "medicamentos": (
        "Renovacao de receitas deve ser agendada previamente na recepcao ou pelo telefone "
        "(55) 3174-1588. Leve a ultima receita e o Cartao SUS."
    ),
}


INTENT_KEYWORDS = {
    "informacoes": ["informacao", "informacoes", "opcoes", "assunto", "saber"],
    "horario": ["horario", "hora", "funcionamento", "aberto", "abre", "fecha", "fechado"],
    "coleta": ["coleta", "laboratorio", "laboratorial", "exame", "exames", "labvida"],
    "grupos": ["grupo", "grupos", "gestante", "gestantes", "vida leve", "fisioterapia"],
    "testes_rapidos": ["teste", "testes", "rapido", "rapidos", "hiv", "sifilis", "hepatite", "curativo", "gravidez"],
    "servicos": ["servico", "servicos", "disponivel", "disponiveis", "vacina", "vacinacao", "odontologia"],
    "equipe": ["equipe", "profissional", "profissionais", "enfermeiro", "dentista", "agente"],
    "endereco": ["endereco", "localizacao", "local", "onde", "mapa", "rua"],
    "medicamentos": ["medicamento", "medicamentos", "receita", "receitas", "renovacao", "remedio"],
    "voltar_inicio": ["inicio", "menu", "voltar", "recomecar"],
    "encerrar": ["encerrar", "finalizar", "sair", "tchau", "obrigado", "obrigada"],
}

SCHEDULING_KEYWORDS = [
    "agendamento",
    "agendar",
    "consulta",
    "marcar",
    "clinico",
    "medico",
    "dentista",
]


def start_response() -> FlowResult:
    return FlowResult(
        current_node=START_NODE,
        messages=[
            "Ola! Sou o assistente da ESF Sao Carlos/Urlandia. Como posso ajudar? Escolha uma das opcoes abaixo."
        ],
        options=ROOT_OPTIONS,
    )


def handle_chat(message: Optional[str] = None, option_id: Optional[str] = None) -> FlowResult:
    action = option_id or detect_intent(message or "")

    if action == "voltar_inicio":
        return start_response()

    if action == "encerrar":
        return FlowResult(
            current_node=END_NODE,
            messages=["Atendimento encerrado. Obrigado pelo contato!"],
            options=[],
            ended=True,
        )

    if action == "informacoes":
        return FlowResult(
            current_node=INFO_NODE,
            messages=["Selecione o assunto do qual deseja saber."],
            options=INFO_OPTIONS,
        )

    if action == "agendamento_indisponivel":
        return FlowResult(
            current_node=START_NODE,
            messages=[
                "Por enquanto, o chatbot ainda nao realiza agendamentos.",
                "Posso ajudar com informacoes da unidade enquanto isso.",
            ],
            options=ROOT_OPTIONS,
        )

    if action in CONTENT_RESPONSES:
        return FlowResult(
            current_node=AFTER_INFO_NODE,
            messages=[CONTENT_RESPONSES[action], "Deseja mais alguma coisa?"],
            options=AFTER_INFO_OPTIONS,
        )

    return FlowResult(
        current_node=START_NODE,
        messages=["Nao encontrei essa opcao. Escolha uma das opcoes abaixo para continuar."],
        options=ROOT_OPTIONS,
    )


def detect_intent(message: str) -> str:
    normalized = normalize(message)
    if not normalized:
        return "voltar_inicio"

    if any(keyword in normalized for keyword in SCHEDULING_KEYWORDS):
        return "agendamento_indisponivel"

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent

    return "fallback"


def normalize(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in without_accents if not unicodedata.combining(char))
    return without_accents.casefold().strip()
