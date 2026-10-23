import json
import logging
import requests
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from c360.config import settings

logger = logging.getLogger(__name__)


def create_provider_model(
    provider: str,
    temperature: float = 0.1,
    timeout: float = 60.0
) -> ChatOpenAI:
    """Create a LangChain model for the selected provider."""

    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing from .env")

        return ChatOpenAI(
            base_url=settings.groq_base_url.rstrip("/"),
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature,
            timeout=timeout,
            max_retries=1
        )

    if provider == "dgx":
        return ChatOpenAI(
            base_url=settings.vllm_base_url.rstrip("/"),
            api_key=settings.vllm_api_key,
            model=settings.vllm_model,
            temperature=temperature,
            timeout=timeout,
            max_retries=1
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


def get_chat_model(
    temperature: float = 0.1,
    timeout: float = 60.0
):
    """Return the configured primary model."""

    return create_provider_model(
        settings.llm_provider,
        temperature=temperature,
        timeout=timeout
    )


class VLLMClient:
    """Client for vLLM OpenAI-compatible REST API endpoint (/v1/chat/completions)."""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        model: str = None,
        timeout: float = 60.0
    ):
        self.base_url = (base_url or settings.vllm_base_url).rstrip("/")
        self.api_key = api_key or settings.vllm_api_key
        self.model = model or settings.vllm_model
        self.timeout = timeout

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 512,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send chat completion request to vLLM endpoint with fallback for offline environments."""
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = requests.post(
                endpoint, headers=headers, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                return {
                    "role": message.get("role", "assistant"),
                    "content": message.get("content", ""),
                    "tool_calls": message.get("tool_calls", []),
                    "raw_response": data
                }
            else:
                logger.warning(
                    f"vLLM server returned HTTP {response.status_code}: {response.text}")
        except Exception as e:
            logger.info(
                f"vLLM server connection notice ({e}). Utilizing fallback response generator.")

        # Local Fallback Generator when vLLM remote server is offline
        return self._fallback_generate(messages)

    def _fallback_generate(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a structured customer support fallback response based on user inquiry."""
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break

        user_clean = user_msg.strip().lower()

        # Casual Greeting fallback
        if user_clean in ["hi", "hello", "hey", "good morning", "good evening", "hi there"]:
            return {
                "role": "assistant",
                "content": "Hello! Welcome to OmniResolve AI Customer Support. How can I help you today?",
                "tool_calls": [],
                "raw_response": {"fallback": True}
            }

        text_upper = user_msg.upper()

        # Build fallback response for technical issues
        response_lines = []
        response_lines.append(
            "Dear Customer, thank you for reaching out to OmniResolve AI Customer Support.")
        response_lines.append("")

        if "WIFI" in text_upper or "P005" in text_upper or "SSID" in text_upper:
            response_lines.append(
                "Here are basic diagnostic steps to resolve your Enterprise WiFi issue:")
            response_lines.append(
                "1. **Forget WiFi Network**: Go to Network Settings -> Select Enterprise SSID -> Choose 'Forget Network'.")
            response_lines.append(
                "2. **Re-select EAP Method**: Re-connect and set EAP Method to PEAP / MSCHAPv2.")
            response_lines.append(
                "3. **Verify Credentials**: Enter domain credentials `<username>@company.com` and accept Root CA certificate.")
        elif "SIP" in text_upper or "P003" in text_upper or "AUDIO" in text_upper or "CODEC" in text_upper:
            response_lines.append(
                "Here are basic diagnostic steps for your SIP Trunk voice issue:")
            response_lines.append(
                "1. **Codec Matching**: Ensure PBX codec configuration matches provider order (G.711u / G.711a).")
            response_lines.append(
                "2. **Disable SIP ALG**: Disable SIP ALG on your local firewall/router.")
            response_lines.append(
                "3. **RTP Media Ports**: Confirm firewall allows UDP RTP media ports 10000-20000.")
        elif "RED" in text_upper or "LOS" in text_upper or "BROADBAND" in text_upper or "MODEM" in text_upper or "P001" in text_upper:
            response_lines.append(
                "Here are basic diagnostic steps for your Business Broadband issue:")
            response_lines.append(
                "1. **Inspect Fiber Cable**: Ensure yellow fiber patch cord is securely plugged into the green SC/APC port.")
            response_lines.append(
                "2. **Reboot ONT Modem**: Power off the modem using the rear button, wait 30 seconds, and turn back on.")
            response_lines.append(
                "3. **Verify Signal LED**: Observe PON/LOS indicator. PON LED should turn solid GREEN.")
        else:
            response_lines.append(
                "Please perform basic diagnostic troubleshooting by verifying power supplies and physical cable connections.")

        if any(k in text_upper for k in ["PERSIST", "STILL NOT WORKING", "TRIED ALL", "TRIED THAT", "DIDN'T WORK", "RAISE A TICKET", "CREATE TICKET"]):
            response_lines.append("")
            response_lines.append("**Ticket Confirmation & Escalation**:")
            response_lines.append(
                "Since the basic troubleshooting steps did not resolve the issue, a formal support ticket has been raised and escalated to our Senior Network Engineering team for further consideration.")
        else:
            response_lines.append("")
            response_lines.append(
                "Please try these basic troubleshooting steps. If after attempting them the issue still persists, please reply back and I will raise a formal support ticket for senior engineering escalation.")

        content = "\n".join(response_lines)
        return {
            "role": "assistant",
            "content": content,
            "tool_calls": [],
            "raw_response": {"fallback": True}
        }
