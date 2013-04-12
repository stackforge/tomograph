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
from tomograph import cache

import base64
import StringIO
import time
import random
import socket
import struct
import sys
import traceback
import atexit

scribe_sender = sender.ScribeSender()
atexit.register(scribe_sender.close)

hostname_cache = cache.Cache(socket.gethostbyname)

def send(span):

    def endpoint(note):
        try:
            ip = hostname_cache.get(note.address)
        except:
            print >>sys.stderr, 'host resolution error: ', traceback.format_exc()
            ip = '0.0.0.0'
        return zipkin_thrift.Endpoint(ipv4 = ip_to_i32(ip),
                                      port = port_to_i16(note.port),
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
    try:
        zspan.write(raw)
    except OverflowError:
        traceback.print_exc()
    scribe_sender.send('zipkin', base64.b64encode(out.getvalue()))

def ip_to_i32(ip_str):
    """convert an ip address from a string to a signed 32-bit number"""
    return struct.unpack('!i', socket.inet_aton(ip_str))[0]

def port_to_i16(port_num):
    """conver a port number to a signed 16-bit int"""
    if port_num > 2**15:
        port_num -= 2**16
    return port_num
