"""Shared OpenAI SDK transport layer for MegaAgent.

Single implementation of the modern Chat Completions tool-use interface
(tools / tool_calls / role:"tool"). Every llm.py in this repo delegates
here; all framework logic, prompts and tool schemas stay in their
original files unchanged.
"""
import json
import logging

import httpx
from openai import OpenAI

_clients = {}


def get_client(api_key, base_url):
    key = (api_key, base_url)
    if key not in _clients:
        _clients[key] = OpenAI(
            api_key=api_key,
            base_url=base_url,
            # Reasoning models can think for a long time, so the read timeout
            # is generous — but not unlimited: some gateways occasionally
            # accept a request and never answer it, and an unbounded read
            # would hang that agent forever. 30 min covers any observed
            # xhigh generation with wide margin; the callers' retry loops
            # re-issue the request if it ever trips.
            timeout=httpx.Timeout(connect=30.0, read=1800.0, write=600.0, pool=30.0),
        )
    return _clients[key]


def wrap_tools(bare_tools):
    """Wrap legacy bare function schemas into the modern tools format.

    Only name/description/parameters are copied; stray top-level keys (e.g.
    a "required" list sitting next to "parameters") were never enforced by
    the legacy API and are dropped. A schema without "parameters"
    (terminate) gets the canonical empty object schema.
    """
    wrapped = []
    for t in bare_tools:
        fn = {"name": t["name"]}
        if "description" in t:
            fn["description"] = t["description"]
        fn["parameters"] = t.get("parameters", {"type": "object", "properties": {}})
        wrapped.append({"type": "function", "function": fn})
    return wrapped


def normalize_response(d):
    """Restore legacy dict semantics on a model_dump()'d response.

    Drops None-valued keys (model_dump artifacts like function_call/refusal)
    so that `'tool_calls' in message` is a reliable presence check, and
    guarantees message['content'] is always indexable.
    """
    for choice in d.get("choices") or []:
        msg = choice.get("message")
        if isinstance(msg, dict):
            for k in list(msg):
                if msg[k] is None and k != "content":
                    del msg[k]
            if not msg.get("tool_calls"):
                msg.pop("tool_calls", None)
            msg.setdefault("content", None)
    return d


def _to_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _clean_tool_calls(tool_calls):
    cleaned = []
    for tc in tool_calls:
        fn = tc.get("function") or {}
        arguments = fn.get("arguments")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments if arguments is not None else {})
        cleaned.append({
            "id": tc.get("id"),
            "type": "function",
            "function": {"name": fn.get("name"), "arguments": arguments},
        })
    return cleaned


def _clean_message(m):
    role = m.get("role")
    content = m.get("content")
    if role == "assistant":
        out = {"role": "assistant", "content": content}
        tool_calls = m.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            out["tool_calls"] = _clean_tool_calls(tool_calls)
        return out
    if role in ("tool", "function"):
        out = {"role": "tool", "content": _to_text(content)}
        if m.get("tool_call_id"):
            out["tool_call_id"] = m["tool_call_id"]
        return out
    if role in ("system", "user"):
        return {"role": role, "content": _to_text(content)}
    return {"role": "user", "content": _to_text(content)}


def sanitize_messages(messages):
    """Make an arbitrary stored history legal under the strict tool-use
    protocol, without changing how callers store their memories.

    The legacy API accepted loose role:"function" messages anywhere; the
    modern API requires every role:"tool" message to directly follow an
    assistant message carrying the matching tool_call id, and every id to
    be answered. Stored histories here violate that routinely (memory
    windowing, compaction rewrites, terminate short-circuits), so orphaned
    tool results are demoted to plain user text and unanswered tool_calls
    are stripped. Builds new dicts; never mutates the input.
    """
    cleaned = [_clean_message(m) for m in messages]
    out = []
    i = 0
    n = len(cleaned)
    while i < n:
        msg = cleaned[i]
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            ids = [tc["id"] for tc in msg["tool_calls"]]
            j = i + 1
            run = []
            while j < n and cleaned[j]["role"] == "tool":
                run.append(cleaned[j])
                j += 1
            answered = {t.get("tool_call_id") for t in run}
            if set(ids) <= answered:
                out.append(msg)
                seen = set()
                for t in run:
                    tcid = t.get("tool_call_id")
                    if tcid in ids and tcid not in seen:
                        seen.add(tcid)
                        out.append(t)
                    else:
                        out.append({"role": "user", "content": t["content"]})
            else:
                out.append({
                    "role": "assistant",
                    "content": msg["content"] if msg["content"] is not None else "",
                })
                for t in run:
                    out.append({"role": "user", "content": t["content"]})
            i = j
            continue
        if msg["role"] == "tool":
            out.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant" and msg.get("content") is None:
            out.append({"role": "assistant", "content": ""})
        else:
            out.append(msg)
        i += 1
    return out


