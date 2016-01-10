# plex
Plex utilities

The utility "rename_from_disk" will rename Plex shows - a season at a
time - based on the filenames associated with the episodes.

It searches Plex based on the library (TV Show, Music, Movies, etc),
show title and season indicated on the command line, and renames the
episodes based on the related file name.

The file name is assumed to be in a reasonable Plex format -
    <show title> - S<nn>E<nn> - <extra stuff>.extension
The episode will be named according to the "<extra stuff>" in the filename.

Usage:
  rename_from_disk -l <library> -t <show title> -s <season> [-d] [-D]
  	-l <library>		e.g. 'TV Shows', 'Music', etc
	-t <show title>	Exactly as it appears in the Plex GUI
  	-s <season>        Season name as it appears in Plex (e.g. "Season 1")
option flags: "-d" for debugging, "-D" for "don't do" - process and
  show what renaming would occur.

examples:
	rename_from_disk.py -l 'TV Shows' -t 'Miss Marple' -s 'Season 1'

Credits:
	Credits to github user "profplump" for his renameFromDisk.pl -
	which helped me figure out the messy Plex API.
