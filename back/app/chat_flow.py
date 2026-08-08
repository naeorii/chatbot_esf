import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, quote, unquote, urlencode

from app.appointment_store import is_appointment_slot_booked


START_NODE = "inicio"
INFO_NODE = "informacoes"
AFTER_INFO_NODE = "mais_alguma_coisa"
SCHEDULING_NODE = "agendamento"
SCHEDULING_NAME_NODE = "agendamento_nome"
SCHEDULING_DOCUMENT_NODE = "agendamento_documento"
SCHEDULING_SLOT_NODE = "agendamento_horario"
SCHEDULING_CONFIRM_NODE = "agendamento_confirmacao"
AFTER_SCHEDULING_NODE = "agendamento_finalizado"
END_NODE = "encerrado"
UNIT_SITE_URL = "https://urlandiaesf.lovable.app/"
UNIT_FACEBOOK_URL = (
    "https://www.facebook.com/people/Esf-Url%C3%A2ndia/61579852984607/?locale=pt_BR"
)
SCHEDULING_INSURANCE_LABEL = "SUS"
SCHEDULING_LOOKAHEAD_DAYS = 7
SCHEDULING_SHIFT_TIMES = {
    "manha": "10:00",
    "tarde": "14:00",
}
INFO_SUGGESTION_MESSAGE = (
    "Para acessar mais informações, visite o site da unidade: "
    f"{UNIT_SITE_URL} ou acompanhe o Facebook: {UNIT_FACEBOOK_URL}"
)


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
class FlowImage:
    url: str
    alt: str
    caption: Optional[str] = None


@dataclass(frozen=True)
class FlowAppointment:
    patient_name: str
    document: str
    service: str
    professional: str
    appointment_date: str
    appointment_time: str


@dataclass(frozen=True)
class FlowResult:
    current_node: str
    messages: List[str]
    options: List[FlowOption]
    ended: bool = False
    map: Optional[FlowMap] = None
    image: Optional[FlowImage] = None
    appointment: Optional[FlowAppointment] = None


UBS_ADDRESS_MAP = FlowMap(
    latitude=-29.712747,
    longitude=-53.8217719,
    label="ESF Sao Carlos/Urlândia",
    address="R. Agostinho Scolari, 546 - Urlândia, Santa Maria - RS, 97070-030",
)

AREAS_MAP_IMAGE = FlowImage(
    url="/templates/mapaAreas.jpeg",
    alt="Mapa do territorio das áreas 19 e 20 da ESF Sao Carlos/Urlândia",
    caption="Mapa do território das áreas 19 e 20",
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
    FlowOption("areas_atendidas", "Áreas atendidas"),
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
    FlowOption("agendamento", "Realizar outro agendamento"),
    FlowOption("informacoes", "Ver informações da unidade"),
    FlowOption("voltar_inicio", "Voltar ao início"),
    FlowOption("encerrar", "Encerrar atendimento"),
]

SCHEDULING_SERVICE_LABELS = {
    "agendar_dentista": "dentista",
    "agendar_enfermagem": "enfermagem",
    "agendar_medico": "médico",
}

SCHEDULING_SERVICE_DISPLAY_LABELS = {
    "agendar_dentista": "Dentista",
    "agendar_enfermagem": "Enfermagem",
    "agendar_medico": "Médico",
}

SCHEDULING_PROFESSIONAL_LABELS = {
    "agendar_dentista": "Cirurgião-dentista da ESF São Carlos/Urlândia",
    "agendar_enfermagem": "Equipe de enfermagem da ESF São Carlos/Urlândia",
    "agendar_medico": "Equipe médica da ESF São Carlos/Urlândia",
}

SCHEDULING_SLOT_OPTION_PREFIX = "agendamento_horario_"
SCHEDULING_WEEKDAY_LABELS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]
SCHEDULING_SHIFT_LABELS = {
    "manha": "Manhã",
    "tarde": "Tarde",
}

