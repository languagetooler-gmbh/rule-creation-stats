import argparse
import os
from lib.logger import logger_wrapper
from lib.rule_dump import RuleDump
from lib.constants import *
from lib.writing_goals import WritingGoal
from pandas import DataFrame
import pandas as pd
import collections


class CLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='LT style stats',
            description='Simple script that compiles stats on style rule creation'
        )
        self.parser.add_argument('-v', '--verbosity', default='INFO')
        self.parser.add_argument('-o', '--out-dir', default='lt-style-out')
        self.parser.add_argument('-f', '--from-dir')
        self.parser.add_argument('-t', '--to-dir')
        self.args = self.parser.parse_args()
        os.makedirs(self.args.out_dir, exist_ok=True)


def rows_from_rule_tone_tag(rule, repo_name, row_list):
    tone_tags = rule.tone_tags
    if len(tone_tags) == 0:
        row_list.append([
            rule.id,
            'untagged',
            repo_name
        ])
        return
    row_list.append([
        rule.id,
        'tagged',
        repo_name
    ])
    for tt in rule.tone_tags:
        row_list.append([
            rule.id,
            tt.tag,
            repo_name
        ])


def rows_from_rule_writing_goal(rule, repo_name, row_list):
    tone_tags = rule.tone_tags
    if len(tone_tags) == 0:
        row_list.append([
            rule.id,
            'untagged',
            repo_name
        ])
        return
    row_list.append([
        rule.id,
        'tagged',
        repo_name
    ])
    writing_goals = WritingGoal.list_from_tags(tone_tags)
    for wg in writing_goals:
        row_list.append([
            rule.id,
            wg,
            repo_name
        ])


# Yeah, yeah, function controlled by a param, bite me
def rows_from_rule(rule, repo_name, row_list, column_name):
    if column_name == 'tone_tags':
        rows_from_rule_tone_tag(rule, repo_name, row_list)
    elif column_name == 'writing_goals':
        rows_from_rule_writing_goal(rule, repo_name, row_list)


def df_from_repo(to_dir, repo_dir, repo_name, locale, row_list, column):
    repo_path = os.path.join(to_dir, repo_dir)
    dump = RuleDump(repo_path, locale, 'style')
    for rule in [rule for rule_list in [file.rules for file in dump.files] for rule in rule_list]:
        rows_from_rule(rule, repo_name, row_list, column)


# Also prints, because lazy
def compare_dfs(df_to, df_from, column):
    coll_to = collections.Counter(df_to[column])
    coll_from = collections.Counter(df_from[column])
    coll_to.subtract(coll_from)
    return "\n".join([f"{key},{value}" for key, value in coll_to.items()])


def summarize_by_column(df, column_name, logger):
    repo_groups = df.groupby(by='repo')
    summary = repo_groups[column_name].value_counts().reset_index(name='count')

    try:
        total_tts = repo_groups.apply(lambda x: x[(x[column_name] != 'tagged') & (x[
            column_name] != 'untagged')][column_name].count()).reset_index(name='count')
        total_tts[column_name] = "total"
    except TypeError as e:
        logger.warning(e.__str__() + "\n*total* is set to 0 for all repos")
        total_tts = pd.DataFrame([['os', 'total', 0], ['premium', 'total', 0]], columns=['repo', column_name, 'count'])

    unique_rules = repo_groups['id'].nunique().to_frame().reset_index()
    unique_rules = unique_rules.rename(columns={'id': 'count'})
    unique_rules[column_name] = "unique_rules"

    summary = pd.concat([summary, total_tts, unique_rules], axis=0).sort_values(['repo', column_name])
    return summary


def __main__():
    cli = CLI()
    logger = logger_wrapper(cli.parser.prog, cli.args.verbosity)
    logger.debug(f"Starting script...\nInvoked with options: {cli.args}")
    for column in ['tone_tags', 'writing_goals']:
        all_rows_to = []
        headers = ['id', column, 'repo']
        for locale in LOCALES:
            target_dir = os.path.join(cli.args.out_dir, locale, column)
            os.makedirs(target_dir, exist_ok=True)
            summary_filepath = os.path.join(target_dir, 'all_time_summary.txt')
            added_filepath = os.path.join(target_dir, 'added_this_quarter.txt')
            logger.debug(f"\nCompiling style stats for {locale} (by {column})...")
            rows_to = []
            rows_from = []
            for repo_name, repo_dir in REPOS.items():
                df_from_repo(cli.args.to_dir, repo_dir, repo_name, locale, rows_to, column)
                df_from_repo(cli.args.from_dir, repo_dir, repo_name, locale, rows_from, column)
            all_rows_to.extend(rows_to)
            df_to = DataFrame(rows_to, columns=headers)
            df_from = DataFrame(rows_from, columns=headers)
            locale_summary = summarize_by_column(df_to, column, logger)
            logger.debug(f"\n{locale} summary (by {column}):\n{locale_summary.to_string(index=False)}")
            open(summary_filepath, 'w').write(locale_summary.to_string(index=False))
            comparison = compare_dfs(df_to, df_from, column)
            logger.debug(f"\n{locale} comparison (by {column}):\n{comparison}")
            open(added_filepath, 'w').write(comparison)
        df_all_to = DataFrame(all_rows_to, columns=headers)
        all_dir = os.path.join(cli.args.out_dir, 'all', column)
        os.makedirs(all_dir, exist_ok=True)
        all_summary = summarize_by_column(df_all_to, column, logger)
        logger.debug(f"\nall locales summary (by {column}):\n{all_summary.to_string(index=False)}")
        all_filepath = os.path.join(all_dir, 'all_time_summary.txt')
        open(all_filepath, 'w').write(all_summary.to_string(index=False))


__main__()
