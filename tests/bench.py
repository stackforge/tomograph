#!/usr/bin/env python

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

import tomograph
import cProfile
import sys
import time

@tomograph.traced('test server', 'server response', port=80)
def server(latency):
    time.sleep(latency)


@tomograph.traced('test client', 'client request')
def client(client_overhead, server_latency):
    time.sleep(client_overhead)
    server(server_latency)

def clientloop():
    for i in xrange(10000):
        client(0, 0)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        tomograph.config.set_backends(sys.argv[1:])
    cProfile.run('clientloop()', 'tomo-bench')


