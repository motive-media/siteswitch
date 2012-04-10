#!/usr/bin/python

sites = {
    'site1': {
        'old_domain': 'domain',
        'new_domain': 'domain',

        'old_ftp_host': 'host',
        'old_ftp_user':'user',
        'old_ftp_password': 'password',
        'old_ftp_root': 'documentroot',

        'new_ftp_host': 'host',
        'new_ftp_user': 'user',
        'new_ftp_password': 'password',
        'new_ftp_root': 'documentroot',

        'new_db_host': 'dbhost',
        'new_db_user': 'dbuser',
        'new_db_password': 'dbpassword',
        'new_db_db': 'dbdatabase',
    }
}

DEBUG = 0

# End configuration


import ftplib
import tempfile
import getpass
import os
import sys
import re
import ConfigParser
import json


# Required Options:
#
# old_domain
# new_domain
#
# old_ftp_host
# old_ftp_user
# old_ftp_password
# old_ftp_root
#
# new_ftp_host
# new_ftp_user
# new_ftp_password
# new_ftp_root
#
# new_db_host
# new_db_user
# new_db_password
# new_db_db
#

# Optional:
# no-replace-db-config - give a value to prevent from replacing configuration.  Instead configuration will only be used to get current DB info.
# no-update-db-hostname - won't do a find and replace on the hostname in the SQL dump.
#


# Not yet implemented:
# old_db_host
# old_db_user
# old_db_password
# old_db_db




config_file_names = {
    '/wp-config.php': 'wordpress',


    # Thanks to @cointilt's organizational strategy.
    '/wp-environment.php': 'wordpress',
    '/wp-database.php': 'wordpress',
    '/wp-database/stage.php': 'wordpress',


    '/settings.php': 'drupal',
    '/config.php': 'opencart'
}




config_file_matching = {
    'wordpress': {
        'db_user': '\'DB_USER\', \'(.*)\'',
        'db_host': '\'DB_HOST\', \'(.+)\'',
        'db_password': '\'DB_PASSWORD\', \'(.+)\'',
        'db_db': '\'DB_NAME\', \'(.+)\''
    },
    'opencart': {
        'db_user': '\'DB_USERNAME\', \'(.*)\'',
        'db_host': '\'DB_HOSTNAME\', \'(.+)\'',
        'db_password': '\'DB_PASSWORD\', \'(.+)\'',
        'db_db': '\'DB_DATABASE\', \'(.+)\''
    },
    'drupal': {
        'db_user': '[\'"]username[\'"]\s*=>\s*[\'"]([^\'"]+)[\'"]',
        'db_host': '[\'"]host[\'"]\s*=>\s*[\'"]([^\'"]+)[\'"]',
        'db_password': '[\'"]password[\'"]\s*=>\s*[\'"]([^\'"]+)[\'"]',
        'db_db': '[\'"]database[\'"]\s*=>\s*[\'"]([^\'"]+)[\'"]'
    }
}



