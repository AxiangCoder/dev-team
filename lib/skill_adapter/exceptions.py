"""Exception types for skill adapter library."""


class SkillAdapterError(Exception):
    """Base exception for all skill adapter errors."""


class SkillDefinitionError(SkillAdapterError):
    """Raised when a skill definition is missing or invalid."""


class SkillImportError(SkillAdapterError):
    """Raised when a skill entrypoint cannot be imported."""


class SkillConflictError(SkillAdapterError):
    """Raised when a skill registration conflicts with an existing one."""


class SkillNotFoundError(SkillAdapterError):
    """Raised when a requested skill does not exist in the registry."""


class SkillPermissionError(SkillAdapterError):
    """Raised when middleware denies access to a skill."""


class SkillExecutionError(SkillAdapterError):
    """Raised when a skill handler fails during execution."""


class SkillConfigurationError(SkillAdapterError):
    """Raised when registry configuration is invalid."""


class SkillValidationError(SkillAdapterError):
    """Raised when runtime input or output fails validation."""


# Backward-compatible alias
ManifestValidationError = SkillDefinitionError
