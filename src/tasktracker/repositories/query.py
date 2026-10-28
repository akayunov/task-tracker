def escape_like(value: str) -> str:
    """Экранировать символы шаблона LIKE, чтобы поиск был буквальным.

    :param value: сырой фрагмент от клиента
    :return: строка, безопасная для ILIKE ... ESCAPE '\\'
    """
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
