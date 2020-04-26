import socket
import re
import concurrent.futures
from tqdm import tqdm
from time import sleep

TCP_IP = '222.222.1.38'
PRINTER_PORT = 8899
BUFFER_SIZE = 1024
# print status
PRINT_STATUS = b"~M27"
# print status
PRINT_TEMPERATURE = b"~M105"
# printer status
PRINT_NOZZLE_STATUS = b"~M119"

def test_connection(addr, port):
    # print("Checking " + addr)
    socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setdefaulttimeout(1)
    result = socket_obj.connect_ex((addr, port))
    socket_obj.close()
    return result


def find_printer(ip_template):
    printer_candidate = []
    addr_list = []
    for test_ip in range(0, 255):
        addr_list.append(ip_template + str(test_ip))
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_addr = {executor.submit(test_connection, addr, PRINTER_PORT): addr for addr in addr_list}
        for future in tqdm(concurrent.futures.as_completed(future_to_addr), total=len(addr_list),
                           desc="Searching for printers"):
            addr = future_to_addr[future]
            data = future.result()
            if data == 0:
                printer_candidate.append(addr)
    return printer_candidate


def read_byte_response(byte_response):
    return byte_response.decode("utf-8").split('\n', 1)[1][:-4]


def send_command(s, cmd, msg):
    s.send(cmd)
    return read_byte_response(s.recv(BUFFER_SIZE))


#    print(msg, data)


def get_printer_status(printer_ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setdefaulttimeout(1)
    s.connect((printer_ip, PRINTER_PORT))
    out = ""
    out += send_command(s, PRINT_STATUS, "Print progress:\n")
#    if(re.match("failed", out)sea):
    current_percentage = read_current_percentage(out)
    out += send_command(s, PRINT_TEMPERATURE, "Printer temperature:\n")
    out += send_command(s, PRINT_NOZZLE_STATUS, "Status:\n")
    s.close()
    return current_percentage, out


def read_current_percentage(out):
    current_percentage = re.search("\d+", out).group(0)
    return current_percentage


localIP = (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [
    [(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in
     [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0]

ip_template = re.match("\d+\.\d+\.\d+\.", localIP).group(0)
printers = find_printer(ip_template)

if len(printers) == 0:
    print("No printers found. Goodbye.")
    exit(0)
else:
    pbars = {}
    last_values = {}
    for ip in printers:
        pbars[ip] = tqdm(total=100, desc=ip)
        last_values[ip] = 0
    try:
        while True:
            for ip in printers:
                result = get_printer_status(ip)
                intr = int(result[0])
                pbars[ip].update(intr - last_values[ip])
#                pbars[ip].write(result[1])
                last_values[ip] = intr
            sleep(1)
    except KeyboardInterrupt:
        for key in pbars:
            pbars[key].close()
        print('interrupted! Goodbye!')
