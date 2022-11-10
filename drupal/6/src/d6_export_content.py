from operator import truediv
from xml.sax.saxutils import escape

import string
import sys
import argparse
import os
import MySQLdb
import re
import sshtunnel
import html
import wget

OUTPUT_DIRECTORY = 'output'
LOGS_DIRECTORY = 'logs'
FILES_DIRECTORY = 'files'

ENDL = '\n'

SINGLE_QUOTE = "'"
DOUBLE_QUOTE = '"'

DOWNLOAD_NONE = 0
DOWNLOAD_UNCACHED = 1
DOWNLOAD_ALL = 2
    
current_website = os.environ.get("D6ET_CURR_SITE_NAME")
current_website_url = os.environ.get("D6ET_CURR_SITE_URL")
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
ignore_case_replace_curr_domain = re.compile(current_website, re.IGNORECASE)
ignore_case_replace_file_path = re.compile('sites/default/files/', re.IGNORECASE)

html_escape_table = {
'"': "&quot;",
"'": "&apos;",
">": "&gt;",
"<": "&lt;",
'': "&ldquo;",
'': "&rdquo;",
}

def ends_with(haystack, needle):
    length_of_needle = len(needle)

    if length_of_needle > len(haystack):
        return False
    
    if haystack[-length_of_needle:] == needle :
        return True

    return False
        
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
    return_string = (' ' * num_spaces) + "<" + xml_tag_name + ">"
    
    if xml_field is not None:
        prepped_xml_field = prep_for_xml_out(str(xml_field))        
        if prepped_xml_field != "None":
            return_string += prepped_xml_field
        
    return_string += "</" + xml_tag_name + ">" + ENDL
    
    return return_string

def getLastExtensionOfFile(filename):
    filePieces = str(filename).split(".")
    numberOfPieces = len(filePieces)
    
    fileExtension = filePieces[numberOfPieces - 1]
    
    return "." + fileExtension.strip()

def drupalSimilarFileAfterUploadCheck(file1, file2):
    file1Extension = ""
    file2Extension = ""
    
    if(len(file1) > 4):
        file1Extension = getLastExtensionOfFile(file1)
        #print(file1Extension)
    if(len(file2) > 4):
        file2Extension = getLastExtensionOfFile(file2)
        #print(file2Extension)
        
    if(file1Extension != file2Extension):
        return False

    file1name = str(file1).replace(file1Extension, "")
    file2name = str(file2).replace(file2Extension, "")

    #print(file1name)
    #print(file2name)
    
    difference = file2name.replace(file1name, "")
    difference = difference.replace("_", "")
    difference = difference.replace("-", "")
    difference.strip()

    #print(difference)
    
    if(difference is None or difference == ""):
        return True
    
    if(difference.isnumeric()):
        return True
    
    return False

def drupalSimilarFileListAfterUploadCheck(fileList1, fileList2):
    if(fileList1 is None or fileList1 == ""):
        if(fileList2 is None or fileList2 == ""):
            return True
        else:
            return False

    fileArray1 = fileList1.split(", ")
    fileArray2 = fileList2.split(", ")

    if(len(fileArray1) != len(fileArray2)):
        return False

    fileArrayIndex = 0
    for file1name in fileArray1:
        if(file1name == fileArray2[fileArrayIndex]):
            fileArrayIndex += 1
            continue
        
        if(not drupalSimilarFileAfterUploadCheck(file1name, fileArray2[fileArrayIndex])):
            return False
        
        fileArrayIndex += 1

    return True

def get_filename(file_url):
    if(file_url is None or file_url == ""):
        return ""

    if file_url.find("/") != -1:
        file_url_pieces = file_url.split("/")
        return file_url_pieces[-1].strip()
    
    return file_url.strip()

def get_file(debug_output_file_handle, download_method, file_url, output_directory):
    if(file_url is None or file_url == ""):
        return

    if(download_method == DOWNLOAD_UNCACHED and os.path.isdir(output_directory + get_filename(file_url))):
        debug_output_file_handle.write("File already downloaed from this url (not redownloading): " + str(file_url) + ENDL)
        return

    debug_output_file_handle.write("Downloading file from url: " + str(file_url) + ENDL)
    
    wget.download(file_url, output_directory)
    
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
    
