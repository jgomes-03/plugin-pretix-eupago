# -*- coding: utf-8 -*-
#
# Copyright © 2025 Jorge Gomes
# All rights reserved.
# This software is protected by a proprietary license.
# Modification, or distribution without express permission is prohibited.
#
from .apps import PluginApp, __version__

# Expose PretixPluginMeta for entry point
PretixPluginMeta = PluginApp.PretixPluginMeta
