#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Supports flushing metrics to graphite via SSL socket connection

WARNING: There's no host / cert checking here!

For improved security see:
* https://docs.python.org/3/library/ssl.html#ssl-security
* https://github.com/RTBHOUSE/graphite-gw
'''

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
    with_statement,
)

import logging
import socket
import ssl
import sys

from graphite import GraphiteStore


class GraphiteStoreSSL(GraphiteStore):
    '''Graphite store pusher
    '''
    def __init__(self, *args, **kwargs):
        super(GraphiteStoreSSL, self).__init__(*args, **kwargs)
        self.ssl_opts = kwargs['ssl_opts']
        self.hostname = kwargs['hostname']


    def _create_socket(self):
        '''Creates a SSL socket and connects to the graphite server
        '''
        #cli_ctx = ssl.create_default_context()

        cli_ctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
        cli_ctx.verify_mode = ssl.CERT_REQUIRED
        cli_ctx.check_hostname = True
        cli_ctx.verify_flags = ssl.VERIFY_X509_STRICT
        if hasattr(ssl, 'VERIFY_X509_TRUSTED_FIRST'):
            cli_ctx.verify_flags |= getattr(ssl, 'VERIFY_X509_TRUSTED_FIRST', 0)
        cli_ctx.options = 0
        for opt in ['OP_NO_TLSv1', 'OP_NO_TLSv1_1', 'OP_NO_SSLv2', 'OP_NO_SSLv3', \
                'OP_NO_COMPRESSION', 'OP_CIPHER_SERVER_PREFERENCE', \
                'OP_SINGLE_DH_USE', 'OP_SINGLE_ECDH_USE']:
            cli_ctx.options |= getattr(ssl, opt, 0)

        cli_ctx.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)

        if self.ssl_opts['cafile']:
            cli_ctx.load_verify_locations(cafile=self.ssl_opts['cafile'])

        if self.ssl_opts['cli_certfile'] and self.ssl_opts['cli_keyfile']:
            cli_ctx.load_cert_chain(
                self.ssl_opts['cli_certfile'], keyfile=self.ssl_opts['cli_keyfile'],
                password=self.ssl_opts['cli_passfile'] \
                    if self.ssl_opts.get('cli_keyfile') else None)

        cli_ctx.set_ciphers(
            'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:' \
            'ECDH+AES128:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS')

        if self.ssl_opts['cli_dhfile']:
            cli_ctx.load_dh_params(self.ssl_opts['cli_dhfile'])

        #def server_name_callback(ssl_sock, server_name, ssl_ctx):
        #    print('ssl_sock:', ssl_sock)
        #    print('server_name:', server_name)
        #    print('ssl_ctx:', ssl_ctx)

        #cli_ctx.set_servername_callback(server_name_callback)

        cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli_sock.settimeout(10)

        ssl_sock = cli_ctx.wrap_socket(cli_sock, server_hostname=self.hostname)
        ssl_sock.connect((self.host, self.port))

        return ssl_sock


def main():
    '''Main method
    '''
    logging.basicConfig(
        level=logging.NOTSET,
        format='%(asctime)s %(name)s %(levelname)s %(module)s:%(lineno)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %Z')

    graphite = GraphiteStoreSSL(*sys.argv[1:])
    metrics = sys.stdin.read()
    graphite.flush(metrics.split('\n'))
    graphite.close()


if __name__ == '__main__':
    main()