def get_old_config(site):
    SITE_FOLDER = site['folder']

    os.chdir(SITE_FOLDER)

    cmd = """lftp -e "find; exit" -u '%s,%s' %s/%s  """ % (site['old_ftp_user'], site['old_ftp_password'], site['old_ftp_host'], site['old_ftp_root'])

    if DEBUG: 
        sys.stdout.write("Executing: " + cmd + "\n")

    fd = os.popen(cmd)

    all_files = ""

    while True:
        chunk = fd.read(100)

        if DEBUG:
            sys.stdout.write(chunk)

        if (not chunk):
            break

        all_files += chunk

    if DEBUG:
        print "Debug: all_files: ", all_files

    fd.close()
    fd = open("test-output.txt", "w")
    fd.write(all_files)
    fd.close()

    possible_matches = {}

    found = 1

    while (found):
        found = 0

        for fn in config_file_names:
            end = all_files.find(fn)

            if end < 0:
                continue
            
            end += len(fn)

            if not found:
                found = end

            if (end < found):
                found = end

            start = all_files.rfind("\n", 0, end)

            start += 1

            possible_matches[all_files[start:end]] = config_file_names[fn]

            if DEBUG:
                print "Found config file match: ", all_files[start:end]

        if found:
            all_files = all_files[end:]


    working_configurations = []


    for config in possible_matches:
        cmd = """lftp -e "cat %s; exit" -u '%s,%s' %s/%s  """ % (config, site['old_ftp_user'], site['old_ftp_password'], site['old_ftp_host'], site['old_ftp_root'])

        if DEBUG: 
            sys.stdout.write(cmd + "\n")

        fd = os.popen(cmd)

        config_content = ""

        while True:
            chunk = fd.read(100)

            if DEBUG:
                sys.stdout.write(chunk)

            if (not chunk):
                break

            config_content += chunk
        
        fd = open("test-config-file-content.txt", "w")
        fd.write(config_content)

        config_type = possible_matches[config]

        replacements = config_file_matching[config_type]

        this_config = {}

        end_loop = 0

        for term in replacements:

            if DEBUG:
                print "Trying to match ", term, " with ", replacements[term]
            
            m = re.search(replacements[term], config_content, re.MULTILINE)

            if m:
                this_config[term] = m.group(1)
                if DEBUG:
                    print "Matched!"
            else:
                if DEBUG:
                    print "Couldn't match config term ", term

                end_loop = 1
                break

        if end_loop:
            if DEBUG: 
                print "No Match:", config
            continue

        if config_type == 'magento':
            print "Magento stuff here"
            exit(1)

        this_config['config_file'] = config
        this_config['config_type'] = config_type

        working_configurations.append(this_config)

        if DEBUG:
            print "Adding to working_configurations:", this_config

    site['configs'] = working_configurations

    return site



def copy_site_to_local(site):
    SITE_FOLDER = site['folder']
    SITE_DL_FOLDER = site['dl_folder']
    SITE_DB_FOLDER = site['db_folder']

    os.chdir(SITE_DL_FOLDER)

    cmd = """lftp -e "mirror; get .htaccess; exit" -u '%s,%s' %s/%s  """ % (site['old_ftp_user'], site['old_ftp_password'], site['old_ftp_host'], site['old_ftp_root'])

    if DEBUG: 
        sys.stdout.write("Executing:" + cmd + "\n")

    fd = os.popen(cmd)
    output = fd.read()

    if DEBUG:
        sys.stdout.write(output)

    os.chdir(SITE_DB_FOLDER)

    config_index = 0

    for config in site['configs']:


        # Make a temp folder on the server we can use.
        cmd = """lftp -e "mkdir motive-temp; chmod 0777 motive-temp; exit" -u '%s,%s' %s/%s  """ % (site['old_ftp_user'], site['old_ftp_password'], site['old_ftp_host'], site['old_ftp_root'])

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)
        output = fd.read()

        if DEBUG:
            sys.stdout.write(output)

        # Just in case we can't remove the scripts we're creating, they're protected by obscurity too.
        toHex = lambda x: "".join([hex(ord(c))[2:].zfill(2) for c in x])
        secret_key = toHex(os.urandom(15))

        # This is a pretty basic DB dump script in pure php.  It would be nice to pull indexes but that's a long way off.

        script_name = "motive-db-downloader-" + secret_key + ".php"

        script_to_upload = open(script_name, "w")

        downloader_content = "<?php \n"
        downloader_content += "backup_tables('" + config['db_host'] + "', '" + config['db_user'] + "', '" + config['db_password'] + "', '" + config['db_db'] + "');\n"
        downloader_content += """
            /* backup the db OR just a table */
            function backup_tables($host,$user,$pass,$name,$tables = '*')
            {
                
                $link = mysql_connect($host,$user,$pass);
                mysql_select_db($name,$link);
                
                //get all of the tables
                if($tables == '*')
                {
                    $tables = array();
                    $result = mysql_query('SHOW TABLES');

                    while($row = mysql_fetch_row($result))
                    {
                        $tables[] = $row[0];
                    }
                }
                else
                {
                    $tables = is_array($tables) ? $tables : explode(',',$tables);
                }
                
                //cycle through
                foreach($tables as $table)
                {
                    $result = mysql_query('SELECT * FROM '.$table);
                    $num_fields = mysql_num_fields($result);
                    
                    $return.= 'DROP TABLE IF EXISTS '.$table.';';
                    $row2 = mysql_fetch_row(mysql_query('SHOW CREATE TABLE '.$table));
                    $return.= "\n\n".$row2[1].";\n\n";
                    
                    for ($i = 0; $i < $num_fields; $i++) 
                    {
                        while($row = mysql_fetch_row($result))
                        {
                            $return.= 'INSERT INTO '.$table.' VALUES(';
                            for($j=0; $j<$num_fields; $j++) 
                            {
                                $row[$j] = addslashes($row[$j]);
                                $row[$j] = ereg_replace("\n","\\n",$row[$j]);
                                if (isset($row[$j])) { $return.= '"'.$row[$j].'"' ; } else { $return.= '""'; }
                                if ($j<($num_fields-1)) { $return.= ','; }
                            }
                            $return.= ");\n";
                        }
                    }
                    $return.="\n\n\n";
                }
                
                //save file
                $handle = fopen('motive-temp/db-""" + secret_key + """.sql','w+');
                fwrite($handle,$return);
                fclose($handle);

            }

            $handle = fopen('motive-temp/server-""" + secret_key + """.txt', 'w+');
            fwrite($handle, json_encode($_SERVER));
            fclose($handle);

            chmod('motive-temp/db-""" + secret_key + """.sql', 0777);
            chmod('motive-temp/server-""" + secret_key + """.txt', 0777);
        """

        script_to_upload.write(downloader_content)
        script_to_upload.close()


        # Upload and run our script

        cmd = """lftp -e "put %s; exit" -u '%s,%s' %s/%s  """ % (script_name, site['old_ftp_user'], site['old_ftp_password'], site['old_ftp_host'], site['old_ftp_root'])

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)
        output = fd.read()

        if DEBUG:
            sys.stdout.write(output)


        

        cmd = "wget http://" + site['old_domain'] + '/' + script_name

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)

        output = fd.read()

        if DEBUG:
            print output




        cmd = "wget http://" + site['old_domain'] + '/motive-temp/db-' + secret_key + '.sql'

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)

        output = fd.read()

        if DEBUG:
            print output

        config['database_sql'] = SITE_DB_FOLDER + '/db-' + secret_key + '.sql'
        config['secret_key'] = secret_key





        # We also pulled the $_SERVER as JSON so we can properly replace paths later.

        cmd = "wget http://" + site['old_domain'] + '/motive-temp/server-' + secret_key + '.txt'

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)

        output = fd.read()

        if DEBUG:
            print output

        fd = open('server-' + secret_key + '.txt')
        server_json = fd.read()
        fd.close()

        config['old_server_info'] = json.loads(server_json)




        # Remove the DB dump and script from the server

        cmd = """lftp -e "rm motive-temp/*; rmdir motive-temp; rm %s; exit" -u '%s,%s' %s/%s  """ % (script_name, site['old_ftp_user'], site['old_ftp_password'], site['old_ftp_host'], site['old_ftp_root'])

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)
        output = fd.read()

        if DEBUG:
            sys.stdout.write(output)




        # Save updated config for later use        

        site['configs'][config_index] = config
        config_index += 1



    return site





