# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class NLSettingBlock(models.TransientModel):
    _inherit = 'nl.setting.block'

    add_anal_tags = fields.Boolean(string="Allow support for Analytic Tags",translate=True)
    add_obj_inv = fields.Boolean(string="Allow support for Objected Invoices",translate=True)

    @api.one
    def set_add_anal_tags(self):
        upd = self.env['base.module.update'].update_module()
        inst = self.env['ir.module.module'].search([('name','=','vitt_analytic_tags')])
        if inst:
            inst.button_immediate_install()
            conf = self.env['ir.config_parameter']
            conf.set_param('check.add_anal_tags', str(self.add_anal_tags))
        else:
            raise UserError(_("Module not found"))

    @api.model
    def get_default_add_anal_tags(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.add_anal_tags') == 'True':
            return {'add_anal_tags': True}
        else:
            return {'add_anal_tags': False}

    @api.one
    def set_add_obj_inv(self):
        upd = self.env['base.module.update'].update_module()
        inst = self.env['ir.module.module'].search([('name','=','vitt_objected_invoices')])
        if inst:
            inst.button_immediate_install()
            conf = self.env['ir.config_parameter']
            conf.set_param('check.add_obj_inv', str(self.add_obj_inv))
        else:
            raise UserError(_("Module not found"))

    @api.model
    def get_default_add_obj_inv(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.add_obj_inv') == 'True':
            return {'add_obj_inv': True}
        else:
            return {'add_obj_inv': False}
