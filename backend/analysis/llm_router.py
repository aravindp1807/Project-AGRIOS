import requests
import os
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from config import settings

@dataclass
class SynthesisResult:
    text: str
    provider_used: str

class LLMRouter:
    def __init__(self):
        self.openrouter_key = settings.OPENROUTER_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.nvidia_key = settings.NVIDIA_NIM_API_KEY

    def synthesize(self, prompt: str, task_type: str, fallback_context_data: Optional[Dict[str, Any]] = None) -> SynthesisResult:
        """
        Routes the synthesis prompt through the tiered LLM fallback chain.
        task_type: "search" (latency-sensitive) or "monitor" (background)
        """
        providers = self._get_provider_order(task_type)
        errors = []

        for provider in providers:
            try:
                # Check key existence before trying
                if not self._has_api_key(provider):
                    continue
                
                result_text = self._call_provider(provider, prompt)
                if result_text and result_text.strip():
                    return SynthesisResult(text=result_text.strip(), provider_used=provider)
            except Exception as e:
                errors.append(f"{provider} failed: {str(e)}")
                print(f"LLM Provider {provider} failed: {e}")
                continue

        # If all API calls fail, fallback to a local rule-based intelligence generator
        print(f"All LLM providers failed or were unconfigured. Errors: {errors}")
        fallback_text = self._generate_rule_based_fallback(fallback_context_data)
        return SynthesisResult(text=fallback_text, provider_used="local_rule_engine")

    def _get_provider_order(self, task_type: str) -> List[str]:
        if task_type == "search":
            return ["groq", "openrouter_nemotron", "gemini_flash", "nim"]
        # background/monitor jobs: skip groq to preserve tight rate limits
        return ["openrouter_nemotron", "gemini_flash", "nim"]

    def _has_api_key(self, provider: str) -> bool:
        if provider == "groq":
            return bool(self.groq_key)
        if provider == "openrouter_nemotron":
            return bool(self.openrouter_key)
        if provider == "gemini_flash":
            return bool(self.gemini_key)
        if provider == "nim":
            return bool(self.nvidia_key)
        return False

    def _call_provider(self, provider: str, prompt: str) -> str:
        timeout = 10
        if provider == "openrouter_nemotron":
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/aravindp1807/EYE_of_Kartikeya",
                "X-Title": "AGRIOS"
            }
            payload = {
                "model": "nvidia/llama-3.1-nemotron-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=timeout)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]

        elif provider == "gemini_flash":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }
            res = requests.post(url, json=payload, headers=headers, timeout=timeout)
            res.raise_for_status()
            return res.json()["candidates"][0]["content"]["parts"][0]["text"]

        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=timeout)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]

        elif provider == "nim":
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.nvidia_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=timeout)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]

        raise ValueError(f"Unknown provider: {provider}")

    def _generate_rule_based_fallback(self, context: Optional[Dict[str, Any]]) -> str:
        """
        Creates a high-quality summary narrative using local rule engine, 
        ensuring the application remains fully functional if APIs are offline or unconfigured.
        """
        if not context or "metrics" not in context:
            return "Environmental and agricultural resources are currently within normal baseline ranges. No alerts or severe deviations detected."
            
        aoi_name = context.get("aoi_name", "the Area of Interest")
        metrics = context.get("metrics", [])
        
        if not metrics:
            return f"No environmental or agricultural data metrics are currently available for {aoi_name} to generate a resource synthesis report."
            
        sentences = [f"AGRIOS Local synthesis report for {aoi_name}."]
        critical_deviations = []
        warning_deviations = []
        normal_metrics = []

        for m in metrics:
            name = m.get("name", "").replace("_", " ").capitalize()
            val = m.get("value")
            unit = m.get("unit", "")
            base = m.get("baseline")
            dev = m.get("deviation_pct", 0.0)
            trend = m.get("direction", "stable")
            
            if base is None:
                normal_metrics.append(f"{name} is currently {val} {unit} (no historical baseline available).")
                continue
                
            dev_direction = "above" if dev > 0 else "below"
            dev_abs = abs(dev)
            
            detail = f"{name} is measuring {val} {unit}, which is {dev_abs:.1f}% {dev_direction} the 30-day baseline of {base:.1f} {unit} and showing a {trend} trend."
            
            if dev_abs >= 30.0:
                critical_deviations.append(detail)
            elif dev_abs >= 15.0:
                warning_deviations.append(detail)
            else:
                normal_metrics.append(detail)

        # Build narrative order
        if critical_deviations:
            sentences.append("CRITICAL DEVIATION DETECTED: " + " ".join(critical_deviations))
        if warning_deviations:
            sentences.append("Attention required: " + " ".join(warning_deviations))
        if normal_metrics:
            sentences.append("Stable indicators: " + " ".join(normal_metrics))
            
        return " ".join(sentences)
