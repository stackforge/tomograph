import eventlet

socket = eventlet.import_patched('socket')
time = eventlet.import_patched('time')
scribe = eventlet.import_patched('scribe.scribe')
TTransport = eventlet.import_patched('thrift.transport.TTransport')
TSocket = eventlet.import_patched('thrift.transport.TSocket')
collections = eventlet.import_patched('collections')
traceback = eventlet.import_patched('traceback')
threading = eventlet.import_patched('threading')

from thrift.protocol import TBinaryProtocol

class ScribeSender(object):
    def __init__(self, host='127.0.0.1', port=1463,debug=False,
                 target_write_size=1000, max_write_interval=1.0, 
                 socket_timeout=5.0, max_queue_length=50000, must_yield=True):
        self.dropped = 0
        self._remote_host = host
        self._remote_port = port
        self._socket_timeout = socket_timeout
        self._hostname = socket.gethostname()
        self._max_queue_length = max_queue_length
        self._max_write_interval = max_write_interval
        self._target_write_size = target_write_size

        self._debug = True
        self._log_buffer = collections.deque()
        self._last_write = 0
        self._must_yield = must_yield
        self._lock = threading.Lock()
        eventlet.spawn_after(max_write_interval, self.flush)

    def close(self):
        self.flush()

    def send(self, category, msg):
        """
        Send one record to scribe.
        """
        log_entry = scribe.LogEntry(category=category, message=msg)
        self._log_buffer.append(log_entry)
        self._dropMsgs()
        
        now = time.time()
        if len(self._log_buffer) >= self._target_write_size or \
                now - self._last_write > self._max_write_interval:
            self._last_write = now
            eventlet.spawn_n(self.flush)
            # We can't do a "looping call" or other permanent thread
            # kind of thing because openstack creates new hubs.  The
            # spawn_after here (and in __init__) give us a simple way
            # to ensure stuff doesn't sit in the buffer forever just
            # because the app isn't logging stuff.
            eventlet.spawn_after(self._max_write_interval, self.flush)
        if self._must_yield:
            # prevent the flushers from starving
            eventlet.sleep()

    def flush(self):
        dropped = 0
        try:
            self._lock.acquire()
            buf = []
            while self._log_buffer:
                buf.append(self._log_buffer.popleft())
            if buf:
                if self._debug:
                    print "ScribeSender: flushing {0} msgs".format(len(buf))
                try:
                    client = self._getClient()
                    result = client.Log(messages=buf)
                    if result == scribe.ResultCode.TRY_LATER:
                        dropped += len(buf)
                except:
                    if self._debug:
                        print "ScribeSender: caught exception writing log message:"
                        traceback.print_exc()
                    dropped += len(buf)
        finally:
            self._lock.release()
            self.dropped += dropped
            if self._debug and dropped:
                print "ScribeSender: dropped {0} messages for communication problem.".format(dropped)

    def _dropMsgs(self):
        dropped = 0
        while len(self._log_buffer) > self._max_queue_length:
            self._log_buffer.popleft()
            dropped += 1
        self.dropped += dropped
        if self._debug and dropped:
            print "ScribeSender: dropped {0} messages for queue length.".format(dropped)

    def _getClient(self):
        # We can't just keep a connection because the app might fork
        # and we'll be left with the parent process's connection.
        # More robust to just open one for each flush.
        sock = TSocket.TSocket(host=self._remote_host, port=self._remote_port)
        sock.setTimeout(self._socket_timeout * 1000)
        transport = TTransport.TFramedTransport(sock)
        transport.open()
        protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
        return scribe.Client(protocol)
        