def alter_downloaded_site(site):
#    SITE_FOLDER = site['folder']
    SITE_DL_FOLDER = site['dl_folder']
    SITE_DB_FOLDER = site['db_folder']
    os.chdir(SITE_DL_FOLDER)

    for config in site['configs']:
        os.chdir(SITE_DL_FOLDER)

        if not site.has_key('no-replace-db-config'):

            fn = config['config_file']

            fd = open(fn, "r")
            config_content = fd.read()
            fd.close()

            replacements = config_file_matching[config['config_type']]

            for term in replacements:

                iterator = re.finditer(replacements[term], config_content, re.MULTILINE)

                for match in iterator:
                    the_start = match.start(1)
                    the_end = match.end(1)

                    config_content = config_content[:the_start] + site['new_' + term] + config_content[the_end:]

                    if DEBUG:
                        print "Updated config term", term, ": ", config_content[the_start - 25:the_end + 25]



            fd = open(fn, "w")
            fd.write(config_content)
            fd.close()

            del(config_content)

    
        if not site.has_key('no-update-db-hostname'):

            if (site['old_domain'] != site['new_domain']):
                os.chdir(SITE_DB_FOLDER)

                fd = open(config['database_sql'], "r")
                db_content = fd.read()
                fd.close()

                quote_matcher = re.compile(r'(?<![\\])"', re.MULTILINE)
                old_site_matcher = re.compile("(www\.)?" + site['old_domain'], re.MULTILINE)

                the_start = 0
                match = 1

                while match:
                    match = old_site_matcher.search(db_content, the_start)

                    if not match:
                        break

                    the_start = match.start()
                    the_end = match.end()

                    if DEBUG:
                        print "the_start", the_start

                    # This seems rather expensive to do for the whole DB, so we'll just search the 5000 characters up to the current position.
                    section_start_iter = quote_matcher.finditer(db_content, the_start - 5000, the_start)

                    section_start_match = None

                    for section_start_match in section_start_iter:
                        pass

                    section_end_match = quote_matcher.search(db_content, the_end)

                    if (not section_start_match) or (not section_end_match):
                        db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
                        continue

                    section_start_pos = section_start_match.start() + 1
                    section_end_pos = section_end_match.start()

                    section = db_content[section_start_pos:section_end_pos]

                    pre = db_content[:section_start_pos]
                    post = db_content[section_end_pos:]

                    serialized_match = re.search(r'[a-zA-Z]:[0-9]+:{', section)

                    if not serialized_match:
                        db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
                    else:
                        group = match.group()

                        len_start = db_content.rfind("s:", 0, the_start) + 2
                        len_end = db_content.find(":", len_start)

                        old_len = int(db_content[len_start:len_end])
                        len_diff = len(site['new_domain']) - len(group)
                        new_len = old_len + len_diff

                        db_content = db_content[:len_start] + str(new_len) + db_content[len_end:]

                        # Make sure it's still in the same spot...
                        match = old_site_matcher.search(db_content, len_start)

                        the_start = match.start()
                        the_end = match.end()

                        db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]

                fd = open(config['database_sql'], "w")
                fd.write(db_content)
                fd.close()

                del(db_content)

    return site

