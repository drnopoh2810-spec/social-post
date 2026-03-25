import requests
import json
import logging

logger = logging.getLogger(__name__)

COHERE_BASE = "https://api.cohere.com/v2/chat"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# OpenAI-compatible base URLs for each provider
PROVIDER_BASE_URLS = {
    "cohere":     "https://api.cohere.com/v2/chat",
    "groq":       "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai":     "https://api.openai.com/v1/chat/completions",
}


# ── Low-level callers (accept a single api_key) ───────────────────────────────

def _call_cohere(api_key: str, model: str, system_prompt: str, user_prompt: str,
                 temperature=0.8, max_tokens=2048) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    r = requests.post(COHERE_BASE, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("message", {}).get("content", [{}])[0].get("text", "")


def _call_openai_compat(api_key: str, model: str, system_prompt: str, user_prompt: str,
                        temperature=0.8, max_tokens=2048, base_url: str = "") -> str:
    """Generic OpenAI-compatible endpoint (Groq, OpenRouter, OpenAI)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    r = requests.post(base_url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _call_gemini(api_key: str, model: str, system_prompt: str, user_prompt: str,
                 temperature=0.8, max_tokens=2048) -> str:
    url = f"{GEMINI_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Unified caller with key rotation ─────────────────────────────────────────

def call_ai(provider: str, model_id: str, system_prompt: str, user_prompt: str,
            temperature=0.8, max_tokens=2048) -> str:
    """
    Call an AI provider with automatic key rotation.
    Tries all available keys in priority order; raises on total exhaustion.
    """
    from services.key_rotator import call_with_rotation

    def _do_call(api_key: str) -> str:
        if provider == "gemini":
            return _call_gemini(api_key, model_id, system_prompt, user_prompt, temperature, max_tokens)
        elif provider == "cohere":
            return _call_cohere(api_key, model_id, system_prompt, user_prompt, temperature, max_tokens)
        else:
            base_url = PROVIDER_BASE_URLS.get(provider, PROVIDER_BASE_URLS["openai"])
            return _call_openai_compat(api_key, model_id, system_prompt, user_prompt,
                                       temperature, max_tokens, base_url)

    return call_with_rotation(provider, _do_call)


# ── High-level task functions ─────────────────────────────────────────────────

def generate_ideas(niche, all_ideas, recent_ideas, saturated_topics, stats, prompt_row, provider):
    user_prompt = prompt_row.user_prompt \
        .replace("{niche}", niche) \
        .replace("{all_ideas_text}", all_ideas) \
        .replace("{recent_ideas_text}", recent_ideas) \
        .replace("{saturated_topics}", saturated_topics) \
        .replace("{total_ideas}", str(stats.get("total", 0))) \
        .replace("{total_posted}", str(stats.get("posted", 0))) \
        .replace("{total_pending}", str(stats.get("pending", 0))) \
        .replace("{post_sequence_num}", str(stats.get("posted", 0) + 1)) \
        .replace("{top5_performing}", stats.get("top5", "لا توجد بيانات")) \
        .replace("{bottom5_performing}", stats.get("bottom5", "لا توجد بيانات")) \
        .replace("{avg_engagement_score}", str(stats.get("avg_score", 0))) \
        .replace("{performance_summary}", stats.get("perf_summary", "أول دورة")) \
        .replace("{recent_styles}", stats.get("recent_styles", "")) \
        .replace("{recent_openings}", stats.get("recent_openings", "")) \
        .replace("{last_post_snippet}", stats.get("last_snippet", ""))

    raw = call_ai(provider, prompt_row.model, prompt_row.system_prompt, user_prompt,
                  prompt_row.temperature, prompt_row.max_tokens)

    import re
    cleaned = re.sub(r'```json\s*', '', raw)
    cleaned = re.sub(r'```\s*', '', cleaned).strip()
    start = cleaned.find('[')
    end = cleaned.rfind(']')
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array in response: {raw[:300]}")
    return json.loads(cleaned[start:end + 1])


def write_post(idea_data, niche, prompt_row, provider):
    user_prompt = prompt_row.user_prompt \
        .replace("{niche}", niche) \
        .replace("{idea}", idea_data.get("idea", "")) \
        .replace("{keywords}", idea_data.get("keywords", "")) \
        .replace("{tone}", idea_data.get("tone", "")) \
        .replace("{writing_style}", idea_data.get("writing_style", "")) \
        .replace("{opening_type}", idea_data.get("opening_type", "")) \
        .replace("{last_post_snippet}", idea_data.get("last_snippet", ""))

    return call_ai(provider, prompt_row.model, prompt_row.system_prompt, user_prompt,
                   prompt_row.temperature, prompt_row.max_tokens)


def generate_image_prompt(idea_data, niche, width, height, prompt_row, provider):
    user_prompt = prompt_row.user_prompt \
        .replace("{niche}", niche) \
        .replace("{idea}", idea_data.get("idea", "")) \
        .replace("{keywords}", idea_data.get("keywords", "")) \
        .replace("{tone}", idea_data.get("tone", "")) \
        .replace("{image_width}", str(width)) \
        .replace("{image_height}", str(height))

    return call_ai(provider, prompt_row.model, prompt_row.system_prompt, user_prompt,
                   prompt_row.temperature, prompt_row.max_tokens)


def adapt_caption(platform, post_content, prompt_row, provider):
    user_prompt = prompt_row.user_prompt.replace("{post_content}", post_content)
    return call_ai(provider, prompt_row.model, prompt_row.system_prompt, user_prompt,
                   prompt_row.temperature, prompt_row.max_tokens)
