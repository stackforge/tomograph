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

import config
from types import Span, Note, Tag

import random
import sys
import time
from eventlet import corolocal
import socket
import pickle
import base64
import logging
import webob.dec

span_stack = corolocal.local()

def start(service_name, name, address, port, trace_info=None):
    parent_id = None
    if hasattr(span_stack, 'trace_id'):
        trace_id = span_stack.trace_id
        parent_id = span_stack.spans[-1].id
    else:
        if trace_info is None:
            trace_id = span_stack.trace_id = getId()
        else:
            trace_id = span_stack.trace_id = trace_info[0]
            parent_id = trace_info[1]
        span_stack.spans = []

    span = Span(trace_id, parent_id, getId(), name, [], [])
    span_stack.spans.append(span)
    annotate('start', service_name, address, port)

def get_trace_info():
    return (span_stack.trace_id, span_stack.spans[-1].id)

def stop(name):
    annotate('stop')
    span = span_stack.spans.pop()
    assert span.name == name, 'start span name {0} not equal to end span name {1}'.format(span.name, name)
    if not span_stack.spans:
        del(span_stack.trace_id)
    for backend in config.get_backends():
        backend.send(span)

def annotate(value, service_name=None, address=None, port=None, duration=None):
    """add an annotation at a particular point in time (with an optional duration)"""
    cur_span = span_stack.spans[-1]
    # attempt to default some values
    if service_name is None:
        service_name = cur_span.notes[0].service_name
    if address is None:
        address = cur_span.notes[0].address
    if port is None:
        port = cur_span.notes[0].port
    if duration is None:
        duration = 0
    note = Note(time.time(), str(value), service_name, address, int(port),
                int(duration))
    span_stack.spans[-1].notes.append(note)

def tag(key, value, service_name=None, address=None, port=None):
    """add a key/value tag to the current span.  values can be int,
    float, or string."""
    assert isinstance(value, str) or isinstance(value, int) or isinstance(value, float)
    cur_span = span_stack.spans[-1]
    if service_name is None:
        service_name = cur_span.notes[0].service_name
    if address is None:
        address = cur_span.notes[0].address
    if port is None:
        port = cur_span.notes[0].port
    tag = Tag(str(key), value, service_name, address, port)
    span_stack.spans[-1].dimensions.append(tag)
    
def getId():
    return random.randrange(sys.maxint >> 10)

## wrapper/decorators
def tracewrap(func, service_name, name, host='0.0.0.0', port=0):
    if host == '0.0.0.0':
        host = socket.gethostname()
    def trace_and_call(*args, **kwargs):
        if service_name is None and len(args) > 0 and isinstance(args[0], object):
            s = args[0].__class__.__name__
        else:
            s = service_name
        start(s, name, host, port)
        ret = func(*args, **kwargs)
        stop(name)
        return ret
    return trace_and_call

def traced(service_name, name, host='0.0.0.0', port=0):
    def t1(func):
        return tracewrap(func, service_name, name, host, port)
    return t1


## sqlalchemy event listeners 
def before_execute(name):
    def handler(conn, clauseelement, multiparams, params):
        if not config.db_tracing_enabled:
            return
        h = str(conn.connection.connection)
        a = h.find("'")
        b = h.find("'", a+1)
        if b > a:
            h = h[a+1:b]
        else:
            h = 'unknown'
        port = conn.connection.connection.port
        #print >>sys.stderr, 'connection is {0}:{1}'.format(h, port)
        #print >>sys.stderr, 'sql statement is {0}'.format(clauseelement)
        start(str(name) + 'db client', 'execute', h, port)
        annotate(clauseelement)
    return handler

def after_execute(name):
    # name isn't used, at least not yet...
    def handler(conn, clauseelement, multiparams, params, result):
        if not config.db_tracing_enabled:
            return
        stop('execute')
    return handler

def dbapi_error(name):
    def handler(conn, cursor, statement, parameters, context, exception):
        if not config.db_tracing_enabled:
            return
        annotate('database exception {0}'.format(exception))
        stop('execute')
    return handler

## http helpers
def start_http(service_name, name, request):
    trace_info_enc = request.headers.get('X-Trace-Info')
    (host, port) = request.host.split(':')
    if trace_info_enc:
        trace_info = pickle.loads(base64.b64decode(trace_info_enc))
    else:
        trace_info = None
    start(service_name, name, host, port, trace_info)

def add_trace_info_header(headers):
    headers['X-Trace-Info'] = base64.b64encode(pickle.dumps(get_trace_info()))


## WSGI middleware
class Middleware(object):
    """
    WSGI Middleware that enables tomograph tracing for an application.
    """

    def __init__(self, application, service_name='Server', name='WSGI'):
        self.application = application
        self.service_name = service_name
        self.name = name
    
    @classmethod
    def factory(cls, global_conf, **local_conf):
        def filter(app):
            return cls(app, **local_conf)
        return filter

    @webob.dec.wsgify
    def __call__(self, req):
        start_http(self.service_name, self.name, req)
        response = req.get_response(self.application)
        stop(self.name)
        return response

