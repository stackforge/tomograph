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

from __future__ import print_function

from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket
from thrift.transport import TTransport

from tomograph.backends.zipkin.generated.scribe import scribe
from tomograph.backends.zipkin import sender
from tomograph.backends.zipkin import zipkin_thrift

from tomograph import cache
from tomograph import config

import StringIO

import atexit
import base64
import random
import socket
import struct
import sys
import time
import traceback

scribe_config = {
    'host': config.zipkin_host,
    'port': config.zipkin_port,
    'socket_timeout': config.zipkin_socket_timeout,
    'target_write_size': config.zipkin_target_write_size,
    'max_queue_length': config.zipkin_max_queue_length,
    'must_yield': config.zipkin_must_yield,
    'max_write_interval': config.zipkin_max_write_interval,
    'debug': config.zipkin_debug_scribe_sender,
}
scribe_sender = sender.ScribeSender(**scribe_config)
atexit.register(scribe_sender.close)

hostname_cache = cache.Cache(socket.gethostbyname)


def send(span):

    def endpoint(note):
        try:
            ip = hostname_cache.get(note.address)
        except Exception:
            print('host resolution error: %s' % traceback.format_exc(),
                  file=sys.stderr)
            ip = '0.0.0.0'
        return zipkin_thrift.Endpoint(ipv4=ip_to_i32(ip),
                                      port=port_to_i16(note.port),
                                      service_name=note.service_name)

    def annotation(note):
        return zipkin_thrift.Annotation(timestamp=int(note.time * 1e6),
                                        value=note.value,
                                        duration=note.duration,
                                        host=endpoint(note))

    def binary_annotation(dimension):
        if isinstance(dimension.value, str):
            tag_type = zipkin_thrift.AnnotationType.STRING
            val = dimension.value
        elif isinstance(dimension.value, float):
            tag_type = zipkin_thrift.AnnotationType.DOUBLE
            val = struct.pack('>d', dimension.value)
        elif isinstance(dimension.value, int):
            tag_type = zipkin_thrift.AnnotationType.I64
            val = struct.pack('>q', dimension.value)
        else:
            raise RuntimeError("unsupported tag type")
        return zipkin_thrift.BinaryAnnotation(key=dimension.key,
                                              value=val,
                                              annotation_type=tag_type,
                                              host=endpoint(dimension))

    binary_annotations = [binary_annotation(d) for d in span.dimensions]
    zspan = zipkin_thrift.Span(trace_id=span.trace_id,
                               id=span.id,
                               name=span.name,
                               parent_id=span.parent_id,
                               annotations=[annotation(n) for n in span.notes],
                               binary_annotations=binary_annotations)
    out = StringIO.StringIO()
    #raw = TBinaryProtocol.TBinaryProtocolAccelerated(out)
    raw = TBinaryProtocol.TBinaryProtocol(out)
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
    if port_num > 2 ** 15:
        port_num -= 2 ** 16
    return port_num
