echo OFF
set D6ET_CURR_SITE_NAME=new_d6_folder
set D6ET_CURR_DB_HOST=localhost
set D6ET_CURR_DB_PORT=3306
set D6ET_CURR_DB_USER=
set D6ET_CURR_DB_PASS=
set D6ET_CURR_DB_NAME=
echo ON

exporting website %D6ET_CURR_SITE_NAME% to output\%D6ET_CURR_SITE_NAME%
python src\d6exportTaxonomy.py
