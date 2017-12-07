"""
This script will generate xsede usage plots
In order to run this script, you will need two files: 'gather.dat' and 'setup.dat'
 """

import sys
import getopt
import os
import errno
from datetime import datetime, tzinfo, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sqlite3
import numpy as np
import add_to_db
from operator import itemgetter


def run(db_file, setup_file, output_path):
    currentDate = datetime.now()
    print('database file: ' + db_file)
    assert os.path.isfile(db_file), \
        'Fatal Error: database file %s cannot be found' % db_file

    print('setup file: ' + setup_file)
    assert os.path.isfile(
        setup_file), 'Fatal Error: Cannot find file %s' % setup_file
    machine_dict = add_to_db.read_setup_file(setup_file)

    conn = sqlite3.connect(db_file)

    machine_usage = get_machine_usage_from_db(
        conn=conn, machine_dict=machine_dict)
    last_dates = get_last_two_dates(conn)
    prev_usage = get_user_usage_on_date(conn, machine_dict, last_dates[0])
    current_usage = get_user_usage_on_date(conn, machine_dict, last_dates[1])
    change_usage = calc_difference_in_usage(
        machine_dict, first_usage=prev_usage, second_usage=current_usage)
    percent_user_usage = calc_users_percent_usage(machine_dict, current_usage)
    plot_figures(machine_dict=machine_dict,
                 machine_usage=machine_usage,
                 change_user_usage=change_usage,
                 percent_user_usage=percent_user_usage,
                 output_path=output_path)

    conn.close()


def get_last_two_dates(conn, machine_name=''):
    date_string_format = "%Y-%m-%d %H:%M:%S.000"
    last_two_dates = []

    # Get two dates
    if len(machine_name) == 0:
        # inner selection 1 - get any single machine name
        machine_name = ''' SELECT machine 
                                From Machines 
                                ORDER BY machine ASC 
                                LIMIT 1'''
        machine_name = '(' + machine_name + ')'

    # inner selection 2 - get any single user
    user_name = ''' SELECT name 
                    From Users 
                    ORDER BY name ASC 
                    LIMIT 1'''
    user_name = '(' + user_name + ')'
    # main selection - select last two dates for single user and single machine
    selection_string = '''  SELECT date 
                            FROM Users 
                            WHERE Machine=%s
                            AND name=%s
                            ORDER BY date DESC 
                            LIMIT 2''' % (machine_name, user_name)

    for row in conn.cursor().execute(selection_string):
        last_two_dates.append(datetime.strptime(row[0], date_string_format))

    assert len(last_two_dates) == 2, \
        'Fatal Error: At least two date entries must be inputted before plots can be generated'
    last_two_dates.reverse()
    return last_two_dates


def get_machine_usage_from_db(conn, machine_dict):
    date_string_format = "%Y-%m-%d %H:%M:%S.000"

    c = conn.cursor()
    hours_dict = {}
    machine_keys = machine_dict.keys()
    machine_keys.append('Total')
    for machine_name in machine_keys:
        dates = []
        cpuHours = []
        for row in c.execute('SELECT date, remainingSU FROM Machines where machine = ? ORDER BY date', (machine_name,)):
            theDate = datetime.strptime(row[0], date_string_format)
            dates.append(theDate)
            cpuHours.append(float(row[1]))
        hours_dict[machine_name] = dict(
            [('dates', dates), ('usage', cpuHours)])
    return hours_dict


def get_user_usage_on_date(conn, machine_dict, date):
    date_string_format = "%Y-%m-%d %H:%M:%S.000"
    c = conn.cursor()
    total_user_usage = {}
    for machine_name in machine_dict.keys():
        names = []
        usage = []
        total_user_usage[machine_name] = {}
        for row in c.execute('SELECT name, usage FROM Users WHERE machine=? AND date = ? ORDER BY usage',
                             (machine_name, date.strftime(date_string_format))):
            user_name = row[0]
            usage = int(row[1])
            total_user_usage[machine_name][user_name] = usage
    return total_user_usage


def calc_users_percent_usage(machine_dict, users_usage, other_fraction=0.1):
    machine_percent_usage = {}
    for machine_name in machine_dict.keys():

        machine_sum = 0.0
        other_usage = 0.0
        fractional_usage = []
        names = []
        mykeys = users_usage[machine_name].keys()

        for user_name in mykeys:
            myusage = users_usage[machine_name][user_name]
            machine_sum += myusage

        if machine_sum > 0.0:
            for user_name in mykeys:
                user_usage = users_usage[machine_name][user_name] / machine_sum
                if user_usage > other_fraction:
                    fractional_usage.append(user_usage)
                    names.append(user_name.split()[0])
                else:
                    other_usage += user_usage

            fractional_usage.append(other_usage)
            names.append('other')

        machine_percent_usage[machine_name] = dict(
            [('names', names), ('usage', fractional_usage)])
    return machine_percent_usage


