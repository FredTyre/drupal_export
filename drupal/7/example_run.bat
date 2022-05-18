echo OFF
set D7ET_CURR_SITE_NAME=new_d7_folder
set D7ET_CURR_DB_HOST=localhost
set D7ET_CURR_DB_PORT=3306
set D7ET_CURR_DB_USER=
set D7ET_CURR_DB_PASS=
set D7ET_CURR_DB_NAME=
echo ON

exporting website %D7ET_CURR_SITE_NAME% to output\%D7ET_CURR_SITE_NAME%
python src\d7_export_taxonomy.py
