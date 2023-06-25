# coding: utf-8

import socket
import selectors
import signal
import logging
import argparse
import datetime

# configure logger output format
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger('Load Balancer')


# used to stop the infinity loop
done = False

sel = selectors.DefaultSelector()

policy = None
mapper = None


# implements a graceful shutdown
def graceful_shutdown(signalNumber, frame):  
    logger.debug('Graceful Shutdown...')
    global done
    done = True


# n to 1 policy
class N2One:
    def __init__(self, servers):
        self.servers = servers  

    def select_server(self):
        return self.servers[0]

    def update(self, *arg):
        pass


# round robin policy
class RoundRobin:
    

    def __init__(self, servers):
        self.servers = servers
        self.index = 0

    def select_server(self):
        
        if self.index > len(self.servers)-1:
            self.index = 0
        
        position = self.index
        self.index += 1

        return self.servers[position]
    
    def update(self, *arg):
        pass


# least connections policy
class LeastConnections:
    def __init__(self, servers):
        self.servers = servers
        self.conn_array = []
        for i in self.servers:
            self.conn_array.append(0)


    def select_server(self):  
        minimum = min(self.conn_array)
        index = self.conn_array.index(minimum)
        self.conn_array[index] += 1
        return self.servers[index]



    def update(self, *arg):     #terminar ligaçao
        index = 0
        for i in self.servers:
            if i == arg[0]:
                self.conn_array[index] -= 1
            index += 1
            
            


# least response time
class LeastResponseTime:
    def __init__(self, servers):
        self.servers = servers
        self.n_conn = []
        self.average_time = []
        self.timestamp_inic = []
        self.timestamp_final = []
        for i in self.servers:
            self.n_conn.append(0)
            self.timestamp_inic.append(0)
            self.average_time.append(0)
            self.timestamp_final.append(0)
            

    def select_server(self):
        minimum = min(self.average_time)
        index = self.average_time.index(minimum)
        if self.timestamp_inic[index] <= self.timestamp_final[index]:
            self.timestamp_inic[index] = datetime.datetime.now().timestamp()
        self.n_conn[index] += 1
        self.average_time[index] += 0.0000000001
        return self.servers[index]

    def update(self, *arg):
        idx = 0
        for i in self.servers:
            if i == arg[0]:
                break
            idx += 1
        self.timestamp_final[idx] += datetime.datetime.now().timestamp()
        self.average_time[idx] = (self.timestamp_final[idx] - self.timestamp_inic[idx]) / self.n_conn[idx]
        

POLICIES = {
    "N2One": N2One,
    "RoundRobin": RoundRobin,
    "LeastConnections": LeastConnections,
    "LeastResponseTime": LeastResponseTime
}

class SocketMapper:
    def __init__(self, policy):
        self.policy = policy
        self.map = {}

    def add(self, client_sock, upstream_server):
        client_sock.setblocking(False)
        sel.register(client_sock, selectors.EVENT_READ, read)
        upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream_sock.connect(upstream_server)
        upstream_sock.setblocking(False)
        sel.register(upstream_sock, selectors.EVENT_READ, read)
        logger.debug("Proxying to %s %s", *upstream_server)
        self.map[client_sock] =  upstream_sock

    def delete(self, sock):
        paired_sock = self.get_sock(sock)
        sel.unregister(sock)
        sock.close()
        sel.unregister(paired_sock)
        paired_sock.close()
        if sock in self.map:
            self.map.pop(sock)
        else:
            self.map.pop(paired_sock)

    def get_sock(self, sock):
        for client, upstream in self.map.items():
            if upstream == sock:
                return client
            if client == sock:
                return upstream
        return None
    
    def get_upstream_sock(self, sock):
        return self.map.get(sock)

    def get_all_socks(self):
        """ Flatten all sockets into a list"""
        return list(sum(self.map.items(), ())) 

def accept(sock, mask):
    client, addr = sock.accept()
    logger.debug("Accepted connection %s %s", *addr)
    mapper.add(client, policy.select_server())

def read(conn,mask):
    data = conn.recv(4096)
    if len(data) == 0: # No messages in socket, we can close down the socket
        mapper.delete(conn)
    else:
        mapper.get_sock(conn).send(data)


def main(addr, servers, policy_class):
    global policy
    global mapper

    # register handler for interruption 
    # it stops the infinite loop gracefully
    signal.signal(signal.SIGINT, graceful_shutdown)

    policy = policy_class(servers)
    mapper = SocketMapper(policy)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(addr)
    sock.listen()
    sock.setblocking(False)

    sel.register(sock, selectors.EVENT_READ, accept)

    try:
        logger.debug("Listening on %s %s", *addr)
        while not done:
            events = sel.select(timeout=1)
            for key, mask in events:
                if(key.fileobj.fileno()>0):
                    callback = key.data
                    callback(key.fileobj, mask)
                
    except Exception as err:
        logger.error(err)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pi HTTP server')
    parser.add_argument('-a', dest='policy', choices=POLICIES)
    parser.add_argument('-p', dest='port', type=int, help='load balancer port', default=8080)
    parser.add_argument('-s', dest='servers', nargs='+', type=int, help='list of servers ports')
    args = parser.parse_args()
    
    servers = [('localhost', p) for p in args.servers]
    
    main(('127.0.0.1', args.port), servers, POLICIES[args.policy])
