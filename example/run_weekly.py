import sys
sys.path.append("/Users/morris/GitHub/xsede_report/xsede")

import add_to_db
import plot_graphs
import datetime

db_file = 'xsede.2018.db'
xdusage_file = 'gather.dat'
setup_file = 'setup.dat'
output_path = './'
current_date = datetime.datetime.now()

add_to_db.run(db_file=db_file, xdusage_file=xdusage_file, setup_file=setup_file, current_date=current_date, setup=False)
plot_graphs.run(db_file=db_file, setup_file=setup_file, output_path=output_path)


