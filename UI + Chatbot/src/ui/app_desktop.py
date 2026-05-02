# app_desktop.py
import logging
import os
import re
import uuid

import streamlit as st

from src.components.voice_assistant import voice_assistant_orb
from src.components.voice_bridge import handle_voice_request
from src.workflow import Workflow
from .styles_desktop import inject_styles


LOGGER = logging.getLogger(__name__)
MEMORY_BASE = os.getenv("APP_MEMORY_BASE", "./memories")

DEFAULT_ASSISTANT_GREETING = (
    "Bonjour, je suis le robot d'accueil. Comment puis-je vous aider ? "
    "Où voulez-vous aller ou que souhaitez-vous savoir ?"
)

CATEGORY_PALETTE = {
    "administratif": ("#f3e8ff", "#7c3aed"),
    "sante": ("#dcfce7", "#15803d"),
    "laboratoire": ("#dbeafe", "#2563eb"),
    "alimentation": ("#fef3c7", "#b45309"),
    "media": ("#fee2e2", "#dc2626"),
    "detente": ("#e0f2fe", "#0369a1"),
    "clubs": ("#ede9fe", "#6d28d9"),
    "services": ("#cffafe", "#0f766e"),
    "autre": ("#e2e8f0", "#334155"),
    "sanitaires": ("#fef9c3", "#a16207"),
}


def configure_page() -> None:
    st.set_page_config(
        page_title="Navigateur Robot Universitaire",
        page_icon="🧭",
        layout="wide",
    )


@st.cache_resource(show_spinner=False)
def build_runtime(memory_base: str) -> Workflow:
    return Workflow(memory_base=memory_base)


def get_runtime() -> Workflow:
    return build_runtime(MEMORY_BASE)


def init_session_state(assistant: Workflow) -> None:
    if "chat_conversation_id" not in st.session_state:
        st.session_state.chat_conversation_id = str(uuid.uuid4())
        assistant.memory_service.create(st.session_state.chat_conversation_id)

    if "audio_conversation_id" not in st.session_state:
        st.session_state.audio_conversation_id = str(uuid.uuid4())
        assistant.memory_service.create(st.session_state.audio_conversation_id)

    st.session_state.setdefault("selected_destination", None)
    st.session_state.setdefault("robot_status", "Prêt")
    st.session_state.setdefault("last_navigation_command", None)
    st.session_state.setdefault("last_voice_error", None)
    st.session_state.setdefault("last_voice_response", "")
    st.session_state.setdefault("last_voice_transcription", "")
    st.session_state.setdefault("last_voice_event_nonce", None)
    st.session_state.setdefault("last_playback_nonce", None)
    st.session_state.setdefault("voice_response", None)
    st.session_state.setdefault("chat_panel_open", False)
    st.session_state.setdefault("voice_panel_open", False)
    st.session_state.setdefault("pending_chat_prompt", None)
    st.session_state.setdefault("chat_processing", False)
    st.session_state.setdefault("voice_reset_token", str(uuid.uuid4()))
    st.session_state.setdefault("dock_minimized", False)


def state_value(result, key: str, default=None):
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


def load_history(assistant: Workflow, conversation_id: str) -> list[dict]:
    return [
        {"role": message["role"], "content": message["text"]}
        for message in assistant.memory_service.get_messages(conversation_id)
    ]


def get_destination_details(assistant: Workflow, location_name: str | None):
    if not location_name:
        return None

    for location in assistant.navigation_service.list_locations():
        if location.location_name == location_name:
            return location

    return assistant.navigation_service.resolve_location(location_name)


def new_chat_conversation(assistant: Workflow) -> None:
    st.session_state.chat_conversation_id = str(uuid.uuid4())
    assistant.memory_service.create(st.session_state.chat_conversation_id)
    st.session_state.pending_chat_prompt = None
    st.session_state.chat_processing = False


def new_audio_conversation(assistant: Workflow) -> None:
    st.session_state.audio_conversation_id = str(uuid.uuid4())
    assistant.memory_service.create(st.session_state.audio_conversation_id)
    st.session_state.last_voice_error = None
    st.session_state.last_voice_response = ""
    st.session_state.last_voice_transcription = ""
    st.session_state.last_voice_event_nonce = None
    st.session_state.last_playback_nonce = None
    st.session_state.voice_response = None
    st.session_state.voice_reset_token = str(uuid.uuid4())
    st.session_state.robot_status = "Prêt"


