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

current_website = os.environ.get("D9ET_CURR_SITE_NAME")
db_host = os.environ.get("D9ET_CURR_DB_HOST")
db_port = int(os.environ.get("D9ET_CURR_DB_PORT"))
db_user = os.environ.get("D9ET_CURR_DB_USER")
db_password =  os.environ.get("D9ET_CURR_DB_PASS")
db_database =  os.environ.get("D9ET_CURR_DB_NAME")

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

def csvStringToList(csvString, separator):
    if csvString is None or csvString =="" :
        return []

    csvArray = csvString.split(separator)

    returnList = []
    for record in csvArray:
        returnList.append(record)

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

def wrap_xml_field(num_spaces, xml_tag_name, xml_field):
    return (' ' * num_spaces) + "<" + xml_tag_name + ">" + prep_for_xml_out(str(xml_field)) + "</" + xml_tag_name + ">" + ENDL


def drupal_9_json_get_key(json_string, json_key):
    """drupal 9 does JSON differently than python does, apparently. 
       Find the json_key in json_string and return it's value."""

    str_json_string = str(json_string)
    return_string = str_json_string[str_json_string.find(json_key):]
    return_string = return_string.replace(';', ':')
    return_string_array = return_string.split(':')
    return_string = return_string_array[3]
    
    return return_string.strip('"')

def check_if_table_exists(table_name):
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