SCHEDULING_CONFIRM_OPTIONS = [
    FlowOption("agendamento_confirmar", "Confirmar agendamento"),
    FlowOption("agendamento_trocar_horario", "Escolher outro horário"),
    FlowOption("agendamento_cancelar", "Cancelar"),
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
        "A coleta laboratorial (LABVIDA) sem agendamento prévio acontece às terças e "
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
    "areas_atendidas": (
        "A ESF São Carlos/Urlândia atende os territórios das Áreas 19 e 20, definidos "
        "pela Secretaria Municipal de Saúde para organizar o acompanhamento das famílias. "
        "A Área 19 tem aproximadamente 3 mil pessoas cadastradas e a Área 20 cerca de "
        "2.500 pessoas. Cada área conta com equipe responsável por consultas médicas e "
        "de enfermagem, visitas domiciliares, acompanhamento de gestantes, crianças, "
        "idosos e pessoas com doenças crônicas, prevenção em saúde e atualização de cadastros."
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


def content_response_messages(action: str) -> List[str]:
    return [
        CONTENT_RESPONSES[action],
        INFO_SUGGESTION_MESSAGE,
        "Deseja mais alguma coisa?",
    ]


INTENT_KEYWORDS = {
    "informacoes": ["informacao", "informacoes", "opcoes", "assunto", "saber"],
    "horario": ["horario", "hora", "funcionamento", "aberto", "abre", "fecha", "fechado"],
    "coleta": ["coleta", "laboratorio", "laboratorial", "exame", "exames", "labvida"],
    "grupos": ["grupo", "grupos", "gestante", "gestantes", "vida leve", "fisioterapia"],
    "testes_rapidos": ["teste", "testes", "rapido", "rapidos", "hiv", "sifilis", "hepatite", "curativo", "gravidez"],
    "servicos": ["servico", "servicos", "disponivel", "disponiveis", "vacina", "vacinacao", "odontologia"],
    "equipe": ["equipe", "profissional", "profissionais", "enfermeiro", "dentista", "agente"],
    "endereco": ["endereco", "localizacao", "local", "onde", "mapa", "rua"],
    "areas_atendidas": ["area", "areas", "area 19", "area 20", "territorio", "territorios", "abrangencia", "atendidas"],
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


def scheduling_slot_options(today: Optional[date] = None) -> List[FlowOption]:
    start_date = today or date.today()
    options: List[FlowOption] = []

    for offset in range(SCHEDULING_LOOKAHEAD_DAYS + 1):
        slot_date = start_date + timedelta(days=offset)
        if slot_date.weekday() >= 5:
            continue

        for shift in SCHEDULING_SHIFT_TIMES:
            if slot_date.weekday() == 2 and shift == "tarde":
                continue

            slot_time = SCHEDULING_SHIFT_TIMES[shift]
            if is_appointment_slot_booked(slot_date.isoformat(), slot_time):
                continue

            options.append(
                FlowOption(
                    slot_option_id(slot_date, shift),
                    f"{date_display_label(slot_date, start_date)} - "
                    f"{SCHEDULING_SHIFT_LABELS[shift]}, {format_date(slot_date)}, "
                    f"{slot_time}",
                )
            )

    return options


def slot_is_available(slot_id: str) -> bool:
    details = slot_details(slot_id)
    if not details:
        return False

    return not is_appointment_slot_booked(details["date_iso"], details["time"])


def scheduling_slot_selection_result(payload: Dict[str, str], messages: List[str]) -> FlowResult:
    options = scheduling_slot_options()
    if options:
        return FlowResult(
            current_node=state_with_schedule_payload(SCHEDULING_SLOT_NODE, payload),
            messages=messages,
            options=options,
        )

    return FlowResult(
        current_node=AFTER_SCHEDULING_NODE,
        messages=[
            "No momento não encontrei horários disponíveis para os próximos dias.",
            "Deseja mais alguma coisa?",
        ],
        options=AFTER_SCHEDULING_OPTIONS,
    )


def slot_option_id(slot_date: date, shift: str) -> str:
    return f"{SCHEDULING_SLOT_OPTION_PREFIX}{slot_date:%Y%m%d}_{shift}"


def is_scheduling_slot_action(action: str) -> bool:
    return slot_details(action) is not None


def slot_label(slot_id: str) -> str:
    details = slot_details(slot_id)
    if not details:
        return "horário selecionado"

    return f"{details['weekday']}, {details['date']} às {details['time']}"


def slot_details(slot_id: str) -> Optional[Dict[str, str]]:
    match = re.fullmatch(rf"{SCHEDULING_SLOT_OPTION_PREFIX}(\d{{8}})_(manha|tarde)", slot_id)
    if not match:
        return None

    raw_date, shift = match.groups()
    slot_date = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:]))
    return {
        "date_iso": slot_date.isoformat(),
        "date": format_date(slot_date),
        "time": SCHEDULING_SHIFT_TIMES[shift],
        "shift": SCHEDULING_SHIFT_LABELS[shift],
        "weekday": SCHEDULING_WEEKDAY_LABELS[slot_date.weekday()],
    }


