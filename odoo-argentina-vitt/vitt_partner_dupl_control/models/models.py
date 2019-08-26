# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, Warning

class ResCompany(models.Model):
    _inherit = "res.company"

    main_id_category_ids = fields.Many2many('res.partner.id_category',string="Categorias")


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    main_id_category_ids = fields.Many2many(related='company_id.main_id_category_ids')



class ResPartnerId_number(models.Model):
    _inherit = 'res.partner.id_number'

    @api.model
    def create(self, vals):
        control_ids = self.env.user.company_id.main_id_category_ids.ids
        if 'name' in vals.keys() and 'category_id' in vals.keys():
            if vals['category_id'] in control_ids:
                partner = self.env['res.partner'].search([('id', '=', vals['partner_id'])])
                if not partner.parent_id:
                    if self.env['res.partner.id_number'].search([('name', '=', vals['name']), ('category_id', '=', vals['category_id'])]).ids:
                        raise ValidationError(_("NO puede haber 2 contactos con el mismo %s") % (vals['name']))
        return super(ResPartnerId_number, self).create(vals)

