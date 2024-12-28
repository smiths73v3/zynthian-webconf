# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Web Configurator
#
# Audio Configuration Handler
#
# Copyright (C) 2017-2024 Fernando Moyano <jofemodo@zynthian.org>
#
# ********************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ********************************************************************

import os
import logging
import tornado.web
from collections import OrderedDict
from subprocess import check_output

import zynconf

from lib.zynthian_config_handler import ZynthianConfigHandler

# ------------------------------------------------------------------------------
# GIT Repository Configuration
# ------------------------------------------------------------------------------

class RepositoryHandler(ZynthianConfigHandler):
    zynthian_base_dir = os.environ.get('ZYNTHIAN_DIR', "/zynthian")
    stable_branch = os.environ.get('ZYNTHIAN_STABLE_BRANCH', "oram")
    testing_branch = os.environ.get('ZYNTHIAN_TESTING_BRANCH', "vangelis")

    repository_list = [
        ['zynthian-ui', False],
        ['zynthian-webconf', False],
        ['zyncoder', True],
        ['zynthian-sys', True],
        ['zynthian-data', True]
    ]

    @tornado.web.authenticated
    def get(self, errors=None):
        super().get("Software Version", self.get_config_info(), errors)

    @tornado.web.authenticated
    def post(self):
        postedConfig = tornado.escape.recursive_unicode(self.request.arguments)
        logging.info(postedConfig)
        try:
            version = postedConfig['ZYNTHIAN_VERSION'][0]
        except:
            version = self.stable_branch
        errors = {}

        changed_repos = 0
        if postedConfig["_command"] == ["SAVE"]:
            if version == "custom":
                for repitem in self.repository_list:
                    posted_key = f"ZYNTHIAN_REPO_{repitem[0]}"
                    stag = postedConfig[posted_key][0]
                    if self.set_repo_branch(repitem[0], stag):
                        changed_repos += 1
                stable_tag = ""
            else:
                for repitem in self.repository_list:
                    if version == self.stable_branch + "-last":
                        stag = self.get_repo_tag_list(repitem[0], filter=self.stable_branch + "-")[-1]
                    else:
                        stag = version
                    if self.set_repo_branch(repitem[0], stag):
                        changed_repos += 1
                if version == self.stable_branch + "-last":
                    stable_tag = "last"
                else:
                    stable_tag = version

            # Save stable tag configuration in config
            zynconf.save_config({
                "ZYNTHIAN_STABLE_TAG": stable_tag
            })

            #except Exception as err:
            #    logging.error(err)
            #    errors[posted_key] = err

                #self.redirect("/sw-update")
                #return
            #self.restart_ui_flag = True
            #self.restart_webconf_flag = True

        refresh = postedConfig["_changed"] == ["ZYNTHIAN_VERSION"] and postedConfig["ZYNTHIAN_VERSION"]==["custom"]
        config = self.get_config_info(version, refresh)
        if changed_repos > 0:
            config['ZYNTHIAN_MESSAGE'] = {
                'type': 'html',
                'content': "<div class='alert alert-success'>Some repo changed its branch. You may want to <a href='/sw-update'>update the software</a> for getting the latest changes.</div>"
            }
        super().get("Software Version", config, errors)

    def get_config_info(self, version=None, refresh=False):
        repo_branches = []
        for repitem in self.repository_list:
            branch = self.get_repo_current_branch(repitem[0])
            repo_branches.append(branch)
            if version is None and branch.split('.')[0] != repo_branches[0].split('.')[0]:
                version = "custom"
        if version is None and os.environ.get('ZYNTHIAN_STABLE_TAG', "") == "last":
            version = self.stable_branch + "-last"
        if version is None and repo_branches:
            version = repo_branches[0]

        version_options = {}
        if refresh:
            self.sync_repo("zynthian-sys")
        # Get stable tag list => WARNING! zynthian-sys rules!
        stags = self.get_repo_tag_list("zynthian-sys", filter=self.stable_branch + "-")
        #for stag in stags:
        #    version_options[stag] = f"stable (FROZEN {stag} => no updates!)"
        version_options[self.stable_branch + "-last"] = f"stable ({stags[-1]})"
        version_options[self.stable_branch] = f"staging ({self.stable_branch})"
        version_options[self.testing_branch] = f"testing ({self.testing_branch})"
        version_options["custom"] = "custom (individual selection for each repository - wait 10s for page to refresh after selecting)"

        config = {
            "ZYNTHIAN_VERSION": {
                'type': 'select',
                'title': 'Version',
                'value': version,
                'options': list(version_options.keys()),
                'option_labels': version_options,
                'refresh_on_change': True,
                'advanced': False
            }
        }
        if version == "custom":
            for i, repitem in enumerate(self.repository_list):
                if refresh and repitem != "zynthian-sys":
                    self.sync_repo(repitem[0])
                options = self.get_repo_tag_list(repitem[0])
                options += self.get_repo_branch_list(repitem[0])
                config[f"ZYNTHIAN_REPO_{repitem[0]}"] = {
                    'type': 'select',
                    'title': repitem[0],
                    'value': repo_branches[i],
                    'options': options,
                    'option_labels': OrderedDict([(opt, opt) for opt in options]),
                    'advanced': repitem[1]
                }
        config['_SPACER_'] = {
            'type': 'html',
            'content': "<br>"
        }
        return config

    def sync_repo(self, repo_name):
        repo_dir = self.zynthian_base_dir + "/" + repo_name
        check_output(f"git -C '{repo_dir}' fetch --tags --prune --prune-tags", shell=True)

    def get_repo_tag_list(self, repo_name, filter=None):
        result = []
        repo_dir = self.zynthian_base_dir + "/" + repo_name
        for bline in check_output(f"git -C '{repo_dir}' tag -l {filter}*", shell=True).splitlines():
            result.append(bline.decode("utf-8").strip())
        result.sort()
        return result

    def get_repo_branch_list(self, repo_name):
        result = []
        repo_dir = self.zynthian_base_dir + "/" + repo_name
        for bline in check_output(f"git -C '{repo_dir}' branch -a", shell=True).splitlines():
            bname = bline.decode("utf-8").strip()
            if bname.startswith("*"):
                bname = bname[2:]
            if bname.startswith("remotes/origin/"):
                bname = bname[15:]
            if "->" in bname:
                continue
            if bname not in result:
                result.append(bname)
        result.sort()
        return result

    def get_repo_current_branch(self, repo_name):
        repo_dir = self.zynthian_base_dir + "/" + repo_name
        for bline in check_output(f"git -C '{repo_dir}' branch | grep \* | cut -d ' ' -f2", encoding="utf-8", shell=True).splitlines():
            return bline

    def set_repo_branch(self, repo_name, branch_name):
        logging.info(f"Changing repository '{repo_name}' to branch '{branch_name}'")
        repo_dir = self.zynthian_base_dir + "/" + repo_name
        current_branch = self.get_repo_current_branch(repo_name)
        branches = check_output(f"git -C {repo_dir} branch -a", encoding="utf-8", shell=True).split("\n")
        tags = check_output(f"git -C {repo_dir} tag", encoding="utf-8", shell=True).split("\n")
        if branch_name in branches and branch_name in tags:
            check_output(f"git -C {repo_dir} branch -D {branch_name}", shell=True)
        if branch_name != current_branch:
            logging.info(f"... needs change: '{current_branch}' != '{branch_name}'")
            check_output(f"cd {repo_dir}; git checkout .; git clean -f; git checkout {branch_name}", shell=True)
            return True

# -----------------------------------------------------------------------------
