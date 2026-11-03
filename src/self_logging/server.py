from ssl import SSLContext

from pydantic import BaseModel


class HTTPHandlerArgument(BaseModel):
    host: str
    url: str
    context: SSLContext | None = None