def if_content_type_has_body(content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT data FROM config WHERE name = 'field.field.node." + content_type + ".body'"
    
    debug_output_file_handle.write("if_content_type_has_body sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    body_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if len(body_data) > 0 :
        return True

    return False

def get_content_type_body_label(content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT data FROM config WHERE name = 'field.field.node." + content_type + ".body'"
    
    debug_output_file_handle.write("get_content_type_body_label sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    body_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if len(body_data) > 0 :
        return drupal_9_json_get_key(body_data, "label")

    return None

def get_content_types(content_types_to_exclude):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT data FROM config WHERE name LIKE 'node.type.%'"

    debug_output_file_handle.write("get_content_types sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    content_types_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    content_types = []
    for curr_ct_data in content_types_data:
        curr_d9_json_string = curr_ct_data[0]

        content_type = drupal_9_json_get_key(curr_d9_json_string, "type")
        name = drupal_9_json_get_key(curr_d9_json_string, "name")
        if name in content_types_to_exclude:
            continue
        
        #module = drupal_9_json_get_key(curr_d9_json_string, "module")
        module = ""
        description = drupal_9_json_get_key(curr_d9_json_string, "description")
        help = drupal_9_json_get_key(curr_d9_json_string, "help")
        #has_title = drupal_9_json_get_key(curr_d9_json_string, "")
        has_title = ""
        #title_label = drupal_9_json_get_key(curr_d9_json_string, "")
        title_label = ""
        has_body = if_content_type_has_body(content_type)
        if has_body :
            body_label = get_content_type_body_label(content_type)
        else:
            body_label = ""
        #min_word_count = drupal_9_json_get_key(curr_d9_json_string, "")
        min_word_count = ""
        #custom = drupal_9_json_get_key(curr_d9_json_string, "")
        custom = ""
        #modified = drupal_9_json_get_key(curr_d9_json_string, "")
        modified = ""
        #locked = drupal_9_json_get_key(curr_d9_json_string, "")
        locked = ""
        #orig_type = drupal_9_json_get_key(curr_d9_json_string, "")
        orig_type = ""

        content_types.append((content_type, name, module, description, help, has_title, title_label, has_body, body_label, min_word_count, custom, modified, locked, orig_type))

    return content_types

def get_content_type_fields(content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    get_sql = "SELECT data FROM config WHERE name LIKE 'field.field.node." + content_type + ".%' AND name != 'field.field.node." + content_type + ".body'"

    debug_output_file_handle.write("get_content_type_fields sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    field_data = cursor.fetchall()
    cursor.close()
    conn.close()

    fields = []
    for curr_field_data in field_data:
        curr_d9_json_string = curr_field_data
        field_name = drupal_9_json_get_key(curr_d9_json_string, "field_name")
        field_type = drupal_9_json_get_key(curr_d9_json_string, "field_type")
        global_settings = drupal_9_json_get_key(curr_d9_json_string, "settings")
        required = drupal_9_json_get_key(curr_d9_json_string, "required")
        multiple = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        db_storage = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        module = drupal_9_json_get_key(curr_d9_json_string, "module")
        db_columns = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        active = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        weight = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        label = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        widget_type = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        widget_settings = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        display_settings = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        description = drupal_9_json_get_key(curr_d9_json_string, "description")
        widget_module = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")
        widget_active = "" #drupal_9_json_get_key(curr_d9_json_string, "field_name")

        fields.append((field_name, field_type, global_settings, required, multiple, db_storage, module, db_columns, 
                       active, weight, label, widget_type, widget_settings, display_settings, description, 
                       widget_module, widget_active))
    
    return fields

def export_content_type_metadata(output_file_handle, content_type):
    export_string = ""
    
    export_string += wrap_xml_field(6, "ct_machine_name", content_type[0])
    export_string += wrap_xml_field(6, "ct_human_name", content_type[1])
    export_string += wrap_xml_field(6, "ct_description", content_type[3])
    export_string += wrap_xml_field(6, "ct_module", content_type[2])
    export_string += wrap_xml_field(6, "ct_help", content_type[4])
    export_string += wrap_xml_field(6, "ct_has_title", content_type[5])
    export_string += wrap_xml_field(6, "ct_title_label", content_type[6])
    export_string += wrap_xml_field(6, "ct_has_body", content_type[7])
    export_string += wrap_xml_field(6, "ct_body_label", content_type[8])
    export_string += wrap_xml_field(6, "ct_min_word_count", content_type[9])
    export_string += wrap_xml_field(6, "ct_custom", content_type[10])
    export_string += wrap_xml_field(6, "ct_modified", content_type[11])
    export_string += wrap_xml_field(6, "ct_locked", content_type[12])
    export_string += wrap_xml_field(6, "ct_orig_type", content_type[13])
    output_file_handle.write(export_string)
    flush_print_files()

def export_content_type_fields(output_file_handle, content_type):
    content_type_machine_name = content_type[0]
    fields = get_content_type_fields(content_type_machine_name)
    for field in fields:
        export_string = ""
        
        output_file_handle.write("      <content_type_field>" + ENDL)
        export_string += wrap_xml_field(9, "ct_field_name", field[0])
        export_string += wrap_xml_field(9, "ct_field_type", field[1])
        export_string += wrap_xml_field(9, "ct_field_global_settings", field[2])
        export_string += wrap_xml_field(9, "ct_field_required", field[3])
        export_string += wrap_xml_field(9, "ct_field_multiple", field[4])
        export_string += wrap_xml_field(9, "ct_field_db_storage", field[5])
        export_string += wrap_xml_field(9, "ct_field_module", field[6])
        export_string += wrap_xml_field(9, "ct_field_db_columns", field[7])
        export_string += wrap_xml_field(9, "ct_field_active", field[8])
        export_string += wrap_xml_field(9, "ct_field_weight", field[9])
        export_string += wrap_xml_field(9, "ct_field_label", field[10])
        export_string += wrap_xml_field(9, "ct_field_widget_type", field[11])
        export_string += wrap_xml_field(9, "ct_field_widget_settings", field[12])
        export_string += wrap_xml_field(9, "ct_field_display_settings", field[13])
        export_string += wrap_xml_field(9, "ct_field_description", field[14])
        export_string += wrap_xml_field(9, "ct_field_widget_module", field[15])
        export_string += wrap_xml_field(9, "ct_field_widget_active", field[16])
        
        output_file_handle.write(export_string)
        output_file_handle.write("      </content_type_field>" + ENDL)
        flush_print_files()

def main():

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

    parser = argparse.ArgumentParser(description='Export drupal content types from a drupal 9 website.')
    parser.add_argument('--exclude', type=string, const=sum, default=max,
                        help='sum the integers (default: find the max)')

    parameters = parser.parse_args()

    content_types_to_exclude = csvStringToList(parameters.exclude, ",")

    content_types = get_content_types(content_types_to_exclude)
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

if __name__ == "__main__":
    main()


