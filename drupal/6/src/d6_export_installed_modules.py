from operator import truediv
import string
import sys
import argparse
import os
import MySQLdb
import re
import sshtunnel
from xml.sax.saxutils import escape

OUTPUT_DIRECTORY = 'output'
LOGS_DIRECTORY = 'logs'

ENDL = '\n'

SINGLE_QUOTE = "'"
DOUBLE_QUOTE = '"'

current_website = os.environ.get("D6ET_CURR_SITE_NAME")
db_host = os.environ.get("D6ET_CURR_DB_HOST")
db_port = int(os.environ.get("D6ET_CURR_DB_PORT"))
db_user = os.environ.get("D6ET_CURR_DB_USER")
db_password =  os.environ.get("D6ET_CURR_DB_PASS")
db_database =  os.environ.get("D6ET_CURR_DB_NAME")

ignore_case_replace_end_lines_1 = re.compile("<br/>", re.IGNORECASE)
ignore_case_replace_end_lines_2 = re.compile("<br />", re.IGNORECASE)
ignore_case_replace_end_lines_3 = re.compile("<br>", re.IGNORECASE)
ignore_case_replace_paragraph_tag_begin = re.compile("<p>", re.IGNORECASE)
ignore_case_replace_paragraph_tag_end = re.compile("</p>", re.IGNORECASE)
ignore_case_replace_space = re.compile("&nbsp;", re.IGNORECASE)
ignore_case_replace_dollar_sign = re.compile("\$", re.IGNORECASE)
ignore_case_replace_comma = re.compile(",", re.IGNORECASE)
ignore_case_replace_left_parenthesis = re.compile("\(", re.IGNORECASE)
ignore_case_replace_right_parenthesis = re.compile("\)", re.IGNORECASE)
ignore_case_replace_negative = re.compile("-", re.IGNORECASE)
ignore_case_replace_forward_slash = re.compile("[/]+", re.IGNORECASE)
ignore_case_replace_letters = re.compile("[a-z]+", re.IGNORECASE)
ignore_case_replace_period = re.compile("[\.]+", re.IGNORECASE)
ignore_case_replace_amp = re.compile("\&", re.IGNORECASE)

html_escape_table = {
'"': "&quot;",
"'": "&apos;",
">": "&gt;",
"<": "&lt;",
'?': "&ldquo;",
'?': "&rdquo;",
}

def csvStringToList(csvString, separator):
    if csvString is None or csvString =="" :
        return []

    csvArray = csvString.split(separator)

    returnList = []
    for currField in csvArray:
        returnList.append(currField)

    return returnList

def remove_empty_lines(string_to_fix, end_line):
    return_string = ""

    lines = string_to_fix.split(end_line)
    for line in lines:
        if line is None :
            continue
        
        if len(line.strip()) > 0 :
            return_string += line + end_line

    return return_string

def shrink_width(string_to_shrink, new_width):    
    return_string = ""
    
    current_line_length = 0
    first_word = True
    for current_word in string_to_shrink.split(" "):
        if not first_word and current_line_length > new_width:
            return_string += ENDL
            current_line_length = 0
            first_word = True
            
        return_string += current_word + " "
        current_line_length += len(current_word) + 1
        first_word = False

    return_string = remove_empty_lines(return_string, ENDL)
    
    return return_string.strip()

def convert_html(string_to_convert, end_line):
    if string_to_convert is None:
        return ""
    
    return_string = string_to_convert
    return_string = ignore_case_replace_end_lines_1.sub(end_line, return_string)
    return_string = ignore_case_replace_end_lines_2.sub(end_line, return_string)
    return_string = ignore_case_replace_end_lines_3.sub(end_line, return_string)
    return_string = ignore_case_replace_paragraph_tag_begin.sub("", return_string)
    return_string = ignore_case_replace_paragraph_tag_end.sub("", return_string)
    return_string = ignore_case_replace_space.sub(" ", return_string)

    return_string = remove_empty_lines(return_string, end_line)
    # print('================================================\n')
    # print(string2Convert)
    # print('--------------------------------------\n')
    # print(returnString + '================================================\n')
    
    return return_string.strip()

