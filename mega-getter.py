#!/usr/bin/env python

from __future__ import print_function

import argparse
import git
import json
import re
import requests
import requests.auth
import sys

from pprint import pprint  # noqa

# Possible options include:
#         'DETAILED_LABELS', 'CURRENT_REVISION', 'CURRENT_COMMIT',
#         'CURRENT_FILES', 'REVIEWED', 'DETAILED_ACCOUNTS'
_gerrit_opts = ['CURRENT_REVISION', 'CURRENT_COMMIT', 'CURRENT_COMMIT',
                'CURRENT_FILES', 'DETAILED_ACCOUNTS']


def get_reviews(auth, host, query, limit=None):
    print('Running: %s' % (query))
    url = 'https://%s/a/changes/' % (host)
    params = {'q': query, 'o': _gerrit_opts}
    if limit:
        params.update({'limit': limit})
    r = requests.get(url, auth=auth, params=params)
    if r.status_code == 200:
        data = json.loads(r.text[4:])
    else:
        print('Status : Failed')
        print('       : %s' % (r))
        print('       : %s' % (r.text))
        data = []
    return data


def main(args):
    auth = requests.auth.HTTPDigestAuth(args.user, args.password)
    # Assume the query will be for chnages that match the current repo
    # *and* we're in that project already
    repo = git.Repo(args.repo)
    for change in get_reviews(auth, args.host, args.query,
                              limit=args.limit):
        sha = list(change['revisions'].keys())[0]
        revision = change['revisions'][sha]
        refspec = revision['ref']

        topic = change.get('topic', change['_number'])
        try:
            author = re.sub('\W+', '_', change['owner']['name']).lower()
        except KeyError:
            author = 'unknown'
        branch_name = "review/%s/%s" % (author, topic)

        print('Grabbing %d into %s' % (change['_number'], branch_name))
        repo.git.fetch('gerrit', '%s:%s' % (refspec, branch_name))
        repo.git.format_patch(branch_name, '-1', o=args.outdir)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Vote-a-tron')

    # FIXME: Make the required args more robust
    parser.add_argument('--host', dest='host',
                        default='review.openstack.org',
                        help=('Gerrit hostname default: %(default)s'))
    parser.add_argument('--user', dest='user', required=True,
                        help=('Gerrit username'))
    parser.add_argument('--password', dest='password', required=True,
                        help=('Gerrit HTTP password'))
    parser.add_argument('--query', dest='query', required=True,
                        help=('Gerrit query matching *ALL* reviews to '
                              'vote on'))
    parser.add_argument('--repo', dest='repo', required=True,
                        help=('Full path to project repo'))
    parser.add_argument('--out-dir', dest='outdir', required=True,
                        help=('Full path to where you want the patch files'))
    # FIXME: Limit mist be >= 0
    parser.add_argument('--limit', dest='limit', default=0, type=int,
                        help=('The maximum number of reviews to '
                              'post. 0 for no limit.'))

    args, extras = parser.parse_known_args()

    sys.exit(main(args))
