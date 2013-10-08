import httplib
import logging
import ssl
import socket
import urllib

from trpycore.chunk.basic import BasicChunker

from trhttp.errors import HttpError
from trhttp.utils import parse_url


class ResponseContextManager(object):

    def __init__(self, client, response):
        self.client = client
        self.response = response
    
    def get(self):
        return self.response

    def __enter__(self):
        """Context manager entry point.

        Returns:
            Http response instance
        """
        return self.get()

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Exit context manager without suppressing exceptions."""
        
        if self.client.keepalive:
            #ensure response is read and closed for future requests
            self.response.read()
            self.response.close()
        else:
            self.client.connection.close()
        return False

class RestClient(object):
    """HTTP Rest Client"""
    def __init__(self,
            endpoint,
            authenticator=None,
            timeout=10,
            retries=1,
            keepalive=True,
            proxy=None,
            connection_class=None,
            response_context_manager_class=None,
            debug_level=0):
        """RestClient constructor

        Args:
            endpoint: API endpoint, i.e. http://api.techresidents.com/v1
            authenticator: optional RestAuthenticator object to use
                for authentication and re-authentication on 401 errors.
            timeout: socket timeout in seconds
            retries: Number of times to try a request with an unexpected
                error before an exception is raised. Note that a value of 2
                means to try each api request twice (not 3 times) before
                raising an exception.
            keepalive: boolean indicating whether connections to the
                cloudfiles servers should be maintained between requests.
                If false, connections will be closed immediately following
                each api request.
            proxy: (host, port) tuple specifying proxy for connection
            connection_class: optional HTTP connectino class. It not 
                specified sensible default will be used.
            response_context_manager_class: optional context manager
                to wrap HTTP response objects in. If not provided
                a default will be used to properly manage the 
                connection based on keepalive settings.
            debug_level: httplib debug level. Setting this to 1 will log
                http requests and responses which is very useful for 
                debugging.
        """
        self.endpoint = endpoint.rstrip("/")
        self.authenticator = authenticator
        self.timeout = timeout
        self.retries = retries
        self.keepalive = keepalive
        self.proxy = proxy
        self.connection_class = connection_class
        self.response_context_manager_class = response_context_manager_class
        self.debug_level = debug_level
        self.auth_headers = None
        self.last_http_error = None
        self.log = logging.getLogger(self.__class__.__name__)
        
        if self.connection_class is None:
            if endpoint.startswith("https:"):
                self.connection_class = httplib.HTTPSConnection
            else:
                self.connection_class = httplib.HTTPConnection
        
        if self.response_context_manager_class is None:
            self.response_context_manager_class = ResponseContextManager
        
        #parse endpoint
        self.host, self.port, self.path, self.is_ssl = \
                parse_url(self.endpoint)
     
        #connection
        self.connection = self._create_connection()

        #authenticate
        self._authenticate()

    def default_headers(self, method, path, data=None, data_size=None):
        data_size = data_size or 0
        headers = {
            "Content-Length": str(data_size)
        }

        if self.auth_headers:
            headers.update(self.auth_headers)
        return headers

    def send_request(self, method, path, data=None, headers=None,
            params=None, data_size=None, chunk_size=65535):
        
        response = self._retry_send_request(method=method, path=path,
                data=data, headers=headers, params=params,
                data_size=data_size, chunk_size=chunk_size)
        result = self.response_context_manager_class(self, response)
        return result

    def validate_response(self, response):
        if response.status < 200 or response.status > 299:
            data = response.read()
            raise HttpError(status=response.status,
                    reason=response.reason,
                    response_data=data,
                    response_headers=response.getheaders())

    def _create_connection(self):
        if self.proxy:
            connection = self.connection_class(
                    host=self.proxy[0],
                    port=self.proxy[1],
                    timeout=self.timeout)
            connection.set_tunnel(self.host, self.port)
        else:
            connection = self.connection_class(
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout)

        if self.debug_level:
            connection.set_debuglevel(self.debug_level)
        
        return connection

    def _authenticate(self, force=False):
        if self.authenticator is not None:
            self.auth_headers = self.authenticator.authenticate(self, force)

    def _normalize_path(self, path, params=None):
        if self.path:
            path = "/%s/%s" % (self.path, path.strip("/"))
        else:
            path = "/%s" % path.strip("/")

        if params:
            path = "%s?%s" % (path, urllib.urlencode(params))

        return path

    def _retry_send_request(self, method, path, data=None, headers=None,
            params=None, data_size=None, chunk_size=65535, reset=None):
        
        if reset is None and \
                hasattr(data, "tell") and hasattr(data, "seek"):
                pos = data.tell()
                reset = lambda *args, **kwargs: data.seek(pos)

        for retry in range(self.retries):
            try:
                response = self._send_request( method=method, path=path,
                        data=data, headers=headers, params=params,
                        data_size=data_size, chunk_size=chunk_size)
                return response
            except HttpError:
                raise
            except Exception as e:
                if retry + 1 < self.retries:
                    msg = "%s %s attempt (%s of %s) failed: %s" % \
                            (method, path, retry+1, self.retries, str(e))
                    self.log.warning(msg)
                last_error = e

            if reset:
                reset(method=method, path=path, data=data,
                        headers=headers, params=params,
                        data_size=data_size, chunk_size=chunk_size)
        raise last_error

    def _send_request(self, method, path, data=None, headers=None,
            params=None, data_size=None, chunk_size=65535):

        path = self._normalize_path(path, params)
        
        if data and data_size is None:
            if isinstance(data, basestring):
                data_size = len(data)

        #prepare headers
        user_headers = headers
        headers = self.default_headers(method, path, data_size=data_size)
        if user_headers:
            headers.update(user_headers)
        if data and data_size is None:
            del headers["Content-Length"]
            headers["Transfer-Encoding"] = "chunked"

        try:
            response = self._do_request(method=method, path=path,
                        data=data, headers=headers, params=params,
                        data_size=data_size, chunk_size=chunk_size)
            self.validate_response(response)
            self.last_http_error = None
        except HttpError as error:
            retry = error.status == 401 and \
                    self.authenticator and \
                    (self.last_http_error is None or \
                     self.last_http_error.status != 401)
            self.last_http_error = error
            if retry:
                self._authenticate(force=True)
                headers.update(self.auth_headers)
                response = self._do_request(method=method, path=path,
                            data=data, headers=headers, params=params,
                            data_size=data_size, chunk_size=chunk_size)
                self.validate_response(response)
                self.last_http_error = None
            else:
                raise
        except Exception as e:
            #Close the connection on any unhandled exceptions to avoid
            #leaving the httplib connection in an improper state
            #where all future requests will result in an
            #httplib.ImproperConnectionState exception.
            self.connection.close()
            self.connection = self._create_connection()
            raise

        return response

    def _do_request(self, method, path, data=None, headers=None,
            params=None, data_size=None, chunk_size=65535):

            self.connection.putrequest(method, path)
            for name, value in headers.items():
                if not isinstance(value, basestring):
                    value = str(value)
                self.connection.putheader(name, value)
            self.connection.endheaders()

            if data:
                if not hasattr(data, "chunks"):
                    data = BasicChunker(data)

                if data_size is None:
                    for chunk in data.chunks(chunk_size):
                        self.connection.send("%x\r\n%s\r\n" % (len(chunk), chunk))
                    self.connection.send("0\r\n\r\n")
                else:
                    for chunk in data.chunks(chunk_size):
                        self.connection.send(chunk)
            
            return self.connection.getresponse()
