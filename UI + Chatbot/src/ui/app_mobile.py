# app_mobile.py
import logging
import uuid

from html import escape
from textwrap import dedent
from typing import Any

import streamlit as st

from src.ui.app_desktop import (
    get_runtime, 
    state_value, 
    get_destination_details,
    CATEGORY_PALETTE,
    normalize_category_key
)
from src.components.voice_assistant import voice_assistant_orb
from src.components.voice_bridge import handle_voice_request
from .styles_mobile import inject_styles

LOGGER = logging.getLogger(__name__)


def normalize_category_key(category: str) -> str:
    value = (category or "").strip().lower()
    if "admin" in value: return "administratif"
    if "labor" in value: return "laboratoire"
    if "aliment" in value or "caf" in value or "food" in value: return "alimentation"
    if "club" in value: return "clubs"
    if "service" in value: return "services"
    if "sant" in value or "health" in value: return "sante"
    if "media" in value or "press" in value: return "media"
    # Both accented and unaccented forms — JSON uses "Détente".
    if "détente" in value or "detente" in value or "lounge" in value or "relax" in value: return "detente"
    if "sanit" in value or "toilet" in value or "restroom" in value: return "sanitaires"
    return "autre"


def get_category_emoji(category: str) -> str:
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


def get_category_colors(category: str) -> tuple[str, str]:
    key = normalize_category_key(category)
    return CATEGORY_PALETTE.get(key, ("#e2e8f0", "#334155"))



def init_state(assistant) -> None:
    st.session_state.setdefault("mobile_tab", "lieux")
    st.session_state.setdefault("mobile_assistant_mode", None)
    st.session_state.setdefault("mobile_selected_location", None)
    st.session_state.setdefault("mobile_nav_success_message", None)
    
    if "mobile_chat_id" not in st.session_state:
        st.session_state.mobile_chat_id = str(uuid.uuid4())
        assistant.memory_service.create(st.session_state.mobile_chat_id)
        
    if "mobile_audio_id" not in st.session_state:
        st.session_state.mobile_audio_id = str(uuid.uuid4())
        assistant.memory_service.create(st.session_state.mobile_audio_id)
        
    st.session_state.setdefault("mobile_voice_response", None)
    st.session_state.setdefault("mobile_last_voice_nonce", None)
    st.session_state.setdefault("mobile_last_playback_nonce", None)
    st.session_state.setdefault("mobile_voice_reset_token", str(uuid.uuid4()))
    st.session_state.setdefault("mobile_is_typing", False)
    
    if "mobile_chat_history" not in st.session_state:
        st.session_state.mobile_chat_history = [{"role": "assistant", "content": "Bonjour! Comment puis-je vous aider?"}]
        
    st.session_state.setdefault("mobile_pending_prompt", None)


def render_navbar() -> None:
    with st.container(key="mobile_navbar"):
        cols = st.columns(3, gap="small")
        with cols[0]:
            with st.container(key="tab_lieux"):
                if st.button("📍 Lieux", key="mob_nav_lieux", use_container_width=True):
                    st.session_state.mobile_tab = "lieux"
                    st.rerun()
        with cols[1]:
            with st.container(key="tab_assist"):
                if st.button("🗣️ Assistant", key="mob_nav_assist", use_container_width=True):
                    st.session_state.mobile_tab = "assistant"
                    st.rerun()
        with cols[2]:
            with st.container(key="tab_status"):
                if st.button("📊 Statut", key="mob_nav_status", use_container_width=True):
                    st.session_state.mobile_tab = "status"
                    st.rerun()


