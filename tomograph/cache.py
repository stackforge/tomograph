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

import threading

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

