import os
import subprocess
import time
import rrdtool
import configuration as config

# Configuration
IP_ADDRESSES = config.IP_ADDRESSES #  ['8.8.8.8', '1.1.1.1', 'google.com']
LOG_FILE = config.LOG_FILE #  = 'ping_log.txt'
RRD_DIR = config.RRD_DIR # = './rrd_files'
GRAPH_DIR = config.GRAPH_DIR # = './graphs'
STEP = config.STEP # = 1  # default 60 seconds between samples
HEARTBEAT = config.HEARTBEAT # = 60  # default 120 max interval between updates in seconds
SAMPLE_POINTS = config.SAMPLE_POINTS # = 1440 # 1440 sample points = 60 mins x 24 hrs

# Ensure directories exist
os.makedirs(RRD_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

def ping_ip(ip):
    """Ping an IP address once and return the response time in ms or None if no response."""
    try:
        # Using system ping command
        output = subprocess.check_output(
            ['ping', '-c', '1', '-W', '1', ip],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        # Parse response time
        for line in output.split('\n'):
            if 'time=' in line:
                time_ms = float(line.split('time=')[1].split(' ')[0])
                return time_ms
    except subprocess.CalledProcessError:
        return None

def create_rrd(ip):
    """Create an RRD database for an IP if it doesn't exist."""
    rrd_path = os.path.join(RRD_DIR, f'{ip}.rrd')
    if not os.path.exists(rrd_path):
        rrdtool.create(
            rrd_path,
            '--step', str(STEP),
            'DS:ping:GAUGE:{}:0:U'.format(HEARTBEAT),
            'RRA:AVERAGE:0.5:1:{}'.format(SAMPLE_POINTS)  # store 1 day of data (1440 samples of 1 min)
        )

def update_rrd(ip, value):
    """Update the RRD database with the latest ping result."""
    rrd_path = os.path.join(RRD_DIR, f'{ip}.rrd')
    timestamp = str(int(time.time()))
    data = str(value) if value is not None else 'U'
    rrdtool.update(rrd_path, f'{timestamp}:{data}')

def log_result(ip, value):
    """Log ping result to a log file."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'{timestamp} IP: {ip} Response Time: {value if value is not None else "Timeout"} ms\n'
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)

def generate_graph(ip):
    """Generate a graph image from RRD data."""
    rrd_path = os.path.join(RRD_DIR, f'{ip}.rrd')
    graph_path = os.path.join(GRAPH_DIR, f'{ip}.png')
    end_time = int(time.time())
    delta_time_secs = 3600  # 24*60*60 = last 24 hours
    start_time = end_time - delta_time_secs
    
    rrdtool.graph(
        graph_path,
        '--start', str(start_time),
        '--end', str(end_time),
        '--title', f'Ping Response Time for {ip}',
        '--vertical-label', 'ms',
        '--width', '600',
        '--height', '200',
        'DEF:ping=' + rrd_path + ':ping:AVERAGE',
        'LINE1:ping#0000FF:Response Time'
    )

def main():
    # Create RRDs for each IP
    for ip in IP_ADDRESSES:
        create_rrd(ip)

    while True:
        print(f"Pinging: {IP_ADDRESSES}")
        for ip in IP_ADDRESSES:
            response_time = ping_ip(ip)
            log_result(ip, response_time)
            update_rrd(ip, response_time)
            generate_graph(ip)
        time.sleep(STEP)

if __name__ == '__main__':
    main()