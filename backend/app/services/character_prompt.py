from app.models.character import Character


def build_system_prompt(character: Character) -> str:
    """Имя и характер, плюс описание и сценарий, если они заданы."""
    prompt = f"Ты — {character.name}. {character.personality or ''}"
    extra: list[str] = []
    description = _filled(character.description)
    scenario = _filled(character.scenario)
    if description:
        extra.append(f"Описание: {description}")
    if scenario:
        extra.append(f"Сценарий: {scenario}")
    if not extra:
        return prompt
    return prompt.rstrip() + "\n" + "\n".join(extra)


def opening_greeting(character: Character | None) -> str | None:
    """Первое сообщение персонажа как реплика ассистента, без изменений текста."""
    if character is None or character.first_message is None:
        return None
    if not character.first_message.strip():
        return None
    return character.first_message


def _filled(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
