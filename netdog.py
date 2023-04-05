import getopt
import os
import subprocess
import sys
import socket
import threading
import chardet

from _socket import SocketType

listen = False
execute = ""
port: int
command = ""
upload_destination = ""
target = ""
file = ""


def recv_custom(client_socket: SocketType) -> str:
    return client_socket.recv(1024).decode()


def send_custom(client_socket: SocketType, msg: str) -> int:
    return client_socket.send(msg.encode())


def usage():
    print("NetDog - the Net Cat Clone Tool")
    print("")
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving a connection")
    print("-c --command - initialize a command shell")
    print("-u --upload=destination - upon receiving connection upload a file and write to [destination]")
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
    global file

    print("main")
    # Check args if valid or not
    if not (len(sys.argv[1:])):
        usage()
    # read the commandline options
    opts, args = getopt.getopt(sys.argv[1:], "hle:p:cu:t:f:",
                               ["help", "listen", "execute", "port", "command", "upload", "target", "file"])

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
        elif o in ("-f", "--file"):
            file = a
        else:
            assert False, "Unhandled Option"

    # read data and send if not listen
    if not listen and len(target) and port > 0:
        if file:
            file_discriptor = open(file, "r")
            send_data(file_discriptor.read())
            file_discriptor.close()
        else:
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
            client.send(buffer.encode())
            client.close()
        if not file:
            while True:
                recv_len = 1
                response = ""

                while recv_len:
                    data = client.recv(4096)
                    recv_len = len(data)
                    response += data.decode()

                    # last data packet
                    if recv_len < 4096:
                        break

                print(response)
                buffer = input("")
                buffer += "\n"

                client.send(buffer.encode())

    except Exception as e:
        print(e)
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
    # subprocess.call() creates a new process.The cd works in that process, but when the process exits it won't
    # affect the current process. This is how processes are designed to work. If you need your script to change to a
    # different directory you can use os.chdir which will change the directory for the current process.
    try:
        if command[0:5] == "cd ..":
            os.chdir("..")
            return "Current working dir is: %s" % os.getcwd()
        elif command[0:3] == "cd ":
            os.chdir(command[3:len(command)])
            return "Current working dir is: %s" % command[3:len(command)]
        else:
            byte = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            the_encoding = chardet.detect(byte)['encoding']
            return byte.decode(the_encoding)
    except Exception as e:
        return e


def client_handler(client_socket: SocketType):
    global upload
    global command
    global execute

    # check for download
    if len(upload_destination):
        file_buffer = ""
        while True:
            data = client_socket.recv(1024).decode()

            if not data:
                break
            else:
                file_buffer += data

        # read file and write to destination
        try:
            file_descriptor = open("file", "w")
            file_descriptor.write(file_buffer)
            file_descriptor.close()
            client_socket.send("Save file successfully!!!".encode())
        except Exception as e:
            client_socket.send(e)
            client_socket.send("Failed to save file to %s\r\n" % upload_destination)

    # check for execute
    if len(execute):
        send_custom(client_socket, run_command(execute))
    if command:
        # wait til command send then execute 
        while True:
            # send_custom(client_socket, "NetDog: #> ")
            # client_socket.send("NetDog: #> ".encode())
            cmd_buffer: str = ""

            while "\n" not in cmd_buffer:
                # cmd_buffer += recv_custom(client_socket)
                cmd_buffer += client_socket.recv(1024).decode()
            client_socket.send(run_command(cmd_buffer).encode())
            # send_custom(client_socket, run_command(cmd_buffer))


main()
