from operator import truediv
from xml.sax.saxutils import escape

import string
import sys
import argparse
import os
import MySQLdb
import re
import sshtunnel

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

def mysql_gen_select_statement(column_names, from_tables, where_clause = None, order_by = None, groupby = None):
    return_sql = "SELECT "
    for column_name in column_names:
        return_sql += str(column_name) + ", "
    return_sql = return_sql.strip(", ")
    
    return_sql += " FROM "
    for table_name in from_tables:
        return_sql += str(table_name) + ", "
    return_sql = return_sql.strip(", ")
    
    if where_clause is not None:
        return_sql += " WHERE " + where_clause
        
    if order_by is not None:
        return_sql += " ORDER BY " + order_by
        
    if groupby is not None:
        return_sql += " GROUP BY " + groupby

    return return_sql
        
def mysql_add_left_join_on(content_type, left_table_name, right_table_name):
    return "LEFT JOIN " + right_table_name + " ON " + left_table_name + ".nid = " + right_table_name + ".entity_id AND " + right_table_name + ".entity_type = 'node' AND " + right_table_name + ".bundle = '" + content_type + "' AND " + right_table_name + ".deleted = 0 AND " + right_table_name + ".language = 'und' "

def get_content_types(debug_output_file_handle, content_types_to_exclude):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT type, name, module, description, help, has_title, title_label, NULL has_body, "
    get_sql += "NULL body_label, NULL min_word_count, custom, modified, locked, orig_type FROM node_type"
    
    debug_output_file_handle.write("get_content_types sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    content_type_records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    content_types = []
    for curr_content_type in content_type_records:
        content_type = curr_content_type[0]

        if content_type is None :
            continue

        if content_types_to_exclude is not None and content_type in content_types_to_exclude:
            continue

        content_types.append(curr_content_type)

    return content_types

def get_content_type_fields(debug_output_file_handle, content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    fields = []
    get_sql = "SELECT content_node_field_instance.field_name, type, global_settings, required, "
    get_sql += "multiple, db_storage, module, db_columns, active, weight, label, widget_type, "
    get_sql += "widget_settings, display_settings, description, "
    get_sql += "widget_module, widget_active "
    get_sql += "FROM content_node_field_instance, content_node_field "
    get_sql += "WHERE content_node_field_instance.field_name = content_node_field.field_name "
    get_sql += "AND type_name = '" + content_type + "'"
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

def get_content_type_data(debug_output_file_handle, curr_content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    get_sql = "SELECT node.nid, node.vid, node.title, node.uid, node.created, node.changed, node.comment, node.promote, node.sticky, node.tnid, node.translate "
    get_sql += " , content_type_" + curr_content_type + ".*"
    get_sql += " FROM node "
    get_sql += " LEFT JOIN content_type_" + curr_content_type + " ON node.nid = content_type_" + curr_content_type + ".nid"
    get_sql += " WHERE node.status = 1 "
    get_sql += " AND node.type = '" + curr_content_type + "' "
    
    debug_output_file_handle.write("get_content_type_data sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    content_type_data = cursor.fetchall()
    cursor.close()
    conn.close()

    ct_data_records = []
    for curr_data_record in content_type_data:
        ct_data_records.append(curr_data_record)

    field_names = [curr_index[0] for curr_index in cursor.description]
    
    return (field_names, ct_data_records)

def export_ct_data_record(debug_output_file_handle, output_file_handle, curr_content_type, field_names, ct_data_record):
    export_string = ""

    curr_index = 0
    for field_name in field_names:
        if curr_index > len(ct_data_record) :
            break
        export_string += wrap_xml_field(6, field_name, ct_data_record[curr_index])
        curr_index += 1
        
    output_file_handle.write(export_string)
    flush_print_files(debug_output_file_handle, output_file_handle)

def main():
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

    debug_output_file = os.path.join(logs_directory, 'content_debug.log')

    debug_output_file_handle = open(debug_output_file, mode='w')

    content_types = get_content_types(debug_output_file_handle, content_types_to_exclude)
    for content_type in content_types:
        curr_content_type = prep_for_xml_out(str(content_type[0]))        
        if curr_content_type in content_types_to_exclude:
            print("Excluding content type: " + curr_content_type)
            continue
        output_file_handle = open(os.path.join(export_directory, "content_type_data_" + curr_content_type + ".xml"), mode='w', encoding='utf-8')
        output_file_handle.write('<?xml version="1.0" ?>' + ENDL)
        output_file_handle.write("<content_type_data>" + ENDL)
        (field_names, ct_data_records) = get_content_type_data(debug_output_file_handle, curr_content_type)
        for ct_data_record in ct_data_records:
            output_file_handle.write("   <ct_data_record>" + ENDL)
            export_ct_data_record(debug_output_file_handle, output_file_handle, curr_content_type, field_names, ct_data_record)
            output_file_handle.write("   </ct_data_record>" + ENDL)
            
        output_file_handle.write("</content_type_data>" + ENDL)
        output_file_handle.close()
    debug_output_file_handle.close()

if __name__ == "__main__":
    main()
