import getopt
import subprocess
import sys
import socket
import threading

from _socket import SocketType


def usage():
    print("NetDog - the Net Cat Clone Tool")
    print("")
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving a connection")
    print("-c --command - initialize a command shell")
    print(
        "-u --upload=destination - upon receiving connection upload a file and write to [destination]")
    print("")
    print("")
    print("Examples: ")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)


def main():
    global listen
    global execute
    global port
    global command
    global upload_destination
    global target

    # Check args if valid or not
    if not (len(sys.argv[1:])):
        usage()
    # read the commandline options
    opts, args = getopt.getopt(sys.argv[1:], "hle:p:cu:t:",
                               ["help", "listen", "execute", "port", "command", "upload", "target"])

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--commandshell"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled Option"

    # read data and send if not listen
    if not listen and len(target) and port > 0:
        buffer = sys.stdin.read()
        send_data(buffer)

    if listen:
        server_loop()


def send_data(buffer):
    # create a socket object
    # AF_INET: host's ipv4
    # AF_INET6: host's ipv6
    # SOCK_STREAM: tcp socket
    # SOCK_DGRAM: UDP socket.
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect to client
    try:
        client.connect((target, port))
        # send data
        if len(buffer):
            client.send(buffer)
        while True:
            recv_len = 1
            response = ""

            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data

                # last data packet
                if recv_len < 4096:
                    break

            print(response)
            buffer = input("")
            buffer += "\n"

            client.send(buffer)

    except:
        print("[*] Exception! Exiting.")
        # tear down the connection
        client.close()


def server_loop():
    global target
    # if no target is defined, we listen on all interfaces
    if not len(target):
        target = "0.0.0.0"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)
    while True:
        client_socket, addr = server.accept()
        # spin off a thread to handle our new client
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

def run_command(command: str) -> str:
    command = command.rstrip()
    try:
        return subprocess.check_output(command,stderr=subprocess.STDOUT, shell=True)
    except:
        return "Failed to execute command.\r\n"

def client_handler(client_socket: SocketType):
    global upload
    global command
    global execute

    # check for download
    if len(upload_destination):
        file_buffer = ""
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            else:
                file_buffer += data

        # read file and write to destination
        try:
            file_descriptor = open("file", "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()
        except:
            client_socket.send("Failed to save file to %s\r\n" %upload_destination)

    # check for execute
    if len(execute):
        client_socket.send(run_command(execute))


main()