def date_display_label(slot_date: date, today: date) -> str:
    if slot_date == today:
        return "Hoje"

    if slot_date == today + timedelta(days=1):
        return "Amanhã"

    return SCHEDULING_WEEKDAY_LABELS[slot_date.weekday()].capitalize()


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def scheduling_confirmation_message(current_node: Optional[str]) -> str:
    payload = schedule_payload(current_node or "")
    patient_name = payload.get("name", "paciente").strip()
    service_action = payload.get("service", "")
    slot_id = payload.get("slot", "")
    slot = slot_details(slot_id) or {
        "date_iso": date.today().isoformat(),
        "date": format_date(date.today()),
        "time": SCHEDULING_SHIFT_TIMES["manha"],
        "shift": SCHEDULING_SHIFT_LABELS["manha"],
    }
    service_label = SCHEDULING_SERVICE_DISPLAY_LABELS.get(service_action, "Consulta")
    professional_label = SCHEDULING_PROFESSIONAL_LABELS.get(
        service_action,
        "Equipe da ESF São Carlos/Urlândia",
    )

    return (
        f"Olá, {patient_name.upper()} você possui um agendamento conosco.\n\n"
        f"🗓️ {slot['date']}     ⏰ {slot['time']}hrs\n"
        f"Convênio: {SCHEDULING_INSURANCE_LABEL}\n"
        f"Serviço: {service_label}\n"
        f"Profissional: {professional_label}\n"
        f"Endereço: {UBS_ADDRESS_MAP.address}\n\n"
        "🪪 Apresentar RG, CPF e Cartão SUS.\n\n"
        "📝 Solicite seu atestado durante a consulta.\n\n"
        "🗓️ Agende seu retorno ao sair da consulta"
    )


