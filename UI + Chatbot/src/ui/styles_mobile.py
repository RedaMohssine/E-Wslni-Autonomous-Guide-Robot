# styles_mobile.py
import streamlit as st

CSS = """
<style>

/* ═══════════════════════════════════════════════════════════════════
   GLOBAL MOBILE OVERRIDES
   ═══════════════════════════════════════════════════════════════════ */
.st-key-mobile_viewport .stApp {
    padding-top: 0rem;
    padding-bottom: 5rem;
}
.st-key-mobile_viewport [data-testid="stSidebar"] {
    display: none !important;
}
.stApp {
    display: flex;
    flex-direction: column;
}
/* ═══════════════════════════════════════════════════════════════════
   FIXED BOTTOM NAVBAR (Horizontal, Emojis, Perimeters)
   ═══════════════════════════════════════════════════════════════════ */
.st-key-mobile_navbar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
    z-index: 1001; 
    padding: 0.5rem 0.5rem;
    padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
    box-shadow: 0 -6px 16px rgba(0,0,0,0.06);
}
.st-key-mobile_navbar [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
    gap: 0.4rem !important;
}
.st-key-mobile_navbar [data-testid="stColumn"] {
    width: 33.33% !important;
    flex: 1 1 0% !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
.st-key-mobile_navbar button {
    border-radius: 10px;
    font-weight: 700;
    font-size: 0.8rem;
    background: transparent;
    color: #64748b;
    border: 2px solid transparent;
    padding: 0.6rem 0;
    min-height: 2.5rem;
    width: 100%;
    text-align: center;
    transition: all 0.2s ease;
}
.st-key-mobile_navbar button:hover {
    background: #f1f5f9;
    color: #334155;
}

/* ═══════════════════════════════════════════════════════════════════
   TAB 1: LIEUX
   ═══════════════════════════════════════════════════════════════════ */
.mob-hero-title { text-align: center; font-size: 1.6rem; font-weight: 800; color: #0f172a; margin-bottom: 1.25rem; padding-top: 0.5rem; }
.mob-hero-icon { color: #2563eb; margin-right: 0.4rem; }
.mob-search-title { font-size: 0.9rem; font-weight: 700; color: #475569; margin-bottom: 0.4rem; }

.st-key-mob_search_input input { border-radius: 12px !important; border: 1px solid #e2e8f0 !important; padding: 0.65rem 0.85rem !important; font-size: 0.9rem !important; background-color: #f8fafc !important; }
.st-key-mob_search_input input::placeholder { color: #94a3b8 !important; font-style: italic; }
.st-key-mob_cat_select select { border-radius: 12px !important; font-size: 0.85rem !important; border: 1px solid #e2e8f0 !important; margin-top: 0.5rem !important; }
.mob-empty-state { text-align: center; padding: 2rem; color: #94a3b8; background: rgba(255,255,255,0.6); border-radius: 16px; border: 1px dashed #cbd5e1; margin-top: 1rem; font-weight: 500; }

.st-key-mobile_locations_grid [data-testid="stVerticalBlockBorderWrapper"],
.st-key-mobile_locations_grid [data-testid="stVerticalBlock"] { width: 100% !important; padding: 0 !important; margin: 0 !important; }
.st-key-mobile_locations_grid [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; width: 100% !important; gap: 0.5rem !important; margin: 0.25rem 0 !important; }
.st-key-mobile_locations_grid [data-testid="stColumn"] { width: 50% !important; flex: 0 0 50% !important; min-width: 0 !important; max-width: 50% !important; position: relative !important; padding: 0 !important; margin: 0 !important; }
.st-key-mobile_locations_grid [data-testid="stColumn"] > *,
.st-key-mobile_locations_grid [data-testid="stColumn"] > * > * { position: static !important; margin: 0 !important; padding: 0 !important; }

.mob-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding:  1rem ; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.02); gap: 0.3rem; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
.st-key-mobile_locations_grid [data-testid="stColumn"]:hover .mob-card { border-color: #93c5fd; box-shadow: 0 8px 16px rgba(37, 99, 235, 0.12); transform: translateY(-3px); }

.mob-card-top { display: flex; align-items: center; gap: 0.4rem; width: 100%; }
.mob-card-icon { font-size: 1rem; flex-shrink: 0; }
.mob-card-name { font-weight: 700; color: #0f172a; font-size: 0.75rem; line-height: 1.3; word-break: break-word; overflow-wrap: break-word; flex: 1; }
.mob-card-cat { font-size: 0.55rem; color: #6d28d9; background: #ede9fe; padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.02em; align-self: flex-end; }

.st-key-mobile_locations_grid button { position: absolute !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; opacity: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; cursor: pointer; z-index: 10; color: transparent !important; line-height: 0 !important; font-size: 0 !important; }
.st-key-mobile_locations_grid button:hover, .st-key-mobile_locations_grid button:focus, .st-key-mobile_locations_grid button:active { background: transparent !important; border: none !important; box-shadow: none !important; color: transparent !important; }

/* ═══════════════════════════════════════════════════════════════════
   LIEUX: MODAL
   ═══════════════════════════════════════════════════════════════════ */
.mob-modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.6); z-index: 1000; backdrop-filter: blur(4px); }
.st-key-mobile_modal { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 400px; background: white; border-radius: 24px; padding: 1.75rem; z-index: 1001; box-shadow: 0 25px 50px rgba(0,0,0,0.25); max-height: 80vh; overflow-y: auto; border: 1px solid rgba(255,255,255,0.2); }
.mob-modal-title { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 0.75rem; }
.mob-modal-desc { font-size: 0.9rem; color: #475569; line-height: 1.6; margin-bottom: 1rem; }
.mob-modal-details { font-size: 0.85rem; color: #334155; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #f1f5f9; line-height: 1.8; }
.st-key-mobile_modal button[key="mob_modal_nav"] { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important; color: white !important; border-radius: 14px !important; padding: 0.9rem !important; font-weight: 700 !important; border: none !important; width: 100% !important; margin-top: 0.5rem; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); transition: all 0.2s ease; }
.st-key-mobile_modal button[key="mob_modal_nav"]:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4); }
.st-key-mobile_modal button[key="mob_modal_close"] { background: #f1f5f9 !important; color: #475569 !important; border-radius: 14px !important; padding: 0.9rem !important; font-weight: 600 !important; border: none !important; width: 100% !important; transition: all 0.2s ease; }
.st-key-mobile_modal button[key="mob_modal_close"]:hover { background: #e2e8f0 !important; }

/* ═══════════════════════════════════════════════════════════════════
   TAB 2: ASSISTANT CHOICE
   ═══════════════════════════════════════════════════════════════════ */
.mob-assist-choice-title { font-size: 1.5rem; font-weight: 800; color: #0f172a; text-align: center; margin-bottom: 2.5rem; margin-top: 10rem; }
.st-key-choice_chat button { padding: 1.2rem 1rem !important; border-radius: 16px !important; font-size: 1rem !important; font-weight: 700 !important; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important; color: white !important; border: none !important; min-height: 3.5rem !important; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3); transition: all 0.2s ease; }
.st-key-choice_chat button:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4); }
.st-key-choice_voice button { padding: 1.2rem 1rem !important; border-radius: 16px !important; font-size: 1rem !important; font-weight: 700 !important; background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important; color: white !important; border: none !important; min-height: 3.5rem !important; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.3); transition: all 0.2s ease; }
.st-key-choice_voice button:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(124, 58, 237, 0.4); }

/* ═══════════════════════════════════════════════════════════════════
   FIXED TOP BAR - CENTER TITLE + LEFT BUTTON
   ═══════════════════════════════════════════════════════════════════ */
.st-key-mobile_top_bar {
    display: flex !important;
    position: fixed;
    top: 60px;
    left: 0;
    right: 0;
    height: 60px;
    width: 100%;
    z-index: 2000;

    background: rgba(255, 255, 255, 0.98);
    border-bottom: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

/* Center title absolutely (true center, not flex fake center) */
.mob-header-title {
    position: relative;
    text-align: center;
    top: 100%;
    font-size: 1.25rem;
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
}

/* Position button at extreme left */
.st-key-mobile_top_bar button {
    position: absolute !important;
    z-index: 10000 !important;
    left: 50%;
    top: 10px !important;
    background: #2563eb !important;
    color: white !important;
    border: none !important;

    font-size: 1.2rem !important;
    font-weight: 800 !important;

    padding: 0.5rem 1rem !important;
    border-radius: 20px !important;

    width: auto !important;
    min-width: auto !important;

    box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3);
}

/* Hover */
.st-key-mobile_top_bar button:hover {
    background: #1d4ed8 !important;
}
/* ═══════════════════════════════════════════════════════════════════
   CHAT (Fixed Input at Bottom)
   ═══════════════════════════════════════════════════════════════════ */
.st-key-mobile_viewport [data-testid="stChatInput"] { position: fixed !important; bottom: 4rem !important; left: 0 !important; right: 0 !important; width: 100% !important; background: rgba(255,255,255,0.98) !important; padding: 0.5rem 0.75rem !important; z-index: 998 !important; border-top: 1px solid #e2e8f0 !important; box-shadow: 0 -4px 12px rgba(0,0,0,0.04) !important; }
.st-key-mobile_viewport [data-testid="stChatInput"] > div { max-width: 100% !important; }
.st-key-mobile_viewport [data-testid="stChatInput"] input { border-radius: 14px !important; border: 1px solid #e2e8f0 !important; background-color: #f8fafc !important; }
.mob-chat-bubble-wrapper {
    position: relative;
    top: 120px;
    left: 0;
    right: 0;
    bottom: 170px;              /* more room for input + navbar */
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem 0.75rem 180px;
    box-sizing: border-box;
    -webkit-overflow-scrolling: touch;
    scroll-padding-bottom: 260px;
}

.mob-chat-bubble { 
    position: relative;
    bottom:50px;
    max-width: 90%;
    padding: 0.55rem 0.75rem; 
    border-radius: 12px; 
    font-size: 0.9rem; 
    line-height: 1.4; 
    word-wrap: break-word; 
    box-shadow: 0 1px 2px rgba(0,0,0,0.06); 
    transition: transform 0.1s ease; 
    }
.mob-chat-bubble.user { align-self: flex-end; background: #dcf8c6; color: #111b21; border-bottom-right-radius: 4px; }
.mob-chat-bubble.assistant { align-self: flex-start; background: #ffffff; color: #111b21; border-bottom-left-radius: 4px; border: 1px solid #e2e8f0; }
.mob-chat-inner {
    margin-top: 25px;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

/* ═══════════════════════════════════════════════════════════════════
   Typing...
   ═══════════════════════════════════════════════════════════════════ */
.mob-chat-bubble.typing {
    display: flex;
    gap: 4px;
    align-items: center;
    width: fit-content;
    padding: 0.6rem 0.9rem;
}

.mob-chat-bubble.typing .dot {
    width: 8px;
    height: 8px;
    background: #94a3b8;
    border-radius: 50%;
    animation: blink 1.4s infinite ease-in-out;
}

.mob-chat-bubble.typing .dot:nth-child(2) {
    animation-delay: 0.2s;
}

.mob-chat-bubble.typing .dot:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes blink {
    0%, 80%, 100% { opacity: 0.2; transform: translateY(0px); }
    40% { opacity: 1; transform: translateY(-2px); }
}
/* ═══════════════════════════════════════════════════════════════════
   TAB 3: STATUT
   ═══════════════════════════════════════════════════════════════════ */

/* Exact same title styling as the Assistant Choice tab */
.mob-status-title { 
    font-size: 1.5rem; 
    font-weight: 800; 
    color: #0f172a; 
    text-align: center; 
    margin-bottom: 1.5rem; 
    margin-top: 10rem; /* Pushes it down slightly from the top of the screen */
}

/* ---------------------------------------------------------
   INFO BOXES (100% UNTOUCHED - PERFECT ALIGNMENT PRESERVED)
   --------------------------------------------------------- */
.st-key-status_destination_section,
.st-key-status_robot_section {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.25rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.status-title {
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #64748b;
    margin-bottom: 1.5rem; 
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center; 
    margin-bottom: 0.55rem;
}

.status-row:last-child {
    margin-bottom: 1;
}

.status-label {
    color: #64748b;
    font-size: 0.88rem;
    margin: 0; 
}

.status-value {
    color: #0f172a;
    font-size: 0.92rem;
    font-weight: 700;
    text-align: right;
    overflow-wrap: anywhere;
    max-width: 65%; 
    margin: 0; 
}
</style>
"""


def inject_styles() -> None:
    active_tab = st.session_state.get("mobile_tab", "lieux")
    tab_selectors = {
        "lieux": ".st-key-tab_lieux",
        "assistant": ".st-key-tab_assist",
        "status": ".st-key-tab_status"
    }
    active_selector = tab_selectors.get(active_tab, tab_selectors["lieux"])
    
    dynamic_active_css = f"""
    <style>
    {active_selector} button {{
        background: #2563eb !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    }}
    </style>
    """
    
    st.markdown(dynamic_active_css, unsafe_allow_html=True)
    st.markdown(CSS, unsafe_allow_html=True)