def get_field_tables(debug_output_file_handle, content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SHOW TABLES LIKE 'content_field_" + content_type + "%'"
    
    debug_output_file_handle.write("get_field_tables sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    tables = cursor.fetchall()
    cursor.close()
    conn.close()

    field_tables = []
    for table in tables:
        field_tables.append(table[0])        

    return field_tables

def get_field_names(debug_output_file_handle, field_table):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "DESCRIBE " + field_table
    
    debug_output_file_handle.write("get_field_names sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    fields = cursor.fetchall()
    cursor.close()
    conn.close()

    field_names = []
    for field in fields:
        field_names.append(field[0])        

    return field_names
    

def get_filepath(debug_output_file_handle, file_id):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT filepath "
    get_sql += "FROM files "
    get_sql += "WHERE fid = " + str(file_id)
    
    debug_output_file_handle.write("get_filepath sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    filepaths = cursor.fetchall()
    cursor.close()
    conn.close()

    for filepath in filepaths:        
        return filepath[0]
    
    return None

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

def run_sql_fetch_all(sql_to_fetch): 
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    cursor.execute(sql_to_fetch)
    records = cursor.fetchall()
    cursor.close()
    conn.commit()
    conn.close()

    return records

def get_node_type_count(content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    get_sql = "SELECT COUNT(*) "
    get_sql += "FROM node "
    get_sql += "WHERE type = '" + content_type + "' "
    get_sql += "AND status = 1"

    node_type_count = run_sql_fetch_all(get_sql)

    if(len(node_type_count) > 0):
        return node_type_count[0][0]

    return None
        
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

def get_content_type_taxonomy_fields(debug_output_file_handle, content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    get_sql = "SELECT content_node_field.field_name "
    get_sql += "FROM content_node_field_instance, content_node_field "
    get_sql += "WHERE content_node_field_instance.field_name = content_node_field.field_name "
    get_sql += "AND content_node_field.type = 'content_taxonomy' "
    get_sql += "AND content_node_field_instance.type_name = '" + content_type + "'"
    debug_output_file_handle.write("get_content_type_fields sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    fieldrecords = cursor.fetchall()
    cursor.close()
    conn.close()

    fields = []
    for fieldrecord in fieldrecords:
        fields.append(fieldrecord[0])
    
    return fields

def get_content_type_data(debug_output_file_handle, curr_content_type):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()

    taxonomy_fields = get_content_type_taxonomy_fields(debug_output_file_handle, curr_content_type)

    get_sql = "SELECT node.nid, node.vid, node.title, node.uid, node.created, node.changed, node.comment, node.promote, node.sticky, node.tnid, node.translate "
    get_sql += " , node_revisions.body " + curr_content_type + "_body "
    get_sql += " , users.name user_name"
    get_sql += " , content_type_" + curr_content_type + ".*"
    
    for taxonomy_field in taxonomy_fields:
        get_sql += " , term_data.name " + taxonomy_field + "_name "

    get_sql += " FROM node "
    get_sql += " LEFT JOIN node_revisions ON node.nid = node_revisions.nid AND node.vid = node_revisions.vid "
    get_sql += " LEFT JOIN content_type_" + curr_content_type + " ON node.nid = content_type_" + curr_content_type + ".nid"
    get_sql += " LEFT JOIN users ON node.uid = users.uid "

    for taxonomy_field in taxonomy_fields:
        get_sql += " LEFT JOIN term_data ON content_type_digital_publication." + taxonomy_field + "_value = term_data.tid "

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

def get_xml_of_field_table_data(debug_output_file_handle, field_table, curr_nid, curr_vid):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    export_string = ""
    
    field_names = get_field_names(debug_output_file_handle, field_table)

    get_sql = "SELECT nid"
    for field_name in field_names:
        if field_name != "nid" and field_name != "vid":
            get_sql += ", " + str(field_name) + " "
    
    get_sql += " FROM " + field_table + " "
    get_sql += " WHERE nid = " + str(curr_nid)
    get_sql += " AND vid = " + str(curr_vid)
    
    debug_output_file_handle.write("get_xml_of_field_table_data sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    field_table_data = cursor.fetchall()
    cursor.close()
    conn.close()

    ct_data_records = []
    for curr_field_table_data in field_table_data:
        curr_index = 1
        for field_name in field_names:
            if field_name != "nid" and field_name != "vid" and curr_index < len(curr_field_table_data):
                new_field_name = field_name
                if new_field_name == "delta":
                    new_field_name = field_table + "_" + field_name
                export_string += wrap_xml_field(6, new_field_name, curr_field_table_data[curr_index])
                curr_index += 1

    return export_string

def export_ct_data_record(debug_output_file_handle, output_file_handle, files_directory, download_method, curr_content_type, field_names, ct_data_record):
    export_string = ""

    curr_nid = ct_data_record[0]
    curr_vid = ct_data_record[1]

    #print("processing node id: " + str(curr_nid))
    
    curr_index = 0
    for field_name in field_names:
        if curr_index > len(ct_data_record) :
            break
            
        export_string += wrap_xml_field(6, field_name, ct_data_record[curr_index])
        
        if ct_data_record[curr_index] is not None and ends_with(field_name, "_fid"):
            new_field_name = field_name.replace("_fid", "_filename")
            new_field_name_data = get_filepath(debug_output_file_handle, ct_data_record[curr_index])
            file_url = current_website_url + "/" + new_field_name_data
            if download_method != DOWNLOAD_NONE:
                get_file(debug_output_file_handle, download_method, file_url, files_directory)
            curr_filename = get_filename(file_url)
            export_string += wrap_xml_field(6, new_field_name, curr_filename)
            
        curr_index += 1

    # Find any fields we missed.    
    field_tables = get_field_tables(debug_output_file_handle, curr_content_type)

    for field_table in field_tables:
        export_string += get_xml_of_field_table_data(debug_output_file_handle, field_table, curr_nid, curr_vid)
    
    output_file_handle.write(export_string)
    flush_print_files(debug_output_file_handle, output_file_handle)
    
def print_new_stats(debug_output_file_handle, content_types_to_exclude):
    output_string = "><><><><><><><><><><><><><><><><><><><><><><" + ENDL
    output_string += "Counts of content in the current website..." + ENDL

    output_string += get_all_site_stats(debug_output_file_handle, content_types_to_exclude) + ENDL
    output_string += "><><><><><><><><><><><><><><><><><><><><><><" + ENDL

    print(output_string)
    debug_output_file_handle.write(output_string)
    
def get_site_stats_of_content_type(content_type):
    output_string = ""
    
    content_type_count = get_node_type_count(content_type)
    output_string += "Number of " + str(content_type) + ": " + str(content_type_count) + ENDL

    return output_string

def get_all_site_stats(debug_output_file_handle, content_types_to_exclude):
    output_string = ""

    content_types = get_content_types(debug_output_file_handle, content_types_to_exclude)
    for content_type in content_types:
        curr_content_type = str(content_type[0])

        if curr_content_type not in content_types_to_exclude:
            output_string += get_site_stats_of_content_type(curr_content_type)  

    return output_string
    
def main():
    parser = argparse.ArgumentParser(description='Export drupal content types from a drupal 9 website.')
    parser.add_argument('--exclude', type=str, required=False, help='comma separated list of content types to exclude from export')
    parser.add_argument('--ignore-file-download', type=str, required=False, help='do not download the files listed in the XML export')
    parser.add_argument('--file-download-cache', type=str, required=False, help='only download the files listed in the XML export if they have not already been downloaded')
    parser.add_argument('--file-download-all', type=str, required=False, help='download all the files listed in the XML export')

    parameters = parser.parse_args()
    
    content_types_to_exclude = csvStringToList(parameters.exclude, ",")
    print(content_types_to_exclude)
    
    download_method = DOWNLOAD_UNCACHED
        
    if parameters.file_download_all != "":
        download_method = DOWNLOAD_ALL
          
    if parameters.file_download_cache != "":
        download_method = DOWNLOAD_UNCACHED
        
    if parameters.ignore_file_download != "":
        download_method = DOWNLOAD_NONE

    if(not os.path.isdir(OUTPUT_DIRECTORY)):
        os.mkdir(OUTPUT_DIRECTORY)

    export_directory = os.path.join(OUTPUT_DIRECTORY, current_website)
    if(not os.path.isdir(export_directory)):
        os.mkdir(export_directory)

    logs_directory = os.path.join(export_directory, LOGS_DIRECTORY)
    if(not os.path.isdir(logs_directory)):
        os.mkdir(logs_directory)

    files_directory = os.path.join(export_directory, FILES_DIRECTORY)
    if(not os.path.isdir(files_directory)):
        os.mkdir(files_directory)
    
    debug_output_file = os.path.join(logs_directory, 'content_debug.log')

    debug_output_file_handle = open(debug_output_file, mode='w')

    print_new_stats(debug_output_file_handle, content_types_to_exclude)
    
    content_types = get_content_types(debug_output_file_handle, content_types_to_exclude)
    for content_type in content_types:
        curr_content_type = prep_for_xml_out(str(content_type[0]))        
        if curr_content_type in content_types_to_exclude:
            print("Excluding content type: " + curr_content_type)
            continue
        output_file_handle = open(os.path.join(export_directory, "ct_data_" + curr_content_type + ".xml"), mode='w', encoding='utf-8')
        output_file_handle.write('<?xml version="1.0" ?>' + ENDL)
        output_file_handle.write("<content_type_data>" + ENDL)
        (field_names, ct_data_records) = get_content_type_data(debug_output_file_handle, curr_content_type)
        for ct_data_record in ct_data_records:
            output_file_handle.write("   <ct_data_record>" + ENDL)
            export_ct_data_record(debug_output_file_handle, output_file_handle, files_directory, download_method, curr_content_type, field_names, ct_data_record)
            output_file_handle.write("   </ct_data_record>" + ENDL)
            
        output_file_handle.write("</content_type_data>" + ENDL)
        output_file_handle.close()

    print_new_stats(debug_output_file_handle, content_types_to_exclude)
    
    debug_output_file_handle.close()

if __name__ == "__main__":
    main()
