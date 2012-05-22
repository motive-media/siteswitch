#!/usr/bin/python

sites = {
    'site1': {
        'old_domain': 'domain',
        'new_domain': 'domain',
        'database_file': 'db.sql'
    }
}


DEBUG = 0



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

        quote_type_matcher = re.compile(r'(;s:[0-9]+:\\")', re.MULTILINE)

        match = quote_type_matcher.search(db_content)

        if (match):
            quote_matcher = re.compile(r'(?<=\\)"', re.MULTILINE)
            print 'Matching with (?<=\\)"'
        else:
            quote_matcher = re.compile(r'(?<![\\])"', re.MULTILINE)
            print 'Matching with (?<![\\])"'

        old_site_matcher = re.compile("(www\.)?" + site['old_domain'].replace('.', '\.'), re.MULTILINE)

        serialized_matcher = re.compile(r'([;{][sS]:[0-9]+:)', re.MULTILINE)

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

            section_start_pos = section_start_match.start() - 15
            section_end_pos = section_end_match.start()

            section = db_content[section_start_pos:section_end_pos]

            serialized_match = serialized_matcher.search(section)

            if not serialized_match:
                if DEBUG: print "Unserialized: " + db_content[the_start - 50:the_end] + "\nsection: " + section
                db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
            else:
                if DEBUG: print "Serialized: " + db_content[the_start - 50:the_end] + "\nsection: " + section
                group = match.group()

                len_start = db_content.rfind("s:", 0, the_start) + 2
                len_end = db_content.find(":", len_start)

                if (len_end - len_start > 10):
                    db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
                    continue

                if DEBUG: print "Looking for length in: %s" % db_content[len_start:len_end]

                try:
                    old_len = int(db_content[len_start:len_end])
                except:
                    print "Unexpected error, trying to keep going:", sys.exc_info(), serialized_match.groups()
                    print "Context: ", db_content[the_start-100:the_end+100]
                    db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
                    continue

                if DEBUG: print "old len: ", old_len

                if DEBUG: print "group: " + group

                len_diff = len(site['new_domain']) - len(group)
                new_len = old_len + len_diff

                if DEBUG: print "len diff: %s " % len_diff

                if DEBUG: print "new len: ", new_len

                print "Replaced serialized: " + db_content[len_start - 2: the_end]

                db_content = db_content[:len_start] + str(new_len) + db_content[len_end:]

                # Make sure it's still in the same spot...
                match = old_site_matcher.search(db_content, len_start)

                the_start = match.start()
                the_end = match.end()

                db_content = db_content[:the_start] + site['new_domain'] + db_content[the_end:]
                print "With: " + db_content[len_start - 2: the_end + len_diff]

        out = open(site['database_file'] + '_modified.sql', "w")
        out.write(db_content)
        out.close()

        print "New database is in", site['database_file'] + '_modified.sql'

sys.exit(0)

