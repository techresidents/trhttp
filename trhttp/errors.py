class HttpError(Exception):
    def __init__(self, status, reason, response_data, response_headers):
        self.status = status
        self.reason = reason
        self.response_data = response_data
        self.response_headers = response_headers

    def __repr__(self):
        return "%s(status=%d, reason=%s)" % \
                (self.__class__, self.status, self.reason)

    def __str__(self):
        return "%s(status=%d, reason=%s)" % \
                (self.__class__.__name__, self.status, self.reason)
