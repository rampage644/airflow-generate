#!/usr/bin/env python
import sys
import os
import re

from optparse import OptionParser
from crontab import CronTab
from jinja2 import FileSystemLoader, Environment

from yaml import dump


def remove_user_from_templated(command_with_user):
    match = re.search(r'\{{0,2}\s?\w+\s?\}{0,2}\s(.*)', command_with_user)
    return match.group(1) if match else command_with_user


def substitute_template_variables_with_config(command):
    config_vars = []

    def replace(input_string):
        config_vars.append(input_string.group(1))
        return '{{{}}}'.format(input_string.group(1))
        # return 'task_config[\'{0}\']'.format(input_string.group(1))

    formatted_string = re.sub(r'\{{2}\s*(\w+)\s*\}{2}', replace, command)
    formatted_args = ', '.join(
        ['{0}=task_config[\'{0}\']'.format(var) for var in config_vars])

    return '\'{0}\'.format({1})'.format(
        formatted_string, formatted_args
    ), config_vars


def main():
    parser = OptionParser()
    parser.add_option("-d", "--directory", dest="directory",
                      help="directory for output files")
    parser.add_option("-f", "--force",
                      action="store_true", dest="force", default=False,
                      help="force file overwrite")

    (options, args) = parser.parse_args()

    env = Environment(loader=FileSystemLoader('.'))
    for cron in [CronTab(tabfile=os.path.abspath(arg)) for arg in args]:
        for job in cron:
            test_template = env.get_template('workflow-test-template.jj2')
            template = env.get_template('workflow-template.jj2')
            match = re.search(r'/(.*)\.', job.command)
            command = remove_user_from_templated(job.command)
            task_name = match.group(1) if match else ''
            task_name = task_name.replace('-', '_')
            command, vars = substitute_template_variables_with_config(command)
            values = {
                'hour': job.hour,
                'minute': job.minute,
                'task_config_filename': task_name + '.yaml',
                'dag_id': task_name,
                'task_id': task_name,
                'command': command
            }

            with open(task_name + '.py', 'w') as wfile:
                wfile.write(template.render(**values))
            with open('test_' + task_name + '.py', 'w') as tfile:
                tfile.write(test_template.render({
                            'workflow_module_name': task_name
                            }))
            with open(task_name + '.yaml', 'w') as cfile:
                dump({var: '' for var in vars}, cfile)

    return 0

if __name__ == '__main__':
    sys.exit(main())
