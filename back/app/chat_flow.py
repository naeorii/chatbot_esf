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
class FlowMap:
    latitude: float
    longitude: float
    label: str
    address: str


@dataclass(frozen=True)
class FlowResult:
    current_node: str
    messages: List[str]
    options: List[FlowOption]
    ended: bool = False
    map: Optional[FlowMap] = None


UBS_ADDRESS_MAP = FlowMap(
    latitude=-29.712747,
    longitude=-53.8217719,
    label="ESF Sao Carlos/Urlandia",
    address="R. Agostinho Scolari, 546 - Urlândia, Santa Maria - RS, 97070-030",
)


ROOT_OPTIONS = [
    FlowOption("informacoes", "Informações"),
    FlowOption("horario", "Horario de funcionamento"),
    FlowOption("agendamento", "Agendamento"),

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
    FlowOption("informacoes", "Ver outras informações"),
    FlowOption("voltar_inicio", "Voltar ao início"),
    FlowOption("encerrar", "Encerrar atendimento"),
]

CONTENT_RESPONSES: Dict[str, str] = {
    "coleta": (
        "A coleta laboratorial (LABVIDA) com agendamento prévio acontece as terças e "
        "quintas-feiras, às 8h. Lembre-se do jejum quando indicado pelo médico e leve "
        "seu pedido de exame e Cartão SUS."
    ),
    "grupos": (
        "Temos 4 grupos abertos a comunidade:\n"
        "- Amigos da Saúde: segundas, 8h\n"
        "- Vida Leve: terças, 14h\n"
        "- Fisioterapia UFN: quartas, 8h\n"
        "- Gestantes: mensal, confirme a data na recepção"
    ),
    "testes_rapidos": (
        "Testes rápidos acontecem todos os dias, das 8h às 11h e das 13h às 16h. "
        "Estão disponíveis HIV, sifilis, hepatites B e C e gravidez, conforme protocolo."
    ),
    "servicos": (
        "Serviços disponiveis:\n"
        "- Consultas médicas\n"
        "- Consultas de enfermagem\n"
        "- Puericultura e pré-natal\n"
        "- Coleta de citopatológico\n"
        "- Vacinacão\n"
        "- Coleta laboratorial\n"
        "- Odontologia\n"
        "- Curativos e procedimentos\n"
        "- Testes rápidos\n"
        "- Visitas domiciliares\n"
        "- Grupos de educação em saúde\n"
        "- Renovação de receitas"
    ),
    "equipe": (
        "Nossa equipe tem 2 médicos(as), 2 enfermeiros(as), 2 técnicos(as) de enfermagem, "
        "8 agentes comunitários de saúde e 1 dentista, com média de 40 horas semanais."
    ),
    "endereco": (
        "A ESF fica na R. Agostinho Scolari, 546 - Urlândia, Santa Maria - RS, "
        "97070-030, Brasil."
    ),
    "horario": (
        "Atendemos de segunda a sexta-feira, das 8h ao meio-dia e das 13h às 17h.\n"
        "Quartas-feiras à tarde a unidade esta fechada para reunião de equipe.\n"
        "Não há atendimento aos fins de semana e feriados. Em emergências, ligue 192 (SAMU).\n"
        "Importante: sempre traga um documento de identificação (RG, CPF e Cartao SUS) "
        "para consultas, retirada de medicamentos e atualização de cadastro."
    ),
    "medicamentos": (
        "Renovação de receitas deve ser agendada previamente na recepção ou pelo telefone "
        "(55) 3174-1588. Leve a última receita e o Cartao SUS."
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
            "Olá! Sou o assistente da ESF São Carlos/Urlândia. Como posso ajudar? Escolha uma das opções abaixo."
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

    if action in {"agendamento", "agendamento_indisponivel"}:
        return FlowResult(
            current_node=START_NODE,
            messages=[
                "Por enquanto, o chatbot ainda não realiza agendamentos.",
                "Posso ajudar com informações da unidade enquanto isso.",
            ],
            options=ROOT_OPTIONS,
        )

    if action in CONTENT_RESPONSES:
        if action == "endereco":
            return FlowResult(
                current_node=AFTER_INFO_NODE,
                messages=[CONTENT_RESPONSES[action], "Deseja mais alguma coisa?"],
                options=AFTER_INFO_OPTIONS,
                map=UBS_ADDRESS_MAP,
            )

        return FlowResult(
            current_node=AFTER_INFO_NODE,
            messages=[CONTENT_RESPONSES[action], "Deseja mais alguma coisa?"],
            options=AFTER_INFO_OPTIONS,
        )

    return FlowResult(
        current_node=START_NODE,
        messages=["Nao encontrei essa opção. Escolha uma das opções abaixo para continuar."],
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