def open_chat_panel() -> None:
    st.session_state.chat_panel_open = True
    st.session_state.voice_panel_open = False


def open_voice_panel() -> None:
    st.session_state.voice_panel_open = True
    st.session_state.chat_panel_open = False


def close_chat_panel() -> None:
    st.session_state.chat_panel_open = False


def close_voice_panel() -> None:
    st.session_state.voice_panel_open = False


def minimize_dock() -> None:
    st.session_state.dock_minimized = True


def restore_dock() -> None:
    st.session_state.dock_minimized = False


def select_destination(location_name: str) -> None:
    st.session_state.selected_destination = location_name
    st.session_state.robot_status = "Destination sélectionnée"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def short_description(text: str, limit: int = 82) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1].rstrip()}…"


def category_badge(category: str) -> str:
    key = normalize_category_key(category)
    background, foreground = CATEGORY_PALETTE.get(key, ("#e2e8f0", "#334155"))
    return (
        f'<span class="category-pill" style="background:{background};color:{foreground};">'
        f"{category}</span>"
    )


def normalize_category_key(category: str) -> str:
    value = (category or "").strip().lower()
    if "admin" in value:
        return "administratif"
    if "labor" in value:
        return "laboratoire"
    if "aliment" in value or "caf" in value or "food" in value:
        return "alimentation"
    if "club" in value:
        return "clubs"
    if "service" in value:
        return "services"
    if "sant" in value or "health" in value:
        return "sante"
    if "media" in value or "press" in value:
        return "media"
    # Both the accented and unaccented forms — JSON uses "Détente".
    if "détente" in value or "detente" in value or "lounge" in value or "relax" in value:
        return "detente"
    if "sanit" in value or "toilet" in value or "restroom" in value:
        return "sanitaires"
    return "autre"


def category_icon(category: str) -> str:
    key = normalize_category_key(category)
    icon = {
        "administratif": "&#128188;",
        "sante": "&#127973;",
        "laboratoire": "&#129514;",
        "alimentation": "&#127860;",
        "media": "&#127897;",
        "detente": "&#127918;",
        "clubs": "&#128101;",
        "services": "&#128295;",
        "autre": "&#128205;",
    }.get(key, "&#128205;")
    return f'<span class="destination-name-icon" aria-hidden="true">{icon}</span>'


def build_destination_meta(location) -> str:
    chips = []
    if location.building:
        chips.append(f'<span class="meta-chip">🏢 {location.building}</span>')
    if location.floor:
        chips.append(f'<span class="meta-chip">📍 {location.floor}</span>')
    if location.accessible:
        chips.append('<span class="meta-chip accessible">♿ Accessible</span>')
    return "".join(chips)


def render_header() -> None:
    st.markdown(
        """
        <div class="hero-wrap">
            <h1 class="hero-title"><span class="hero-icon">➤</span>Navigateur Robot Universitaire</h1>
            <div class="hero-subtitle">Sélectionnez une destination et notre robot intelligent vous y guidera</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_search_panel(assistant: Workflow):
    categories = ["Toutes les catégories", *assistant.navigation_service.get_categories()[1:]]

    with st.container(key="search_panel"):
        st.markdown(
            '<div class="search-title-row"><span>🔎</span><span>Trouvez votre destination</span></div>',
            unsafe_allow_html=True,
        )

        cols = st.columns([5.1, 1.45], gap="medium")
        with cols[0]:
            query = st.text_input(
                "Recherche",
                placeholder="Rechercher par mot-clé dans le titre…",
                label_visibility="collapsed",
            )
        with cols[1]:
            category = st.selectbox(
                "Catégorie",
                categories,
                index=0,
                label_visibility="collapsed",
            )
    return query, category


def render_destination_card(location, is_selected: bool) -> None:
    slug = slugify(location.location_name)
    key_prefix = f"destination_card_selected_{slug}" if is_selected else f"destination_card_{slug}"

    with st.container(key=key_prefix):
        st.markdown(
            f"""
            <div class="destination-title-row">
                <div class="destination-name-row">
                    {category_icon(location.category)}
                    <div class="destination-name">{location.location_name}</div>
                </div>
                {category_badge(location.category)}
            </div>
            <div class="destination-description">{short_description(location.description)}</div>
            <div class="destination-meta">{build_destination_meta(location)}</div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Sélectionné" if is_selected else "Sélectionner",
            key=f"select_{slug}",
            use_container_width=True,
            on_click=select_destination,
            args=(location.location_name,),
        )


