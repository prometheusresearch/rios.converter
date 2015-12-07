This file exists so hg will include **temp** in the repository.

**temp** is the directory the server uses for temporary files.
It is in the repository so that the server does not have to create it dynamically.

- ``static/settings.yaml`` sets temp_dir to **./temp**
- ``.hgignore`` is configured to ignore files in **temp** 

