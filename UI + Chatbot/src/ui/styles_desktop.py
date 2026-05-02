# styles_desktop.py
import streamlit as st

APP_CSS = """
<style>
/* ═══════════════════════════════════════════════════════════════════
   VIEWPORT SWITCH - TOP LEVEL, NOT NESTED
   ═══════════════════════════════════════════════════════════════════ */
.st-key-mobile_viewport {
    display: none !important;
}

.st-key-desktop_viewport {
    display: block !important;
}

/* ═══════════════════════════════════════════════════════════════════
   BASE STYLES
   ═══════════════════════════════════════════════════════════════════ */
.stApp {
    background:
        radial-gradient(circle at top center, rgba(255, 255, 255, 0.62), transparent 28%),
        linear-gradient(180deg, #dfe8fb 0%, #dfe7f7 100%);
}

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 8rem;
    max-width: 1640px;
}

.hero-wrap {
    text-align: center;
    padding: 0.25rem 0 1.35rem 0;
}

.hero-title {
    color: #0f172a;
    font-size: 2.95rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0;
}

.hero-subtitle {
    color: #475569;
    font-size: 1.08rem;
    margin-top: 0.75rem;
}

.hero-icon {
    color: #2563eb;
    margin-right: 0.55rem;
}

.st-key-search_panel,
.st-key-destination_panel,
.st-key-status_panel,
.st-key-selected_panel,
.st-key-floating_chat_panel,
.st-key-floating_voice_panel,
.st-key-chat_widget_panel,
.st-key-voice_widget_panel,
.st-key-assistant_dock {
    background: rgba(255, 255, 255, 0.98);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 24px;
    box-shadow:
        0 16px 30px rgba(15, 23, 42, 0.05),
        0 3px 10px rgba(15, 23, 42, 0.03);
}

.st-key-search_panel,
.st-key-destination_panel,
.st-key-status_panel,
.st-key-selected_panel {
    padding: 1.15rem 1.2rem 2rem 1.2rem;
}

.section-title {
    color: #0f172a;
    font-size: 1.08rem;
    font-weight: 800;
    margin-bottom: 0.15rem;
}

.section-subtitle {
    color: #64748b;
    font-size: 0.96rem;
    margin-bottom: 0.9rem;
}

.search-title-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.9rem;
    color: #0f172a;
    font-size: 1.08rem;
    font-weight: 800;
}

.status-grid {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0.95rem 0.8rem;
    align-items: center;
}

.status-label {
    color: #475569;
    font-size: 0.98rem;
}

.status-value {
    color: #0f172a;
    font-size: 1.02rem;
    font-weight: 700;
    text-align: right;
}

.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    padding: 0.18rem 0.68rem;
    font-size: 0.88rem;
    font-weight: 700;
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid #e2e8f0;
}

[class*="st-key-destination_card_"] {
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.98);
    padding: 1rem 1rem 0.95rem 1rem;
    transition: background 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

[class*="st-key-destination_card_"]:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
    transform: translateY(-1px);
}

[class*="st-key-destination_card_selected_"] {
    border: 2px solid #2563eb;
    background: #f8fbff;
    box-shadow: 0 14px 26px rgba(37, 99, 235, 0.10);
}

.destination-title-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.9rem;
    margin-bottom: 0.5rem;
}

.destination-name-row {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    min-width: 0;
}

.destination-name-icon {
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #eff6ff;
    color: #2563eb;
    font-size: 1rem;
    flex-shrink: 0;
}

.destination-name {
    color: #0f172a;
    font-size: 1.02rem;
    font-weight: 800;
    line-height: 1.35;
}

.destination-description {
    color: #64748b;
    font-size: 0.93rem;
    line-height: 1.5;
    margin-bottom: 0.75rem;
    min-height: 2.8rem;
}

.destination-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-bottom: 0.85rem;
}

.meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 999px;
    padding: 0.22rem 0.62rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-size: 0.84rem;
    font-weight: 700;
}

.meta-chip.accessible {
    background: #f0fdf4;
    color: #16a34a;
    border-color: #bbf7d0;
}

.category-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.28rem 0.72rem;
    font-size: 0.82rem;
    font-weight: 800;
    white-space: nowrap;
}

[class*="st-key-destination_card_"] button {
    min-height: 2.75rem;
    border-radius: 14px;
    font-weight: 700;
    border: 1px solid #dbe4f0;
    background: #ffffff;
    color: #0f172a;
}

[class*="st-key-destination_card_"] button:hover {
    border-color: #94a3b8;
    background: #f8fafc;
}

.empty-state {
    border: 1px dashed rgba(148, 163, 184, 0.35);
    border-radius: 18px;
    padding: 1rem;
    color: #64748b;
    background: rgba(248, 250, 252, 0.84);
}

.selected-destination {
    color: #0f172a;
    font-size: 1.28rem;
    font-weight: 800;
    margin-bottom: 0.55rem;
}

.selected-description {
    color: #475569;
    font-size: 0.98rem;
    line-height: 1.65;
    margin-bottom: 1rem;
}

.selected-details {
    display: grid;
    gap: 0.85rem;
    padding: 0.2rem 0 1rem 0;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 1rem;
}

.selected-detail {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    color: #334155;
    font-size: 0.98rem;
}

.selected-detail-icon {
    width: 1.5rem;
    text-align: center;
    color: #64748b;
}

.selected-detail.accessible {
    color: #16a34a;
    font-weight: 700;
}

.st-key-nav_action_button button {
    min-height: 3.25rem;
    border-radius: 16px;
    background: #0f172a;
    color: #ffffff;
    border: 1px solid #0f172a;
    font-size: 0.98rem;
    font-weight: 800;
}

.st-key-nav_action_button button:hover {
    background: #020617;
    border-color: #020617;
    color: #ffffff;
}

.assist-copy {
    color: #0f172a;
    font-size: 0.96rem;
    font-weight: 800;
    margin-bottom: 0.32rem;
}

.assist-subcopy {
    color: #64748b;
    font-size: 0.85rem;
    margin-bottom: 0.78rem;
    line-height: 1.5;
}

.typing {
    display: inline-flex;
    gap: 0.22rem;
    align-items: center;
    padding: 0.25rem 0.1rem;
}

.typing span {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: #94a3b8;
    display: inline-block;
    animation: blink 1.1s infinite ease-in-out;
}

.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.30s; }

@keyframes blink {
    0%, 80%, 100% { opacity: 0.28; transform: translateY(0); }
    40% { opacity: 1; transform: translateY(-1px); }
}

.st-key-assistant_dock {
    position: fixed;
    right: 1.3rem;
    bottom: 1.1rem;
    width: 19rem;
    z-index: 999;
    padding: 0.95rem;
    box-shadow: 0 24px 52px rgba(15, 23, 42, 0.16);
}

.st-key-assistant_dock button {
    min-height: 3rem;
    border-radius: 999px;
    font-size: 0.98rem;
    font-weight: 800;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    border: 1px solid rgba(148, 163, 184, 0.22);
    color: #0f172a;
}

.st-key-assistant_dock button:hover {
    border-color: rgba(37, 99, 235, 0.35);
    color: #2563eb;
}

.st-key-floating_chat_panel,
.st-key-floating_voice_panel {
    position: fixed;
    right: 1.1rem;
    bottom: -0.2rem;
    width: min(28.5rem, calc(100vw - 1rem));
    z-index: 998;
    padding: 1rem 1rem 1.1rem 1rem;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    box-shadow: 0 28px 62px rgba(15, 23, 42, 0.22);
}

.st-key-chat_widget_panel,
.st-key-voice_widget_panel {
    background: transparent;
    border: none;
    box-shadow: none;
    padding: 0;
}

.widget-header-title {
    color: #0f172a;
    font-size: 1.06rem;
    font-weight: 800;
    padding-top: 0.1rem;
}

[class*="st-key-widget_icon_button_"] button {
    min-height: 2.6rem;
    width: 2.6rem;
    border-radius: 50%;
    padding: 0;
    background: linear-gradient(135deg, #ffffff, #f0f4ff);
    color: #1e293b;
    border: none;
    font-weight: 700;
    font-size: 1.1rem;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    transition: all 0.2s ease-in-out;
}

[class*="st-key-widget_icon_button_"] button:hover {
    background: linear-gradient(135deg, #dbeafe, #93c5fd);
    color: #1e40af;
    transform: scale(1.1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.voice-panel-note {
    color: #64748b;
    font-size: 0.92rem;
    text-align: center;
    margin-top: 0rem;
    margin-bottom: 1.5rem;
}

/* ── Minimised dock pill ───────────────────────────────────────────── */
.st-key-assistant_dock_mini {
    position: fixed;
    right: 1.3rem;
    bottom: 1.1rem;
    width: fit-content;
    z-index: 999;
}

.st-key-assistant_dock_mini button {
    min-height: 3rem;
    border-radius: 999px;
    font-size: 0.96rem;
    font-weight: 800;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff !important;
    border: none;
    padding: 0.5rem 1.4rem;
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.38);
    transition: all 0.2s ease-in-out;
}

.st-key-assistant_dock_mini button:hover {
    background: linear-gradient(135deg, #1d4ed8, #1e40af);
    box-shadow: 0 8px 26px rgba(37, 99, 235, 0.50);
    transform: translateY(-2px);
}

/* ── Dock close button ─────────────────────────────────────────────── */
.st-key-widget_icon_button_dock_close button {
    min-height: 2rem !important;
    width: 2rem !important;
    border-radius: 50% !important;
    padding: 0 !important;
    background: #f1f5f9 !important;
    color: #64748b !important;
    border: 1px solid #e2e8f0 !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    box-shadow: none !important;
    line-height: 1 !important;
    margin-top: -0.1rem;
}

.st-key-widget_icon_button_dock_close button:hover {
    background: #fee2e2 !important;
    color: #dc2626 !important;
    border-color: #fecaca !important;
    transform: none !important;
}

/* ═══════════════════════════════════════════════════════════════════
   MOBILE RESPONSIVE (≤ 768 px) - DESKTOP VIEWPORT ADJUSTMENTS
   ═══════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    .st-key-mobile_viewport {
        display: block !important;
    }

    .st-key-desktop_viewport {
        display: none !important;
    }

    .block-container {
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        padding-bottom: 5rem;
    }

    .hero-wrap { padding-bottom: 0.5rem; }
    .hero-title { font-size: 2rem; }
    .hero-subtitle { font-size: 0.85rem; margin-top: 0.35rem; }

    .st-key-search_panel,
    .st-key-destination_panel,
    .st-key-status_panel,
    .st-key-selected_panel {
        padding: 0.8rem 0.85rem 0.9rem 0.85rem;
        border-radius: 16px;
    }

    .st-key-search_panel [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    .st-key-search_panel [data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 0 !important;
    }

    [data-testid="stHorizontalBlock"]:has(.st-key-destination_panel) {
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-destination_panel)
        > [data-testid="stColumn"]:first-child {
        order: 2;
        width: 100% !important;
        flex: 1 1 100% !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-destination_panel)
        > [data-testid="stColumn"]:last-child {
        order: 1;
        width: 100% !important;
        flex: 1 1 100% !important;
    }

    .st-key-status_panel { padding: 0.55rem 0.85rem !important; }
    .st-key-status_panel .section-title,
    .st-key-status_panel .section-subtitle { display: none; }
    .status-grid {
        grid-template-columns: auto 1fr;
        gap: 0.35rem 0.6rem;
        font-size: 0.84rem;
    }

    .st-key-selected_panel .section-subtitle { display: none; }
    .selected-description { font-size: 0.88rem; }
    .selected-details { gap: 0.5rem; padding-bottom: 0.75rem; }

    .st-key-destination_panel [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    .st-key-destination_panel [data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 0 !important;
    }
    [class*="st-key-destination_card_"] {
        padding: 0.6rem 0.8rem 0.65rem 0.8rem;
        border-radius: 14px;
    }
    .destination-description { display: none; }
    .destination-meta { margin-bottom: 0.5rem; }

    .st-key-destination_panel [data-testid="stVerticalBlockBorderWrapper"] {
        height: auto !important;
        max-height: 52vh !important;
        overflow-y: auto !important;
        overscroll-behavior: contain;
    }
    .st-key-destination_panel
        [data-testid="stVerticalBlockBorderWrapper"] > div {
        height: auto !important;
    }

    .st-key-chat_widget_panel  [data-testid="stHorizontalBlock"]:first-of-type,
    .st-key-voice_widget_panel [data-testid="stHorizontalBlock"]:first-of-type,
    .st-key-assistant_dock     [data-testid="stHorizontalBlock"]:first-of-type {
        flex-wrap: nowrap !important;
        flex-direction: row !important;
        align-items: center !important;
    }
    .st-key-chat_widget_panel  [data-testid="stHorizontalBlock"]:first-of-type
        [data-testid="stColumn"]:first-child,
    .st-key-voice_widget_panel [data-testid="stHorizontalBlock"]:first-of-type
        [data-testid="stColumn"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }
    .st-key-chat_widget_panel  [data-testid="stHorizontalBlock"]:first-of-type
        [data-testid="stColumn"]:not(:first-child),
    .st-key-voice_widget_panel [data-testid="stHorizontalBlock"]:first-of-type
        [data-testid="stColumn"]:not(:first-child) {
        flex: 0 0 2.6rem !important;
        min-width: 0 !important;
    }

    .st-key-floating_chat_panel,
    .st-key-floating_voice_panel {
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100vw !important;
        border-radius: 20px 20px 0 0 !important;
        padding: 0.75rem 0.8rem 1rem 0.8rem !important;
    }

    .st-key-assistant_dock {
        left: 0.5rem !important;
        right: 0.5rem !important;
        width: auto !important;
    }

    .st-key-assistant_dock_mini {
        right: 0.75rem !important;
        bottom: 0.85rem !important;
    }

    .st-key-assistant_dock [data-testid="stHorizontalBlock"]:last-of-type {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }

    .st-key-assistant_dock [data-testid="stHorizontalBlock"]:last-of-type
        [data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
    }
}

@media (max-width: 960px) and (min-width: 769px) {
    .hero-title {
        font-size: 2rem;
    }

    .st-key-assistant_dock,
    .st-key-floating_chat_panel,
    .st-key-floating_voice_panel {
        width: calc(100vw - 1rem);
        right: 0.5rem;
    }
}
</style>
"""


def inject_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)