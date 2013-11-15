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
import eventlet

from tomograph import cache
from tomograph import config

logging = eventlet.import_patched('logging')
socket = eventlet.import_patched('socket')
threading = eventlet.import_patched('threading')

logger = logging.getLogger(__name__)

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

hostname_cache = cache.Cache(socket.gethostbyname)

lock = threading.Lock()


def send(span):

    def statsd_send(name, value, units):
        stat = (str(name).replace(' ', '-') + ':' + str(int(value)) +
                '|' + str(units))
        with lock:
            try:
                udp_socket.sendto(stat,
                                  (hostname_cache.get(config.statsd_host),
                                   config.statsd_port))
            except Exception:
                if config.debug:
                    logger.warning("Error sending metric to statsd.",
                                   exc_info=True)

    def server_name(note):
        address = note.address.replace('.', '-')
        return note.service_name + ' ' + address + ' ' + str(note.port)

    # the timing stat:
    delta = span.notes[-1].time - span.notes[0].time
    deltams = delta * 1000
    time_stat_name = server_name(span.notes[0]) + '.' + span.name
    statsd_send(time_stat_name, deltams, 'ms')

    # a count stat for each note
    for note in span.notes:
        stat_name = server_name(note) + '.' + span.name + '.' + str(note.value)
        statsd_send(stat_name, 1, 'c')
