# devfort mirroring system

First, we had a shell script. (Well, first we had notes. Then they became a shell script.) That was bad because it didn't set up the mirrors usefully, and we'd mess around at forts making things work.

Then, we had a load of chef. Every fort we'd have to update it because chef would change. We had a four year break between forts at one point, and chef changed enormously and I really couldn't be bothered to figure out how to update it.

So next I figured out what commands the chef was running underneath. (It worked by creating templated upstart jobs that ran the mirror, and apache2 virtual hosts to server them.) And I reckoned almost all of it could be turned into a single JSON configuration file, with a couple of templates.

## How to build a fort

1. Install Ubuntu 18.04; just accept all the defaults and create yourself an account called 'fort'
 * note that galle currently has a bunch of other things installed, including microk8s, postgresql10, docker, and kata-containers (all of which use snap, which complained a bit while installing, so might not actually work)
 * `apt-get install python3-venv apt-mirror rsync wget`
2. `sudo chown fort:fort /srv`
3. Install from `requirements.txt`, and run `python mirror.py` _as the fort user_, with `GITHUB_TOKEN` in the environment.
 * Some things it will create and run under separate venvs, where the mirroring system is driving other python packages.
 * Slightly confusingly this includes gitmirror.py which is here as a helper but depends on `PyGithub` which isn't in `requirements.txt`.
4. Configure pypi for the fort user to use the local
 * `mkdir ~fort/.pip && echo -e '[global]\nindex-url = https://pypi.fort/' > ~fort/.pip/pip.conf`
5. Configure apt by setting apt.fort in /etc/apt/sources.lists (add it as an additional apt source, disable the others, and apt-get update -- then it's an example for configuring other machines)

## TODO

* consider blacklists or whitelists for bandersnatch to reduce what we pull
* configure bandersnatch to reduce historical versions?
* nicer output from both mirror.py and gitmirror.py; the former at least uses logfiles (this would also enable us to control the parallelism in git mirroring, using a pool rather than just all the subprocesses -- although that might end up running slower)
