# pitweb

pitweb is a web frontend for git repositories written in python.

pitweb was created because I wasn't able to find any web interface suitable for deployment on my python hosting. pitweb is strongly inspired by cgit and gitweb.

## License
pitweb is distributed under the GNU Lesser General Public License v3. The GNU Lesser General Public License v3 should be available at http://www.gnu.org/licenses/lgpl.html

## Usage
pitweb is currently prepared to run under [apache's](http://httpd.apache.org/)
[mod\_python](http://www.modpython.org/) module but is shouldn't be problem to run it
as cgi script or anything else. Here will be described how to deploy pitweb under mod\_python.

### 1. Apache configuration
Here is how should look configuration for virtual host. All directives should be self explanatory.
```apache
<VirtualHost *:80>
    ServerName pitweb.host.com

    DocumentRoot "/path/to/directory"

    <Directory "/path/to/directory">
        SetHandler mod_python
        PythonPath "['/path/to/pitweb'] + sys.path"
        PythonHandler index
        PythonDebug On

        Options Indexes FollowSymLinks
        AllowOverride None
        Order allow,deny
        Allow from all
    </Directory>
</VirtualHost>
```

### 2. mod_python dispatcher
In configuration above is defined that handler is located in index.py file (PythonHandler directive).
```py
from mod_python import apache, util
import pitweb

def handler(req):
    parent_dir = '/path/to/dir/with/git/repositories'
    prj_list = pitweb.ProjectListDir(req, parent_dir)
    return prj_list.run()
```

### 3. Directories with git repositories
Last thing to do is correctly prepare directories with git repositories.
Directory (defined in python script above in variable parent\_dir) must contain git
repositories created with *--bare* option (*git --bare clone* ...).
Every git repository that also contains *pitweb.py* configuration file will be listed on pitweb projects page.

Template configuration file *pitweb.py* can be found in the pitweb source.
All configuration options are described there.
