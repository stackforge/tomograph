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

import zipkin_thrift
from generated.scribe import scribe
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




def send(span):
    tsocket = TSocket.TSocket(config.zipkin_host, config.zipkin_port)
    transport = TTransport.TFramedTransport(tsocket)
    transport.open()
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    client = scribe.Client(protocol)

    def endpoint(note):
        try:
            ip = socket.gethostbyname(note.address)
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
    raw = TBinaryProtocol.TBinaryProtocol(out)
    zspan.write(raw)
    logentry = scribe.LogEntry('zipkin', base64.b64encode(out.getvalue()))
    client.Log([logentry])
    transport.close()

def ip_to_i32(ip_str):
    """convert an ip address from a string to a signed 32-bit number"""
    return -0x80000000 + (IPy.IP(ip_str).int() & 0x7fffffff)
