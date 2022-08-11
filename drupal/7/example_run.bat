echo OFF
set D7ET_CURR_SITE_NAME=new_d7_folder
set D7ET_CURR_DB_HOST=localhost
set D7ET_CURR_DB_PORT=3306
set D7ET_CURR_DB_USER=
set D7ET_CURR_DB_PASS=
set D7ET_CURR_DB_NAME=
echo ON

echo exporting website %D7ET_CURR_SITE_NAME% to output\%D7ET_CURR_SITE_NAME%
exporting website %D7ET_CURR_SITE_NAME% to output\%D7ET_CURR_SITE_NAME%
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D7ET_CURR_SITE_URL%
python src\d7_export_content_types.py
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D7ET_CURR_SITE_URL%
python src\d7_export_installed_modules.py
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D7ET_CURR_SITE_URL%
python src\d7_export_taxonomy.py

xcopy /Y output\%D7ET_CURR_SITE_NAME% ..\..\..\drupal_import\drupal\9\input\%D7ET_CURR_SITE_NAME%