from dataclasses import dataclass
from typing import Dict, List, Optional
import unicodedata
import re


START_NODE = "inicio"
INFO_NODE = "informacoes"
AFTER_INFO_NODE = "mais_alguma_coisa"
SCHEDULING_NODE = "agendamento"
SCHEDULING_NAME_NODE = "agendamento_nome"
SCHEDULING_DOCUMENT_NODE = "agendamento_documento"
SCHEDULING_SIGSS_PATIENT_NODE = "agendamento_verificacao_sigss"
SCHEDULING_SIGSS_SCHEDULE_NODE = "agendamento_agenda_sigss"
SCHEDULING_SLOT_NODE = "agendamento_horario"
SCHEDULING_CONFIRM_NODE = "agendamento_confirmacao"
SCHEDULING_SAVE_NODE = "agendamento_gravacao_sigss"
AFTER_SCHEDULING_NODE = "agendamento_finalizado"
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
    FlowOption("horario", "Horário de funcionamento"),
    FlowOption("agendamento", "Agendamento"),
]

INFO_OPTIONS = [
    FlowOption("coleta", "Coleta laboratorial"),
    FlowOption("grupos", "Grupos da comunidade"),
    FlowOption("testes_rapidos", "Curativos e testes rápidos"),
    FlowOption("servicos", "Serviços"),
    FlowOption("equipe", "Equipe"),
    FlowOption("endereco", "Endereço"),
    FlowOption("medicamentos", "Medicamentos/Receitas"),
    FlowOption("voltar_inicio", "Voltar ao início"),
]

AFTER_INFO_OPTIONS = [
    FlowOption("informacoes", "Ver outras informações"),
    FlowOption("voltar_inicio", "Voltar ao início"),
    FlowOption("encerrar", "Encerrar atendimento"),
]

SCHEDULING_OPTIONS = [
    FlowOption("agendar_dentista", "Dentista"),
    FlowOption("agendar_enfermagem", "Enfermagem"),
    FlowOption("agendar_medico", "Médico"),
    FlowOption("voltar_inicio", "Voltar ao início"),
]

AFTER_SCHEDULING_OPTIONS = [
    FlowOption("informacoes", "Ver informações da unidade"),
    FlowOption("voltar_inicio", "Voltar ao início"),
    FlowOption("encerrar", "Encerrar atendimento"),
]

SCHEDULING_SERVICE_LABELS = {
    "agendar_dentista": "dentista",
    "agendar_enfermagem": "enfermagem",
    "agendar_medico": "médico",
}

SIGSS_PATIENT_RESULT_OPTIONS = [
    FlowOption("sigss_paciente_vinculado", "Cadastro ativo na ESF"),
    FlowOption("sigss_paciente_nao_vinculado", "Não cadastrado na ESF"),
]

SIGSS_SCHEDULE_RESULT_OPTIONS = [
    FlowOption("sigss_horarios_disponiveis", "Há horários disponíveis"),
    FlowOption("sigss_sem_horarios", "Sem horários disponíveis"),
    FlowOption("sigss_erro_consulta", "Erro ao consultar SIGSS"),
]

SCHEDULING_SLOT_OPTIONS = [
    FlowOption("agendamento_horario_1", "Segunda-feira, 8h"),
    FlowOption("agendamento_horario_2", "Terça-feira, 14h"),
    FlowOption("agendamento_horario_3", "Quinta-feira, 10h"),
]

SCHEDULING_SLOT_LABELS = {
    "agendamento_horario_1": "segunda-feira, 8h",
    "agendamento_horario_2": "terça-feira, 14h",
    "agendamento_horario_3": "quinta-feira, 10h",
}

SCHEDULING_CONFIRM_OPTIONS = [
    FlowOption("agendamento_confirmar", "Confirmar agendamento"),
    FlowOption("agendamento_trocar_horario", "Escolher outro horário"),
    FlowOption("agendamento_cancelar", "Cancelar"),
]

SIGSS_SAVE_RESULT_OPTIONS = [
    FlowOption("sigss_gravacao_sucesso", "Gravou com sucesso"),
    FlowOption("sigss_erro_gravacao", "Erro ao gravar no SIGSS"),
]

SCHEDULING_SERVICE_INTENTS = {
    "medico": "agendar_medico",
    "clinico": "agendar_medico",
    "consulta medica": "agendar_medico",
    "enfermagem": "agendar_enfermagem",
    "enfermeiro": "agendar_enfermagem",
    "enfermeira": "agendar_enfermagem",
    "dentista": "agendar_dentista",
    "odontologia": "agendar_dentista",
}