def print_empty_line(output_file_handle):
    output_file_handle.write(ENDL)
    
def flush_print_files(debug_output_file_handle, output_file_handle):
    debug_output_file_handle.flush()
    output_file_handle.flush()

def drupal_6_json_get_key(json_string, json_key):
    """drupal 6 does JSON differently than python does, apparently. 
       Find the json_key in json_string and return it's value."""

    str_json_string = str(json_string)
    index_of_json_key = str_json_string.find(json_key)
    if(index_of_json_key < 0):
        return ""
    return_string = str_json_string[index_of_json_key:]
    return_string = return_string.replace(';', ':')
    return_string_array = return_string.split(':')
    return_string = return_string_array[3]
    
    return return_string.strip('"')

def get_installed_modules(debug_output_file_handle):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    modules = []
    get_sql = "SELECT name, filename, schema_version, weight, info "
    get_sql += "FROM system "
    get_sql += "WHERE type = 'module' "
    get_sql += "  AND status = 1 "
    get_sql += "ORDER BY name"
    debug_output_file_handle.write("get_installed_modules sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    module_records = cursor.fetchall()
    cursor.close()
    conn.close()

    modules = []
    for module_record in module_records:
        modules.append(module_record)
    
    return modules

def main():
    # Start exporting the data
    if(not os.path.isdir(OUTPUT_DIRECTORY)):
        os.mkdir(OUTPUT_DIRECTORY)

    export_directory = os.path.join(OUTPUT_DIRECTORY, current_website)
    if(not os.path.isdir(export_directory)):
        os.mkdir(export_directory)

    logs_directory = os.path.join(export_directory, LOGS_DIRECTORY)
    if(not os.path.isdir(logs_directory)):
        os.mkdir(logs_directory)
    debug_output_file = os.path.join(logs_directory, 'installed_modules_debug.log')

    debug_output_file_handle = open(debug_output_file, mode='w')
    output_file_handle = open(os.path.join(export_directory, "installed_modules.xml"), mode='w', encoding='utf-8')
    output_file_handle.write('<?xml version="1.0" ?>' + ENDL)
    output_file_handle.write("<modules>" + ENDL)
    
    installed_modules = get_installed_modules(debug_output_file_handle)
    for installed_module in installed_modules:
        curr_module_name = installed_module[0]
        curr_module_filename = installed_module[1]
        curr_module_schema_ver = installed_module[2]
        curr_module_weight = installed_module[3]
        curr_module_info = installed_module[4]
        curr_module_project = drupal_6_json_get_key(curr_module_info, "project")
        curr_module_version = drupal_6_json_get_key(curr_module_info, "version")

        output_file_handle.write(' ' + "<module>" + ENDL)
        output_file_handle.write(' ' + "<name>" + str(curr_module_name) + "</name>" + ENDL)
        output_file_handle.write(' ' + "<filename>" + str(curr_module_filename) + "</filename>" + ENDL)
        output_file_handle.write(' ' + "<schema_version>" + str(curr_module_schema_ver) + "</term_id>" + ENDL)
        output_file_handle.write(' ' + "<weight>" + str(curr_module_weight) + "</weight>" + ENDL)
        output_file_handle.write(' ' + "<project>" + str(curr_module_project) + "</project>" + ENDL)
        output_file_handle.write(' ' + "<version>" + str(curr_module_version) + "</version>" + ENDL)
        output_file_handle.write(' ' + "<info>" + str(curr_module_info) + "</info>" + ENDL)
        output_file_handle.write(' ' + "</module>" + ENDL)

    flush_print_files(debug_output_file_handle, output_file_handle)
    
    output_file_handle.write("</modules>" + ENDL)
    output_file_handle.close()
    debug_output_file_handle.close()

if __name__ == "__main__":
    main()
