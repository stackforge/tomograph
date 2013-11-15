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

### Initialize logging in case it hasn't been done.  We need two
### versions of this, one for the eventlet logging module and one for
### the non-eventlet one...

from __future__ import absolute_import

import logging
import sys

import eventlet
eventlet_logging = eventlet.import_patched('logging')
eventlet_sys = eventlet.import_patched('sys')


def _initLogging(logging, sys):
    """Set up some default stuff, in case nobody configured logging yet."""
    logger = logging.getLogger('tomograph')

    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s '
                                               '%(name)s %(message)s'))
        logger.addHandler(handler)


_initLogging(logging, sys)
_initLogging(eventlet_logging, eventlet_sys)


from tomograph.tomograph import *
