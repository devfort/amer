import argparse
from github import Github
import os.path
import toml
import subprocess
import sys


MIRROR_BASEDIR = '/srv/sources'


def mirror(configfile, apitoken):
    with open(configfile, 'r') as fp:
        config = toml.load(fp)

    clone_actions = []
    update_actions = []

    for host in config.values():
        hostname = host['hostname']
        if hostname == 'github.com':
            gh = Github(apitoken)

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

    clones = []
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
        clones.append(p)
    others = []
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
        others.append(p)

    for clone in clones:
        clone.wait()
    for target, url in clone_actions:
        p = subprocess.Popen(
            [
                'git',
                'update-server-info',
            ],
            cwd=target,
        )
        others.append(p)

    for other in others:
        other.wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Clone lots of git repositories, for fortly purposes.",
    )
    parser.add_argument(
        'configfile',
        metavar='configfile',
        type=str,
        nargs=1,
        help='Configuration file location',
    )
    parser.add_argument(
        'apitoken',
        metavar='apitoken',
        type=str,
        nargs='?',
        default=os.environ.get('GITHUB_TOKEN'),
        help='Github API token',
    )
    args = parser.parse_args()
    mirror(args.configfile[0], args.apitoken)
