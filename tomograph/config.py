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

import logging

logger = logging.getLogger(__name__)

enabled_backends = ['tomograph.backends.zipkin',
                    'tomograph.backends.statsd',
                    'tomograph.backends.log']
backend_modules = []

zipkin_host = '127.0.0.1'
zipkin_port = 9410

statsd_host = '127.0.0.1'
statsd_port = 8125

zipkin_socket_timeout = 5.0
zipkin_max_queue_length = 50000
zipkin_target_write_size = 1000
zipkin_max_write_interval = 1
zipkin_must_yield = True
zipkin_debug_scribe_sender=False

debug = False
db_tracing_enabled = True
db_trace_as_spans = False

def set_backends(backends):
    """
    Set the list of enabled backends.  Backend name should be the full
    module name of the backend.  All backends must support a
    send(span) method.
    """
    global enabled_backends
    global backend_modules
    enabled_backends = backends[:]
    backend_modules = []
    for backend in enabled_backends:
        try:
            logger.info('loading backend {0}'.format(backend))
            module = __import__(backend)
            for submodule in backend.split('.')[1:]:
                module = getattr(module, submodule)
            backend_modules.append(module)
        except (ImportError, AttributeError, ValueError) as err:
            raise RuntimeError('Could not load tomograph backend {0}: {1}'.format(
                    backend, err))

def get_backends():
    if not backend_modules:
        set_backends(enabled_backends)
    return backend_modules
    