def upload_to_remote(site):
    SITE_FOLDER = site['folder']
    SITE_DL_FOLDER = site['dl_folder']
    SITE_DB_FOLDER = site['db_folder']

    os.chdir(SITE_DL_FOLDER)

    cmd = """lftp -e "mirror -R; put .htaccess; exit" -u '%s,%s' %s/%s  """ % (site['new_ftp_user'], site['new_ftp_password'], site['new_ftp_host'], site['new_ftp_root'])

    if DEBUG: 
        sys.stdout.write("Executing:" + cmd + "\n")

    fd = os.popen(cmd)
    output = fd.read()

    if DEBUG:
        sys.stdout.write(output)

    os.chdir(SITE_DB_FOLDER)

    for config in site['configs']:
        cmd = "mysql --user='%s' --host='%s' --password='%s' '%s' < %s" % (
                                                                                site['new_db_user'],
                                                                                site['new_db_host'],
                                                                                site['new_db_password'],
                                                                                site['new_db_db'],
                                                                                config['database_sql']
                                                                            )

        if DEBUG: 
            sys.stdout.write("Executing:" + cmd + "\n")

        fd = os.popen(cmd)
        output = fd.read()

        if DEBUG:
            sys.stdout.write(output)





TEMP_FOLDER = tempfile.mkdtemp()
if not TEMP_FOLDER:
    print sys.stderr, "Couldn't create temp folder!"
    sys.exit(1)




for site_name in sites:
    site = sites[site_name]

    SITE_FOLDER = TEMP_FOLDER + "/" + site['old_domain']
    SITE_DL_FOLDER = SITE_FOLDER + "/download"
    SITE_DB_FOLDER = SITE_FOLDER + "/database"

    os.mkdir(SITE_FOLDER)
    os.mkdir(SITE_DL_FOLDER)
    os.mkdir(SITE_DB_FOLDER)

    site['folder'] = SITE_FOLDER
    site['dl_folder'] = SITE_DL_FOLDER
    site['db_folder'] = SITE_DB_FOLDER

    site = sites[site_name] = get_old_config(site)

    if not site['configs']:
        print "Couldn't find config for site: ", site_name

        del(sites[site_name])


if not sites:
    print "No sites to switch!  Please check config settings!!!"

if DEBUG:
    print "After getting config, sites: ", sites

for site_name in sites:
    site = sites[site_name]

    site = sites[site_name] = copy_site_to_local(site)

    if DEBUG:
        print "\nAfter copy_to_local, site: ", site

    site = sites[site_name] = alter_downloaded_site(site)
    site = sites[site_name] = upload_to_remote(site)



sys.exit(0)

