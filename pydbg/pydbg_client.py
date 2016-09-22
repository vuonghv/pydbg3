#!c:\python\python.exe

#
# PyDBG
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: pydbg_client.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation;
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""
@author:       Pedram Amini
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
"""

import socket
try:
    import cPickle as pickle
except ImportError:
    import pickle

from pydbg.pydbg import PyDBG
from pydbg.defines import *
from pydbg.errors import PDError


class PyDBGClient(object):
    """
    This class defines the client portion of the
    decoupled client/server PyDBG debugger.
    The class was designed to be completely transparent to the end user,
    requiring only the simple change from::

        dbg = PyDBG()

    to::

        dbg = PyDBGClient(host, port)

    Command line options can be used to control which instantiation
    is used thereby allowing for any PyDBG driver to be
    used locally or remotely.
    """

    def __init__(self, host, port):
        """
        Set the default client attributes. The target host and port are required.

        @type  host: String
        @param host: Host address of PyDBG server (dotted quad IP address or hostname)
        @type  port: Integer
        @param port: Port that the PyDBG server is listening on.

        @raise PDError: An exception is raised if a connection to the PyDbg server can not be established.
        """

        self.host = host
        self.port = port
        self.pydbg = PyDBG()
        self.callbacks = {}

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
        except:
            raise PDError("connection severed")

    def __getattr__(self, method_name):
        """
        This routine is called by default when a requested attribute
        (or method) is accessed that has no definition.
        Unfortunately __getattr__ only passes the requested method name and
        not the arguments. So we extend the functionality with
        a little lambda magic to the routine method_missing().
        Which is actually how Ruby handles missing methods
        by default ... with arguments. Now we are just as cool as Ruby.

        @type  method_name: String
        @param method_name: The name of the requested and undefined attribute (or method in our case).

        @rtype:  Lambda
        @return: Lambda magic passing control (and in turn the arguments we want) to self.method_missing().
        """

        return lambda *args, **kwargs: self.method_missing(method_name, *args, **kwargs)

    def debug_event_loop(self):
        """
        Overriden debug event handling loop.
        A transparent mirror here with method_missing() would not do.
        Our debug event loop is reduced here to a data marshaling loop with
        the server. If the received type from the server is a tuple then
        we assume a debug or exception event has occured and
        pass it to any registered callbacks.
        The callback is free to call arbitrary PyDbg routines.
        Upon return of the callback, a special token, **DONE**, is used to
        flag to the PyDbg server that we are done processing
        the exception and it is free to move on.
        """

        self.pickle_send(("debug_event_loop", ()))

        while 1:
            received = self.pickle_recv()

            if not received:
                continue

            # if we received a "special" type, which can currently be one of:
            #   - debugger callback event
            #   - user callback event
            #   - raised exception

            if isinstance(received, tuple):
                # callback type
                if received[0] == "callback":
                    (msg_type, dbg, context) = received

                    # debugger callback event
                    if dbg and context:
                        # propogate the convenience variables.
                        self.dbg = dbg
                        self.context = context
                        self.exception_address = dbg.u.Exception.ExceptionRecord.ExceptionAddress
                        self.write_violation = dbg.u.Exception.ExceptionRecord.ExceptionInformation[0]
                        self.violation_address = dbg.u.Exception.ExceptionRecord.ExceptionInformation[1]
                        
                        exception_code = dbg.u.Exception.ExceptionRecord.ExceptionCode
                        ret = DBG_CONTINUE
    
                        if exception_code in self.callbacks:
                            print('processing handler for 0x{:08x}'.format(exception_code))
                            ret = self.callbacks[exception_code](self)
                    
                    # user callback event.
                    elif USER_CALLBACK_DEBUG_EVENT in self.callbacks:
                            ret = self.callbacks[USER_CALLBACK_DEBUG_EVENT](self)
                
                # raised exception type.
                elif received[0] == "exception":
                    (msg_type, exception_string) = received
                    print(exception_string)
                    raise PDError(exception_string)
                    
                self.pickle_send(('**DONE**', ret))

    def method_missing(self, method_name, *args, **kwargs):
        """
        See the notes for __getattr__ for related notes.
        This method is called, in the Ruby fashion, with the method
        name and arguments for any requested but undefined class method.
        We utilize this method to transparently wrap requested PyDBG routines,
        transmit the method name and arguments to the server,
        then grab and return the methods return value.
        This transparency allows us to modify pydbg.py freely without
        having to add support for newly created methods to pydbg_client.py.
        Methods that require "special" attention and can not simply
        be mirrored are individually overridden and handled separately.

        @type  method_name: String
        @param method_name: The name of the requested and undefined attribute (or method in our case).
        @type  args:       Tuple
        @param args:       Tuple of arguments.
        @type  kwargs     Dictionary
        @param kwargs:    Dictioanry of arguments.

        @rtype:  Mixed
        @return: Return value of the mirrored method.
        """

        # some functions shouldn't go over the network.
        # XXX - there may be more routines we have to add to this list.
        if method_name in ("hex_dump", "flip_endian", "flip_endian_dword"):
            exec("method_pointer = self.pydbg.%s" % method_name)
            ret = method_pointer(*args, **kwargs)
        else:
            self.pickle_send((method_name, (args, kwargs)))
            ret = self.pickle_recv()

        if ret == "**SELF**":
            return self
        else:
            return ret

    def pickle_recv(self):
        """
        This routine is used for marshaling arbitrary data from
        the PyDbg server. We can send pretty much anything here.
        For example a tuple containing integers, strings, arbitrary objects
        and structures. Our "protocol" is a simple length-value protocol
        where each datagram is prefixed by a 4-byte length of
        the data to be received.

        @raise pdx: An exception is raised if the connection was severed.
        @rtype:     Mixed
        @return:    Whatever is received over the socket.
        """

        try:
            length = int(self.sock.recv(4), 16)
            received = self.sock.recv(length)
        except:
            raise PDError("connection severed")
        
        return pickle.loads(received)

    def pickle_send(self, data):
        """
        This routine is used for marshaling arbitrary data to the PyDbg server.
        We can send pretty much anything here.
        For example a tuple containing integers, strings, arbitrary objects
        and structures. Our "protocol" is a simple length-value protocol
        where each datagram is prefixed by a 4-byte length of
        the data to be received.

        @type  data: Mixed
        @param data: Data to marshal and transmit. Data can *pretty much* contain anything you throw at it.

        @raise pdx: An exception is raised if the connection was severed.
        """

        data = pickle.dumps(data)

        try:
            self.sock.send("%04x" % len(data))
            self.sock.send(data)
        except:
            raise PDError("connection severed")

    def run(self):
        """
        Alias for debug_event_loop().

        @see: debug_event_loop()
        """
        self.debug_event_loop()

    def set_callback(self, exception_code, callback_func):
        """
        Overriden callback setting routing.
        A transparent mirror here with method_missing() would not do.
        We save the requested callback address / exception code pair
        and then tell the PyDbg server about it. For more information
        see the documentation of pydbg.set_callback().

        @type  exception_code: Long
        @param exception_code: Exception code to establish a callback for
        @type  callback_func:  Function
        @param callback_func:  Function to call when specified exception code is caught.
        """

        self.callbacks[exception_code] = callback_func

        self.pickle_send(("set_callback", exception_code))
        
        return self.pickle_recv()
