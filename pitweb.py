##
## This is configuration file for pitweb.
## It takes place in .git directory of repository and must be written in
## python syntax because.
##


### Name of the project (repository)
# If project name is not set it will be derived from git directory.
project_name = 'ProjectName'

### Commits per page shown in Log section
# Default value is 50.
commits_per_page = 50

### Number of commits shown in Summary section
# Default value is 15
commits_in_summary = 15

### Maximal length of one line comment (shown for example in log)
# Default value is 50
one_line_comment_max_len = 50

### Description of project - will be shown in summary
description = 'Some description of your project'

### Owner of project
owner = 'Joe Doe <joe@doe.com>'

### List of urls from which can be repository cloned
urls = ['git://git.project.net', 'https://project.net/git']

### Url of homepage of project
homepage = 'http://project.net'

### List of formats in which snapshots can be downloaded.
# Available formats are 'tgz', 'tbz2', 'txz', 'zip'
# Default value is ['tgz', 'tbz2']
snapshots = ['tgz', 'tbz2', 'txz', 'zip']
