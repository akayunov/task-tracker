import enum


class UserRole(enum.StrEnum):
    USER = 'user'
    ADMIN = 'admin'


class TaskStatus(enum.StrEnum):
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'


class TaskPriority(enum.StrEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
