tomograph
=========

A library to help distributed applications send trace information to
metrics backends like [Zipkin][zipkin] and [Statsd][statsd].

Data Model
----------

A request to a distributed application is modeled as a trace.  Each
trace consists of a set of spans, and a span is a set of notes.

Each span's extent is defined by its first and last notes.  Any number
of additional notes can be added in between -- for example in a
handler for ERROR-level logging.

The tomograph data model is basically the Dapper/Zipkin data model.
For translation to statsd, we emit the length of the span as a timer
metric, and each note gets emitted individually as a counter metric.

For example, here is a basic client/server interaction.  It is one
trace, with two spans, each with two notes -- their beginning and end:

![zipkin client server](https://raw.github.com/timjr/tomograph/raw/master/doc/screenshots/client-server-zipkin.png)

This is the same data as it would be viewed in using the statsd
backend with graphite:

![graphite client server](https://raw.github.com/timjr/tomograph/master/doc/screenshots/client-server-graphite.png)


Tracing Your Application
------------------------

There are a few basic ways to add tracing to your application.  The
lowest level one is to call start, stop, and annotate yourself:

    import tomograph

    tomograph.start('my service', 'a query', '127.0.0.1', 80)
    (...)
    tomograph.annotate('something happened')
    (...)
    tomograph.stop('a query')

Each start/stop pair defines a span.  Spans can be arbitrarily nested
using this interface as long they stay on a single thread: tomograph
keeps the current span stack in thread local storage.

When continuing a trace from one thread to another, you must grab the
trace token from tomograph and pass it:

    token = tomograph.get_trace_info()
    (...)
    tomograph.start('my service', 'a query', '127.0.0.1', 80, token)
    (...)

That will enable tomograph to connect all of the spans into one trace.

Helpers
-------

There are some slightly higher level interfaces to help you add
tracing.  For HTTP, add_trace_info_header() will add an X-Trace-Info
header to a dict on the client side, and start_http() will consume
that header on the server side:

    def traced_http_client(url, body, headers):
        tomograph.start('client', 'http request', socket.gethostname(), 0)
        tomograph.add_trace_info_header(headers)
        http_request(url, body, headers)
        tomograph.stop('http request')


    def traced_http_server(request):
        tomograph.start_http('server', 'http response', request)
        (...)
        tomograph.stop('http response')

There's no need to call start and stop yourself -- you can use the
@tomograph.traced decorator:

        @tomograph.traced('My Server', 'myfunc')
        def myfunc(yadda):
            dosomething()

For WSGI pipelines, there's the class tomograph.Middleware that will
consume the X-Trace-Info header.  It can be added to a paste pipeline
like so:

    [pipeline:foo]
    pipeline = tomo foo bar baz...

    [filter:tomo]
    paste.filter_factory = tomograph:Middleware.factory
    service_name = glance-registry
    
If you use [SQL Alchemy][sql alchemy] in your application, there are
some event listeners available that will trace SQL statement
execution:

    _ENGINE = sqlalchemy.create_engine(FLAGS.sql_connection, **engine_args)

    sqlalchemy.event.listen(_ENGINE, 'before_execute', tomograph.before_execute('my app'))
    sqlalchemy.event.listen(_ENGINE, 'after_execute', tomograph.after_execute('my app'))


Screenshots
-----------

Here is a slightly more involved example -- a glance image list
command in [Openstack][openstack].  It uses SQL statement tracing and
the tomograph middleware:

![zipkin glance image list](https://raw.github.com/timjr/tomograph/raw/master/doc/screenshots/zipkin-glance-image-list.png)


[openstack]: http://www.openstack.org/
[statsd]: https://github.com/etsy/statsd
[zipkin]: http://twitter.github.com/zipkin/
[sql alchemy]: http://www.sqlalchemy.org/
