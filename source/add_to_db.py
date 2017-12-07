"""
This script will setup the xsede usage database
In order to run this script, you will need two files: 'gather.dat' and 'setup.dat'
 """

import sys
import os
import errno
from datetime import datetime, tzinfo
import numpy as np
import sqlite3


def run(db_file, xdusage_file, setup_file, current_date, setup=False):
    descriptionString = ''' This script will setup the database for the XSEDE Usage Report\n
    Please check to make sure the user input variables below are correct\n
    Note: This script should only be used at the beginning of the year\n'''
    print(descriptionString)

    print('database file: ' + db_file)
    assert not os.path.isfile(db_file), \
        'Fatal Error: database file %s already exists. Please remove before continuing' % db_file

    print('xdusage file name: ' + xdusage_file)
    assert os.path.isfile(
        xdusage_file), 'Fatal Error: Cannot find file %s' % xdusage_file

    print('setup file: ' + setup_file)
    assert os.path.isfile(
        setup_file), 'Fatal Error: Cannot find file %s' % setup_file
    machine_dict = read_setup_file(setup_file)

    conn = sqlite3.connect(db_file)
    create_db(conn)

    #date_string_format = "%Y-%m-%d"
    read_xdusage_output(xdusage_file, conn, machine_dict,
                        current_date, setup=True)

    conn.close()


def get_norm_total(machine_dict, machine_names, service_units):
    """Get normalized SU total from many machines

    Args:
        machine_dict (dictionary): dictionary of machines with conversion factors
        service_units (array-like): SUs for each machine
        machine_names (array-like): names of machines to get total from

    Returns:
        total(float): value for total number of normalized computing units.
    """

    total = 0.0
    assert len(machine_names) == len(service_units), \
        'The number of machines and the number of conversion factors are not the same'
    if len(service_units) == 0:
        print 'WARNING: No machines to tally'
        return total

    for i, machine_name in enumerate(machine_names):
        conversion_factor = machine_dict[machine_name]['conversionFactor']
        total += conversion_factor * service_units[i]
    return total


def read_xdusage_output(input_file, db_conn, machine_dict, current_date, setup=False):
    print "hello"
    date_string_format = "%Y-%m-%d %H:%M:%S.000"

    current_date_string = current_date.strftime(date_string_format)

    with open(input_file) as fp:
        working_on_machine = False
        machine_info = []
        user_info = []
        machine_name = ''
        for line in fp:
            if 'Project' in line:
                machine_name = line.strip().split()[1].split('/')[1]
                if machine_name in machine_dict:
                    working_on_machine = True
                else:
                    working_on_machine = False
            elif 'Allocation' in line:
                time_period = line.strip().split()[1].split('/')
                begin_date = datetime.strptime(
                    time_period[0], date_string_format)
                end_date = datetime.strptime(
                    time_period[1], date_string_format)
                if current_date > end_date or current_date < begin_date:
                    working_on_machine = False

            elif working_on_machine and 'Total' in line:
                split = line.strip().split()
                remaining = int(float(split[1].split('=')[1].replace(
                    ',', '')))
                if setup:
                    remaining = int(float(split[0].split('=')[1].replace(
                        ',', '')))

                machine_info.append(
                    (machine_name, current_date_string, remaining))

            elif (working_on_machine) and ('portal' in line) and (not 'inactive' in line):
                split = line.strip().split('usage')
                usage = int(float(split[1].split()[0].split(
                    '=')[1].replace(',', '')))
                if setup:
                    usage = 0
                nameString = split[0].replace('PI ', '')
                nameArray = nameString.split('portal')[0].strip().split(', ')
                name = nameArray[1] + ' ' + nameArray[0]
                user_info.append(
                    (name, machine_name, current_date_string, usage))

    data = zip(*machine_info)
    machine_info.append(
        ('Total', current_date_string, get_norm_total(machine_dict, data[0], data[2])))
    # print machineInfo

    c = db_conn.cursor()
    c.executemany(
        'INSERT INTO Machines (machine, date, remainingSU) VALUES (?,?,?)', machine_info)
    c.executemany(
        'INSERT INTO Users (name, machine, date, usage) VALUES (?,?,?,?)', user_info)

    db_conn.commit()


def create_db(db_conn):
    """Create Database file with tables

    Args: 
        db_file_conn (db connection): connection to database
    """

    c = db_conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Machines
                (key        INTEGER PRIMARY KEY,
                machine     TEXT,
                date        TEXT,
                remainingSU INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Users
        (key        INTEGER PRIMARY KEY,
            name        TEXT,
            machine     TEXT,
            date        TEXT,
            usage       INTEGER)''')
    db_conn.commit()


def read_setup_file(setup_file):
    """ Read setup file

    Args:
        setup_file (string): name of file to read in

    Returns:
        machine_dict (dictionary): dictionary of machines with conversion factors
    """
    machine_dict = {}
    with open(setup_file) as fp:
        print('\nMachines to input:')
        for line in fp:
            if len(line.strip()) > 0 and line[0] is not '#':
                split = line.split(',')
                machine_dict[split[0].strip()] = \
                    dict('outName': split[1].strip(),
                         'conversionFactor': float(split[2].strip()))
                print(split[0])
        print('\n')
    return machine_dict