def render_destination_panel(assistant: Workflow, query: str, category: str) -> None:
    results = assistant.navigation_service.search_locations(query=query, category=category)

    with st.container(key="destination_panel"):
        st.markdown('<div class="section-title">🏢 Emplacements disponibles</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-subtitle">{len(results)} emplacement(s) trouvé(s)</div>',
            unsafe_allow_html=True,
        )

        if not results:
            st.markdown(
                '<div class="empty-state">Aucun emplacement ne correspond à votre recherche actuelle.</div>',
                unsafe_allow_html=True,
            )
            return

        list_box = st.container(height=640)
        with list_box:
            for index in range(0, len(results), 2):
                row = st.columns(2, gap="medium")
                for column, location in zip(row, results[index:index + 2]):
                    with column:
                        render_destination_card(
                            location,
                            is_selected=st.session_state.selected_destination == location.location_name,
                        )


def render_status_panel() -> None:
    current_position = "Station de recharge"
    battery = "100%"
    if st.session_state.robot_status.startswith("Navigation") and st.session_state.last_navigation_command:
        battery = "90%"
        current_position = st.session_state.last_navigation_command["location_name"]

    with st.container(key="status_panel"):
        st.markdown('<div class="section-title"> Statut du robot</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">État opérationnel en direct</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="status-grid">
                <div class="status-label">Statut:</div>
                <div class="status-value"><span class="status-pill">{st.session_state.robot_status}</span></div>
                <div class="status-label">Batterie:</div>
                <div class="status-value">{battery}</div>
                <div class="status-label">Position actuelle:</div>
                <div class="status-value">{current_position}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_selected_panel(assistant: Workflow) -> None:
    destination = get_destination_details(assistant, st.session_state.selected_destination)

    with st.container(key="selected_panel"):
        st.markdown('<div class="section-title">📌 Destination sélectionnée</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Détails de la zone choisie</div>', unsafe_allow_html=True)

        if not destination:
            st.markdown(
                '<div class="empty-state">Cliquez sur une destination à gauche pour afficher sa description ici.</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(f'<div class="selected-destination">{destination.location_name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="selected-description">{destination.description}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="selected-details">
                <div class="selected-detail"><span class="selected-detail-icon">🏢</span><span>Bâtiment: {destination.building or 'Non précisé'}</span></div>
                <div class="selected-detail"><span class="selected-detail-icon">📍</span><span>Étage: {destination.floor or 'Non précisé'}</span></div>
                <div class="selected-detail {'accessible' if destination.accessible else ''}"><span class="selected-detail-icon">♿</span><span>{'Accessible fauteuil roulant' if destination.accessible else 'Accessibilité non précisée'}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="nav_action_button"):
            if st.button("➜ Démarrer la navigation robot", use_container_width=True):
                try:
                    payload = assistant.navigation_service.start_navigation(
                        destination.location_name,
                        requested_by="streamlit_ui",
                    )
                except Exception as exc:
                    LOGGER.exception("Navigation start failed: %s", exc)
                    st.error("Impossible de démarrer la navigation pour le moment.")
                    return

                if payload:
                    st.session_state.last_navigation_command = payload
                    st.session_state.robot_status = f"Navigation vers {payload['location_name']}"
                    dispatch_status = payload.get("dispatch", {}).get("status", "queued")
                    st.success(
                        f"Navigation demandée vers {payload['location_name']} ({dispatch_status})."
                    )


def render_chat_messages(assistant: Workflow, pending_prompt: str | None = None) -> None:
    history = load_history(assistant, st.session_state.chat_conversation_id)

    if not history and not pending_prompt:
        with st.chat_message("assistant"):
            st.write(DEFAULT_ASSISTANT_GREETING)

    for message in history[-12:]:
        with st.chat_message("assistant" if message["role"] == "assistant" else "user"):
            st.write(message["content"])

    if pending_prompt:
        with st.chat_message("user"):
            st.write(pending_prompt)
        with st.chat_message("assistant"):
            st.markdown(
                '<div class="typing"><span></span><span></span><span></span></div>',
                unsafe_allow_html=True,
            )


def render_chat_widget(assistant: Workflow) -> None:
    pending_prompt = st.session_state.pending_chat_prompt

    with st.container(key="chat_widget_panel"):
        top_cols = st.columns([6.5, 0.9, 0.9])
        with top_cols[0]:
            st.markdown('<div class="widget-header-title">Assistant chat</div>', unsafe_allow_html=True)
        with top_cols[1]:
            with st.container(key="widget_icon_button_chat_new"):
                if st.button("+", key="new_chat_widget", use_container_width=True):
                    new_chat_conversation(assistant)
                    st.rerun(scope="fragment")
        with top_cols[2]:
            with st.container(key="widget_icon_button_chat_close"):
                if st.button("×", key="close_chat_widget", use_container_width=True):
                    close_chat_panel()
                    st.rerun(scope="fragment")

        message_box = st.container(height=360)
        with message_box:
            render_chat_messages(assistant, pending_prompt=pending_prompt)

        with st.form("chat_widget_form", clear_on_submit=True):
            input_cols = st.columns([6.2, 0.9], gap="small")
            with input_cols[0]:
                prompt = st.text_input(
                    "Message",
                    placeholder="Ecrivez votre message...",
                    label_visibility="collapsed",
                )
            with input_cols[1]:
                submitted = st.form_submit_button(">", use_container_width=True)

        if submitted and prompt.strip():
            st.session_state.pending_chat_prompt = prompt.strip()
            st.session_state.chat_processing = True
            st.rerun(scope="fragment")

    if pending_prompt and st.session_state.chat_processing:
        try:
            assistant.run_text(
                pending_prompt,
                conversation_id=st.session_state.chat_conversation_id,
            )
        except Exception as exc:
            LOGGER.exception("Chat processing failed: %s", exc)
            st.error("Le chat est temporairement indisponible. Veuillez réessayer.")
        finally:
            st.session_state.pending_chat_prompt = None
            st.session_state.chat_processing = False
            st.rerun(scope="fragment")


def render_voice_widget(assistant: Workflow) -> None:
    with st.container(key="voice_widget_panel"):
        top_cols = st.columns([6.5, 0.9, 0.9])
        with top_cols[0]:
            st.markdown('<div class="widget-header-title">Assistant vocal</div>', unsafe_allow_html=True)
        with top_cols[1]:
            with st.container(key="widget_icon_button_voice_new"):
                if st.button("+", key="new_audio_widget", use_container_width=True):
                    new_audio_conversation(assistant)
                    st.rerun(scope="fragment")
        with top_cols[2]:
            with st.container(key="widget_icon_button_voice_close"):
                if st.button("×", key="close_audio_widget", use_container_width=True):
                    close_voice_panel()
                    st.rerun(scope="fragment")

        st.markdown(
            '<div class="voice-panel-note">Parlez au robot, puis attendez sa réponse vocale automatique.</div>',
            unsafe_allow_html=True,
        )

        component_result = voice_assistant_orb(
            key="voice_assistant_orb_component",
            data={
                "conversation_id": st.session_state.audio_conversation_id,
                "reset_token": st.session_state.voice_reset_token,
                "response": st.session_state.get("voice_response"),
            },
        )

        voice_input = state_value(component_result, "voice_input")

        if isinstance(voice_input, dict):
            nonce = voice_input.get("nonce")

            if nonce != st.session_state.last_voice_event_nonce:
                st.session_state.last_voice_event_nonce = nonce
                
                request_payload = {
                    "audio_base64": str(voice_input.get("audio_base64", "")),
                    "mime_type": str(voice_input.get("mime_type", "audio/wav")),
                    "conversation_id": (
                        voice_input.get("conversation_id")
                        or st.session_state.audio_conversation_id
                    ),
                }

                response = handle_voice_request(request_payload)

                if not isinstance(response, dict):
                    response = {"error": "Réponse vocale invalide du serveur."}

                st.session_state.voice_response = {
                    "nonce": nonce,
                    **response,
                }

                if "error" in response:
                    st.session_state.last_voice_error = response["error"]
                    st.session_state.robot_status = "Erreur vocale"
                else:
                    st.session_state.last_voice_response = response.get("response", "") or ""
                    st.session_state.last_voice_transcription = response.get("transcription", "") or ""
                    st.session_state.last_voice_error = None
                    st.session_state.robot_status = "Réponse vocale en cours"

                st.rerun(scope="fragment")

        voice_result = state_value(component_result, "voice_result")

        if voice_result:
            nonce = voice_result.get("nonce")
            if nonce != st.session_state.last_playback_nonce:
                st.session_state.last_playback_nonce = nonce
                st.session_state.last_voice_response = voice_result.get("response", "") or ""
                st.session_state.last_voice_transcription = voice_result.get("transcription", "") or ""
                st.session_state.last_voice_error = None
                st.session_state.robot_status = "Réponse vocale en cours"
                st.rerun(scope="fragment")

        playback_finished = state_value(component_result, "playback_finished")
        if playback_finished and playback_finished != st.session_state.last_playback_nonce:
            st.session_state.last_playback_nonce = playback_finished
            st.session_state.robot_status = "Prêt"
            st.session_state.voice_response = None

        voice_error = state_value(component_result, "error")
        if voice_error:
            st.session_state.last_voice_error = voice_error
            st.session_state.robot_status = "Erreur vocale"

        if st.session_state.last_voice_error:
            st.caption(f"Statut vocal: {st.session_state.last_voice_error}")


def render_assistant_dock() -> None:
    if st.session_state.chat_panel_open or st.session_state.voice_panel_open:
        return

    if st.session_state.dock_minimized:
        with st.container(key="assistant_dock_mini"):
            st.button(
                "💬 Chat with me!",
                key="restore_dock_button",
                use_container_width=True,
                on_click=restore_dock,
            )
        return

    with st.container(key="assistant_dock"):
        header_cols = st.columns([7.5, 1], gap="small")
        with header_cols[0]:
            st.markdown('<div class="assist-copy">Besoin d\u2019aide\u00a0?</div>', unsafe_allow_html=True)
        with header_cols[1]:
            with st.container(key="widget_icon_button_dock_close"):
                st.button("×", key="minimize_dock_button", use_container_width=True, on_click=minimize_dock)

        st.markdown(
            '<div class="assist-subcopy">Discutez avec le robot ou lancez une interaction vocale pour trouver votre destination.</div>',
            unsafe_allow_html=True,
        )

        dock_cols = st.columns(2, gap="small")
        with dock_cols[0]:
            st.button(
                "💬 Chat",
                key="chat_dock_button",
                use_container_width=True,
                on_click=open_chat_panel,
            )
        with dock_cols[1]:
            st.button(
                "🎤 Voix",
                key="voice_dock_button",
                use_container_width=True,
                on_click=open_voice_panel,
            )


@st.fragment
def render_navigation_fragment(assistant: Workflow) -> None:
    query, category = render_search_panel(assistant)

    main_left, main_right = st.columns([2.15, 1.0], gap="large")
    with main_left:
        render_destination_panel(assistant, query, category)
    with main_right:
        render_selected_panel(assistant)
        st.write("")
        render_status_panel()


@st.fragment
def render_assistant_fragment(assistant: Workflow) -> None:
    if st.session_state.chat_panel_open:
        with st.container(key="floating_chat_panel"):
            render_chat_widget(assistant)
        return

    if st.session_state.voice_panel_open:
        with st.container(key="floating_voice_panel"):
            render_voice_widget(assistant)
        return

    render_assistant_dock()


def run_app() -> None:
    configure_page()
    inject_styles()

    try:
        assistant = get_runtime()
    except Exception as exc:
        LOGGER.exception("Runtime initialization failed: %s", exc)
        st.error("Erreur critique lors de l'initialisation du service robot.")
        st.stop()

    init_session_state(assistant)

    with st.container(key="desktop_viewport"):
        render_header()
        render_navigation_fragment(assistant)
        render_assistant_fragment(assistant)

    with st.container(key="mobile_viewport"):
        from src.ui.app_mobile import run_mobile
        run_mobile()