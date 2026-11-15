import json

import httpx

from app.core.config import settings
from app.services.geocoding import get_region_name

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_HISTORY = 12
MAX_ANALYSIS_CHARS = 5000

SYSTEM_PROMPT = """You are TerraWise Assistant a farming advisor inside the TerraWise app. You help farmers with two things:

1. WHERE TO BUY SEEDS
- Use the farm details below (location, size, soil pH, nitrogen, moisture, rainfall, \
temperature, last crop, water source, budget) to suggest which crops/varieties suit the farm, \
then where to buy their seeds.
- Prefer sources close to the farm's region: local agricultural cooperatives, government \
extension or agriculture offices, certified seed dealers, and well-known seed companies that ship \
to that country.
- Only name a specific shop, company, website or price if it appears in web search results you \
were given or you are certain it is real. Never invent businesses, addresses, phone numbers or \
prices. If you are not sure, describe the TYPE of seller to look for and how to verify it.
- Mention buying certified seed, checking germination rate and expiry date, and choosing \
varieties suited to the local climate. Respect the farmer's budget if one is given.
- Rotate crops: take the last crop planted into account.

2. AGRICULTURAL PESTS AND DISEASES
- If the farmer describes a problem, first ask the 1-2 most useful questions you still need \
(which crop, what the damage looks like, which part of the plant, how widespread, how long) \
unless they already gave enough detail.
- Give the most likely causes (not just one if unsure), how to confirm them, and what to do.
- Follow integrated pest management: start with cultural and biological controls (crop rotation, \
removing infected plants, beneficial insects, resistant varieties, correct watering), and only \
then mention chemical options, in general terms. Do not give exact pesticide doses; tell the \
farmer to follow the product label, local regulations and safety gear, and to check with the local \
agricultural extension office for confirmation.

STYLE
- Reply in the same language the farmer writes in.
- Be concise and clear: short paragraphs, simple words, a few steps at most.
- Use PLAIN TEXT only. No markdown symbols such as ** or # . For lists, start each line with "- ".
- If the farm data is missing or an error, say so and work with what you have; never make up \
measurements.
- Stay on farming topics. Politely steer other requests back to farming.
- You are an assistant, not a replacement for a local agronomist: for serious crop loss, \
suggest contacting one."""


class ChatConfigError(Exception):
    """The chatbot is not configured (e.g. missing API key)."""


class ChatUpstreamError(Exception):
    """OpenRouter failed or rejected the request."""


_region_cache: dict[tuple[float, float], dict | None] = {}


async def _region_for(lat: float, lng: float):
    # Cache by rounded coordinates so a conversation does not hit Nominatim
    # (1 request/second policy) on every message.
    key = (round(lat, 2), round(lng, 2))
    if key not in _region_cache:
        try:
            _region_cache[key] = await get_region_name(lat, lng)
        except Exception:
            _region_cache[key] = None
    return _region_cache[key]


def _compact_analysis(analysis: dict) -> str:
    compact = {}
    for name in ("rain", "temperature", "ph", "nitrogen", "moisture"):
        dataset = analysis.get(name)
        if not isinstance(dataset, dict):
            continue
        rows = dataset.get("rows") or []
        compact[name] = rows[:12] if rows else {"unavailable": dataset.get("error")}
    text = json.dumps(compact, separators=(",", ":"), default=str)
    return text[:MAX_ANALYSIS_CHARS]


async def build_farm_context(farm: dict | None) -> str:
    if not farm:
        return "No farm details were provided. Ask the farmer where the farm is and what they grow."

    lines = []
    lat, lng = farm.get("lat"), farm.get("lng")
    if lat is not None and lng is not None:
        region = await _region_for(lat, lng)
        lines.append(f"Farm coordinates: {lat:.5f}, {lng:.5f}")
        if region:
            lines.append(
                f"Nearest place: {region.get('region')}, {region.get('country')}"
                f" ({region.get('display_name')})"
            )
    else:
        lines.append("Farm location: not selected yet.")

    if farm.get("acres") is not None:
        lines.append(f"Farm size: {farm['acres']} acres ({farm.get('hectares')} hectares)")
    for label, key in (
        ("Last crop planted", "last_crop"),
        ("Water source", "water_source"),
        ("Budget", "budget"),
    ):
        if farm.get(key):
            lines.append(f"{label}: {farm[key]}")

    if farm.get("analysis"):
        lines.append(
            "Terawise analysis for this location (JSON, rainfall in mm, temperature in C, "
            "nitrogen in g/kg, moisture in %): " + _compact_analysis(farm["analysis"])
        )
    else:
        lines.append("The farmer has not run 'Analyze My Farm' yet, so there is no soil/climate data.")

    return "\n".join(lines)


def _sources(message: dict) -> list[dict]:
    seen, sources = set(), []
    for note in message.get("annotations") or []:
        citation = note.get("url_citation") if isinstance(note, dict) else None
        url = citation.get("url") if citation else None
        if url and url not in seen:
            seen.add(url)
            sources.append({"title": citation.get("title") or url, "url": url})
    return sources[:5]


async def generate_reply(messages: list[dict], farm: dict | None) -> dict:
    if not settings.OPENROUTER_API_KEY:
        raise ChatConfigError(
            "The AI assistant is not configured. Add OPENROUTER_API_KEY to backend/.env."
        )

    farm_context = await build_farm_context(farm)
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "temperature": 0.4,
        "max_tokens": 900,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nFARM DETAILS:\n" + farm_context},
            *messages[-MAX_HISTORY:],
        ],
    }
    if settings.OPENROUTER_WEB_SEARCH:
        payload["plugins"] = [{"id": "web", "max_results": 5}]

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": "TerraWise",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
    except httpx.HTTPError:
        raise ChatUpstreamError("Could not reach the AI service. Please try again.")

    if response.status_code in (401, 403):
        raise ChatUpstreamError("The AI service rejected the API key.")
    if response.status_code == 402:
        raise ChatUpstreamError("The AI service account is out of credits.")
    if response.status_code == 429:
        raise ChatUpstreamError("The AI service is busy. Please wait a moment and try again.")
    if response.status_code >= 400:
        raise ChatUpstreamError(f"The AI service returned an error ({response.status_code}).")

    try:
        message = response.json()["choices"][0]["message"]
        reply = (message.get("content") or "").strip()
    except (ValueError, KeyError, IndexError, TypeError):
        raise ChatUpstreamError("The AI service returned an unexpected response.")

    if not reply:
        raise ChatUpstreamError("The AI service returned an empty answer. Please try again.")

    return {"reply": reply, "sources": _sources(message)}