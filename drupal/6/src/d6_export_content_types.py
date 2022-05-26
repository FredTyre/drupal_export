from operator import truediv
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
'': "&ldquo;",
'': "&rdquo;",
}

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
    if string_to_convert is None :
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

def print_empty_line():
    output_file_handle.write(ENDL)
    
def flush_print_files():
    debug_output_file_handle.flush()
    output_file_handle.flush()

def prep_for_xml_out(string_to_prep):
    return_string = escape(string_to_prep)

    return_string = "".join(html_escape_table.get(c, c) for c in return_string)

    return return_string

def check_if_table_exists(table_name):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SHOW TABLES LIKE '" + table_name + "'"
    
    debug_output_file_handle.write("get_content_types sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if len(tables) > 0 :
        return True

    return False

def get_content_types():
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT type, name, module, description, help, has_title, title_label, has_body, "
    get_sql += "body_label, min_word_count, custom, modified,locked, orig_type FROM node_type"
    
    debug_output_file_handle.write("get_content_types sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    content_types = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return content_types

def get_content_type_fields(content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    fields = []
    table_name = "content_type_" + content_type
    if check_if_table_exists(table_name):
        get_sql = "DESCRIBE " + table_name
        debug_output_file_handle.write("get_content_type_fields sql statement: " + str(get_sql) + ENDL)
        debug_output_file_handle.flush()
        cursor.execute(get_sql)
        fieldrecords = cursor.fetchall()
        cursor.close()
        conn.close()

        fields = []
        for fieldrecord in fieldrecords:
            if fieldrecord[0] != "vid" and fieldrecord[0] != "nid" and fieldrecord[0] != "delta" :
                fields.append(fieldrecord)
    
    return fields

def export_content_type_metadata(output_file_handle, content_type):
    content_type_machine_name = content_type[0]
    output_file_handle.write("      <ct_machine_name>" + str(content_type_machine_name) + "</ct_machine_name>" + ENDL)
    output_file_handle.write("      <ct_human_name>" + str(content_type[1]) + "</ct_human_name>" + ENDL)
    output_file_handle.write("      <ct_module>" + str(content_type[2]) + "</ct_module>" + ENDL)
    output_file_handle.write("      <ct_description>" + str(content_type[3]) + "</ct_description>" + ENDL)
    output_file_handle.write("      <ct_help>" + str(content_type[4]) + "</ct_help>" + ENDL)
    output_file_handle.write("      <ct_has_title>" + str(content_type[5]) + "</ct_has_title>" + ENDL)
    output_file_handle.write("      <ct_title_label>" + str(content_type[6]) + "</ct_title_label>" + ENDL)
    output_file_handle.write("      <ct_has_body>" + str(content_type[7]) + "</ct_has_body>" + ENDL)
    output_file_handle.write("      <ct_body_label>" + str(content_type[8]) + "</ct_body_label>" + ENDL)
    output_file_handle.write("      <ct_min_word_count>" + str(content_type[9]) + "</ct_min_word_count>" + ENDL)
    output_file_handle.write("      <ct_custom>" + str(content_type[10]) + "</ct_custom>" + ENDL)
    output_file_handle.write("      <ct_modified>" + str(content_type[11]) + "</ct_modified>" + ENDL)
    output_file_handle.write("      <ct_locked>" + str(content_type[12]) + "</ct_locked>" + ENDL)
    output_file_handle.write("      <ct_orig_type>" + str(content_type[13]) + "</ct_orig_type>" + ENDL)
    flush_print_files()

def export_content_type_fields(output_file_handle, content_type):
    content_type_machine_name = content_type[0]
    fields = get_content_type_fields(content_type_machine_name)
    for field in fields:
        output_file_handle.write("      <content_type_field>" + ENDL)
        output_file_handle.write("         <ct_field_name>" + str(field[0]) + "</ct_field_name>" + ENDL)
        output_file_handle.write("         <ct_field_type>" + str(field[1]) + "</ct_field_type>" + ENDL)
        output_file_handle.write("         <ct_field_can_be_null>" + str(field[2]) + "</ct_field_can_be_null>" + ENDL)
        output_file_handle.write("         <ct_field_key>" + str(field[3]) + "</ct_field_key>" + ENDL)
        output_file_handle.write("         <ct_field_default>" + str(field[4]) + "</ct_field_default>" + ENDL)
        output_file_handle.write("         <ct_field_extra>" + str(field[5]) + "</ct_field_extra>" + ENDL)
        output_file_handle.write("      </content_type_field>" + ENDL)

if(not os.path.isdir(OUTPUT_DIRECTORY)):
    os.mkdir(OUTPUT_DIRECTORY)

export_directory = os.path.join(OUTPUT_DIRECTORY, current_website)
if(not os.path.isdir(export_directory)):
    os.mkdir(export_directory)

logs_directory = os.path.join(export_directory, LOGS_DIRECTORY)
if(not os.path.isdir(logs_directory)):
    os.mkdir(logs_directory)
debug_output_file = os.path.join(logs_directory, 'debug.log')

debug_output_file_handle = open(debug_output_file, mode='w')

content_types = get_content_types()
for content_type in content_types:
    curr_content_type = prep_for_xml_out(str(content_type[0]))
    output_file_handle = open(os.path.join(export_directory, "content_type_" + curr_content_type + ".xml"), mode='w', encoding='utf-8')
    output_file_handle.write('<?xml version="1.0" ?>' + ENDL)
    output_file_handle.write("<content_types>" + ENDL)
    output_file_handle.write("   <content_type>" + ENDL)
    export_content_type_metadata(output_file_handle, content_type)
    export_content_type_fields(output_file_handle, content_type)
    output_file_handle.write("   </content_type>" + ENDL)
    output_file_handle.write("</content_types>" + ENDL)
    output_file_handle.close()
debug_output_file_handle.close()

