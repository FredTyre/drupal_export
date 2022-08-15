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

current_website = os.environ.get("D7ET_CURR_SITE_NAME")
db_host = os.environ.get("D7ET_CURR_DB_HOST")
db_port = int(os.environ.get("D7ET_CURR_DB_PORT"))
db_user = os.environ.get("D7ET_CURR_DB_USER")
db_password =  os.environ.get("D7ET_CURR_DB_PASS")
db_database =  os.environ.get("D7ET_CURR_DB_NAME")

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
        if not first_word and current_line_length > new_width :
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

def prep_for_xml_out(string_to_prep):
    return_string = escape(string_to_prep)

    return_string = "".join(html_escape_table.get(c, c) for c in return_string)

    return return_string

def wrap_xml_field(num_spaces, xml_tag_name, xml_field):
    return (' ' * num_spaces) + "<" + xml_tag_name + ">" + prep_for_xml_out(str(xml_field)) + "</" + xml_tag_name + ">" + ENDL

def check_if_table_exists(debug_output_file_handle, table_name):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SHOW TABLES LIKE '" + table_name + "'"
    
    debug_output_file_handle.write("check_if_table_exists sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if len(tables) > 0 :
        return True

    return False

def drupal_7_json_get_key(json_string, json_key):
    """drupal 7 does JSON differently than python does, apparently. 
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

def get_active_users(debug_output_file_handle):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    user_records = []
    get_sql = "SELECT name, mail, theme, signature, signature_format, created, access, login, status, timezone, language, picture, init, data, changed "
    get_sql += "FROM users "
    get_sql += "WHERE status = 1 "
    get_sql += "ORDER BY uid"
    debug_output_file_handle.write("get_active_users sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    user_records = cursor.fetchall()
    cursor.close()
    conn.close()

    users = []
    for user_record in user_records:
        users.append(user_record)
    
    return users

def main():
    # Start exporting the data
    parser = argparse.ArgumentParser(description='Export drupal content types from a drupal 9 website.')
    parser.add_argument('--exclude', type=str, required=False,
                        help='comma separated list of content types to exclude from export')

    parameters = parser.parse_args()

    content_types_to_exclude = csvStringToList(parameters.exclude, ",")
    print(content_types_to_exclude)

    if(not os.path.isdir(OUTPUT_DIRECTORY)):
        os.mkdir(OUTPUT_DIRECTORY)
	
    export_directory = os.path.join(OUTPUT_DIRECTORY, current_website)
    if(not os.path.isdir(export_directory)):
        os.mkdir(export_directory)
	
    logs_directory = os.path.join(export_directory, LOGS_DIRECTORY)
    if(not os.path.isdir(logs_directory)):
        os.mkdir(logs_directory)
    debug_output_file = os.path.join(logs_directory, 'active_users_debug.log')

    debug_output_file_handle = open(debug_output_file, mode='w')
    output_file_handle = open(os.path.join(export_directory, "active_users.xml"), mode='w', encoding='utf-8')
    output_file_handle.write('<?xml version="1.0" ?>' + ENDL)
    output_file_handle.write("<users>" + ENDL)
    
    active_users = get_active_users(debug_output_file_handle)
    for active_user in active_users:
        curr_user_name = active_user[0]
        curr_user_mail = active_user[1]
        curr_user_theme = active_user[2]
        curr_user_signature = active_user[3]
        curr_user_sig_format = active_user[4]
        curr_user_created = active_user[5]
        curr_user_access = active_user[6]
        curr_user_login = active_user[7]
        curr_user_status = active_user[8]
        curr_user_timezone = active_user[9]
        curr_user_language = active_user[10]
        curr_user_picture = active_user[11]
        curr_user_init = active_user[12]
        curr_user_data = active_user[13]
        curr_user_changed = active_user[14]
        #curr_module_project = drupal_7_json_get_key(curr_module_data, "project")
        #curr_module_version = drupal_7_json_get_key(curr_module_data, "version")

        output_file_handle.write(' ' + "<user>" + ENDL)
        output_file_handle.write(' ' + "<name>" + str(curr_user_name) + "</name>" + ENDL)
        output_file_handle.write(' ' + "<mail>" + str(curr_user_mail) + "</mail>" + ENDL)
        output_file_handle.write(' ' + "<theme>" + str(curr_user_theme) + "</theme>" + ENDL)
        output_file_handle.write(' ' + "<signature>" + str(curr_user_signature) + "</signature>" + ENDL)
        output_file_handle.write(' ' + "<signature_format>" + str(curr_user_sig_format) + "</signature_format>" + ENDL)
        output_file_handle.write(' ' + "<created>" + str(curr_user_created) + "</created>" + ENDL)
        output_file_handle.write(' ' + "<access>" + str(curr_user_access) + "</access>" + ENDL)
        output_file_handle.write(' ' + "<login>" + str(curr_user_login) + "</login>" + ENDL)
        output_file_handle.write(' ' + "<status>" + str(curr_user_status) + "</status>" + ENDL)
        output_file_handle.write(' ' + "<timezone>" + str(curr_user_timezone) + "</timezone>" + ENDL)
        output_file_handle.write(' ' + "<language>" + str(curr_user_language) + "</language>" + ENDL)
        #output_file_handle.write(' ' + "<picture>" + str(curr_user_picture) + "</picture>" + ENDL)
        output_file_handle.write(' ' + "<init>" + str(curr_user_init) + "</init>" + ENDL)
        output_file_handle.write(' ' + "<data>" + str(curr_user_data) + "</data>" + ENDL)
        output_file_handle.write(' ' + "<changed>" + str(curr_user_changed) + "</changed>" + ENDL)
        output_file_handle.write(' ' + "</user>" + ENDL)

    flush_print_files(debug_output_file_handle, output_file_handle)
    
    output_file_handle.write("</users>" + ENDL)
    output_file_handle.close()
    debug_output_file_handle.close()

if __name__ == "__main__":
    main()
