


class GISError(Exception):
    """Базовое  исключение для операций с порталом ГИС ЖКХ"""
    ...


class UploadFileError(GISError):
    """Ошибка отправки файла на портал ГИС ЖКХ"""
    def __init__(self, filename: str, service_response):
        self.filename = filename
        self.service_response = service_response

        super().__init__(f"Ошибка отправки файла: {self.filename}. Ответ портала: {self.service_response}")