CONTENT_RESPONSES: Dict[str, str] = {
    "coleta": (
        "A coleta laboratorial (LABVIDA) sem agendamento prévio acontece as terças e "
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
        "Estão disponíveis HIV, sífilis, hepatites B e C e gravidez, conforme protocolo."
    ),
    "servicos": (
        "Serviços disponíveis:\n"
        "- Consultas médicas\n"
        "- Consultas de enfermagem\n"
        "- Puericultura e pré-natal\n"
        "- Coleta de citopatológico\n"
        "- Vacinação\n"
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
        "Quartas-feiras à tarde a unidade está fechada para reunião de equipe.\n"
        "Não há atendimento aos fins de semana e feriados. Em emergências, ligue 192 (SAMU).\n"
        "Importante: sempre traga um documento de identificação (RG, CPF e Cartão SUS) "
        "para consultas, retirada de medicamentos e atualização de cadastro."
    ),
    "medicamentos": (
        "Renovação de receitas deve ser agendada previamente na recepção ou pelo telefone "
        "(55) 3174-1588. Leve a última receita e o Cartão SUS."
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

GREETING_PATTERNS = [
    r"\boi+\b",
    r"\bola+\b",
    r"\bolá+\b",
    r"\be ai+\b",
    r"\bbom dia+\b",
    r"\bboa tarde+\b",
    r"\bboa noite+\b",
]


def start_response() -> FlowResult:
    return FlowResult(
        current_node=START_NODE,
        messages=[
            "Olá! Sou o assistente da ESF São Carlos/Urlândia. Como posso ajudar? Escolha uma das opções abaixo."
        ],
        options=ROOT_OPTIONS,
    )


def handle_chat(
    message: Optional[str] = None,
    option_id: Optional[str] = None,
    current_node: Optional[str] = None,
) -> FlowResult:
    if current_node and current_node.startswith(SCHEDULING_NAME_NODE):
        return handle_scheduling_name(current_node, message, option_id)

    if current_node and current_node.startswith(SCHEDULING_DOCUMENT_NODE):
        return handle_scheduling_document(current_node, message, option_id)

    if message and is_greeting(message):
        return start_response()

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
            current_node=SCHEDULING_NODE,
            messages=[
                "Qual agendamento deseja realizar?",
            ],
            options=SCHEDULING_OPTIONS,
        )

    if action in SCHEDULING_SERVICE_LABELS:
        return FlowResult(
            current_node=state_with_payload(SCHEDULING_NAME_NODE, action),
            messages=[
                f"Você selecionou {SCHEDULING_SERVICE_LABELS[action]}.",
                "Digite o nome completo do paciente.",
            ],
            options=[],
        )

    if action == "sigss_paciente_nao_vinculado":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=[
                "Desculpe, mas a consulta não pode ser agendada pois o paciente não está cadastrado ou vinculado a esta unidade.",
                "Realize o cadastro na recepção da ESF antes de realizar o agendamento remoto.",
                "Deseja mais alguma coisa?",
            ],
            options=AFTER_SCHEDULING_OPTIONS,
        )

    if action == "sigss_paciente_vinculado":
        return FlowResult(
            current_node=SCHEDULING_SIGSS_SCHEDULE_NODE,
            messages=[
                "Backend verifica no SIGSS a agenda do profissional conforme o tipo escolhido.",
                "No protótipo, selecione o retorno dessa consulta.",
            ],
            options=SIGSS_SCHEDULE_RESULT_OPTIONS,
        )

    if action == "sigss_sem_horarios":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=[
                "Não há horários disponíveis no SIGSS para esse tipo de atendimento no momento.",
                "Posso tentar outro tipo de agendamento ou voltar ao início.",
                "Deseja mais alguma coisa?",
            ],
            options=AFTER_SCHEDULING_OPTIONS,
        )

    if action == "sigss_erro_consulta":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=[
                "Não consegui consultar o SIGSS agora.",
                "Não vou prometer uma vaga sem confirmação do sistema. Oriente o paciente a entrar em contato com a recepção ou tentar novamente mais tarde.",
                "Posso ajudar com mais alguma coisa?",
            ],
            options=AFTER_SCHEDULING_OPTIONS,
        )

    if action == "sigss_horarios_disponiveis":
        return FlowResult(
            current_node=SCHEDULING_SLOT_NODE,
            messages=[
                "Bot mostra os horários disponíveis encontrados no SIGSS.",
                "Escolha uma opção para continuar.",
            ],
            options=SCHEDULING_SLOT_OPTIONS,
        )

    if action in SCHEDULING_SLOT_LABELS:
        return FlowResult(
            current_node=state_with_payload(SCHEDULING_CONFIRM_NODE, action),
            messages=[
                f"Você escolheu {SCHEDULING_SLOT_LABELS[action]}.",
                "Confirme os dados do agendamento: paciente informado, serviço escolhido, profissional disponível, data e horário.",
            ],
            options=SCHEDULING_CONFIRM_OPTIONS,
        )

    if action == "agendamento_trocar_horario":
        return FlowResult(
            current_node=SCHEDULING_SLOT_NODE,
            messages=["Escolha outro horário disponível."],
            options=SCHEDULING_SLOT_OPTIONS,
        )

    if action == "agendamento_cancelar":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=["Agendamento cancelado. Deseja mais alguma coisa?"],
            options=AFTER_SCHEDULING_OPTIONS,
        )

    if action == "agendamento_confirmar":
        return FlowResult(
            current_node=SCHEDULING_SAVE_NODE,
            messages=[
                "Backend grava o agendamento no SIGSS e aguarda protocolo/status.",
                "No protótipo, selecione o retorno da gravação.",
            ],
            options=SIGSS_SAVE_RESULT_OPTIONS,
        )

    if action == "sigss_gravacao_sucesso":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=[
                "Agendamento confirmado no SIGSS.",
                "Leve RG, CPF e Cartão SUS no dia do atendimento. Protocolo: SIGSS-AGD-0001.",
                "Deseja mais alguma coisa?",
            ],
            options=AFTER_SCHEDULING_OPTIONS,
        )

    if action == "sigss_erro_gravacao":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=[
                "O SIGSS não confirmou a gravação do agendamento.",
                "Não vou confirmar a vaga sem retorno do sistema. Oriente o paciente a entrar em contato com a unidade ou tentar novamente.",
                "Deseja mais alguma coisa?",
            ],
            options=AFTER_SCHEDULING_OPTIONS,
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
        messages=["Não encontrei essa opção. Escolha uma das opções abaixo para continuar."],
        options=ROOT_OPTIONS,
    )