def render_lieux(assistant) -> None:
    with st.container(key="mobile_lieux_content"):
        if st.session_state.get("mobile_nav_success_message"):
            st.success(st.session_state.mobile_nav_success_message)
            st.session_state.mobile_nav_success_message = None
        
        st.markdown(
            '<div class="mob-hero-title"><span class="mob-hero-icon">➤</span>Navigateur Robot Universitaire</div>',
            unsafe_allow_html=True
        )

        st.markdown('<div class="mob-search-title">🔍 Recherche</div>', unsafe_allow_html=True)
        
        query = st.text_input(
            "Rechercher...", 
            placeholder="Rechercher un lieu...", 
            label_visibility="collapsed", 
            key="mob_search_input"
        )
        
        categories = ["Toutes les catégories", *assistant.navigation_service.get_categories()[1:]]
        category = st.selectbox(
            "Catégorie", 
            categories, 
            index=0, 
            label_visibility="collapsed",
            key="mob_cat_select"
        )
        
        locations = assistant.navigation_service.search_locations(
            query=query, 
            category=category if category != "Toutes les catégories" else None
        )
        
        if not locations:
            st.markdown(
                '<div class="mob-empty-state">Aucun lieu trouvé.</div>', 
                unsafe_allow_html=True
            )
        else:
            with st.container(key="mobile_locations_grid"):
                for i in range(0, len(locations), 2):
                    cols = st.columns(2, gap="small")
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx < len(locations):
                            loc = locations[idx]
                            with col:
                                emoji = get_category_emoji(loc.category)
                                bg_color, fg_color = get_category_colors(loc.category)
                                st.markdown(
                                    f'''
                                    <div class="mob-card">
                                        <div class="mob-card-top">
                                            <span class="mob-card-icon">{emoji}</span>
                                            <span class="mob-card-name">{loc.location_name}</span>
                                        </div>
                                        <div class="mob-card-cat" style="background-color:{bg_color};color:{fg_color};">{loc.category.upper()}</div>
                                    </div>
                                    ''', 
                                    unsafe_allow_html=True
                                )
                                st.button(
                                    "", 
                                    key=f"mob_card_btn_{loc.location_name}", 
                                    on_click=lambda l=loc: set_mobile_location(l),
                                    use_container_width=True
                                )
                                
        if st.session_state.mobile_selected_location:
            render_location_modal(assistant)


def set_mobile_location(loc) -> None:
    st.session_state.mobile_selected_location = loc
    st.rerun()


def render_location_modal(assistant) -> None:
    loc = st.session_state.mobile_selected_location
    
    st.markdown('<div class="mob-modal-overlay"></div>', unsafe_allow_html=True)
    
    with st.container(key="mobile_modal"):
        st.markdown(f'<div class="mob-modal-title">{loc.location_name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="mob-modal-desc">{loc.description}</div>', unsafe_allow_html=True)
        
        details = []
        if loc.building: details.append(f"🏢 Bâtiment: {loc.building}")
        if loc.floor: details.append(f"📍 Étage: {loc.floor}")
        if loc.accessible: details.append("♿ Accessible fauteuil roulant")
        
        if details:
            st.markdown(
                '<div class="mob-modal-details">' + "<br>".join(details) + '</div>', 
                unsafe_allow_html=True
            )
            
        if st.button("➜ Démarrer la navigation", key="mob_modal_nav", use_container_width=True):
            try:
                payload = assistant.navigation_service.start_navigation(
                    loc.location_name, 
                    requested_by="mobile_ui"
                )
                if payload:
                    st.session_state.last_navigation_command = payload
                    st.session_state.robot_status = f"Navigation vers {loc.location_name}"
                    st.session_state.selected_destination = loc.location_name
                    st.session_state.mobile_nav_success_message = f"La navigation commencera vers {loc.location_name}"
            except Exception as exc:
                LOGGER.exception("Mobile navigation failed: %s", exc)
                st.error("Erreur lors du lancement.")
            finally:
                st.session_state.mobile_selected_location = None
                st.rerun()
                
        if st.button("Fermer", key="mob_modal_close", use_container_width=True):
            st.session_state.mobile_selected_location = None
            st.rerun()


