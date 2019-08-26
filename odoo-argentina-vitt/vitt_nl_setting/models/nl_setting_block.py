# -*- coding: utf-8 -*-
# 2018 Moogah

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class NLSettingBlock(models.TransientModel):
    _inherit = 'account.config.settings'
    _name = 'nl.setting.block'
