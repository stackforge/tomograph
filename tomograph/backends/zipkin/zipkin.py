# Copyright (c) 2012 Yahoo! Inc. All rights reserved.  
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 Unless required by
# applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and
# limitations under the License. See accompanying LICENSE file.

from generated.scribe import scribe
import sender
import zipkin_thrift
from thrift.transport import TTransport
from thrift.transport import TSocket
from thrift.protocol import TBinaryProtocol

from tomograph import config

import base64
import StringIO
import IPy
import time
import random
import socket
import sys
import traceback
import atexit
import threading

scribe_sender = sender.ScribeSender()
atexit.register(scribe_sender.close)

class Cache(object):
    def __init__(self, thunk, size_limit=1000):
        self._map = {}
        self._thunk = thunk
        self._size_limit = size_limit
        self._lock = threading.Lock()

    def get(self, k):
        with self._lock:
            if self._map.has_key(k):
                return self._map[k]
            else:
                while len(self._map) >= self._size_limit:
                    self._map.popitem()
                v = self._thunk(k)
                self._map[k] = v
                return v

hostname_cache = Cache(socket.gethostbyname)

def send(span):

    def endpoint(note):
        try:
            ip = hostname_cache.get(note.address)
        except:
            print >>sys.stderr, 'host resolution error: ', traceback.format_exc()
            ip = '0.0.0.0'
        return zipkin_thrift.Endpoint(ipv4 = ip_to_i32(ip),
                                      port = note.port,
                                      service_name = note.service_name)
    def annotation(note):
        return zipkin_thrift.Annotation(timestamp = int(note.time * 1e6),
                                        value = note.value,
                                        host = endpoint(note))

    zspan = zipkin_thrift.Span(trace_id = span.trace_id,
                               id = span.id,
                               name = span.name,
                               parent_id = span.parent_id,
                               annotations = [annotation(n) for n in span.notes])

    out = StringIO.StringIO()
    raw = TBinaryProtocol.TBinaryProtocolAccelerated(out)
    zspan.write(raw)
    scribe_sender.send('zipkin', base64.b64encode(out.getvalue()))

def ip_to_i32(ip_str):
    """convert an ip address from a string to a signed 32-bit number"""
    return -0x80000000 + (IPy.IP(ip_str).int() & 0x7fffffff)

