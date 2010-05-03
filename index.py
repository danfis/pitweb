##
## Example script for mod_python deployment
##

from mod_python import apache, util
import pitweb

def handler(req):
    parent_dir = '/path/to/dir/with/git/repositories'
    prj_list = pitweb.ProjectListDir(req, parent_dir)
    return prj_list.run()
