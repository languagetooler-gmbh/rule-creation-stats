import argparse
from datetime import datetime
from lib.rule_dump import RuleDump
from lib.constants import *
from lib.logger import logger_wrapper
import os
from pandas import DataFrame


class CLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='LT cross language applicability',
            description='Simple script that collects comments in xml files'
        )
        self.parser.add_argument('-v', '--verbosity', default='INFO')
        self.parser.add_argument('-o', '--out-dir', default='lt-cross-language-applicability')
        # self.parser.add_argument('-f', '--from-dir')
        self.parser.add_argument('-t', '--to-dir')
        self.args = self.parser.parse_args()
        os.makedirs(self.args.out_dir, exist_ok=True)


def issue_not_created(issues_path, style_rule_id):
    issues_created = open(issues_path, 'r', encoding='utf-8')
    for line in issues_created:
        if line == style_rule_id:
            return False
    return True


def create_rows(issues_path, dump_files, locale):
    rows = []
    missing_issues = []
    for file in dump_files:
        for element in (file.rulegroups + file.rules):
            for comment in element.comments:
                derived_rule = re.compile(r'\[derived from: [a-z]{2}]')
                if comment.tag == "DESC" and not derived_rule.search(comment.content):
                    rows.append([
                        datetime.strptime(comment.date, '%Y-%m-%d').date(),
                        locale, file.rel_path, element.id, element.sub_id,
                        ','.join([tt.tag for tt in element.tone_tags]),
                        comment.tag, comment.content
                    ])
                    if issue_not_created(issues_path, element.id):
                        missing_issues.append(element.id)
    return rows, missing_issues


# table schema:
# locale
# file
# rule_id
# sub_id
# tone_tags
# tag
# content
def __main__():
    cli = CLI()
    logger = logger_wrapper(cli.parser.prog, cli.args.verbosity)
    logger.debug(f"Starting script...\nInvoked with options: {cli.args}")
    all_path = path.join(cli.args.out_dir, 'all_comments.csv')
    issues_path = path.join(cli.args.out_dir, 'issues_created.txt')
    # diff_path = path.join(cli.args.out_dir, 'diff_comments.csv')
    headers = ['date', 'locale', 'file', 'rule_id', 'sub_id', 'tone_tags', 'tag', 'content']
    # to_rows, from_rows = [], []
    to_rows = []
    # issues_to_be_created = []
    for locale in LOCALES:
        for repo_name, repo_dir in REPOS.items():
            # from_repo_path = path.join(cli.args.from_dir, repo_dir)
            to_repo_path = path.join(cli.args.to_dir, repo_dir)
            # from_dump = RuleDump(from_repo_path, locale)
            to_dump = RuleDump(to_repo_path, locale)
            new_rows, issues_to_be_created = create_rows(issues_path, to_dump.files, locale)
            to_rows += new_rows
            # from_rows += create_rows(from_dump.files, locale)
    df = DataFrame(to_rows, columns=headers).sort_values(['date', 'locale', 'rule_id', 'sub_id'])
    logger.info(df.describe())
    all_comments = open(all_path, 'w', encoding='utf-8')
    all_comments.write(df.to_csv(index=False, line_terminator="\n"))

    # diff_rows = [tr for tr in to_rows if tr not in from_rows]
    # df2 = DataFrame(diff_rows, columns=headers).sort_values(['locale', 'rule_id', 'sub_id'])
    # logger.info(df2.describe())
    # diff_comments = open(diff_path, 'w', encoding='utf-8')
    # diff_comments.write(df2.to_csv(index=False, line_terminator="\n"))


__main__()
