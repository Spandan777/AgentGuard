"""Small provider abstraction for the dynamic two-agent AgentGuard demo.

No API keys are stored in this project. Providers read API keys from
environment variables at runtime.
"""

import json
import os
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv
from groq import Groq


# Load variables from .env
load_dotenv()


class LLMError(RuntimeError):
    """Raised when an LLM provider cannot complete a request."""
    pass


class LLMProvider:
    """Base interface for LLM providers."""

    name = "base"

    def generate_json(self, system: str, user: str) -> dict:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    """Gemini provider used by Agent 1."""

    name = "gemini"

    def __init__(self, model=None):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

        self.model = model or os.getenv(
            "AGENTGUARD_GEMINI_MODEL",
            "gemini-3.6-flash",
        )

        fallback_raw = os.getenv(
            "AGENTGUARD_GEMINI_FALLBACK_MODELS",
            "gemini-3.5-flash-lite,"
            "gemini-flash-lite-latest,"
            "gemini-3.5-flash",
        )

        self.fallback_models = [
            model_name.strip()
            for model_name in fallback_raw.split(",")
            if model_name.strip()
        ]

    def _request(self, model, system, user):
        """Send one request to Gemini."""

        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not set")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )

        payload = {
            "system_instruction": {
                "parts": [
                    {
                        "text": system
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": user
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 512,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=45,
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError:
            raise

        except urllib.error.URLError:
            raise

        except TimeoutError:
            raise

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]

        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Gemini returned an unexpected response: {data}"
            ) from exc

        return self._parse_json(text)

    @staticmethod
    def _parse_json(text):
        """Parse JSON from Gemini robustly.

        Handles:
        - Normal JSON
        - Markdown fenced JSON
        - ```json ... ```
        - Extra text before/after JSON
        - Common unquoted keys such as args:
        """

        if not isinstance(text, str):
            raise LLMError(
                f"Gemini returned a non-text response: {text}"
            )

        text = text.strip()

        # ---------------------------------------------------------
        # STEP 1: Normal JSON
        # ---------------------------------------------------------
        try:
            result = json.loads(text)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # STEP 2: Remove Markdown code fences
        #
        # Handles:
        #
        # ```json
        # {...}
        # ```
        #
        # and:
        #
        # ```
        # {...}
        # ```
        # ---------------------------------------------------------
        if "```" in text:

            lines = text.splitlines()

            cleaned_lines = []

            for line in lines:
                stripped = line.strip()

                # Ignore opening/closing Markdown fences.
                if stripped.startswith("```"):
                    continue

                cleaned_lines.append(line)

            text = "\n".join(cleaned_lines).strip()

            # Try again.
            try:
                result = json.loads(text)

                if isinstance(result, dict):
                    return result

            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # STEP 3: Extract the JSON object from surrounding text.
        #
        # This handles cases like:
        #
        # Here is the result:
        # {"action": "tool", ...}
        #
        # ---------------------------------------------------------
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]

            try:
                result = json.loads(candidate)

                if isinstance(result, dict):
                    return result

            except json.JSONDecodeError:
                pass

            # -----------------------------------------------------
            # STEP 4: Repair common unquoted keys.
            #
            # Example:
            #
            # {"action": "finish", "tool": null, args: {}}
            #
            # becomes:
            #
            # {"action": "finish", "tool": null, "args": {}}
            # -----------------------------------------------------
            repaired = candidate

            known_keys = [
                "action",
                "tool",
                "args",
                "final_answer",
            ]

            for key in known_keys:

                repaired = repaired.replace(
                    f", {key}:",
                    f', "{key}":',
                )

                repaired = repaired.replace(
                    f", {key} :",
                    f', "{key}":',
                )

                repaired = repaired.replace(
                    f"{{{key}:",
                    f'{{"{key}":',
                )

                repaired = repaired.replace(
                    f"{{{key} :",
                    f'{{"{key}":',
                )

            try:
                result = json.loads(repaired)

                if isinstance(result, dict):
                    return result

            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # STEP 5: Nothing worked.
        # ---------------------------------------------------------
        raise LLMError(
            f"Gemini returned invalid JSON: {text}"
        )

    def generate_json(self, system: str, user: str) -> dict:
        """Generate JSON with retry and fallback model support."""

        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not set")

        models = [self.model] + [
            model_name
            for model_name in self.fallback_models
            if model_name != self.model
        ]

        errors = []

        for model in models:

            for attempt in range(2):

                try:
                    return self._request(
                        model,
                        system,
                        user,
                    )

                except urllib.error.HTTPError as exc:

                    body = exc.read().decode(
                        "utf-8",
                        errors="replace",
                    )

                    # Temporary capacity/rate-limit/server errors.
                    if exc.code in (
                        429,
                        500,
                        502,
                        503,
                        504,
                    ):
                        errors.append(
                            f"{model} attempt {attempt + 1}: "
                            f"HTTP {exc.code}"
                        )

                        if attempt == 0:
                            time.sleep(2)
                            continue

                        break

                    # Do not retry authentication or invalid-model
                    # errors.
                    raise LLMError(
                        f"Gemini request failed for {model}: "
                        f"HTTP {exc.code}: {body}"
                    ) from exc

                except (
                    urllib.error.URLError,
                    TimeoutError,
                ) as exc:

                    errors.append(
                        f"{model} attempt {attempt + 1}: {exc}"
                    )

                    if attempt == 0:
                        time.sleep(2)
                        continue

                    break

                except LLMError:
                    # This includes JSON parsing failures.
                    raise

                except Exception as exc:

                    errors.append(
                        f"{model} attempt {attempt + 1}: {exc}"
                    )

                    if attempt == 0:
                        time.sleep(2)
                        continue

                    break

        raise LLMError(
            "All Gemini models failed. "
            + " | ".join(errors)
        )


class GroqProvider(LLMProvider):
    """Groq provider used by Agent 2 / AgentGuard evaluator."""

    name = "groq"

    def __init__(self, model=None):
        self.api_key = os.getenv("GROQ_API_KEY", "")

        self.model = model or os.getenv(
            "AGENTGUARD_GROQ_MODEL",
            "openai/gpt-oss-20b",
        )

        if self.api_key:
            self.client = Groq(
                api_key=self.api_key
            )
        else:
            self.client = None

    def generate_json(self, system: str, user: str) -> dict:
        """Generate JSON using Groq."""

        if not self.api_key:
            raise LLMError("GROQ_API_KEY is not set")

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ],
                response_format={
                    "type": "json_object"
                },
            )

            text = completion.choices[0].message.content

            if not text:
                raise LLMError(
                    "Groq returned an empty response."
                )

            return json.loads(text)

        except json.JSONDecodeError as exc:
            raise LLMError(
                f"Groq returned invalid JSON: {text}"
            ) from exc

        except LLMError:
            raise

        except Exception as exc:
            raise LLMError(
                f"Groq request failed: {exc}"
            ) from exc


def build_provider(provider_name: str) -> LLMProvider:
    """Create an LLM provider from its name."""

    provider_name = provider_name.lower().strip()

    if provider_name == "gemini":
        return GeminiProvider()

    if provider_name == "groq":
        return GroqProvider()

    raise ValueError(
        f"Unsupported provider: {provider_name}"
    )