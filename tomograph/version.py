# Copyright (c) 2013 Yahoo! Inc. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 Unless required by
# applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and
# limitations under the License. See accompanying LICENSE file.

TOMOGRAPH_VERSION = ['2013', '1', None]
YEAR, COUNT, REVISION = TOMOGRAPH_VERSION
FINAL = False  # May never be final ;)


def canonical_version_string():
    return '.'.join(filter(None, TOMOGRAPH_VERSION))


def version_string():
    if FINAL:
        return canonical_version_string()
    else:
        return '%s-dev' % (canonical_version_string())
