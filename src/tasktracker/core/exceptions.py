from fastapi import status


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = 'app_error'

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = 'not_found'


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = 'forbidden'


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = 'conflict'


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 'unauthorized'