def detect_intent(message: str) -> str:
    normalized = normalize(message)
    if not normalized:
        return "voltar_inicio"

    if is_greeting(message):
        return "voltar_inicio"

    for keyword, action in SCHEDULING_SERVICE_INTENTS.items():
        if keyword in normalized:
            return action

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


def is_greeting(message: str) -> bool:
    normalized = normalize(message)
    return any(re.search(pattern, normalized) for pattern in GREETING_PATTERNS)


def is_valid_patient_name(message: str) -> bool:
    normalized = normalize(message)
    tokens = re.findall(r"[a-z]+", normalized)
    name_tokens = [token for token in tokens if token not in {"da", "de", "di", "do", "das", "dos", "e"}]
    blocked_terms = set(SCHEDULING_KEYWORDS)
    blocked_terms.update(SCHEDULING_SERVICE_INTENTS)
    blocked_terms.update(keyword for keywords in INTENT_KEYWORDS.values() for keyword in keywords)

    if is_greeting(message) or len(name_tokens) < 2:
        return False

    return not any(term in normalized for term in blocked_terms)


def looks_like_patient_name(message: str) -> bool:
    normalized = normalize(message)
    tokens = re.findall(r"[a-z]+", normalized)
    name_tokens = [token for token in tokens if token not in {"da", "de", "di", "do", "das", "dos", "e"}]
    return len(name_tokens) >= 1 and not re.search(r"\d", normalized)


def handle_scheduling_name(
    current_node: str,
    message: Optional[str],
    option_id: Optional[str],
) -> FlowResult:
    if option_id:
        return handle_chat(option_id=option_id)

    if not (message or "").strip():
        return FlowResult(
            current_node=current_node,
            messages=["Digite o nome completo do paciente para continuar."],
            options=[],
        )

    if not is_valid_patient_name(message or ""):
        return FlowResult(
            current_node=current_node,
            messages=["Nao identifiquei um nome completo de paciente. Digite novamente o nome completo para continuar."],
            options=[],
        )

    service_action = state_payload(current_node)
    return FlowResult(
        current_node=state_with_payload(SCHEDULING_DOCUMENT_NODE, service_action),
        messages=["Digite o CPF, RG ou Cartão SUS do paciente."],
        options=[],
    )


def handle_scheduling_document(
    current_node: str,
    message: Optional[str],
    option_id: Optional[str],
) -> FlowResult:
    if option_id:
        return handle_chat(option_id=option_id)

    if not (message or "").strip():
        return FlowResult(
            current_node=current_node,
            messages=["Digite o CPF, RG ou Cartão SUS para consultar o cadastro no SIGSS."],
            options=[],
        )

    if looks_like_patient_name(message or ""):
        return FlowResult(
            current_node=current_node,
            messages=["Nao identifiquei CPF, RG ou Cartao SUS. Digite novamente um documento do paciente para continuar."],
            options=[],
        )

    return FlowResult(
        current_node=SCHEDULING_SIGSS_PATIENT_NODE,
        messages=[
            "Backend consulta paciente no SIGSS pelo CPF, RG ou Cartão SUS informado.",
            "No protótipo, selecione o resultado da verificação de cadastro.",
        ],
        options=SIGSS_PATIENT_RESULT_OPTIONS,
    )


def state_with_payload(node: str, value: str) -> str:
    return f"{node}:{value}"


def state_payload(current_node: str) -> str:
    parts = current_node.split(":", 1)
    return parts[1] if len(parts) == 2 else ""
