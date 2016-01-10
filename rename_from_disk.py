#!/usr/bin/python
"""
Usage: rename_from_disk.py -l <Library> -t <show title> -s <season> [-d -D]

This searches Plex for the existing library, title and season, and changes the
Plex "title" entry based on the filenames associated with the episode.  Note 
that this changes *all* episodes in a season, based on the filename.

The [-d] flag is "don't do" - do the lookups, and only show the URL to set the title.
The [-D] flag enables debugging.

Sections (or Library) are the things like "Movies", "TV Shows", etc.
Show title is the title as it appears in Plex.
Season is the season name as it appears in Plex.

This assumes the Plex-friendly file naming, where the description occurs towards
the end.
"""
#
# There are some basic steps to go through to get to where we can even do a search
#     - get the list of sections available.
#               http://localhost:32400/library/sections/all  ('TV Shows' is 6)
#     - based on the show title, get the "key" to find all the seasons
#		http://localhost:32400/<key>/children
#     - based on the season key, get the "key" to find all the episodes
#              http://localhost:32400/<key>/children
#     - now, with the list of all episodes, note that the "file" is indicated
#     Issue a PUT call to
#               http://localhost:32400/<episode key>?title=<URL encoded string>
import sys, os
import getopt, collections
import requests
import xmltodict   # hopefully an easier way to trudge through XML

# usage() and die
def usage():
    print __doc__
    sys.exit(0)

# parse(plex formatted TV show name]
# Tease out the show title, season number, episode number, episode title
# from the standard plex format filenames for TV shows
def tv_parse(fname):
    basename = os.path.basename(fname)
    filename, file_ext = os.path.splitext(basename)
    try:
        (show_title, epi_info, descr) = filename.split(' - ', 2)
    except:
        print "Cannot split fname", fname
        raise
    show_title = show_title.lstrip().rstrip()
    descr = descr.lstrip().rstrip()
    return (show_title, epi_info, '', descr)

# constants
base_url = 'http://plex:32400'
sections_url = base_url + '/library/sections/all'

# command line options
desired_section = ''
desired_show = ''
desired_season = ''
dont_do = 0  # if "dont_do", just print what we'd do - don't change anything
debug = 0

options, remainder = getopt.getopt(sys.argv[1:], 'l:t:s:dD',
                                   ['library=', 'title=', 'season=',
                                    'debug', 'dontdo'])
for opt,arg in options:
    if opt in ['-l','--library']:
        desired_section = arg
    elif opt in ['-t','--title']:
        desired_show = arg
    elif opt in ['-s','--season']:
        desired_season = arg
    elif opt in ['-d','--dontdo']:
        debug = 1
    elif opt in ['-D','--debug']:
        dont_do = 1

if debug:
    print "Arguments:"
    print "\tlibrary", desired_section
    print "\tshow title", desired_show
    print "\tseason", desired_season
    print "\tdebug", debug
    print "\tdontdo", dont_do

if ( desired_section == '' ) or \
   ( desired_show == '' ) or \
   ( desired_season == ''):
    usage()

# get sections (aka library) - "Music", "Movies", "TV Shows"
x = requests.get(sections_url)
if not x.ok:
    print "error getting list of Libraries",x.text
    sys.exit(1)
if debug: print "library/section lookup returns %d bytes" % (len(x.text))
resp_dict = xmltodict.parse(x.text)

# look for desired section, and get "key" value for further lookups
section_key=''
for ordered_d in resp_dict['MediaContainer']['Directory']:
    xml_dict = dict(ordered_d)
    if xml_dict['@title'] == desired_section:
        section_key = xml_dict['@key']
        break
if section_key == '':
    print "Couldn't find section key for section \"%s\"" % (desired_section)
    sys.exit(1)
if debug: print "Desired section \"%s\" key:%s" % (desired_section, section_key)

# now look through all "TV Shows"
x = requests.get(base_url + '/library/sections/' + section_key + '/all')
if not x.ok:
    print >>sys.stderr, x.text
    sys.exit(1)
if debug: print "TV Show lookup returns %d bytes" % (len(x.text))
resp_dict = xmltodict.parse(x.text)

