class CustomAPIException(Exception):
    def __init__(self, http_code, code, message, **context):
        self.http_code = http_code
        self.code = code
        self.message = message
        self.context = context
        super().__init__(message)
