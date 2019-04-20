from github import Github
import os.path
import toml
import subprocess
import sys


MIRROR_BASEDIR = '/srv/sources'


def mirror(configfile):
    with open(configfile, 'r') as fp:
        config = toml.load(fp)

    clone_actions = []
    update_actions = []

    for host in config.values():
        hostname = host['hostname']
        if hostname == 'github.com':
            gh = Github(host.get('apitoken'))

        for repo_owner, repos in host['repos'].items():
            if repos == '*':
                # Find all public repos via github API
                # Note that this can't possibly work for non-github
                # repos...but we don't really support them properly
                # anyway at the moment.
                user = gh.get_user(repo_owner)
                repos = [ repo.name for repo in user.get_repos() ]
            if isinstance(repos, str):
                repos = [ repos ]

            for repo_name in repos:
                target_dir = os.path.join(
                    MIRROR_BASEDIR,
                    hostname,
                    repo_owner,
                    repo_name,
                )
                repo_url = 'https://%s/%s/%s.git' % (
                    hostname,
                    repo_owner,
                    repo_name,
                )
                if not os.path.exists(target_dir):
                    # First, ensure all parents exist
                    os.makedirs(
                        os.path.dirname(target_dir),
                        exist_ok=True,
                    )
                    # First time clone!
                    clone_actions.append(
                        [
                            target_dir,
                            repo_url,
                        ]
                    )
                else:
                    update_actions.append(
                        [
                            target_dir,
                            repo_url,
                        ]
                    )

    for target, url in clone_actions:
        p = subprocess.Popen(
            [
                'git',
                'clone',
                '--shared',
                '--bare',
                url,
                target,
            ]
        )
        p = subprocess.Popen(
            [
                'git',
                'update-server-info',
            ],
            cwd=target,
        )
    for target, url in update_actions:
        p = subprocess.Popen(
            [
                'git',
                'fetch',
                '--tags',
                'origin',
                'master:master',
            ],
            cwd=target,
        )


if __name__ == "__main__":
    mirror(sys.argv[1])
