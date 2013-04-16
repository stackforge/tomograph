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

import random
import sys
import time
from eventlet import corolocal
from collections import namedtuple
import socket
import pickle
import base64
import logging
import webob.dec

span_stack = corolocal.local()

Span = namedtuple('Span', 'trace_id parent_id id name notes')
Note = namedtuple('Note', 'time value service_name address port')

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

    span = Span(trace_id, parent_id, getId(), name, [])
    span_stack.spans.append(span)
    annotate('start', service_name, address, port)

def get_trace_info():
    return (span_stack.trace_id, span_stack.spans[-1].id)

def stop(name):
    annotate('stop')
    span = span_stack.spans.pop()
    assert span.name == name, 'start span name {0} not equal to end span name {1}'.format(span.name, name)
    for backend in config.get_backends():
        backend.send(span)
    if not span_stack.spans:
        del(span_stack.trace_id)

def annotate(value, service_name=None, address=None, port=None):
    last_span = span_stack.spans[-1]
    if service_name is None:
        last_note = last_span.notes[-1]
        service_name = last_note.service_name
        address = last_note.address
        port = last_note.port
    note = Note(time.time(), value, service_name, address, int(port))
    span_stack.spans[-1].notes.append(note)
    
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
        annotate(str(clauseelement))
    return handler

def after_execute(name):
    # name isn't used, at least not yet...
    def handler(conn, clauseelement, multiparams, params, result):
        stop('execute')
        pass
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

