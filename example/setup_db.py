import sys
sys.path.append("/Users/morris/GitHub/xsede_report/xsede")

import add_to_db
import datetime

db_file = 'xsede.2018.db'
xdusage_file = 'gather.dat'
setup_file = 'setup.dat'
current_date = datetime.datetime(2018,1,1,0,0,0,1)
#current_date = datetime.datetime.now()
print current_date
add_to_db.run(db_file=db_file, xdusage_file=xdusage_file, setup_file=setup_file, current_date=current_date, setup=True)



