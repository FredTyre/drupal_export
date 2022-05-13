import os
import MySQLdb
import re
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

def prep_for_xml_out(string_to_prep):
    return_string = escape(string_to_prep)

    return_string = "".join(html_escape_table.get(c, c) for c in return_string)

    return return_string

def get_vocabularies(debug_output_file_handle):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT vid, name FROM vocabulary ORDER BY vid"
    
    debug_output_file_handle.write("getVocabularies sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    vocabularies = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return vocabularies

def get_taxonomy_top_level(debug_output_file_handle, vocabulary_id):
    conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, database=db_database, port=db_port)
    cursor = conn.cursor()
    
    get_sql = "SELECT term_data.tid, name "
    get_sql = get_sql + "FROM term_data "
    get_sql = get_sql + "LEFT JOIN term_hierarchy "
    get_sql = get_sql + "ON (term_data.tid = term_hierarchy.tid) "
    get_sql = get_sql + "WHERE vid = " + str(vocabulary_id) + " "
    get_sql = get_sql + "AND term_hierarchy.parent = 0 "
    get_sql = get_sql + "ORDER BY name, weight, term_data.tid"
    
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
    
    get_sql = "SELECT term_data.tid, name "
    get_sql = get_sql + "FROM term_data "
    get_sql = get_sql + "LEFT JOIN term_hierarchy "
    get_sql = get_sql + "ON (term_data.tid = term_hierarchy.tid) "
    get_sql = get_sql + "WHERE vid = " + str(vocabulary_id) + " "
    get_sql = get_sql + "AND term_hierarchy.parent = " + str(parent_id) + " "
    get_sql = get_sql + "ORDER BY name, weight, term_data.tid"
    
    debug_output_file_handle.write("getTaxonomy sql statement: " + str(get_sql) + ENDL)
    debug_output_file_handle.flush()
    cursor.execute(get_sql)
    children = cursor.fetchall()
    cursor.close()
    conn.close()

    for child in children:
        child_tid = child[0]
        child_term_name = prep_for_xml_out(child[1])
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

        printChildren(debug_output_file_handle, output_file_handle, vocabulary_id, curr_vocabulary_name, depth+1, child_tid, child_term_name)

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

vocabularies = get_vocabularies(debug_output_file_handle)
for vocabulary in vocabularies:
    curr_vocabulary_id = vocabulary[0]
    curr_vocabulary_name = prep_for_xml_out(vocabulary[1])
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

        curr_term_name = prep_for_xml_out(taxonomy_top_level[1])
        output_file_handle.write(' ' + "<term_name>" + str(curr_term_name) + "</term_name>" + ENDL)
        output_file_handle.write(' ' + "</taxonomy_term>" + ENDL)

        printChildren(debug_output_file_handle, output_file_handle, curr_vocabulary_id, curr_vocabulary_name, 1, curr_term_tid, curr_term_name)

        flush_print_files(debug_output_file_handle, output_file_handle)
    
    output_file_handle.write("</taxonomy_terms>" + ENDL)
    output_file_handle.close()
debug_output_file_handle.close()

