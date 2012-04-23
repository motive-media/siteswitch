#!/usr/bin/python

sites = {
    'site1': {
        'old_domain': 'domain',
        'new_domain': 'domain',
        'database_file': 'db.sql'
    }
}






import ftplib
import tempfile
import getpass
import os
import sys
import re
import ConfigParser
import json

for site in sites:
    site = sites[site]

    if (site['old_domain'] != site['new_domain']):
        fd = open(site['database_file'], "r")
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

                try:
                    old_len = int(db_content[len_start:len_end])
                except:
                    db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
                    continue

                len_diff = len(site['new_domain']) - len(group)
                new_len = old_len + len_diff

                db_content = db_content[:len_start] + str(new_len) + db_content[len_end:]

                # Make sure it's still in the same spot...
                match = old_site_matcher.search(db_content, len_start)

                the_start = match.start()
                the_end = match.end()

                db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]

        fd = open(site['database_file'] + '_modified.sql', "w")
        fd.write(db_content)
        fd.close()

        del(db_content)

        print "New database is in", site['database_file'] + '_modified.sql'

sys.exit(0)