def calc_difference_in_usage(machine_dict, first_usage, second_usage):
    machine_user_usage = {}
    for machine_name in machine_dict.keys():
        names = []
        usage = []
        for user_name in second_usage[machine_name]:
            if user_name in first_usage[machine_name]:
                change_in_usage = second_usage[machine_name][
                    user_name] - first_usage[machine_name][user_name]
            else:
                change_in_usage = second_usage[machine_name][user_name]
            names.append(user_name.split()[0])
            usage.append(change_in_usage)

        sortedUsage = []
        sortedName = []
        if len(names) > 0:
            # sort for lowest values first
            sortedUsage, sortedName = [list(x) for x in zip(
                *sorted(zip(usage, names), key=itemgetter(0)))]
            # highest values first
            sortedUsage.reverse()
            sortedName.reverse()
        machine_user_usage[machine_name] = dict(
            [('names', sortedName), ('usage', sortedUsage)])
    return machine_user_usage


def calc_table_data(user_names, usages, num_entries=5):
    table_data = []
    for i in range(num_entries):
        table_data.append((user_names[i].split()[0], usages[i]))
    return table_data


def plot_figures(machine_dict, machine_usage, change_user_usage, percent_user_usage, output_path='./'):
    for machine_name in machine_dict.keys():

        plt.figure(figsize=(9.5, 6))
        ax = plt.subplot2grid((2, 3), (0, 0), colspan=2, rowspan=2)
        ax2 = plt.subplot2grid((2, 3), (0, 2))
        ax3 = plt.subplot2grid((2, 3), (1, 2))

        final_time_delta = timedelta(days=365)

        plot_machine_usage(ax, machine_name,
                           machine_dict[machine_name]['outName'],
                           machine_usage[machine_name]['dates'],
                           machine_usage[machine_name]['usage'],
                           final_time_delta)

        if machine_usage[machine_name]['usage'][-1] - machine_usage[machine_name]['usage'][0] == 0:
            ax3.xaxis.set_visible(False)
            ax3.yaxis.set_visible(False)
            ax3.axison = False
            ax2.xaxis.set_visible(False)
            ax2.yaxis.set_visible(False)
            ax2.axison = False
        elif machine_usage[machine_name]['usage'][-1] < 0:
            ax3.xaxis.set_visible(False)
            ax3.yaxis.set_visible(False)
            ax3.axison = False
            plot_percent_usage(ax2, percent_user_usage[machine_name]['names'],
                               percent_user_usage[machine_name]['usage'])
        else:
            plot_recent_usage(ax3, calc_table_data(change_user_usage[machine_name][
                              'names'], change_user_usage[machine_name]['usage']))
            plot_percent_usage(ax2, percent_user_usage[machine_name]['names'],
                               percent_user_usage[machine_name]['usage'])

        out_file = output_path + '/' + machine_name + '.png'
        plt.savefig(out_file)


def plot_machine_usage(axi, machine_name, machine_title, machine_dates, machine_usage, final_date_delta, hours_scale_factor=1e-3):
    initial_SU = machine_usage[0] * hours_scale_factor
    final_date = machine_dates[0] + final_date_delta
    ideal_dates = [machine_dates[0], final_date]
    ideal_usage = [initial_SU, 0]

    axi.plot(machine_dates, machine_usage * np.full(len(machine_usage), hours_scale_factor), linewidth=2,
             label='Actual', color='#0072bd')
    axi.plot(ideal_dates, ideal_usage, linewidth=2,
             label='Ideal', color='#d95319')
    axi.axis([machine_dates[0], final_date, 0, (ideal_usage[0] * 1.1)])
    axi.xaxis.set_major_locator(mdates.MonthLocator())
    axi.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axi.set_ylabel('1000\'s of SUs')
    axi.set_xlabel("")
    axi.set_title(machine_name.upper())
    plt.setp(axi.get_xticklabels(), rotation=45, ha='right')


def plot_percent_usage(axi, names, values):
    colors = ['#a2142f', '#0072bd', '#d95319',
              '#edb120', '#7e2f8e', '#77ac30', '#4dbeee']
    pie_wedge_collection = axi.pie(
        values, autopct='%1.f%%', labels=names, colors=colors[:len(names)], startangle=90)
    for pie_wedge in pie_wedge_collection[0]:
        pie_wedge.set_edgecolor('white')
    axi.set_title('Total Usage')


def plot_recent_usage(axi, table_data):
    # table_data is a list of 2 value tuples
    axi.table(cellText=table_data, loc='center')
    axi.xaxis.set_visible(False)
    axi.yaxis.set_visible(False)
    axi.axison = False
    axi.set_title('Last Week\'s Usage')
    ttl = axi.title
    ttl.set_position([.5, .85])
