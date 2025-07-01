class CustomAPIException(Exception):
    def __init__(self, status_code, code, message, **context):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.context = context
        super().__init__(message)


class DatabaseError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