def render_assistant(assistant) -> None:
    with st.container(key="mobile_assistant_content"):
        if st.session_state.mobile_assistant_mode is None:
            _, center_col, _ = st.columns([1, 2, 1])
            with center_col:
                st.markdown(
                    """
                    <div class="mob-assist-choice-title", style="font-size:1.8rem;">
                        Choisissez votre mode d’interaction
                    </div>
                    <div style="text-align:center; color:#64748b; font-size:1rem; margin-top:-1rem; margin-bottom:2rem;">
                        Taper ou parler, comme vous préférez
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                with st.container(key="choice_chat"):
                    if st.button("💬  Assistant Chat", key="mob_choice_chat", use_container_width=True):
                        st.session_state.mobile_assistant_mode = "chat"
                        st.rerun()

                st.write("")

                with st.container(key="choice_voice"):
                    if st.button("🎤  Assistant vocal", key="mob_choice_voice", use_container_width=True):
                        st.session_state.mobile_assistant_mode = "voice"
                        st.rerun()
            return

        # Fixed Top Bar Header with wider column for the back button
        with st.container(key="mobile_top_bar"):
            if st.button("←", key="mob_assist_back_btn"):
                st.session_state.mobile_assistant_mode = None
                st.rerun()

            st.markdown(
                '<div class="mob-header-title">Chat Assistant</div>',
                unsafe_allow_html=True
            )
        # Add padding so content doesn't hide behind the fixed top bar
        st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
        
        if st.session_state.mobile_assistant_mode == "chat":
            render_mobile_chat(assistant)
        elif st.session_state.mobile_assistant_mode == "voice":
            render_mobile_voice(assistant)


def render_mobile_chat(assistant):

    # 1. HANDLE LLM FIRST? ❌ NO

    # 2. SHOW CHAT FIRST
    chat_html = '<div class="mob-chat-wrapper"><div class="mob-chat-inner">'

    for msg in st.session_state.mobile_chat_history:
        role = msg["role"]
        chat_html += f'<div class="mob-chat-bubble {role}">{msg["content"]}</div>'

    # typing indicator
    if st.session_state.get("mobile_is_typing"):
        chat_html += '''
        <div class="mob-chat-bubble assistant typing">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
        '''

    chat_html += '</div></div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # 3. INPUT
    if prompt := st.chat_input("Votre message...", key="mob_chat_input"):
        st.session_state.mobile_chat_history.append({"role": "user", "content": prompt})
        st.session_state.mobile_pending_prompt = prompt
        st.session_state.mobile_is_typing = True
        st.rerun()

    # 4. PROCESS LLM AFTER UI IS SHOWN
    if st.session_state.get("mobile_pending_prompt"):

        prompt = st.session_state.mobile_pending_prompt

        try:
            assistant.run_text(prompt, conversation_id=st.session_state.mobile_chat_id)

            messages = assistant.memory_service.get_messages(st.session_state.mobile_chat_id)

            if messages and messages[-1]["role"] == "assistant":
                st.session_state.mobile_chat_history.append({
                    "role": "assistant",
                    "content": messages[-1]["text"]
                })
            else:
                st.session_state.mobile_chat_history.append({
                    "role": "assistant",
                    "content": "Erreur."
                })

        finally:
            st.session_state.mobile_pending_prompt = None
            st.session_state.mobile_is_typing = False   
            st.rerun()

def render_mobile_voice(assistant) -> None:
    with st.container(key="mobile_voice_view"):
        st.markdown('<div class="mob-voice-note">Appuyez sur le bouton et parlez clairement.</div>', unsafe_allow_html=True)
        
        component_result = voice_assistant_orb(
            key="mobile_voice_orb",
            data={
                "conversation_id": st.session_state.mobile_audio_id,
                "reset_token": st.session_state.mobile_voice_reset_token,
                "response": st.session_state.mobile_voice_response,
            },
        )
        
        voice_input = state_value(component_result, "voice_input")
        
        if isinstance(voice_input, dict):
            nonce = voice_input.get("nonce")
            
            if nonce != st.session_state.mobile_last_voice_nonce:
                st.session_state.mobile_last_voice_nonce = nonce
                
                request_payload = {
                    "audio_base64": str(voice_input.get("audio_base64", "")),
                    "mime_type": str(voice_input.get("mime_type", "audio/wav")),
                    "conversation_id": voice_input.get("conversation_id") or st.session_state.mobile_audio_id,
                }
                
                response = handle_voice_request(request_payload)
                
                if not isinstance(response, dict):
                    response = {"error": "Réponse invalide."}
                
                st.session_state.mobile_voice_response = {"nonce": nonce, **response}
                
                if "error" in response:
                    st.error(response["error"])
                else:
                    st.session_state.robot_status = "Réponse vocale en cours"
                
                st.rerun()
                
        voice_result = state_value(component_result, "voice_result")
        if voice_result:
            nonce = voice_result.get("nonce")
            if nonce != st.session_state.mobile_last_playback_nonce:
                st.session_state.mobile_last_playback_nonce = nonce
                st.session_state.robot_status = "Réponse vocale en cours"
                st.rerun()
                
        playback_finished = state_value(component_result, "playback_finished")
        if playback_finished and playback_finished != st.session_state.mobile_last_playback_nonce:
            st.session_state.mobile_last_playback_nonce = playback_finished
            st.session_state.robot_status = "Prêt"
            st.session_state.mobile_voice_response = None
            
        voice_error = state_value(component_result, "error")
        if voice_error:
            st.error(voice_error)


#===================================
#           Statut
#===================================
def _status_row(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="status-row">
            <span class="status-label">{label}</span>
            <span class="status-value">{value}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
def render_status(assistant) -> None:
    robot_status = st.session_state.get("robot_status", "Prêt")
    current_position = "Station de recharge"
    battery = "100%"

    if robot_status.startswith("Navigation") and st.session_state.get("last_navigation_command"):
        battery = "90%"
        current_position = st.session_state.last_navigation_command["location_name"]

    selected_dest = get_destination_details(assistant, st.session_state.get("selected_destination"))

    with st.container(key="mobile_status_content"):
        # Replicate the exact same centering layout as the Assistant Choice tab
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            # Replicate the exact same title/subtitle HTML styling
            st.markdown(
                """
                <div class="mob-status-title", style="font-size:1.8rem;">
                    Statut du robot
                </div>
                <div style="text-align:center; color:#64748b; font-size:1rem; margin-top:-1rem; margin-bottom:2rem;">
                    État opérationnel en direct
                </div>
                """,
                unsafe_allow_html=True
            )

            if selected_dest:
                with st.container(key="status_destination_section"):
                    st.markdown('<div class="status-title">Destination</div>', unsafe_allow_html=True)
                    _status_row("Choisie", selected_dest.location_name)
                    _status_row(
                        "Détails",
                        f"{selected_dest.building or 'N/A'} · {selected_dest.floor or 'N/A'}",
                    )

            with st.container(key="status_robot_section"):
                st.markdown('<div class="status-title">Robot</div>', unsafe_allow_html=True)
                _status_row("Statut", robot_status)
                _status_row("Batterie", battery)
                _status_row("Position actuelle", current_position)
#===================================
#           Run
#===================================
def run_mobile() -> None:
    inject_styles()
    
    try:
        assistant = get_runtime()
    except Exception as exc:
        LOGGER.exception("Mobile runtime init failed: %s", exc)
        st.error("Erreur d'initialisation.")
        return
    
    init_state(assistant)
    
    if st.session_state.mobile_tab == "lieux":
        render_lieux(assistant)
    elif st.session_state.mobile_tab == "assistant":
        render_assistant(assistant)
    elif st.session_state.mobile_tab == "status":
        render_status(assistant)
        
    render_navbar()