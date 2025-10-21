# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Web Configurator
#
# Extra Packages handler
#
# Copyright (C) 2017-2025 Fernando Moyano <fernando@zynthian.org>
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
import sys
import logging
import tornado.web
from subprocess import check_output, STDOUT

import zynconf
from lib.zynthian_config_handler import ZynthianBasicHandler
import zyngine.zynthian_lv2 as zynthian_lv2

# sys.path.append(os.environ.get('ZYNTHIAN_UI_DIR'))

# ------------------------------------------------------------------------------
# Extra Packages Handler
# ------------------------------------------------------------------------------


class ExtraPacksHandler(ZynthianBasicHandler):
    data_dir = os.environ.get('ZYNTHIAN_DATA_DIR', "/zynthian/zynthian-data")
    my_data_dir = os.environ.get('ZYNTHIAN_MY_DATA_DIR', "/zynthian/zynthian-my-data")

    pack_info = {
        "Hydrogen_Drumkits": {
            "title": "Hydrogen Drumkits",
            "description": "A collection of drumkits, using the Hydrogen format, that you can load with Fabla and DrMr sampler.",
            "size": "145MB",
            "url": "https://musical-artifacts.com/artifacts/133",
            "recipe": "install_hydrogen_drumkits.sh",
            "restart_ui_flag": True,
            "installed": False
        },
        "IR_Collection": {
            "title": "IR Collection",
            "description": "A collection of impulse response files that you can load with the X42's IR convolver plugins and others. It includes several free IR libraries: ccgb, jezwells, l480, openairlib, samplicity-m7 and teufelsberg.",
            "size": "245MB",
            "url": "",
            "recipe": "install_ir-lv2-presets.sh",
            "restart_ui_flag": False,
            "installed": False
        },
        "Conners_IR_library": {
            "title": "Conners IR library",
            "description": "A collection of impulse response files that you can load with the X42's IR convolver plugins and others. A huge collection of well organized, experimental IRs, under MIT license. It will surprise you. ",
            "size": "650MB",
            "url": "https://github.com/itsmusician/IR-Library",
            "recipe": "install_Conners_IR_library.sh",
            "restart_ui_flag": False,
            "installed": False
        }
    }

    @tornado.web.authenticated
    def get(self, errors=None):
        config = self.get_config()
        if errors:
            logging.error("Installing Extra Package Failed: %s" % format(errors))
        super().get("extra_packs.html", "Extra Packages", config, errors)

    @tornado.web.authenticated
    def post(self):
        errors = None
        try:
            pack_name = self.get_argument('ZYNTHIAN_EXTRAPACKS_INSTALL')
        except:
            pack_name = None
            logging.error(f"No package to install!")
        if pack_name:
            try:
                errors = self.do_install_package(pack_name)
                self.restart_ui_flag = self.pack_info[pack_name]['restart_ui_flag']
            except Exception as err:
                errors = f"Can't install package {pack_name}"
                logging.error(err)
        self.get(errors)

    def do_install_package(self, pack_name):
        errors = None
        try:
            recipe = self.pack_info[pack_name]['recipe']
            res = check_output(f"$ZYNTHIAN_RECIPE_DIR/{recipe}", shell=True)
        except Exception as e:
            errors = f"Error installing '{pack_name}' => {e}"
        if errors:
            logging.error(errors)
        return errors

    def get_config(self):
        # Check if Hydrogen_Drumkits is installed
        if os.path.isdir(f"{self.data_dir}/soundfonts/hydrogen"):
            res = True
        else:
            res = False
        self.pack_info['Hydrogen_Drumkits']['installed'] = res

        # Check if IR_collection is installed
        subpacks = ["ccgb", "jezwells", "l480", "openairlib", "samplicity-m7", "teufelsberg"]
        res = True
        for subpack in subpacks:
            if not os.path.islink(f"{self.data_dir}/files/IRs/{subpack}"):
                res = False
                break
        self.pack_info['IR_Collection']['installed'] = res

        # Check if Conners_IR_library is installed
        if os.path.isdir(f"{self.data_dir}/files/IRs/Conners"):
            res = True
        else:
            res = False
        self.pack_info['Conners_IR_library']['installed'] = res

        return {'packs': self.pack_info}

# *****************************************************************************