def _accumulate_stream(stream):
    """Rebuild a complete non-streaming-shaped response dict from a chunk
    stream. Streaming is a transport detail here: some gateways enforce a
    response timeout (~120s observed) that kills any non-streamed request
    whose generation runs long — fatal for heavy reasoning calls. With
    streaming, bytes flow from the first chunk and the connection stays
    alive for arbitrarily long generations.
    """
    resp = {"id": None, "object": "chat.completion", "created": None,
            "model": None, "choices": [], "usage": None}
    slots = {}
    for chunk in stream:
        c = chunk.model_dump() if hasattr(chunk, "model_dump") else chunk
        for k in ("id", "created", "model"):
            if c.get(k):
                resp[k] = c[k]
        if c.get("usage"):
            resp["usage"] = c["usage"]
        for ch in c.get("choices") or []:
            idx = ch.get("index") or 0
            slot = slots.setdefault(idx, {
                "message": {"role": "assistant", "content": None, "tool_calls": {}},
                "finish_reason": None,
            })
            if ch.get("finish_reason"):
                slot["finish_reason"] = ch["finish_reason"]
            delta = ch.get("delta") or {}
            if delta.get("role"):
                slot["message"]["role"] = delta["role"]
            if delta.get("content") is not None:
                slot["message"]["content"] = (slot["message"]["content"] or "") + delta["content"]
            for tc in delta.get("tool_calls") or []:
                t = slot["message"]["tool_calls"].setdefault(tc.get("index") or 0, {
                    "id": None, "type": "function",
                    "function": {"name": None, "arguments": ""},
                })
                if tc.get("id"):
                    t["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    t["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    t["function"]["arguments"] += fn["arguments"]
    for idx in sorted(slots):
        slot = slots[idx]
        msg = slot["message"]
        # Some gateways emit the same tool call twice under different stream
        # indexes (same id, full payload each time) — dedupe by id, and drop
        # empty artifacts that never received any fragment.
        tool_calls, seen_ids = [], set()
        for i in sorted(msg["tool_calls"]):
            t = msg["tool_calls"][i]
            if not (t["id"] or t["function"]["name"] or t["function"]["arguments"]):
                continue
            if t["id"] and t["id"] in seen_ids:
                continue
            if t["id"]:
                seen_ids.add(t["id"])
            tool_calls.append(t)
        msg["tool_calls"] = tool_calls or None
        resp["choices"].append({"index": idx, "message": msg,
                                "finish_reason": slot["finish_reason"]})
    return resp


def chat_completion(messages, model, tools=None, api_key=None, base_url=None,
                    reasoning_effort=None):
    """One Chat Completions request. Returns the response as a plain dict
    (legacy shape), or {'error': str(e)} so callers' retry loops keep their
    original semantics. Deliberately sends no temperature and no
    max_tokens/max_completion_tokens. reasoning_effort is only sent when
    set (endpoints that encode effort in the model name don't need it).
    Always streams internally (see _accumulate_stream); callers still get
    one complete response dict.
    """
    try:
        sent = sanitize_messages(messages)
        # Gateway-compat shim: some gateways proxy chat.completions onto the
        # Responses API upstream and deterministically 502 on conversations
        # that contain no user/assistant turn (e.g. an agent whose memory is
        # still only its system prompt). An empty user turn is accepted and
        # adds no prompt text.
        if not any(m["role"] in ("user", "assistant") for m in sent):
            sent = sent + [{"role": "user", "content": ""}]
        kwargs = {
            "model": model,
            "messages": sent,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        stream = get_client(api_key, base_url).chat.completions.create(**kwargs)
        return normalize_response(_accumulate_stream(stream))
    except Exception as e:
        logging.error(f"LLM request failed: {e}")
        return {"error": str(e)}
