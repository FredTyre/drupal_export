import os
import MySQLdb
import re
import string
import sys
import argparse

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
        if(line is None):
            continue
        
        if(len(line.strip()) > 0):
            return_string += line + end_line

    return return_string

def shrink_width(string_to_shrink, new_width):    
    return_string = ""
    
    current_line_length = 0
    first_word = True
    for current_word in string_to_shrink.split(" "):
        if(not first_word and current_line_length > new_width):
            return_string += ENDL
            current_line_length = 0
            first_word = True
            
        return_string += current_word + " "
        current_line_length += len(current_word) + 1
        first_word = False

    return_string = remove_empty_lines(return_string, ENDL)
    
    return return_string.strip()

def convert_html(string_to_convert, end_line):
    if(string_to_convert is None):
        return ""
    
    return_string = string_to_convert
    return_string = ignore_case_replace_end_lines_1.sub(end_line, return_string)
    return_string = ignore_case_replace_end_lines_2.sub(end_line, return_string)
    return_string = ignore_case_replace_end_lines_3.sub(end_line, return_string)
    return_string = ignore_case_replace_paragraph_tag_begin.sub("", return_string)
    return_string = ignore_case_replace_paragraph_tag_end.sub("", return_string)
    return_string = ignore_case_replace_space.sub(" ", return_string)

    return_string = remove_empty_lines(return_string, end_line)
    # print('================================================\n' + string2Convert + '--------------------------------------\n' + returnString + '================================================\n')
    
    return return_string.strip()

def print_empty_line(output_file_handle):
    output_file_handle.write(ENDL)
    
def flush_print_files(debug_output_file_handle, output_file_handle):
    debug_output_file_handle.flush()
    output_file_handle.flush()
    
def drupal_9_json_get_key(json_string, json_key):
    """drupal 9 does JSON differently than python does, apparently. 
       Find the json_key in json_string and return it's value."""

    str_json_string = str(json_string)
    return_string = str_json_string[str_json_string.find(json_key):]
    return_string = return_string.replace(';', ':')
    return_string_array = return_string.split(':')
    
    if len(return_string_array) < 4 :
        print("Could not find json_key " + json_key)
        print()
        print(json_string)
        print()

        return ""

    return_string = return_string_array[3]
    
    return return_string.strip('"')

