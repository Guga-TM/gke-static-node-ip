# GKE static Node IP controller
# Copyright (C) 2026  Guga Mikulich

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# email for contacts: aragornguga@gmail.com

import os

class Colors:
    RED = '\033[31m'
    BLUE = '\033[34m'
    ORANGE = '\033[38;5;214m'
    RESET = '\033[0m'

def get_log_level():
    # default is 'error'
    log_level = os.getenv('LOG_LEVEL', 'error')

    # validation
    if log_level not in ['error', 'info']:
        log_error('logger', f'log level {log_level} is not defined')
        raise Exception
    
    return log_level

def log_system(message):
    print(Colors.BLUE + message + Colors.RESET)

def log_info(component, message):
    if get_log_level() == 'info': 
        print(f"{component}: {message}")

# def log_warn(component, message):
#     print(Colors.ORANGE + f"{component}: {message}" + Colors.RESET)

def log_error(component, message):
    print(Colors.RED + f"{component}: {message}" + Colors.RESET)