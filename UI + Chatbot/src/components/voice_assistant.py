from functools import lru_cache

import streamlit as st


VOICE_ASSISTANT_HTML = """
<div class="voice-assistant-root">
  <button class="voice-orb" type="button" aria-label="Voice assistant microphone">
    <span class="voice-orb-icon">🎙️</span>
  </button>
  <div class="voice-status">Prêt</div>
  <div class="voice-hint">Touchez l'orbe pour parler, puis touchez à nouveau pour envoyer.</div>
</div>
"""


VOICE_ASSISTANT_CSS = """
.voice-assistant-root {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  padding: 0.35rem 0 0.8rem 0;
}

.voice-orb {
  width: 170px;
  height: 170px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.18) 28%, transparent 29%),
    linear-gradient(145deg, #1f2937 0%, #111827 58%, #020617 100%);
  color: white;
  box-shadow:
    0 0 0 18px rgba(15, 23, 42, 0.06),
    0 24px 60px rgba(15, 23, 42, 0.28);
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
}

.voice-orb:hover {
  transform: scale(1.02);
  filter: brightness(1.03);
}

.voice-orb:active {
  transform: scale(0.98);
}

.voice-orb.listening {
  animation: voice-pulse 1.3s infinite ease-in-out;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.18) 28%, transparent 29%),
    linear-gradient(145deg, #2563eb 0%, #1d4ed8 55%, #0f172a 100%);
  box-shadow:
    0 0 0 18px rgba(37, 99, 235, 0.12),
    0 24px 60px rgba(37, 99, 235, 0.26);
}

.voice-orb.processing,
.voice-orb.speaking {
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.18) 28%, transparent 29%),
    linear-gradient(145deg, #38bdf8 0%, #2563eb 52%, #0f172a 100%);
}

.voice-orb-icon {
  font-size: 3.25rem;
  line-height: 1;
}

.voice-status {
  color: #0f172a;
  font-size: 1.08rem;
  font-weight: 800;
  text-align: center;
}

.voice-hint {
  color: #64748b;
  font-size: 0.93rem;
  text-align: center;
  line-height: 1.45;
  max-width: 20rem;
}

@keyframes voice-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.03); }
  100% { transform: scale(1); }
}
"""


