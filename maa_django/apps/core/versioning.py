import subprocess
from datetime import datetime
from pathlib import Path

def get_git_changeset_timestamp(absolute_path):
    repo_dir = absolute_path
    git_log = subprocess.Popen(
        "git log --pretty=format:%ct --quiet -1 HEAD",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
    )
    timestamp = git_log.communicate()[0]
    try:
        timestamp = datetime.utcfromtimestamp(int(timestamp))
    except ValueError:
        # Fallback to current timestamp
        return datetime.now().strftime('%Y%m%d%H%M%S')
    changeset_timestamp = timestamp.strftime('%Y%m%d%H%M%S')
    return changeset_timestamp

def get_static_version(absolute_path):
    """" Permet de forcer le rechargement des fichiers statics
    lors de la modification du fichier maa_django/settings/last-update.txt
    
    Ce fichier peut éventuellement être mis à jour via un git hook/pre-commit
    """
    with open(Path(absolute_path).joinpath('maa_django').joinpath('settings').joinpath('last-update.txt'), 'r') as f:
        version = f.readline().strip()
    return version