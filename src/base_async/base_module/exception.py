from enum import Enum
import json
from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlmodel import Field, SQLModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ModuleExceptionPayload(SQLModel, table=False):
    """."""

    prefix: str = 'ModuleException'

    msg: str
    code: int = Field(default=500)
    data: dict[str, Any] = Field(default_factory=dict)


class ModuleException(Exception):
    """."""

    prefix = 'ModuleException'

    def __init__(
            self,
            msg: str | ModuleExceptionPayload,
            code: int = 500,
            data: dict[str, Any] = None,
    ):
        """."""
        if isinstance(msg, ModuleExceptionPayload):
            self.payload = msg
        else:
            self.payload = ModuleExceptionPayload(msg=msg, code=code, data=data or {})
        super().__init__(self.payload.msg)

    def __repr__(self):
        return repr(self.payload)

    def dict(self):
        return self.payload.model_dump()

    def json(self):
        return self.payload.model_dump_json()


class ResponseException(ModuleExceptionPayload):
    """."""

    custom: bool = Field(default=True, exclude=True)


class ErrorCode(Enum):
    BadRequest = ResponseException(code=400, msg='Bad Request')

    # 404 – File Management Errors
    FileNotExists = ResponseException(code=404, msg='Файл с таким именем не найден')
    FileAlreadyExists = ResponseException(code=409, msg='Файл с таким именем уже существует')

    FileUploadingError = ResponseException(code=500, msg='Ошибка во время загрузки файла в хранилище')
    FileDeletingError = ResponseException(code=500, msg='Ошибка во время удаления файла')
    FileDownloadingError = ResponseException(code=500, msg='Ошибка во время выгрузки файла из хранилища')
    FileMoveError = ResponseException(code=500, msg='Ошибка во время перемещения файла')

    # 422 – Validation Errors
    ValidationError = ResponseException(code=422, msg='Ошибка валидации')
    PathUnsafeError = ResponseException(code=400, msg='Ошибка: путь не является безопасным')

    # 500 – Internal Server Error
    InternalError = ResponseException(code=500, msg='Internal Server Error')
    # 502 – Database Errors
    DbError = ResponseException(code=502, msg='Ошибка базы данных')
    ConnectionsError = ResponseException(code=503, msg='Сервис временно недоступен')


HTTP_2_CUSTOM_ERR: dict[int, ResponseException] = {
    422: ResponseException(code=422, msg='Validation error', custom=False),
}


class EXC(HTTPException):
    """."""

    def __init__(
            self,
            exc: ErrorCode,
            data: dict[str, Any] = {},
    ) -> None:
        error_response = exc.value.model_copy(
            update={'data': data},
        )

        test = error_response.model_dump_json()
        super().__init__(status_code=400, detail=error_response.model_dump_json(), headers=None)


def create_error_response(error_response: ResponseException) -> JSONResponse:
    data = error_response.data.copy()

    if data.get('reason') is None:
        data.pop('reason', None)

    if error_response.custom:
        inner_code = error_response.code
    elif error_response.code in HTTP_2_CUSTOM_ERR:
        custom_error = HTTP_2_CUSTOM_ERR[error_response.code]
        inner_code = custom_error.code
        error_response.msg = custom_error.msg
    else:
        inner_code = 500

    return JSONResponse(
        status_code=inner_code,
        content=jsonable_encoder(
            {
                'msg': error_response.msg,
                'data': data,
            }
        ),
    )


def parse_error_detail(detail: str | dict) -> ResponseException:
    if isinstance(detail, str):
        try:
            error_dict = json.loads(detail)
        except json.JSONDecodeError:
            error_dict = {'msg': detail, 'code': 500, 'custom': False}
    else:
        error_dict = detail
    return ResponseException(**error_dict)


async def http_exception_handler(request: Request, exc: HTTPException):
    error = parse_error_detail(exc.detail)
    error.data['endpoint'] = request.url.path
    return create_error_response(error)


async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    error = parse_error_detail(exc.detail)
    error.data['endpoint'] = request.url.path
    return create_error_response(error)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = ErrorCode.ValidationError.value
    error.data = {
        'endpoint': request.url.path,
        'errors': exc.errors(),
    }
    return create_error_response(error)
