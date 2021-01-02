import json
import argparse
import FioResultDecoder
from dateutil.parser import parse

def is_date(string):
    try:
        parse(string)
        return True
    except ValueError:
        return False

def print_schema_def(key, value):
    typestr = value.__class__.__name__
    if typestr == 'str' or typestr == 'unicode':
        if (is_date(value)):
            typestr = "datetime"
        else:
            typestr = "varchar(256)"
    return ",\n  `{}` {} NOT NULL".format(key, typestr)

parser = argparse.ArgumentParser()
parser.add_argument('infile', help="The json file to strip")
args = parser.parse_args()

json_data = open(args.infile)
data = json.load(json_data, cls=FioResultDecoder.FioResultDecoder)

# These get populated by the test runner, not fio, so add them so their
# definitions get populated in the schema properly
data['global']['config'] = 'default'
data['global']['kernel'] = '4.14'

print("CREATE TABLE `fio_runs` (")
outstr = "  `id` int(11) PRIMARY KEY"
for key,value in data['global'].items():
    outstr += print_schema_def(key, value)
print(outstr)
print(");")

job = data['jobs'][0]
job['run_id'] = 0

print("CREATE TABLE `fio_jobs` (")
outstr = "  `id` int PRIMARY KEY"
for key,value in job.items():
    outstr += print_schema_def(key, value)
print(outstr)
print(");")
