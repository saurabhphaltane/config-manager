import logging

# logging_configurations
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='tool.log',
                    filemode='a+')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

def log_message( *log ):
    """Logs the given message"""
    message = ''.join([i for i in log ])
    if message:
        logging.info(message)

def log_error( *log ):
    """Logs the given error message"""
    message = ''.join([i for i in log ])
    if message:
        logging.error(message)