def scheduling_appointment(current_node: Optional[str]) -> Optional[FlowAppointment]:
    payload = schedule_payload(current_node or "")
    slot = slot_details(payload.get("slot", ""))
    if not slot:
        return None

    service_action = payload.get("service", "")
    return FlowAppointment(
        patient_name=payload.get("name", "Paciente").strip() or "Paciente",
        document=payload.get("document", ""),
        service=SCHEDULING_SERVICE_DISPLAY_LABELS.get(service_action, "Consulta"),
        professional=SCHEDULING_PROFESSIONAL_LABELS.get(
            service_action,
            "Equipe da ESF São Carlos/Urlândia",
        ),
        appointment_date=slot["date_iso"],
        appointment_time=slot["time"],
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

    if is_scheduling_slot_action(action):
        payload = schedule_payload(current_node or "")
        if not slot_is_available(action):
            payload.pop("slot", None)
            return scheduling_slot_selection_result(
                payload,
                [
                    "Esse horário acabou de ser ocupado.",
                    "Escolha outro horário disponível.",
                ],
            )

        payload["slot"] = action
        service_label = SCHEDULING_SERVICE_DISPLAY_LABELS.get(payload.get("service", ""), "Consulta")
        selected_slot_label = slot_label(action)
        return FlowResult(
            current_node=state_with_schedule_payload(SCHEDULING_CONFIRM_NODE, payload),
            messages=[
                f"Você escolheu {selected_slot_label}.",
                (
                    "Confira os dados do agendamento:\n"
                    f"Paciente: {payload.get('name', 'não informado')}\n"
                    f"Serviço: {service_label}\n"
                    f"Horário: {selected_slot_label}"
                ),
            ],
            options=SCHEDULING_CONFIRM_OPTIONS,
        )

    if action == "agendamento_trocar_horario":
        payload = schedule_payload(current_node or "")
        payload.pop("slot", None)
        return scheduling_slot_selection_result(
            payload,
            ["Escolha outro horário disponível."],
        )

    if action == "agendamento_cancelar":
        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=["Agendamento cancelado. Deseja mais alguma coisa?"],
            options=AFTER_SCHEDULING_OPTIONS,
        )

    if action == "agendamento_confirmar":
        appointment = scheduling_appointment(current_node)
        if appointment and is_appointment_slot_booked(appointment.appointment_date, appointment.appointment_time):
            payload = schedule_payload(current_node or "")
            payload.pop("slot", None)
            return scheduling_slot_selection_result(
                payload,
                [
                    "Esse horário acabou de ser ocupado antes da confirmação.",
                    "Escolha outro horário disponível.",
                ],
            )

        return FlowResult(
            current_node=AFTER_SCHEDULING_NODE,
            messages=[
                scheduling_confirmation_message(current_node),
                "Deseja mais alguma coisa?",
            ],
            options=AFTER_SCHEDULING_OPTIONS,
            appointment=appointment,
        )

    if action in CONTENT_RESPONSES:
        if action == "endereco":
            return FlowResult(
                current_node=AFTER_INFO_NODE,
                messages=content_response_messages(action),
                options=AFTER_INFO_OPTIONS,
                map=UBS_ADDRESS_MAP,
            )

        if action == "areas_atendidas":
            return FlowResult(
                current_node=AFTER_INFO_NODE,
                messages=content_response_messages(action),
                options=AFTER_INFO_OPTIONS,
                image=AREAS_MAP_IMAGE,
            )

        return FlowResult(
            current_node=AFTER_INFO_NODE,
            messages=content_response_messages(action),
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
            messages=["Não identifiquei um nome completo de paciente. Digite novamente o nome completo para continuar."],
            options=[],
        )

    service_action = state_payload(current_node)
    payload = {
        "service": service_action,
        "name": normalize_patient_name(message or ""),
    }
    return FlowResult(
        current_node=state_with_schedule_payload(SCHEDULING_DOCUMENT_NODE, payload),
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
            messages=["Digite o CPF, RG ou Cartão SUS para continuar o agendamento."],
            options=[],
        )

    if looks_like_patient_name(message or ""):
        return FlowResult(
            current_node=current_node,
            messages=["Não identifiquei CPF, RG ou Cartão SUS. Digite novamente um documento do paciente para continuar."],
            options=[],
        )

    payload = schedule_payload(current_node)
    payload["document"] = normalize_document(message or "")
    return scheduling_slot_selection_result(
        payload,
        [
            "Encontrei horários disponíveis.",
            "Escolha uma data e horário para continuar.",
        ],
    )


def state_with_payload(node: str, value: str) -> str:
    return f"{node}:{quote(value, safe='')}"


def state_with_schedule_payload(node: str, payload: Dict[str, str]) -> str:
    return f"{node}:{urlencode(payload)}"


def state_payload(current_node: str) -> str:
    return unquote(raw_state_payload(current_node))


def raw_state_payload(current_node: str) -> str:
    parts = current_node.split(":", 1)
    return parts[1] if len(parts) == 2 else ""


def schedule_payload(current_node: str) -> Dict[str, str]:
    return dict(parse_qsl(raw_state_payload(current_node), keep_blank_values=True))


def normalize_patient_name(message: str) -> str:
    return " ".join(message.split())


def normalize_document(message: str) -> str:
    return " ".join(message.split())
