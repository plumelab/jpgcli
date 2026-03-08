class JpgCliError(Exception):
    pass


class ConfigError(JpgCliError):
    pass


class InputDataError(JpgCliError):
    pass


class LLMError(JpgCliError):
    pass


class SpecValidationError(JpgCliError):
    pass


class RenderError(JpgCliError):
    pass
