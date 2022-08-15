echo OFF
set D6ET_CURR_SITE_NAME=new_d6_folder
set D7ET_CURR_SITE_URL=https://www.hlipublishing.com/
set D6ET_CURR_DB_HOST=localhost
set D6ET_CURR_DB_PORT=3306
set D6ET_CURR_DB_USER=
set D6ET_CURR_DB_PASS=
set D6ET_CURR_DB_NAME=
echo ON

exporting website %D6ET_CURR_SITE_NAME% to output\%D6ET_CURR_SITE_NAME%
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D6ET_CURR_SITE_URL%
python src\d6_export_active_users.py
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D6ET_CURR_SITE_URL%
python src\d6_export_content_types.py
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D6ET_CURR_SITE_URL%
python src\d6_export_installed_modules.py
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --profile-directory="Profile 344" %D6ET_CURR_SITE_URL%
python src\d6_export_taxonomy.py