def get_vocabularies(debug_output_file_handle, taxonomies_to_exclude):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT data FROM config WHERE name LIKE 'taxonomy.vocabulary.%'"
    
    debug_output_file_handle.write("getVocabularies sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    vocabularies_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    vocabularies = []
    for vocabulary in vocabularies_data:
        curr_d9_json_string = vocabulary[0]
        vocabulary_name = drupal_9_json_get_key(curr_d9_json_string, "name")
        if vocabulary_name not in taxonomies_to_exclude:
            vocabulary_id = drupal_9_json_get_key(curr_d9_json_string, "vid")
            vocabularies.append((vocabulary_id, vocabulary_name))

    return vocabularies

def get_taxonomy_top_level(debug_output_file_handle, vocabulary_id):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT tid, name, parent_target_id, "
    get_sql = get_sql + "(SELECT name FROM taxonomy_term_field_data "
    get_sql = get_sql + "WHERE vid = taxonomy_term__parent.bundle "
    get_sql = get_sql + "AND tid = taxonomy_term__parent.parent_target_id) "
    get_sql = get_sql + "FROM taxonomy_term_field_data "
    get_sql = get_sql + "LEFT JOIN taxonomy_term__parent "
    get_sql = get_sql + "ON (taxonomy_term_field_data.vid = taxonomy_term__parent.bundle "
    get_sql = get_sql + "AND taxonomy_term_field_data.tid = taxonomy_term__parent.entity_id) "
    get_sql = get_sql + "WHERE vid = '" + str(vocabulary_id) + "' "
    get_sql = get_sql + " AND parent_target_id = 0 "
    get_sql = get_sql + "ORDER BY name, weight, taxonomy_term_field_data.tid"
    
    debug_output_file_handle.write("getTaxonomy sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    taxonomy_top_levels = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return taxonomy_top_levels

def printChildren(debug_output_file_handle, output_file_handle, vocabulary_id, vocabulary_name, depth, parent_id, parent_name):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT tid, name, parent_target_id, "
    get_sql = get_sql + "(SELECT name FROM taxonomy_term_field_data "
    get_sql = get_sql + "WHERE vid = taxonomy_term__parent.bundle "
    get_sql = get_sql + "AND tid = taxonomy_term__parent.parent_target_id) "
    get_sql = get_sql + "FROM taxonomy_term_field_data "
    get_sql = get_sql + "LEFT JOIN taxonomy_term__parent "
    get_sql = get_sql + "ON (taxonomy_term_field_data.vid = taxonomy_term__parent.bundle "
    get_sql = get_sql + "AND taxonomy_term_field_data.tid = taxonomy_term__parent.entity_id) "
    get_sql = get_sql + "WHERE vid = '" + str(vocabulary_id) + "' "
    get_sql = get_sql + " AND parent_target_id = " + str(parent_id) + " "
    get_sql = get_sql + "ORDER BY name, weight, taxonomy_term_field_data.tid"

    debug_output_file_handle.write("getTaxonomy sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    children = cursor.fetchall()
    cursor.close()
    conn.close()

    for child in children:
        child_tid = child[0]
        child_term_name = child[1]
        depth_spacing = ' ' * depth

        output_file_handle.write(depth_spacing + "<taxonomy_term>" + ENDL)
        output_file_handle.write(depth_spacing + "<vocabulary_id>" + str(vocabulary_id) + "</vocabulary_id>" + ENDL)
        output_file_handle.write(depth_spacing + "<vocabulary_name>" + str(vocabulary_name) + "</vocabulary_name>" + ENDL)
        output_file_handle.write(depth_spacing + "<term_depth>" + str(depth) + "</term_depth>" + ENDL)
        output_file_handle.write(depth_spacing + "<term_id>" + str(child_tid) + "</term_id>" + ENDL)
        output_file_handle.write(depth_spacing + "<term_name>" + str(child_term_name) + "</term_name>" + ENDL)
        output_file_handle.write(depth_spacing + "<term_parent_id>" + str(parent_id) + "</term_parent_id>" + ENDL)
        output_file_handle.write(depth_spacing + "<term_parent_name>" + str(parent_name) + "</term_parent_name>" + ENDL)
        output_file_handle.write(depth_spacing + "</taxonomy_term>" + ENDL)
        output_file_handle.flush()

        printChildren(debug_output_file_handle, output_file_handle, vocabulary_id, vocabulary_name, depth+1, child_tid, child_term_name)

def main():
    parser = argparse.ArgumentParser(description='Export drupal taxonomies from a drupal 9 website.')
    parser.add_argument('--exclude', type=str, required=False,
                        help='comma separated list of taxonomies to exclude from export')

    parameters = parser.parse_args()

    taxonomies_to_exclude = csvStringToList(parameters.exclude, ",")
    print(taxonomies_to_exclude)

    if(not os.path.isdir(OUTPUT_DIRECTORY)):
        os.mkdir(OUTPUT_DIRECTORY)

    export_directory = os.path.join(OUTPUT_DIRECTORY, current_website)
    if(not os.path.isdir(export_directory)):
        os.mkdir(export_directory)

    logs_directory = os.path.join(export_directory, LOGS_DIRECTORY)
    if(not os.path.isdir(logs_directory)):
        os.mkdir(logs_directory)
    debug_output_file = os.path.join(logs_directory, 'taxonomy_debug.log')

    debug_output_file_handle = open(debug_output_file, mode='w')

    vocabularies = get_vocabularies(debug_output_file_handle, taxonomies_to_exclude)
    for vocabulary in vocabularies:
        curr_vocabulary_id = vocabulary[0]
        curr_vocabulary_name = vocabulary[1]
        output_file_handle = open(os.path.join(export_directory, curr_vocabulary_name + "_taxonomy.xml"), mode='w', encoding='utf-8')
        output_file_handle.write('<?xml version="1.0" ?>' + ENDL)
        output_file_handle.write("<taxonomy_terms>" + ENDL)
        taxonomy_top_levels = get_taxonomy_top_level(debug_output_file_handle, curr_vocabulary_id)
        flush_print_files(debug_output_file_handle, output_file_handle)
        for taxonomy_top_level in taxonomy_top_levels:
            curr_term_tid = taxonomy_top_level[0]
            output_file_handle.write(' ' + "<taxonomy_term>" + ENDL)
            output_file_handle.write(' ' + "<vocabulary_id>" + str(curr_vocabulary_id) + "</vocabulary_id>" + ENDL)
            output_file_handle.write(' ' + "<vocabulary_name>" + str(curr_vocabulary_name) + "</vocabulary_name>" + ENDL)
            output_file_handle.write(' ' + "<term_id>" + str(curr_term_tid) + "</term_id>" + ENDL)
            curr_term_name = taxonomy_top_level[1]
            output_file_handle.write(' ' + "<term_name>" + str(curr_term_name) + "</term_name>" + ENDL)
            output_file_handle.write(' ' + "</taxonomy_term>" + ENDL)

            printChildren(debug_output_file_handle, output_file_handle, curr_vocabulary_id, curr_vocabulary_name, 1, curr_term_tid, curr_term_name)

            flush_print_files(debug_output_file_handle, output_file_handle)
        
        output_file_handle.write("</taxonomy_terms>" + ENDL)
        output_file_handle.close()
    debug_output_file_handle.close()

if __name__ == "__main__":
    main()