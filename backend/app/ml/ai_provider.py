"""
ml/ai_provider.py
=================
AI / XAI provider abstraction.

    AIProvider (base)
      ├── DeterministicExplanationProvider   (always available, no network)
      └── ExternalLLMProvider                (used only if LLM_API_KEY set)

CONTRACT
--------
- The application MUST work with no API key.
- The AI explains the ALREADY-DECIDED deterministic health state. It never
  decides or overrides fault class / advisory.
- Explanations MUST reference actual evidence (residual numbers, fault class).
- If the external LLM fails for any reason, we fall back to the deterministic
  explainer. The app never crashes because the LLM is down.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("vajra.ai")


class AIProvider:
    name = "base"

    def explain(self, context: Dict[str, object]) -> Dict[str, object]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Deterministic explainer — always available
# ---------------------------------------------------------------------------
class DeterministicExplanationProvider(AIProvider):
    name = "deterministic"

    def explain(self, context: Dict[str, object]) -> Dict[str, object]:
        fault = context.get("fault", {}) or {}
        advisory = context.get("advisory", {}) or {}
        residuals = context.get("residuals", {}) or {}
        anomaly = context.get("anomaly", {}) or {}
        state = context.get("twin_state", {}) or {}

        fault_label = fault.get("fault_label", "Normal")
        advisory_state = advisory.get("state", "GO")
        anomaly_status = anomaly.get("anomaly_status", "NOMINAL")

        d_egt = float(residuals.get("delta_egt_c", 0.0))
        d_cht = float(residuals.get("delta_cht_c", 0.0))
        d_oilp = float(residuals.get("delta_oil_pressure_psi", 0.0))
        d_vib = float(residuals.get("delta_vibration_rms_g", 0.0))
        load = float(state.get("load_factor", 0.0))

        if fault.get("fault_class") == "NORMAL":
            text = (
                f"All monitored residuals are within normal scatter "
                f"(ΔEGT {d_egt:+.1f} °C, ΔCHT {d_cht:+.1f} °C). "
                f"Engine is synchronised with the physics twin and operating "
                f"nominally at load factor {load:.2f}. Advisory: {advisory_state}."
            )
        else:
            # cite the dominant evidence channels
            parts: List[str] = []
            if abs(d_egt) >= 20:
                parts.append(f"EGT is {d_egt:+.1f} °C vs the physics baseline")
            if abs(d_cht) >= 12:
                parts.append(f"CHT is {d_cht:+.1f} °C vs baseline")
            if d_oilp <= -8:
                parts.append(f"oil pressure is {d_oilp:+.1f} psi below expected")
            if d_vib >= 0.5:
                parts.append(f"vibration is {d_vib:+.2f} g above baseline")
            detail = "; ".join(parts) if parts else "residuals have crossed warning thresholds"
            text = (
                f"{fault_label} detected ({anomaly_status}). "
                f"{detail.capitalize()}. The deviation is concentrated at load "
                f"factor {load:.2f}. Deterministic advisory: {advisory_state}. "
                f"{advisory.get('recommended_action', '')}"
            )

        return {
            "explanation": text.strip(),
            "explanation_source": "deterministic",
            "references_evidence": True,
        }


# ---------------------------------------------------------------------------
# External LLM explainer — optional, degrades gracefully
# ---------------------------------------------------------------------------
class ExternalLLMProvider(AIProvider):
    name = "external_llm"

    def __init__(self) -> None:
        self._fallback = DeterministicExplanationProvider()

    def _build_prompt(self, context: Dict[str, object]) -> str:
        fault = context.get("fault", {}) or {}
        advisory = context.get("advisory", {}) or {}
        residuals = context.get("residuals", {}) or {}
        return (
            "You are an aerospace engine-health diagnostics assistant. The "
            "deterministic health engine has ALREADY decided the state below. "
            "Explain it in 2-3 sentences for a UAV operator. Reference the "
            "actual residual numbers. DO NOT change the advisory or fault class.\n\n"
            f"Fault class : {fault.get('fault_class')}\n"
            f"Advisory    : {advisory.get('state')}\n"
            f"Residuals   : {residuals}\n"
        )

    def explain(self, context: Dict[str, object]) -> Dict[str, object]:
        try:
            import httpx  # local import so the app has no hard dep when unused

            prompt = self._build_prompt(context)
            headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
            payload = {
                "model": settings.LLM_MODEL or "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 220,
            }
            base = settings.LLM_API_BASE or "https://api.openai.com/v1"
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(f"{base}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
            return {
                "explanation": text,
                "explanation_source": "external_llm",
                "references_evidence": True,
            }
        except Exception as exc:  # noqa: BLE001 — any failure => deterministic
            logger.warning("External LLM failed (%s); using deterministic explainer", exc)
            out = self._fallback.explain(context)
            out["explanation_source"] = "deterministic_fallback"
            return out


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_PROVIDER: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    global _PROVIDER
    if _PROVIDER is None:
        if settings.llm_enabled:
            logger.info("AI provider: ExternalLLMProvider (%s)", settings.LLM_MODEL or "default")
            _PROVIDER = ExternalLLMProvider()
        else:
            logger.info("AI provider: DeterministicExplanationProvider (no LLM key configured)")
            _PROVIDER = DeterministicExplanationProvider()
    return _PROVIDER
