import argparse
from jinja2 import Environment, FileSystemLoader
import json
from multiprocessing import Pool
import os
import pwd
import shlex
import subprocess
import sys


LOGDIR = "/tmp/mirror-logs"
MIRROR_TEMPLATES_TMPDIR = "/tmp/mirror-templates"


class Mirror:
    """
    A mirror running on a fort server. Consists of:

     * a (textual) identifier, unique in the mirroring system
     * zero or more templates, rendered before mirroring
     * parameters to populate the templates (and the apache vhost template)
     * a series of mirroring steps, each of which is several commands
       run under a particular user (typically root or fort)
    """

    DEFAULTS = {}

    def __init__(self, identifier, steps, templates=None, **params):
        self.identifier = identifier
        self.steps = steps
        self.templates = templates
        if self.templates is None:
            self.templates = []
        self.params = dict(self.DEFAULTS)
        self.params.update(params)
        self.templates.append(
            self.params["vhost-template"]
        )
        self.env = Environment(
            loader=FileSystemLoader('./templates'),
            autoescape=False,
        )
        self.template_dir = os.path.join(
            MIRROR_TEMPLATES_TMPDIR,
            self.identifier,
        )
        os.makedirs(self.template_dir, exist_ok=True)

    def mirror(self, configure_apache=False):
        try:
            self.render_templates()
            if configure_apache:
                # copy in apache2 vhost config and enable that site
                with open(
                    self.rendered_template_filename(self.params['vhost-template']),
                    'r'
                ) as inf, open(
                    os.path.join(
                        '/etc/apache2/sites-available',
                        '%s.conf' % self.identifier,
                    )
                ) as outf:
                    inf.write(outf.read())
                    subprocess.call(
                        "a2ensite %s" % self.identifier
                    )
                # FIXME: add DNS entry

            # need to su before we do the mirroring, because we want
            # that run as another user
            pwdent = pwd.getpwnam(self.params['user'])
            uid = pwdent.pw_uid
            gid = pwdent.pw_gid
            os.seteuid(uid)
            os.setegid(gid)
            # and change directory -- typically to that user's home
            os.chdir(self.params['cwd'])

            for step in self.steps:
                args = shlex.split(step)
                p = subprocess.Popen(args)
        finally:
            for t in self.templates:
                try:
                    os.unlink(
                        self.rendered_template_filename(t)
                    )
                except:
                    pass

    def rendered_template_filename(self, t):
        return os.path.join(self.template_dir, t)
                
    def render_templates(self):
        for t in self.templates:
            self.render_template(
                "%s.template" % t,
                self.rendered_template_filename(t),
            )

    def render_template(self, template, out):
        template = self.env.get_template(template)
        with open(out, 'w') as fout:
            fout.write(template.render(self.params))

    @classmethod
    def from_config(kls, config):
        kls.DEFAULTS = config['defaults']
        for mirror in config['mirrors']:
            yield kls(
                mirror['id'],
                mirror['steps'],
                mirror.get('templates'),
                **mirror['params'],
            )


def do_mirror(mirror):
    # Note that this is run in the sub-Process
    # So it's safe to throw away stdout and stderr and never
    # restore them.
    sys.stdout = open(
        os.path.join(LOGDIR, "%s.out" % mirror.identifier),
        'w',
    )
    sys.stderr = open(
        os.path.join(LOGDIR, "%s.err" % mirror.identifier),
        'w',
    )
    return mirror.mirror()




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Mirror useful parts of the internet, for fortly purposes.",
    )
    parser.add_argument(
        '--serial',
        dest='serial',
        default=False,
        action='store_true',
        help='run in serial rather than parallel',
    )
    parser.add_argument(
        '--logdir',
        dest='logdir',
        default=LOGDIR,
        action='store',
        help='set logging directory',
    )
    parser.add_argument(
        '--tmpdir',
        dest='tmpdir',
        default=MIRROR_TEMPLATES_TMPDIR,
        action='store',
        help='set temp directory',
    )
    parser.add_argument(
        'configfile',
        metavar='configfile',
        type=str,
        nargs=1,
        help='Config file for mirroring',
    )
    parser.add_argument(
        'kv',
        metavar='kv',
        type=str,
        nargs='*',
        help='Key-value pairs to add to defaults',
    )
    args = parser.parse_args()
    defaults = dict(
        (
            kv.split('=', 1)
            for kv in args.kv
        )
    )

    LOGDIR = args.logdir
    MIRROR_TEMPLATES_TMPDIR = args.tmpdir

    with open(args.configfile[0], 'r') as cin:
        config = json.load(cin)
    config['defaults'].update(defaults)
    mirrors = list(Mirror.from_config(config))

    if args.serial:
        for mirror in mirrors:
            do_mirror(mirror)
    else:
        # FIXME: doesn't work because jinja2 isn't pickleable,
        # because pickling is a bad idea but apparently we still
        # use it. Sigh.
        with Pool(len(mirrors)) as p:
            p.map(do_mirror, mirrors)
