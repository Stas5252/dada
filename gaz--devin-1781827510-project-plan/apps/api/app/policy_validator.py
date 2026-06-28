import re


class PolicyValidationError(ValueError):
    pass

class PromptPolicyValidator:
    PROHIBITED_PATTERNS = [
        re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+override", re.IGNORECASE),
        re.compile(r"jailbreak", re.IGNORECASE),
        re.compile(r"flag_bypass", re.IGNORECASE),
        re.compile(r"redact_instructions", re.IGNORECASE),
    ]
    
    SECRET_KEYWORDS = ["database_password", "super_admin_secret", "admin_pass", "secret_key"]

    @classmethod
    def validate_prompt(cls, prompt: str) -> None:
        if not prompt or len(prompt.strip()) < 10:
            raise PolicyValidationError("Промпт слишком короткий (минимальная длина 10 символов).")
            
        if len(prompt) > 4000:
            raise PolicyValidationError("Промпт слишком длинный (максимальная длина 4000 символов).")
            
        for pattern in cls.PROHIBITED_PATTERNS:
            if pattern.search(prompt):
                raise PolicyValidationError("Промпт содержит недопустимые инструкции для обхода правил безопасности ИИ.")
                
        for secret in cls.SECRET_KEYWORDS:
            if secret in prompt:
                raise PolicyValidationError(f"Промпт содержит потенциально небезопасные внутренние данные ({secret}).")