VOICE_ASSISTANT_JS = r"""
export default function(component) {
    // =============================================
    // FIND THE ACTUAL DOM ELEMENT
    // =============================================
    let root = component.element || component.parentElement;

    // Fallback: query from document if component.element is not a DOM node
    if (!root || typeof root.querySelector !== "function") {
        root = document.querySelector(".voice-assistant-root");
    }

    if (!root) {
        console.error("[VOICE_ORB] Could not find root DOM element");
        return;
    }

    const orb = root.querySelector(".voice-orb");
    const status = root.querySelector(".voice-status");
    const hint = root.querySelector(".voice-hint");

    if (!orb || !status || !hint) {
        console.error("[VOICE_ORB] Could not find orb/status/hint elements");
        return;
    }

    // =============================================
    // PERSIST STATE IN WINDOW (survives everything)
    // =============================================
    const STATE_KEY = "__voice_orb_state__";
    if (!window[STATE_KEY]) {
        window[STATE_KEY] = {};
    }
    const state = window[STATE_KEY];

    let isBusy = state.isBusy || false;
    let lastHandledNonce = state.lastHandledNonce || null;

    const setIsBusy = function(val) { isBusy = val; state.isBusy = val; };
    const setLastHandledNonce = function(val) { lastHandledNonce = val; state.lastHandledNonce = val; };

    // MediaRecorder (transient, ok to lose on rerun)
    let mediaRecorder = null;
    let mediaStream = null;
    let chunks = [];

    // Audio element - persist in window
    const AUDIO_KEY = "__voice_orb_audio__";
    let currentAudio = window[AUDIO_KEY] || null;
    const saveAudioRef = function(audio) {
        currentAudio = audio;
        window[AUDIO_KEY] = audio;
    };

    // =============================================
    // UI STATE
    // =============================================
    const resetVisualState = function() {
        orb.classList.remove("listening", "processing", "speaking");
        status.textContent = "Prêt";
        hint.textContent = "Touchez l'orbe pour parler, puis touchez à nouveau pour envoyer.";
    };

    const setVisualState = function(mode, label, hintText) {
        orb.classList.remove("listening", "processing", "speaking");
        if (mode) orb.classList.add(mode);
        status.textContent = label;
        hint.textContent = hintText;
    };

    // =============================================
    // UTILS
    // =============================================
    const blobToBase64 = function(blob) {
        return new Promise(function(resolve, reject) {
            var reader = new FileReader();
            reader.onloadend = function() {
                var result = String(reader.result || "");
                resolve(result.indexOf(",") !== -1 ? result.split(",")[1] : "");
            };
            reader.onerror = function() { reject(reader.error); };
            reader.readAsDataURL(blob);
        });
    };

    const stopTracks = function() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(function(t) { t.stop(); });
            mediaStream = null;
        }
    };

    // =============================================
    // SEND TO STREAMLIT
    // =============================================
    const sendRecording = async function(blob, mimeType) {
        var audioBase64 = await blobToBase64(blob);
        var nonce = Date.now();

        setIsBusy(true);
        setVisualState("processing", "Traitement...", "Le robot prépare sa réponse.");

        component.setTriggerValue("voice_input", {
            nonce: nonce,
            audio_base64: audioBase64,
            mime_type: mimeType,
            conversation_id: data.conversation_id
        });
    };

    // =============================================
    // RECORDING
    // =============================================
    const startRecording = async function() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("Microphone not supported.");
            }

            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

            var mimeType = "";
            if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
                mimeType = "audio/webm;codecs=opus";
            } else if (MediaRecorder.isTypeSupported("audio/webm")) {
                mimeType = "audio/webm";
            }

            mediaRecorder = mimeType
                ? new MediaRecorder(mediaStream, { mimeType: mimeType })
                : new MediaRecorder(mediaStream);

            chunks = [];

            mediaRecorder.ondataavailable = function(e) {
                if (e.data && e.data.size > 0) chunks.push(e.data);
            };

            mediaRecorder.onstop = async function() {
                try {
                    var actualMime = mediaRecorder.mimeType || "audio/webm";
                    var blob = new Blob(chunks, { type: actualMime });
                    stopTracks();
                    await sendRecording(blob, actualMime);
                } catch (err) {
                    setIsBusy(false);
                    setVisualState("", "Erreur capture", "Veuillez réessayer.");
                    component.setTriggerValue("error", String(err));
                }
            };

            mediaRecorder.start();
            setVisualState("listening", "J'écoute...", "Touchez encore l'orbe quand terminé.");
        } catch (err) {
            setVisualState("", "Micro bloqué", "Autorisez le micro.");
            component.setTriggerValue("error", String(err));
        }
    };

    const stopRecording = function() {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        }
    };

    // =============================================
    // HANDLE RESPONSE FROM PYTHON
    // =============================================
    var data = component.data || {};

    if (data.response) {
        var payload = data.response;
        var payloadNonce = payload.nonce;

        console.log("[VOICE_ORB] Response received, nonce:", payloadNonce, "last:", lastHandledNonce);

        if (payloadNonce !== lastHandledNonce) {
            setLastHandledNonce(payloadNonce);

            // Stop previous audio
            if (currentAudio) {
                currentAudio.onended = null;
                currentAudio.onerror = null;
                currentAudio.pause();
                currentAudio.src = "";
                saveAudioRef(null);
            }

            if (!payload.response_audio_base64) {
                console.warn("[VOICE_ORB] No audio data");
                setIsBusy(false);
                resetVisualState();
            } else {
                var mime = payload.response_audio_mime_type || "audio/wav";
                var dataUri = "data:" + mime + ";base64," + payload.response_audio_base64;

                console.log("[VOICE_ORB] Creating audio element, URI length:", dataUri.length);

                var audio = new Audio(dataUri);
                audio.preload = "auto";

                saveAudioRef(audio);
                setVisualState("speaking", "Réponse vocale", "Le robot parle...");

                var playPromise = audio.play();

                if (playPromise !== undefined) {
                    playPromise.then(function() {
                        console.log("[VOICE_ORB] Audio playing");
                        audio.onended = function() {
                            console.log("[VOICE_ORB] Audio ended");
                            setIsBusy(false);
                            resetVisualState();
                            component.setTriggerValue("playback_finished", payloadNonce);
                        };
                        audio.onerror = function(e) {
                            console.error("[VOICE_ORB] Audio error", e);
                            setIsBusy(false);
                            setVisualState("", "Erreur audio", "Lecture échouée.");
                            component.setTriggerValue("error", "Audio playback error");
                        };
                    }).catch(function(err) {
                        if (err.name === "AbortError") return;

                        console.error("[VOICE_ORB] Play failed:", err.name, err.message);

                        if (err.name === "NotAllowedError") {
                            setIsBusy(false);
                            setVisualState("", "Audio prêt", "Cliquez pour écouter.");
                            return;
                        }

                        setIsBusy(false);
                        setVisualState("", "Erreur: " + err.name, err.message);
                        component.setTriggerValue("error", err.name + ": " + err.message);
                    });
                }
            }
        }
    }

    // =============================================
    // CLICK HANDLER
    // =============================================
    orb.onclick = async function() {
        if (isBusy) return;

        if (mediaRecorder && mediaRecorder.state === "recording") {
            stopRecording();
        } else {
            await startRecording();
        }
    };

    // =============================================
    // RESET HANDLING
    // =============================================
    if (data.reset_token && data.reset_token !== state.resetToken) {
        state.resetToken = data.reset_token;

        if (currentAudio) {
            currentAudio.pause();
            currentAudio.src = "";
            saveAudioRef(null);
        }

        setIsBusy(false);
        setLastHandledNonce(null);
        resetVisualState();
    }

    // Sync visual state
    if (!isBusy && !(mediaRecorder && mediaRecorder.state === "recording")) {
        if (!orb.classList.contains("speaking")) {
            resetVisualState();
        }
    }

    // =============================================
    // TEARDOWN
    // =============================================
    return function() {
        stopTracks();
    };
}
"""

@lru_cache(maxsize=1)
def _get_voice_component():
    return st.components.v2.component(
        "voice_assistant_orb",
        html=VOICE_ASSISTANT_HTML,
        css=VOICE_ASSISTANT_CSS,
        js=VOICE_ASSISTANT_JS,
    )


def voice_assistant_orb(*, key: str, data: dict | None = None):
    component = _get_voice_component()
    return component(key=key, data=data or {})