# desired_show = 'The Lucy-Desi Comedy Hour'
show_key=''
for ordered_d in resp_dict['MediaContainer']['Directory']:
    xml_dict = dict(ordered_d)
    if xml_dict['@title'] == desired_show:
        show_key = xml_dict['@key']
        break
if show_key == '':
    print "Couldn't find show key for show \"%s\"" % (desired_show)
    sys.exit(1)
if debug: print "Key for \"%s\" is \"%s\"" % (desired_show, show_key)

# now look up the correct season - get all seasons under the show
x = requests.get(base_url + show_key)
if not x.ok:
    print "Error getting list of seasons",x.text
    sys.exit(1)
if debug: print "Season lookup returns %d bytes" % (len(x.text))
resp_dict = xmltodict.parse(x.text)

season_dict = resp_dict['MediaContainer']['Directory']
# Ensure that returned types are consistent - season_dict should be a list
# See full commentary around "Messiness from here." down below
if type(season_dict) == collections.OrderedDict:
    season_dict = [ season_dict ]
elif type(season_dict) == list:
    pass  # things are fine
else:
    print >>sys.stderr, "Unknown type of response for Season request",type(season_dict)
    sys.exit(1)

# desired_season = "Season 1"
season_key = ''
for ordered_d in season_dict:
    xml_dict = dict(ordered_d)
    if xml_dict['@title'] == desired_season:
        season_key = xml_dict['@key']
        break
if season_key == '':
    print "Couldn't find season key for season \"%s\"" % (desired_season)
    sys.exit(1)
if debug: print "Key for \"%s\" is \"%s\"" % (desired_season, season_key)

# finally, look up episode names
x = requests.get(base_url + season_key)
if not x.ok:
    print "Error getting list of episodes",x.text
    sys.exit(1)
if debug: print "Episode lookup returns %d bytes" % (len(x.text))
resp_dict = xmltodict.parse(x.text)

# Messiness from here.
# In some cases, what should be a consistent list or OrderedDicts is instead "either an
# OrderedDict or list of OrderedDicts".  So there's some ugly code asking about the type
# to accomodate this.
#
# Determine if the Video object is a list or singleton of OrderedDict
if debug:
    vd = resp_dict['MediaContainer']['Video']
    print "Video dictionary is type",type(vd), "len",len(vd)
if type(resp_dict['MediaContainer']['Video']) == list:
    video_dict = resp_dict['MediaContainer']['Video']
elif type(resp_dict['MediaContainer']['Video']) == collections.OrderedDict:
    video_dict = [ resp_dict['MediaContainer']['Video'] ] # put it in a list
else:
    print >>sys.stderr, "Dictionary for Video type unknown",type(resp_dict['MediaContainer']['Video'])
    sys.exit(1)

for ordered_d in video_dict:
    xd = dict(ordered_d)
    # Determine if Media object is a list or singleton of OrderedDict
    if type(xd['Media']) == list:
        md = dict(xd['Media'][0]) # maybe multiple entries if a multi-part show
    elif type(xd['Media']) == collections.OrderedDict:
        md = dict(xd['Media'])
    else:
        # what type?
        print >>sys.stderr, "Show type unknown",type(xd['Media']),"for video",xd
    if type(md['Part']) == list:
        pd = dict(md['Part'][0])
    elif type(md['Part']) == collections.OrderedDict:
        pd = dict(md['Part'])
    else:
        print >>sys.stderr, "Show part type unknown",type(md['Part']),"for video",xd
    (show_title, season_no, episode_no, episode_title) = tv_parse(pd['@file'])
    episode_key = xd['@key']
    enc_title = requests.utils.requote_uri(episode_title)
    if debug:
        print "Title \"%s\" File: \"%s\"" % (xd['@title'], pd['@file'])
        print "\tDescr: %s" % (episode_title)
        print "\tKey: %s" % (episode_key)
    # print "\tPUT %s%s?title=%s" % (base_url, episode_key, enc_title)
    final_url = "%s%s?title=%s&title.locked=1" % \
                (base_url, episode_key, enc_title)
    if not dont_do:
        x = requests.api.put(final_url)
        print x.request.url
    else:
        print "SKIPPED:",final_url
    # need to uuencode the title, then do a request.put() with it and args
