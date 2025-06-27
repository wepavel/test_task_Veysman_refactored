import json
from enum import Enum
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
# from pydantic import BaseModel, Field
from sqlmodel import Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ModuleExceptionPayload(SQLModel, table=False):
    prefix: str = 'ModuleException'

    msg: str
    code: int = Field(default=500)
    data: dict[str, Any] = Field(default_factory=dict)

    def __repr__(self):
        name = type(self).__name__
        return f'{name}({self}) {self.code} {self.data}'

class ModuleException(Exception):
    def __init__(
        self,
        msg: str | ModuleExceptionPayload,
        code: int = 500,
        data: dict[str, Any] = None,
    ):
        if isinstance(msg, ModuleExceptionPayload):
            self.payload = msg
        else:
            self.payload = ModuleExceptionPayload(
                msg=msg,
                code=code,
                data=data or {}
            )
        super().__init__(self.payload.msg)

    def __repr__(self):
        return repr(self.payload)

    def dict(self):
        return self.payload.model_dump()

    def json(self):
        return self.payload.model_dump_json()

class ResponseException(ModuleExceptionPayload):
    custom: bool = Field(default=True, exclude=True)

class ErrorCode(Enum):
    #  4000: Bad Request
    BadRequest = ResponseException(code=4000, msg='Bad Request')
    #  4021 - 4040: User Management Errors
    CouldNotValidateUserCreds = ResponseException(code=4021, msg='Could not validate credentials: ValidationError')
    UserExpiredSignatureError = ResponseException(code=4022, msg='Could not validate credentials: ExpiredSignatureError')
    IncorrUserCreds = ResponseException(code=4023, msg='Incorrect login or password')
    NotAuthenticated = ResponseException(code=4030, msg='Not authenticated')
    InactiveUser = ResponseException(code=4032, msg='Inactive user')
    UserRegistrationForbidden = ResponseException(code=4033, msg='Open user registration is forbidden on this server')
    UserNotExists = ResponseException(code=4035, msg='The user with this username does not exist in the system')
    UserExists = ResponseException(code=4036, msg='The user already exists in the system')
    #  4041 - 4060: Project Management Errors
    ProjectLocked = ResponseException(code=4041, msg='Project locked')

    NameAlreadyExists = ResponseException(code=4044, msg='This name already exists')

    #  4061 - 4080: Task Management Errors
    SessionNotFound = ResponseException(code=4071, msg='Session not found')
    SessionAlreadyExists = ResponseException(code=4072, msg='Session already exists')

    #  4081 - 4010: File Management Errors
    FileNotExists = ResponseException(code=4081, msg='File not found')
    FileAlreadyExists = ResponseException(code=4082, msg='File already exists')
    FileUploadingError = ResponseException(code=4083, msg='Error while uploading file')
    FileDeletingError = ResponseException(code=4084, msg='Error while deleting file')
    FileDownloadingError = ResponseException(code=4085, msg='Error while downloading file')
    FileMoveError = ResponseException(code=4086, msg='Error while moving file')

    #  4301 - 4320: Resource and Limit Errors
    TooManyRequestsError = ResponseException(code=4301, msg='Too Many Requests')
    #  4400: Validation Error
    ValidationError = ResponseException(code=4400, msg='Validation error')
    #  4401-4500: General Validation Errors
    WrongFormat = ResponseException(code=4411, msg='Wrong format')
    PathUnsafeError = ResponseException(code=4416, msg='Path unsafe error')
    #  4501 - 4508: API and Request Errors
    Unauthorized = ResponseException(
        code=4501,
        msg='Sorry, you are not allowed to access this service: UnauthorizedRequest',
    )
    AuthorizeError = ResponseException(code=4502, msg='Authorization error')
    ForbiddenError = ResponseException(code=4503, msg='Forbidden')
    NotFoundError = ResponseException(code=4504, msg='Not Found')
    ResponseProcessingError = ResponseException(code=4505, msg='Response Processing Error')
    #  5000: Internal Server Error
    InternalError = ResponseException(code=5000, msg='Internal Server Error')
    #  5041-5060: Database Errors
    DbError = ResponseException(code=5041, msg='Bad Gateway')
    #  5061 - 5999: System and Server Errors



HTTP_2_CUSTOM_ERR: dict[int, ResponseException] = {
    422: ResponseException(code=4400, msg='Validation error', custom=False),
}


class EXC(HTTPException):
    def __init__(
        self,
        exc: ErrorCode,
        data: dict[str, Any] = {},
    ) -> None:

        error_response = exc.value.model_copy(
            update={'data': data},
        )

        super().__init__(status_code=400, detail=error_response.model_dump_json())


def exception_handler(app: FastAPI) -> None:
    def create_error_response(error_response: ModuleException) -> JSONResponse:
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
            inner_code = 5999

        status_code = 400 if 4000 <= inner_code < 5000 else 500

        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder(
                {
                    'msg': error_response.msg,
                    'code': inner_code,
                    'data': data,
                },
            ),
        )

    def parse_error_detail(detail: str | dict) -> ModuleException:
        if isinstance(detail, str):
            try:
                error_dict = json.loads(detail)
            except json.JSONDecodeError:
                error_dict = {'msg': detail, 'code': 5000, 'custom': False}
        else:
            error_dict = detail

        return ModuleException(**error_dict)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        error = parse_error_detail(exc.detail)
        error.details['endpoint'] = request.url.path
        return create_error_response(error)

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        error = parse_error_detail(exc.detail)
        error.details['endpoint'] = request.url.path
        return create_error_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error = ErrorCode.ValidationError.value
        error.details = {
            'endpoint': request.url.path,
            'errors': exc.errors(),
        }
        return create_error_response(error)